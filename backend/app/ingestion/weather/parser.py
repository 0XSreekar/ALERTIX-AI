"""Open-Meteo rainfall parser."""

from __future__ import annotations

from datetime import UTC, datetime

from app.ingestion.common.dedupe import timestamp_bucket_id
from app.ingestion.common.schemas import NormalizedEvent


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def parse_open_meteo_rainfall(
    payload: dict, *, latitude: float, longitude: float
) -> list[NormalizedEvent]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    precipitation = hourly.get("precipitation") or []
    rain = hourly.get("rain") or []
    showers = hourly.get("showers") or []

    events: list[NormalizedEvent] = []
    for index, time_value in enumerate(times):
        observed_at = _parse_time(str(time_value))
        if observed_at is None:
            continue
        precipitation_mm = precipitation[index] if index < len(precipitation) else None
        rain_mm = rain[index] if index < len(rain) else None
        showers_mm = showers[index] if index < len(showers) else None
        intensity = float(precipitation_mm or 0.0)
        normalized_payload = {
            "provider": "open_meteo",
            "precipitation_mm": precipitation_mm,
            "rain_mm": rain_mm,
            "showers_mm": showers_mm,
        }
        events.append(
            NormalizedEvent(
                source="open_meteo",
                source_event_id=timestamp_bucket_id(
                    "open_meteo",
                    f"{latitude:.4f}",
                    f"{longitude:.4f}",
                    timestamp=observed_at,
                ),
                hazard_type="weather",
                event_timestamp=observed_at,
                latitude=latitude,
                longitude=longitude,
                confidence=0.8,
                raw_payload=normalized_payload,
                normalized_payload=normalized_payload,
                intensity=intensity,
            )
        )
    return events
