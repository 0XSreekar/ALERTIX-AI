"""Async Open-Meteo client for rainfall ingestion."""

from __future__ import annotations

import httpx

from app.ingestion.common.retry_handler import RetryConfig, retry_async

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


async def fetch_open_meteo_rainfall(
    latitude: float, longitude: float, *, forecast_days: int = 1
) -> dict:
    params: dict[str, str | int | float] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation,rain,showers",
        "timezone": "UTC",
        "forecast_days": forecast_days,
    }

    async def _request() -> dict:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "AlertixAI/1.0 ingestion"},
        ) as client:
            response = await client.get(OPEN_METEO_FORECAST_URL, params=params)
            response.raise_for_status()
            return response.json()

    return await retry_async(_request, config=RetryConfig(attempts=3))
