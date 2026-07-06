"""Async clients for official flood sources."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.ingestion.common.cache import AsyncTTLCache
from app.ingestion.common.retry_handler import RetryConfig, retry_async
from app.ingestion.flood.parser import detect_schema_drift
from app.ingestion.metrics import metrics as ingest_metrics
from app.logging import get_logger

log = get_logger(__name__)

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
    html = await fetch_html(settings.cwc_flood_dashboard_url)
    drift, recognised = detect_schema_drift(html)
    if drift:
        # CWC has renamed columns / changed layout. Surface to logs +
        # ingestion metrics so on-call can update the parser fixture.
        log.warning(
            "cwc_schema_drift_detected",
            url=settings.cwc_flood_dashboard_url,
            recognised_tokens=sorted(recognised),
            byte_size=len(html),
        )
        ingest_metrics.record(
            "cwc",
            fetched=0,
            parsed=0,
            valid=0,
            malformed=0,
            duplicates=0,
            stored=0,
            streamed=0,
            schema_drift=1,
        )
    return html


async def fetch_state_bulletins() -> list[tuple[str, str]]:
    settings = get_settings()
    bulletins: list[tuple[str, str]] = []
    for url in settings.state_flood_bulletin_url_list:
        bulletins.append((url, await fetch_html(url)))
    return bulletins
