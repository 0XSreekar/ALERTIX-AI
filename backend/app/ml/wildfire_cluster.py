"""DBSCAN-based wildfire hotspot clustering for FIRMS data."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
from sklearn.cluster import DBSCAN

_EARTH_RADIUS_KM = 6371.0


def _to_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _risk_level(size: int, avg_frp: float | None) -> str:
    if size > 50 or (avg_frp is not None and avg_frp > 200.0):
        return "extreme"
    if size >= 20 or (avg_frp is not None and avg_frp > 100.0):
        return "high"
    if size >= 5 or (avg_frp is not None and avg_frp > 30.0):
        return "moderate"
    return "low"


def _normalize_hotspots(
    hotspots: list[dict] | list[tuple[float, float, float]],
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in hotspots:
        lat: Any
        lon: Any
        frp: Any
        if isinstance(item, tuple):
            lat, lon, frp = item
            occurred_at = None
        else:
            lat = item.get("lat")
            lon = item.get("lon")
            frp = item.get("frp")
            occurred_at = item.get("occurred_at")
        lat_f = _to_float_or_none(lat)
        lon_f = _to_float_or_none(lon)
        if lat_f is None or lon_f is None:
            continue
        if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
            continue
        cleaned.append(
            {
                "lat": lat_f,
                "lon": lon_f,
                "frp": _to_float_or_none(frp),
                "occurred_at": occurred_at if isinstance(occurred_at, datetime) else None,
            }
        )
    return cleaned


def cluster_hotspots(
    hotspots: list[dict] | list[tuple[float, float, float]],
    eps_km: float = 5.0,
    min_samples: int = 3,
) -> list[dict]:
    """Cluster FIRMS hotspots with haversine DBSCAN and summarize each cluster."""
    cleaned = _normalize_hotspots(hotspots)
    if not cleaned:
        return []

    coords_rad = np.radians(np.array([[p["lat"], p["lon"]] for p in cleaned], dtype=float))
    labels = DBSCAN(
        eps=float(eps_km) / _EARTH_RADIUS_KM,
        min_samples=int(min_samples),
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(coords_rad)

    clusters: list[dict] = []
    for label in sorted({int(lbl) for lbl in labels if lbl != -1}):
        members = [
            cleaned[i] for i, member_label in enumerate(labels) if int(member_label) == label
        ]
        lats = [member["lat"] for member in members]
        lons = [member["lon"] for member in members]
        frps = [member["frp"] for member in members if member["frp"] is not None]
        times = [member["occurred_at"] for member in members if member["occurred_at"] is not None]
        avg_frp = float(np.mean(frps)) if frps else None
        size = len(members)
        clusters.append(
            {
                "centroid_lat": float(np.mean(lats)),
                "centroid_lon": float(np.mean(lons)),
                "size": size,
                "avg_frp": avg_frp,
                "risk_level": _risk_level(size, avg_frp),
                "earliest": min(times).isoformat() if times else "",
                "latest": max(times).isoformat() if times else "",
            }
        )
    clusters.sort(key=lambda c: c["size"], reverse=True)
    return clusters
