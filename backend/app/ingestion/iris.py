"""IRIS FDSN — waveform and station data access via HTTP (ObsPy used in Phase 2 training)."""

import httpx

from app.logging import get_logger

log = get_logger(__name__)

IRIS_EVENT_URL = "https://service.iris.edu/fdsnws/event/1/query"


async def fetch_iris_events(
    min_lat: float = 5.0,
    max_lat: float = 40.0,
    min_lon: float = 65.0,
    max_lon: float = 100.0,
    min_magnitude: float = 3.0,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """Query IRIS FDSN event service for Indian subcontinent seismicity.
    Returns QuakeML-style GeoJSON when format=geojson is supported,
    or raw text. Used for backfill and historical analysis.
    """
    params: dict[str, str | int | float] = {
        "format": "text",
        "minlat": min_lat,
        "maxlat": max_lat,
        "minlon": min_lon,
        "maxlon": max_lon,
        "minmagnitude": min_magnitude,
        "orderby": "time-asc",
    }
    if start_time:
        params["starttime"] = start_time
    if end_time:
        params["endtime"] = end_time

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(IRIS_EVENT_URL, params=params)
        resp.raise_for_status()
        return {"raw_text": resp.text, "status_code": resp.status_code}
