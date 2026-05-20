"""Open-Meteo — precipitation and weather data (no key, no rate limit)."""

import httpx

from app.logging import get_logger

log = get_logger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"


async def get_rainfall_forecast(lat: float, lon: float, hours: int = 72) -> dict:
    """Fetch hourly precipitation forecast for a point. Returns raw API response."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,temperature_2m,relative_humidity_2m,wind_speed_10m",
        "forecast_days": max(1, hours // 24),
        "timezone": "UTC",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_rainfall_history(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """Fetch historical hourly rainfall. Dates as 'YYYY-MM-DD'."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "UTC",
    }
    url = "https://archive-api.open-meteo.com/v1/archive"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def get_wind_data(lat: float, lon: float) -> dict:
    """Fetch current wind fields for cyclone tab."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,pressure_msl",
        "forecast_days": 3,
        "timezone": "UTC",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()
