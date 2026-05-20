"""Linear cyclone track extrapolation from historical positions (Alertix AI spec §6.3)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

_EARTH_RADIUS_KM = 6371.0


def _is_finite_num(x: Any) -> bool:
    """Return True if x is a finite real number."""
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _to_float_or_none(x: Any) -> float | None:
    if not _is_finite_num(x):
        return None
    return float(x)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2.0) ** 2
    return 2.0 * _EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def _initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (degrees, 0-360) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlmb = math.radians(lon2 - lon1)
    y = math.sin(dlmb) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlmb)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _project_point(
    lat: float, lon: float, bearing_deg: float, distance_km: float
) -> tuple[float, float]:
    """Project a lat/lon point forward along a bearing by a great-circle distance."""
    ang = distance_km / _EARTH_RADIUS_KM
    brg = math.radians(bearing_deg)
    p1 = math.radians(lat)
    l1 = math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(ang) + math.cos(p1) * math.sin(ang) * math.cos(brg))
    l2 = l1 + math.atan2(
        math.sin(brg) * math.sin(ang) * math.cos(p1),
        math.cos(ang) - math.sin(p1) * math.sin(p2),
    )
    lat2 = math.degrees(p2)
    lon2 = ((math.degrees(l2) + 540.0) % 360.0) - 180.0
    return lat2, lon2


def _impact_radius_km(max_wind_kmh: float) -> float:
    """Map maximum sustained wind to an impact radius in km (IMD-style buckets)."""
    if max_wind_kmh >= 221.0:
        return 250.0
    if max_wind_kmh >= 167.0:
        return 200.0
    if max_wind_kmh >= 118.0:
        return 150.0
    if max_wind_kmh >= 89.0:
        return 100.0
    return 50.0


def extrapolate_track(
    positions: list[dict],
    horizon_hours: int = 12,
    step_hours: int = 3,
) -> dict:
    """Linearly extrapolate a cyclone track from recent observed positions."""
    empty_result: dict = {
        "extrapolated": [],
        "speed_kmh": 0.0,
        "bearing_deg": 0.0,
        "impact_radius_km": 0.0,
    }

    if not positions:
        return empty_result

    cleaned: list[dict] = []
    for p in positions:
        lat = p.get("lat")
        lon = p.get("lon")
        occurred_at = p.get("occurred_at")
        lat_f = _to_float_or_none(lat)
        lon_f = _to_float_or_none(lon)
        if lat_f is None or lon_f is None:
            continue
        if not isinstance(occurred_at, datetime):
            continue
        wind = p.get("wind_kmh")
        wind_f = _to_float_or_none(wind)
        cleaned.append(
            {
                "lat": lat_f,
                "lon": lon_f,
                "occurred_at": occurred_at,
                "wind_kmh": wind_f,
            }
        )

    if len(cleaned) < 2:
        return empty_result

    cleaned.sort(key=lambda x: x["occurred_at"])
    p_prev = cleaned[-2]
    p_last = cleaned[-1]

    dt_hours = (p_last["occurred_at"] - p_prev["occurred_at"]).total_seconds() / 3600.0
    if dt_hours <= 0:
        return empty_result

    distance_km = _haversine_km(p_prev["lat"], p_prev["lon"], p_last["lat"], p_last["lon"])
    speed_kmh = distance_km / dt_hours
    bearing_deg = _initial_bearing_deg(p_prev["lat"], p_prev["lon"], p_last["lat"], p_last["lon"])

    winds = [p["wind_kmh"] for p in cleaned if p["wind_kmh"] is not None]
    max_wind = max(winds) if winds else 0.0
    impact_radius_km = _impact_radius_km(max_wind)

    extrapolated: list[dict] = []
    step = max(1, int(step_hours))
    horizon = max(0, int(horizon_hours))
    offsets = list(range(step, horizon + 1, step))

    for offset in offsets:
        forward_km = speed_kmh * float(offset)
        lat2, lon2 = _project_point(p_last["lat"], p_last["lon"], bearing_deg, forward_km)
        forecast_at = p_last["occurred_at"] + timedelta(hours=offset)
        extrapolated.append(
            {
                "lat": lat2,
                "lon": lon2,
                "forecast_at": forecast_at.isoformat(),
                "hour_offset": int(offset),
            }
        )

    return {
        "extrapolated": extrapolated,
        "speed_kmh": float(speed_kmh),
        "bearing_deg": float(bearing_deg),
        "impact_radius_km": float(impact_radius_km),
    }
