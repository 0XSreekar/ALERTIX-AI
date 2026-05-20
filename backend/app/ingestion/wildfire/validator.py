"""Validation rules for NASA FIRMS hotspots."""

from __future__ import annotations

from app.ingestion.common.geo_validator import validate_point
from app.ingestion.common.schemas import NormalizedEvent


def validate_wildfire(event: NormalizedEvent) -> bool:
    if event.hazard_type != "wildfire":
        return False
    if not event.source_event_id:
        return False
    if validate_point(event.latitude, event.longitude, require_india=True) is None:
        return False
    if event.intensity is not None and event.intensity < 0:
        return False
    return True
