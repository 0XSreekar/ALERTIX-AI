"""USGS GeoJSON parser."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.ingestion.common.schemas import NormalizedEvent


def _confidence_from_status(status: str | None) -> float:
    if status == "reviewed":
        return 1.0
    if status == "automatic":
        return 0.7
    return 0.5


def parse_feature(feature: dict[str, Any]) -> NormalizedEvent | None:
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    if len(coords) < 2:
        return None

    time_ms = props.get("time")
    if time_ms is None:
        return None

    try:
        longitude = float(coords[0])
        latitude = float(coords[1])
        depth_km = float(coords[2]) if len(coords) > 2 and coords[2] is not None else None
        occurred_at = datetime.fromtimestamp(float(time_ms) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None

    source_event_id = str(feature.get("id") or props.get("code") or "").strip()
    if not source_event_id:
        return None

    magnitude = props.get("mag")
    mmi = props.get("mmi")
    normalized_payload = {
        "place": props.get("place"),
        "url": props.get("url"),
        "felt": props.get("felt"),
        "cdi": props.get("cdi"),
        "mmi": mmi,
        "alert": props.get("alert"),
        "status": props.get("status"),
        "tsunami": bool(props.get("tsunami", 0)),
        "sig": props.get("sig"),
        "net": props.get("net"),
        "type": props.get("type"),
        "title": props.get("title"),
    }

    return NormalizedEvent(
        source="usgs",
        source_event_id=source_event_id,
        hazard_type="earthquake",
        event_timestamp=occurred_at,
        latitude=latitude,
        longitude=longitude,
        confidence=_confidence_from_status(props.get("status")),
        raw_payload=feature,
        normalized_payload=normalized_payload,
        magnitude=float(magnitude) if magnitude is not None else None,
        depth_km=depth_km,
        intensity=float(mmi) if mmi is not None else None,
    )


def parse_geojson(payload: dict[str, Any]) -> list[NormalizedEvent]:
    features = payload.get("features") or []
    events: list[NormalizedEvent] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        parsed = parse_feature(feature)
        if parsed is not None:
            events.append(parsed)
    return events
