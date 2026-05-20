"""Landslide risk rules from rainfall thresholds and GSI-style hazard zones."""

from __future__ import annotations

from dataclasses import dataclass

_STATE_BOXES: list[tuple[float, float, float, float, str, str]] = [
    (28.7, 31.5, 77.5, 81.0, "Uttarakhand", "very_high"),
    (30.4, 33.5, 75.0, 79.5, "Himachal Pradesh", "very_high"),
    (32.0, 37.1, 73.5, 80.0, "Jammu & Kashmir / Ladakh", "very_high"),
    (26.5, 29.5, 88.0, 97.5, "Sikkim / Arunachal Pradesh", "very_high"),
    (24.0, 28.3, 89.5, 97.5, "Assam / Meghalaya", "very_high"),
    (23.0, 25.4, 92.0, 96.5, "Manipur / Mizoram", "very_high"),
    (25.0, 27.5, 93.0, 96.0, "Nagaland / Tripura", "very_high"),
    (8.0, 12.8, 76.0, 77.5, "Kerala (Western Ghats)", "high"),
    (15.0, 22.0, 73.0, 74.5, "Maharashtra (Western Ghats)", "high"),
    (12.0, 15.5, 74.0, 75.5, "Goa / Karnataka (Western Ghats)", "high"),
    (10.0, 12.5, 76.5, 78.0, "Tamil Nadu (Nilgiris)", "high"),
    (21.0, 25.5, 84.0, 87.5, "Jharkhand", "moderate"),
    (21.5, 27.5, 85.0, 89.5, "West Bengal (hills / Darjeeling)", "moderate"),
    (13.5, 19.5, 77.0, 84.0, "Andhra Pradesh (Eastern Ghats)", "moderate"),
    (20.0, 24.5, 80.0, 84.5, "Chhattisgarh / Odisha", "moderate"),
]

_THRESHOLD_MM: dict[str, float] = {
    "very_high": 100.0,
    "high": 150.0,
    "moderate": 200.0,
    "low": 300.0,
}

_RISK_MATRIX: dict[tuple[str, bool], str] = {
    ("very_high", True): "extreme",
    ("very_high", False): "elevated",
    ("high", True): "high",
    ("high", False): "moderate",
    ("moderate", True): "moderate",
    ("moderate", False): "low",
    ("low", True): "low",
    ("low", False): "low",
}


@dataclass(slots=True)
class LandslideRuleResult:
    gsi_zone: str
    threshold_mm: float
    cumulative_rainfall_mm: float | None
    rainfall_threshold_exceeded: bool
    risk_level: str


def _gsi_zone_for(lat: float, lon: float) -> str:
    for min_lat, max_lat, min_lon, max_lon, _name, zone in _STATE_BOXES:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return zone
    return "low"


def evaluate(lat: float, lon: float, cumulative_rainfall_mm: float | None) -> LandslideRuleResult:
    zone = _gsi_zone_for(lat, lon)
    threshold = _THRESHOLD_MM[zone]
    exceeded = cumulative_rainfall_mm is not None and cumulative_rainfall_mm >= threshold
    return LandslideRuleResult(
        gsi_zone=zone,
        threshold_mm=threshold,
        cumulative_rainfall_mm=cumulative_rainfall_mm,
        rainfall_threshold_exceeded=exceeded,
        risk_level=_RISK_MATRIX[(zone, exceeded)],
    )


def assess_landslide_risk(rainfall_hourly: list[float], gsi_zone: str | None = None) -> dict:
    zone = gsi_zone or "moderate"
    if zone not in _THRESHOLD_MM:
        zone = "low"
    cumulative = round(sum(float(v or 0.0) for v in rainfall_hourly[:72]), 2)
    threshold = _THRESHOLD_MM[zone]
    exceeded = cumulative >= threshold
    return {
        "gsi_zone": zone,
        "threshold_exceeded": exceeded,
        "cumulative_rainfall_mm": cumulative,
        "threshold_mm": threshold,
        "risk_level": _RISK_MATRIX[(zone, exceeded)],
    }
