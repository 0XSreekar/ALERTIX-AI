"""Async clients for cyclone bulletin pages."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.ingestion.common.cache import AsyncTTLCache
from app.ingestion.common.retry_handler import RetryConfig, retry_async

IMD_RSMC_URL = "https://rsmcnewdelhi.imd.gov.in/index.php"
JTWC_URL = "https://www.metoc.navy.mil/jtwc/jtwc.html"

_cache: AsyncTTLCache[str] = AsyncTTLCache(ttl_seconds=120)


async def fetch_text(url: str) -> str:
    cached = await _cache.get(url)
    if cached is not None:
        return cached

    async def _request() -> str:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=8.0),
            follow_redirects=True,
            headers={"User-Agent": "AlertixAI/1.0 ingestion"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    text = await retry_async(_request, config=RetryConfig(attempts=3, base_delay_seconds=1.0))
    await _cache.set(url, text)
    return text


def _discover_links(base_url: str, html: str, keywords: tuple[str, ...]) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for link in soup.find_all("a", href=True):
        label = link.get_text(" ", strip=True).lower()
        href = str(link["href"])
        candidate = f"{label} {href}".lower()
        if any(keyword in candidate for keyword in keywords):
            url = urljoin(base_url, href)
            if url not in urls:
                urls.append(url)
    return urls[:10]


async def fetch_imd_bulletins() -> list[tuple[str, str]]:
    index_html = await fetch_text(IMD_RSMC_URL)
    urls = _discover_links(
        IMD_RSMC_URL,
        index_html,
        ("cyclone", "bulletin", "warning", "rsmc", "national"),
    )
    if IMD_RSMC_URL not in urls:
        urls.insert(0, IMD_RSMC_URL)

    pages: list[tuple[str, str]] = []
    for url in urls:
        if url.lower().endswith(".pdf"):
            continue
        pages.append((url, await fetch_text(url)))
    return pages


async def fetch_jtwc_bulletins() -> list[tuple[str, str]]:
    index_html = await fetch_text(JTWC_URL)
    urls = _discover_links(
        JTWC_URL,
        index_html,
        ("io", "arb", "bb", "warning", ".txt", "north indian ocean"),
    )
    pages: list[tuple[str, str]] = []
    for url in urls:
        if not (url.lower().endswith(".txt") or "products" in url.lower()):
            continue
        pages.append((url, await fetch_text(url)))
    return pages
