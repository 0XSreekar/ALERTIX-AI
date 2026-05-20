"""Async client for the official USGS GeoJSON earthquake feeds."""

from __future__ import annotations

import httpx

from app.ingestion.common.cache import AsyncTTLCache
from app.ingestion.common.retry_handler import RetryConfig, retry_async

USGS_FEEDS = {
    "all_hour": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "all_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "significant_week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson",
}

_cache: AsyncTTLCache[dict] = AsyncTTLCache(ttl_seconds=20)


async def fetch_usgs_geojson(feed: str = "all_hour") -> dict:
    url = USGS_FEEDS.get(feed, USGS_FEEDS["all_hour"])
    cached = await _cache.get(url)
    if cached is not None:
        return cached

    async def _request() -> dict:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "AlertixAI/1.0 ingestion"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    data = await retry_async(_request, config=RetryConfig(attempts=3))
    await _cache.set(url, data)
    return data
