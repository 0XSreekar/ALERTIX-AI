"""Async NASA FIRMS area API client scoped to India."""

from __future__ import annotations

import httpx

from app.ingestion.common.geo_validator import INDIA_BBOX
from app.ingestion.common.retry_handler import RetryConfig, retry_async

FIRMS_AREA_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{area}/{day_range}"
)
FIRMS_SOURCES = (
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT",
)


def india_area_coordinates() -> str:
    return (
        f"{INDIA_BBOX['min_lon']},{INDIA_BBOX['min_lat']},"
        f"{INDIA_BBOX['max_lon']},{INDIA_BBOX['max_lat']}"
    )


async def fetch_firms_csv(
    map_key: str, *, source: str = "VIIRS_SNPP_NRT", day_range: int = 1
) -> str:
    if source not in FIRMS_SOURCES:
        raise ValueError(f"Unsupported FIRMS source: {source}")
    if day_range < 1 or day_range > 5:
        raise ValueError("FIRMS day_range must be between 1 and 5")

    url = FIRMS_AREA_URL.format(
        key=map_key,
        source=source,
        area=india_area_coordinates(),
        day_range=day_range,
    )

    async def _request() -> str:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(45.0, connect=10.0),
            follow_redirects=True,
            headers={"User-Agent": "AlertixAI/1.0 ingestion"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    return await retry_async(_request, config=RetryConfig(attempts=3, base_delay_seconds=1.0))
