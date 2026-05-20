"""Async clients for official flood sources."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.ingestion.common.cache import AsyncTTLCache
from app.ingestion.common.retry_handler import RetryConfig, retry_async

_html_cache: AsyncTTLCache[str] = AsyncTTLCache(ttl_seconds=120)


async def fetch_html(url: str) -> str:
    cached = await _html_cache.get(url)
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

    html = await retry_async(_request, config=RetryConfig(attempts=3, base_delay_seconds=1.0))
    await _html_cache.set(url, html)
    return html


async def fetch_cwc_dashboard() -> str:
    settings = get_settings()
    return await fetch_html(settings.cwc_flood_dashboard_url)


async def fetch_state_bulletins() -> list[tuple[str, str]]:
    settings = get_settings()
    bulletins: list[tuple[str, str]] = []
    for url in settings.state_flood_bulletin_url_list:
        bulletins.append((url, await fetch_html(url)))
    return bulletins
