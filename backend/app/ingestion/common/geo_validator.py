"""Geometry validation for hazard sources."""

from __future__ import annotations

from dataclasses import dataclass

INDIA_BBOX = {
    "min_lat": 6.0,
    "max_lat": 38.0,
    "min_lon": 68.0,
    "max_lon": 98.0,
}


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float


def is_valid_lat_lon(latitude: float | None, longitude: float | None) -> bool:
    if latitude is None or longitude is None:
        return False
    return -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0


def is_inside_bbox(latitude: float, longitude: float, bbox: dict[str, float]) -> bool:
    return (
        bbox["min_lat"] <= latitude <= bbox["max_lat"]
        and bbox["min_lon"] <= longitude <= bbox["max_lon"]
    )


def is_inside_india_bbox(latitude: float | None, longitude: float | None) -> bool:
    if latitude is None or longitude is None:
        return False
    if not is_valid_lat_lon(latitude, longitude):
        return False
    return is_inside_bbox(latitude, longitude, INDIA_BBOX)


def validate_point(
    latitude: float | None, longitude: float | None, *, require_india: bool = False
) -> GeoPoint | None:
    if latitude is None or longitude is None:
        return None
    if not is_valid_lat_lon(latitude, longitude):
        return None
    lat = latitude
    lon = longitude
    if require_india and not is_inside_india_bbox(lat, lon):
        return None
    return GeoPoint(latitude=lat, longitude=lon)
