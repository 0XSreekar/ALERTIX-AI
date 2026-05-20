"""CSV parser for NASA FIRMS hotspot records."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO

from app.ingestion.common.dedupe import stable_payload_id
from app.ingestion.common.schemas import NormalizedEvent


def _float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _confidence(value: object) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    if text in {"h", "high"}:
        return 0.9
    if text in {"n", "nominal", "medium"}:
        return 0.7
    if text in {"l", "low"}:
        return 0.4
    try:
        number = float(text)
    except ValueError:
        return None
    return max(0.0, min(1.0, number / 100.0))


def parse_firms_csv(csv_text: str, *, source_name: str = "nasa_firms") -> list[NormalizedEvent]:
    if not csv_text.strip():
        return []

    reader = csv.DictReader(StringIO(csv_text))
    events: list[NormalizedEvent] = []
    for row in reader:
        latitude = _float_or_none(row.get("latitude"))
        longitude = _float_or_none(row.get("longitude"))
        acq_date = row.get("acq_date")
        acq_time = str(row.get("acq_time") or "0000").zfill(4)
        if not acq_date:
            continue

        try:
            occurred_at = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M").replace(
                tzinfo=UTC
            )
        except ValueError:
            continue

        satellite = row.get("satellite")
        instrument = row.get("instrument")
        source_event_id = stable_payload_id(
            "firms",
            {
                "lat": latitude,
                "lon": longitude,
                "acq_date": acq_date,
                "acq_time": acq_time,
                "satellite": satellite,
                "instrument": instrument,
            },
        )
        frp = _float_or_none(row.get("frp"))
        normalized_payload = {
            "bright_ti4": _float_or_none(row.get("bright_ti4")),
            "bright_ti5": _float_or_none(row.get("bright_ti5")),
            "brightness": _float_or_none(row.get("brightness")),
            "scan": _float_or_none(row.get("scan")),
            "track": _float_or_none(row.get("track")),
            "confidence_label": row.get("confidence"),
            "frp": frp,
            "satellite": satellite,
            "instrument": instrument,
            "daynight": row.get("daynight"),
            "version": row.get("version"),
        }

        events.append(
            NormalizedEvent(
                source=source_name,
                source_event_id=source_event_id,
                hazard_type="wildfire",
                event_timestamp=occurred_at,
                latitude=latitude,
                longitude=longitude,
                confidence=_confidence(row.get("confidence")),
                raw_payload=dict(row),
                normalized_payload=normalized_payload,
                intensity=frp,
            )
        )
    return events
