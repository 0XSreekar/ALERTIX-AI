"""Deterministic first-pass risk scoring for live hazard events."""

from __future__ import annotations

from typing import Any

from app.processing.events import ProcessingEvent
from app.processing.state import AlertTier


def _tier(score: float) -> AlertTier:
    if score >= 0.85:
        return AlertTier.CRITICAL
    if score >= 0.65:
        return AlertTier.HIGH
    if score >= 0.35:
        return AlertTier.MEDIUM
    return AlertTier.LOW


def _value(event: ProcessingEvent, key: str) -> Any:
    return event.raw_payload.get(key) or event.normalized.get(key)


def score_event(event: ProcessingEvent) -> tuple[float, AlertTier]:
    hazard_type = event.hazard_type.lower()
    score = 0.1

    if hazard_type == "earthquake":
        magnitude = event.magnitude or 0.0
        depth = event.depth_km if event.depth_km is not None else 70.0
        magnitude_score = min(1.0, max(0.0, (magnitude - 3.0) / 4.5))
        shallow_bonus = 0.18 if depth <= 20 else 0.08 if depth <= 70 else 0.0
        score = min(1.0, magnitude_score + shallow_bonus)
    elif hazard_type == "flood":
        severity = event.raw_payload.get("severity") or event.normalized.get("severity")
        water_level = event.raw_payload.get("water_level_m") or event.normalized.get(
            "water_level_m"
        )
        danger_level = event.raw_payload.get("danger_level_m") or event.normalized.get(
            "danger_level_m"
        )
        try:
            score = min(1.0, max(0.0, float(severity) / 3.0))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            try:
                score = 0.25 + max(0.0, float(water_level) - float(danger_level)) / 2.0  # type: ignore[arg-type]
            except (TypeError, ValueError):
                score = 0.25
    elif hazard_type == "wildfire":
        frp = _value(event, "frp")
        confidence = (
            event.confidence if event.confidence is not None else _value(event, "confidence")
        )
        try:
            score = min(1.0, float(frp) / 80.0)
        except (TypeError, ValueError):
            score = 0.25
        try:
            score = min(1.0, score + max(0.0, float(confidence)) / 1000.0)
        except (TypeError, ValueError):
            pass
    elif hazard_type == "cyclone":
        wind = _value(event, "wind_speed_kmh") or _value(event, "wind_kmh")
        pressure = _value(event, "pressure_hpa")
        try:
            score = min(1.0, float(wind) / 221.0)
        except (TypeError, ValueError):
            score = 0.35
        try:
            score = min(1.0, score + max(0.0, 1000.0 - float(pressure)) / 250.0)
        except (TypeError, ValueError):
            pass
    else:
        score = 0.2

    return round(max(0.0, min(1.0, score)), 4), _tier(score)
