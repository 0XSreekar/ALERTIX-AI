"""Typed payloads consumed from Redis streams."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.processing.state import AlertTier, ProcessingState


def _blank_to_none(value: Any) -> Any | None:
    return None if value in (None, "") else value


def _float_or_none(value: Any) -> float | None:
    value = _blank_to_none(value)
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _parse_datetime(value: Any) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@dataclass(slots=True)
class ProcessingEvent:
    event_id: str
    source: str
    hazard_type: str
    timestamp: datetime
    latitude: float | None
    longitude: float | None
    magnitude: float | None
    depth_km: float | None
    confidence: float | None
    raw_payload: dict[str, Any]
    stream_id: str | None = None
    state: ProcessingState = ProcessingState.NEW
    retry_count: int = 0
    risk_score: float = 0.0
    alert_tier: AlertTier = AlertTier.LOW
    normalized: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_stream(cls, stream_id: str, payload: dict[str, Any]) -> ProcessingEvent:
        raw_payload: dict[str, Any] = {}
        if payload.get("raw_payload"):
            try:
                loaded = json.loads(str(payload["raw_payload"]))
                if isinstance(loaded, dict):
                    raw_payload = loaded
            except json.JSONDecodeError:
                raw_payload = {"unparsed": payload["raw_payload"]}

        return cls(
            event_id=str(payload.get("event_id") or payload.get("id") or ""),
            source=str(payload.get("source") or "unknown"),
            hazard_type=str(payload.get("hazard_type") or "unknown").lower(),
            timestamp=_parse_datetime(payload.get("timestamp")),
            latitude=_float_or_none(payload.get("latitude")),
            longitude=_float_or_none(payload.get("longitude")),
            magnitude=_float_or_none(payload.get("magnitude")),
            depth_km=_float_or_none(payload.get("depth")),
            confidence=_float_or_none(payload.get("confidence")),
            raw_payload=raw_payload,
            stream_id=stream_id,
            retry_count=_int_or_zero(payload.get("retry_count")),
        )

    @property
    def dedupe_key(self) -> str:
        if self.event_id:
            return f"{self.source}:{self.event_id}"
        lat = "na" if self.latitude is None else f"{self.latitude:.3f}"
        lon = "na" if self.longitude is None else f"{self.longitude:.3f}"
        return f"{self.source}:{self.hazard_type}:{self.timestamp.isoformat()}:{lat}:{lon}"
