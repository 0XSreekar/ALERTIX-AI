"""Cyclone bulletin parsers and normalizers."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from app.ingestion.common.dedupe import stable_payload_id
from app.ingestion.common.schemas import NormalizedEvent


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(payload: str) -> str:
    if "<html" in payload.lower() or "<body" in payload.lower():
        return _clean(BeautifulSoup(payload, "lxml").get_text(" "))
    return _clean(payload)


def _coords(text: str) -> list[tuple[float, float]]:
    matches = re.finditer(
        r"(?P<lat>\d+(?:\.\d+)?)\s*(?P<lat_dir>[NS])[, ]+"
        r"(?P<lon>\d+(?:\.\d+)?)\s*(?P<lon_dir>[EW])",
        text,
        re.IGNORECASE,
    )
    coords: list[tuple[float, float]] = []
    for match in matches:
        lat = float(match.group("lat"))
        lon = float(match.group("lon"))
        if match.group("lat_dir").upper() == "S":
            lat *= -1
        if match.group("lon_dir").upper() == "W":
            lon *= -1
        coords.append((lat, lon))
    return coords


def _wind_kmh(text: str) -> float | None:
    match = re.search(r"(\d{2,3})\s*(kt|kts|knots|kmph|km/h|kmh)", text, re.IGNORECASE)
    if not match:
        return None
    speed = float(match.group(1))
    unit = match.group(2).lower()
    if unit in {"kt", "kts", "knots"}:
        return round(speed * 1.852, 1)
    return speed


def _pressure_hpa(text: str) -> float | None:
    match = re.search(
        r"(?:pressure|central pressure)[^\d]{0,40}(\d{3,4})\s*(?:hpa|mb)", text, re.IGNORECASE
    )
    return float(match.group(1)) if match else None


def _movement(text: str) -> str | None:
    match = re.search(
        r"(?:moving|moved|movement)[^.,;:]{0,80}?(north-northeast|north-northwest|south-southeast|"
        r"south-southwest|northeast|northwest|southeast|southwest|north|south|east|west)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).lower() if match else None


def _storm_name(text: str) -> str | None:
    patterns = (
        r"(?:tropical cyclone|tc)\s+\d+[a-z]?\s+\(([A-Z0-9-]+)\)",
        r"(?:cyclonic storm|severe cyclonic storm|very severe cyclonic storm|tropical cyclone)\s+([A-Z0-9-]+)",
        r"\bCYCLONE\s+([A-Z0-9-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" -").upper()
    return None


def _warning_level(text: str, wind_speed_kmh: float | None) -> str:
    lowered = text.lower()
    if "very severe" in lowered or "extremely severe" in lowered:
        return "emergency"
    if "cyclone warning" in lowered or (wind_speed_kmh is not None and wind_speed_kmh >= 89):
        return "warning"
    if "depression" in lowered or "watch" in lowered:
        return "watch"
    return "info"


class ForecastNormalizer:
    def normalize_path(self, coords: list[tuple[float, float]]) -> list[dict[str, float]]:
        return [{"latitude": lat, "longitude": lon} for lat, lon in coords[:12]]


class CycloneParser:
    def __init__(self) -> None:
        self.forecast_normalizer = ForecastNormalizer()

    def parse_text(
        self,
        *,
        source: str,
        url: str,
        payload: str,
        fetched_at: datetime | None = None,
    ) -> NormalizedEvent | None:
        fetched_at = fetched_at or datetime.now(UTC)
        text = _plain_text(payload)
        if not any(
            keyword in text.lower() for keyword in ("cyclone", "depression", "storm", "warning")
        ):
            return None

        coords = _coords(text)
        current_position = coords[0] if coords else (None, None)
        lat, lon = current_position
        wind_speed_kmh = _wind_kmh(text)
        pressure = _pressure_hpa(text)
        name = _storm_name(text)
        movement_direction = _movement(text)
        warning_level = _warning_level(text, wind_speed_kmh)
        forecast_path = self.forecast_normalizer.normalize_path(coords)
        normalized_payload: dict[str, Any] = {
            "storm_name": name,
            "wind_speed_kmh": wind_speed_kmh,
            "pressure_hpa": pressure,
            "movement_direction": movement_direction,
            "forecast_path": forecast_path,
            "warning_level": warning_level,
            "url": url,
            "summary": text[:1500],
        }
        return NormalizedEvent(
            source=source,
            source_event_id=stable_payload_id(source, {"url": url, "body": text[:2000]}),
            hazard_type="cyclone",
            event_timestamp=fetched_at,
            latitude=lat,
            longitude=lon,
            confidence=0.75 if source == "imd_rsmc" else 0.65,
            raw_payload={"url": url, "text": text[:6000]},
            normalized_payload=normalized_payload,
            intensity=wind_speed_kmh,
        )


class StormTracker:
    def latest_by_name(self, events: list[NormalizedEvent]) -> dict[str, NormalizedEvent]:
        latest: dict[str, NormalizedEvent] = {}
        for event in events:
            name = str(event.normalized_payload.get("storm_name") or event.source_event_id)
            current = latest.get(name)
            if current is None or event.event_timestamp > current.event_timestamp:
                latest[name] = event
        return latest
