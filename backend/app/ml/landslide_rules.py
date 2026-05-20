"""Landslide risk: IMD intensity-duration rainfall thresholds + GSI zone lookup."""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# GSI hazard zone classification by approximate state bounding boxes
# Source: Geological Survey of India landslide hazard zonation
# ---------------------------------------------------------------------------
# (min_lat, max_lat, min_lon, max_lon, state_name, gsi_zone)
_STATE_BOXES: list[tuple[float, float, float, float, str, str]] = [
    # Very high hazard — Himalayan and NE states
    (28.7, 31.5, 77.5, 81.0, "Uttarakhand", "very_high"),
    (30.4, 33.5, 75.0, 79.5, "Himachal Pradesh", "very_high"),
    (32.0, 37.1, 73.5, 80.0, "Jammu & Kashmir / Ladakh", "very_high"),
    (26.5, 29.5, 88.0, 97.5, "Sikkim / Arunachal Pradesh", "very_high"),
    (24.0, 28.3, 89.5, 97.5, "Assam / Meghalaya", "very_high"),
    (23.0, 25.4, 92.0, 96.5, "Manipur / Mizoram", "very_high"),
    (25.0, 27.5, 93.0, 96.0, "Nagaland / Tripura", "very_high"),
    # High hazard — Western Ghats and hill states
    (8.0, 12.8, 76.0, 77.5, "Kerala (Western Ghats)", "high"),
    (15.0, 22.0, 73.0, 74.5, "Maharashtra (Western Ghats)", "high"),
    (12.0, 15.5, 74.0, 75.5, "Goa / Karnataka (Western Ghats)", "high"),
    (10.0, 12.5, 76.5, 78.0, "Tamil Nadu (Nilgiris)", "high"),
    # Moderate hazard
    (21.0, 25.5, 84.0, 87.5, "Jharkhand", "moderate"),
    (21.5, 27.5, 85.0, 89.5, "West Bengal (hills / Darjeeling)", "moderate"),
    (13.5, 19.5, 77.0, 84.0, "Andhra Pradesh (Eastern Ghats)", "moderate"),
    (20.0, 24.5, 80.0, 84.5, "Chhattisgarh / Odisha", "moderate"),
]


def _gsi_zone_for(lat: float, lon: float) -> str:
    """Return GSI landslide hazard zone for a point. Defaults to 'low'."""
    for min_lat, max_lat, min_lon, max_lon, _name, zone in _STATE_BOXES:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return zone
    return "low"


# ---------------------------------------------------------------------------
# IMD intensity-duration rainfall thresholds (published guidelines)
# Reference: IMD Cyclone Warning Division + NDMA guidelines
# ---------------------------------------------------------------------------
# Cumulative rainfall (mm) thresholds by GSI zone for landslide trigger
_THRESHOLD_MM: dict[str, float] = {
    "very_high": 100.0,   # 24h cumulative rainfall trigger
    "high": 150.0,
    "moderate": 200.0,
    "low": 300.0,
}

# Risk level matrix based on (zone, threshold_exceeded)
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


@dataclass
class LandslideRuleResult:
    gsi_zone: str
    threshold_mm: float
    cumulative_rainfall_mm: float | None
    rainfall_threshold_exceeded: bool
    risk_level: str


def evaluate(lat: float, lon: float, cumulative_rainfall_mm: float | None) -> LandslideRuleResult:
    """Apply IMD threshold rules for the given location and rainfall.

    Args:
        lat, lon: WGS84 coordinates
        cumulative_rainfall_mm: 24h accumulated rainfall (None = unavailable)

    Returns:
        LandslideRuleResult with zone classification and risk assessment.
    """
    zone = _gsi_zone_for(lat, lon)
    threshold = _THRESHOLD_MM[zone]
    exceeded = (cumulative_rainfall_mm is not None) and (cumulative_rainfall_mm >= threshold)
    risk = _RISK_MATRIX[(zone, exceeded)]
    return LandslideRuleResult(
        gsi_zone=zone,
        threshold_mm=threshold,
        cumulative_rainfall_mm=cumulative_rainfall_mm,
        rainfall_threshold_exceeded=exceeded,
        risk_level=risk,
    )
