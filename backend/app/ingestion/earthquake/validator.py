"""Validation rules for normalized USGS earthquake events."""

from __future__ import annotations

from app.ingestion.common.geo_validator import validate_point
from app.ingestion.common.schemas import NormalizedEvent


def validate_earthquake(event: NormalizedEvent) -> bool:
    if event.hazard_type != "earthquake" or event.source != "usgs":
        return False
    if not event.source_event_id:
        return False
    if validate_point(event.latitude, event.longitude) is None:
        return False
    if event.magnitude is not None and not (-2.0 <= event.magnitude <= 12.0):
        return False
    if event.depth_km is not None and not (-20.0 <= event.depth_km <= 800.0):
        return False
    return True
