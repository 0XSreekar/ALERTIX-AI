"""Spatial resolver for Indian disaster context."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_RIVERS: tuple[tuple[str, str, str, float, float], ...] = (
    ("Godavari", "Godavari", "Bhadradri Kothagudem", 17.667, 80.883),
    ("Krishna", "Krishna", "Vijayawada", 16.506, 80.648),
    ("Musi", "Krishna", "Hyderabad", 17.385, 78.486),
    ("Pennar", "Pennar", "Nellore", 14.442, 79.986),
    ("Tungabhadra", "Krishna", "Kurnool", 15.828, 78.037),
    ("Sabari", "Godavari", "Alluri Sitharama Raju", 17.750, 81.450),
    ("Manjira", "Godavari", "Sangareddy", 17.629, 77.950),
    ("Pranhita", "Godavari", "Mancherial", 18.875, 79.900),
)


@dataclass(frozen=True, slots=True)
class SpatialResolution:
    nearest_river_name: str
    basin_name: str
    district_name: str
    distance_to_river_km: float


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def resolve_static(lat: float, lon: float) -> SpatialResolution:
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude/longitude out of range")
    river, basin, district, distance = min(
        (
            (river, basin, district, _haversine_km(lat, lon, r_lat, r_lon))
            for river, basin, district, r_lat, r_lon in _RIVERS
        ),
        key=lambda item: item[3],
    )
    return SpatialResolution(
        nearest_river_name=river,
        basin_name=basin,
        district_name=district,
        distance_to_river_km=round(distance, 3),
    )


async def resolve_with_postgis(session: AsyncSession, lat: float, lon: float) -> SpatialResolution:
    result = await session.execute(
        text("""
            SELECT station_name, river_name, basin, district,
                   ST_Distance(
                       location,
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                   ) / 1000.0 AS distance_km
            FROM river_gauges
            WHERE location IS NOT NULL
            ORDER BY location <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            LIMIT 1
        """),
        {"lat": lat, "lon": lon},
    )
    row = result.fetchone()
    if not row:
        return resolve_static(lat, lon)
    return SpatialResolution(
        nearest_river_name=row.river_name or row.station_name,
        basin_name=row.basin or "unknown",
        district_name=row.district or "unknown",
        distance_to_river_km=round(float(row.distance_km), 3),
    )


class SpatialResolver:
    def predict(self, lat: float, lon: float) -> SpatialResolution:
        return resolve_static(lat, lon)
