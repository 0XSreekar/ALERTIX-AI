"""Normalized event contracts shared by all ingestion services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

HazardType = Literal["earthquake", "wildfire", "flood", "cyclone", "weather"]


@dataclass(slots=True)
class NormalizedEvent:
    source: str
    source_event_id: str
    hazard_type: HazardType
    event_timestamp: datetime
    latitude: float | None
    longitude: float | None
    confidence: float | None
    raw_payload: dict[str, Any]
    normalized_payload: dict[str, Any] = field(default_factory=dict)
    magnitude: float | None = None
    depth_km: float | None = None
    intensity: float | None = None
    processing_state: str = "ingested"
    retry_count: int = 0

    @property
    def source_key(self) -> str:
        return f"{self.source}:{self.source_event_id}"


@dataclass(slots=True)
class StoredEventRef:
    id: str
    source: str
    source_event_id: str
    hazard_type: str

    @property
    def source_key(self) -> str:
        return f"{self.source}:{self.source_event_id}"
