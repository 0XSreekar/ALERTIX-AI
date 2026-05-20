"""CWC river-gauge and official bulletin parsers."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from app.ingestion.common.dedupe import timestamp_bucket_id
from app.ingestion.common.schemas import NormalizedEvent


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_datetime(row: dict[str, str], fallback: datetime) -> datetime:
    date_text = row.get("date") or row.get("observed date") or row.get("forecast date")
    time_text = row.get("time") or row.get("observed time") or row.get("forecast time") or "0000"
    if not date_text:
        return fallback

    for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y %H%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H%M"):
        try:
            return datetime.strptime(f"{date_text} {time_text}", fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return fallback


def _row_dict(headers: list[str], values: list[str]) -> dict[str, str]:
    return {
        _clean(header).lower(): _clean(values[index]) if index < len(values) else ""
        for index, header in enumerate(headers)
        if _clean(header)
    }


def _extract_coords(row: dict[str, str]) -> tuple[float | None, float | None]:
    lat = _float_or_none(row.get("lat") or row.get("latitude"))
    lon = _float_or_none(row.get("lon") or row.get("long") or row.get("longitude"))
    if lat is not None and lon is not None:
        return lat, lon

    combined = " ".join(row.values())
    match = re.search(
        r"(?P<lat>\d+(?:\.\d+)?)\s*(?P<lat_dir>[NS])[, ]+"
        r"(?P<lon>\d+(?:\.\d+)?)\s*(?P<lon_dir>[EW])",
        combined,
        re.IGNORECASE,
    )
    if not match:
        return None, None
    lat = float(match.group("lat"))
    lon = float(match.group("lon"))
    if match.group("lat_dir").upper() == "S":
        lat *= -1
    if match.group("lon_dir").upper() == "W":
        lon *= -1
    return lat, lon


def _severity_from_levels(
    actual: float | None, warning: float | None, danger: float | None
) -> float | None:
    if actual is None:
        return None
    if danger is not None and actual >= danger:
        return 3.0
    if warning is not None and actual >= warning:
        return 2.0
    return 1.0


def parse_cwc_gauge_tables(
    html: str, *, fetched_at: datetime | None = None
) -> list[NormalizedEvent]:
    fetched_at = fetched_at or datetime.now(UTC)
    soup = BeautifulSoup(html, "lxml")
    events: list[NormalizedEvent] = []

    for table in soup.find_all("table"):
        header_cells = table.find_all("th")
        if not header_cells:
            first_row = table.find("tr")
            header_cells = first_row.find_all("td") if first_row else []
        headers = [_clean(cell.get_text(" ")) for cell in header_cells]
        if not headers:
            continue

        rows = table.find_all("tr")[1:]
        for row in rows:
            values = [_clean(cell.get_text(" ")) for cell in row.find_all("td")]
            if not values:
                continue
            mapped = _row_dict(headers, values)
            station = (
                mapped.get("station")
                or mapped.get("site")
                or mapped.get("flood forecasting site")
                or mapped.get("name of river flood forecasting site")
            )
            if not station:
                continue

            lat, lon = _extract_coords(mapped)
            occurred_at = _parse_datetime(mapped, fetched_at)
            actual_level = _float_or_none(
                mapped.get("actual level")
                or mapped.get("water level")
                or mapped.get("level")
                or mapped.get("forecasted level")
            )
            warning_level = _float_or_none(mapped.get("warning level") or mapped.get("warning"))
            danger_level = _float_or_none(mapped.get("danger level") or mapped.get("danger"))
            discharge = _float_or_none(mapped.get("discharge") or mapped.get("average inflow"))
            river = mapped.get("river") or mapped.get("name of river") or ""
            basin = mapped.get("basin") or ""
            state = mapped.get("state") or ""
            district = mapped.get("district") or ""
            normalized_payload: dict[str, Any] = {
                "station": station,
                "river": river,
                "basin": basin,
                "state": state,
                "district": district,
                "water_level_m": actual_level,
                "warning_level_m": warning_level,
                "danger_level_m": danger_level,
                "discharge_cumec": discharge,
                "trend": mapped.get("trend"),
            }
            events.append(
                NormalizedEvent(
                    source="cwc",
                    source_event_id=timestamp_bucket_id(
                        "cwc", station, river or basin, timestamp=occurred_at
                    ),
                    hazard_type="flood",
                    event_timestamp=occurred_at,
                    latitude=lat,
                    longitude=lon,
                    confidence=0.85,
                    raw_payload=mapped,
                    normalized_payload=normalized_payload,
                    intensity=_severity_from_levels(actual_level, warning_level, danger_level),
                )
            )
    return events


def parse_state_bulletin(
    url: str, html: str, *, fetched_at: datetime | None = None
) -> list[NormalizedEvent]:
    fetched_at = fetched_at or datetime.now(UTC)
    text = _clean(BeautifulSoup(html, "lxml").get_text(" "))
    if not text:
        return []
    lat, lon = _extract_coords({"body": text})
    warning_keywords = ("flood warning", "severe flood", "danger level", "evacuation")
    if not any(keyword in text.lower() for keyword in warning_keywords):
        return []
    severity = (
        3.0 if any(word in text.lower() for word in ("severe", "danger", "evacuation")) else 2.0
    )
    return [
        NormalizedEvent(
            source="state_flood_bulletin",
            source_event_id=timestamp_bucket_id("state_flood", url, timestamp=fetched_at),
            hazard_type="flood",
            event_timestamp=fetched_at,
            latitude=lat,
            longitude=lon,
            confidence=0.6,
            raw_payload={"url": url, "text": text[:4000]},
            normalized_payload={"url": url, "summary": text[:1000]},
            intensity=severity,
        )
    ]
