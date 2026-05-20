"""Validation for cyclone bulletins."""

from __future__ import annotations

from app.ingestion.common.geo_validator import is_inside_bbox, validate_point
from app.ingestion.common.schemas import NormalizedEvent

NORTH_INDIAN_OCEAN_BBOX = {
    "min_lat": -5.0,
    "max_lat": 30.0,
    "min_lon": 40.0,
    "max_lon": 105.0,
}


def validate_cyclone(event: NormalizedEvent) -> bool:
    if event.hazard_type != "cyclone":
        return False
    if not event.source_event_id:
        return False
    point = validate_point(event.latitude, event.longitude)
    if point is None:
        return False
    if not is_inside_bbox(point.latitude, point.longitude, NORTH_INDIAN_OCEAN_BBOX):
        return False
    if event.intensity is not None and event.intensity < 0:
        return False
    return True
