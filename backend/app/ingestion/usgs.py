"""Backward-compatible imports for the rebuilt USGS ingestion package."""

from __future__ import annotations

from app.ingestion.earthquake.client import USGS_FEEDS, fetch_usgs_geojson
from app.ingestion.earthquake.parser import parse_feature
from app.ingestion.earthquake.service import ingest_usgs

__all__ = ["USGS_FEEDS", "_parse_feature", "fetch_usgs_geojson", "ingest_usgs"]


def _parse_feature(feature: dict) -> dict | None:
    event = parse_feature(feature)
    if event is None:
        return None
    return {
        "hazard_type": event.hazard_type,
        "source": event.source,
        "external_id": event.source_event_id,
        "occurred_at": event.event_timestamp,
        "longitude": event.longitude,
        "latitude": event.latitude,
        "magnitude": event.magnitude,
        "depth_km": event.depth_km,
        "intensity": event.intensity,
        "metadata": event.normalized_payload,
    }
