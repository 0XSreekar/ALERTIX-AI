"""India-scoped NASA FIRMS ingestion service."""

from __future__ import annotations

import json
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingestion.common.dedupe import unique_by_source_event_id
from app.ingestion.common.logger import (
    get_ingestion_logger,
    log_duplicate_payload,
    log_ingestion_summary,
)
from app.ingestion.common.storage import bulk_upsert_hazard_events, bulk_upsert_legacy_events
from app.ingestion.common.stream import publish_hazard_events
from app.ingestion.metrics import metrics as ingest_metrics
from app.ingestion.wildfire.client import FIRMS_SOURCES, fetch_firms_csv
from app.ingestion.wildfire.parser import parse_firms_csv
from app.ingestion.wildfire.validator import validate_wildfire

log = get_ingestion_logger("wildfire")
T = TypeVar("T")


def _chunks(items: list[T], size: int) -> list[list[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


async def _bulk_upsert_wildfires(session: AsyncSession, events, stored_refs) -> int:
    ref_by_key = {ref.source_key: ref.id for ref in stored_refs}
    records = [
        {
            "hazard_event_id": ref_by_key[event.source_key],
            "source": event.source,
            "external_id": event.source_event_id,
            "detected_at": event.event_timestamp.isoformat(),
            "latitude": event.latitude,
            "longitude": event.longitude,
            "frp": event.intensity,
            "brightness": event.normalized_payload.get("brightness")
            or event.normalized_payload.get("bright_ti4"),
            "confidence": event.confidence,
            "confidence_label": event.normalized_payload.get("confidence_label"),
            "satellite": event.normalized_payload.get("satellite"),
            "instrument": event.normalized_payload.get("instrument"),
            "daynight": event.normalized_payload.get("daynight"),
            "raw_payload": event.raw_payload,
        }
        for event in events
        if event.source_key in ref_by_key
    ]
    if not records:
        return 0

    result = await session.execute(
        text("""
            WITH payload AS (
                SELECT *
                FROM jsonb_to_recordset(CAST(:records AS jsonb)) AS x(
                    hazard_event_id uuid,
                    source text,
                    external_id text,
                    detected_at timestamptz,
                    latitude double precision,
                    longitude double precision,
                    frp double precision,
                    brightness double precision,
                    confidence double precision,
                    confidence_label text,
                    satellite text,
                    instrument text,
                    daynight text,
                    raw_payload jsonb
                )
            )
            INSERT INTO wildfires (
                hazard_event_id, source, external_id, detected_at, location,
                frp, brightness, confidence, confidence_label,
                satellite, instrument, daynight, raw_payload
            )
            SELECT
                hazard_event_id, source, external_id, detected_at,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                frp, brightness, confidence, confidence_label,
                satellite, instrument, daynight, raw_payload
            FROM payload
            ON CONFLICT (source, external_id) DO UPDATE SET
                hazard_event_id = EXCLUDED.hazard_event_id,
                detected_at = EXCLUDED.detected_at,
                location = EXCLUDED.location,
                frp = EXCLUDED.frp,
                brightness = EXCLUDED.brightness,
                confidence = EXCLUDED.confidence,
                confidence_label = EXCLUDED.confidence_label,
                satellite = EXCLUDED.satellite,
                instrument = EXCLUDED.instrument,
                daynight = EXCLUDED.daynight,
                raw_payload = EXCLUDED.raw_payload
            RETURNING id
        """),
        {"records": json.dumps(records, default=str)},
    )
    return len(result.fetchall())


async def ingest_firms(session: AsyncSession, *, day_range: int = 1, batch_size: int = 500) -> dict:
    settings = get_settings()
    if not settings.nasa_firms_map_key:
        log.warning("firms_skip_no_key")
        return {"status": "skipped", "reason": "no FIRMS MAP_KEY configured"}

    all_events = []
    fetched_sources = 0
    for source in FIRMS_SOURCES:
        csv_text = await fetch_firms_csv(
            settings.nasa_firms_map_key, source=source, day_range=day_range
        )
        fetched_sources += 1
        all_events.extend(parse_firms_csv(csv_text, source_name=f"nasa_firms_{source.lower()}"))

    valid = [event for event in all_events if validate_wildfire(event)]
    valid, duplicates = unique_by_source_event_id(valid, lambda event: event.source_key)

    stored_total = 0
    source_rows = 0
    streamed_total = 0
    for batch in _chunks(valid, batch_size):
        stored_refs = await bulk_upsert_hazard_events(session, batch)
        source_rows += await _bulk_upsert_wildfires(session, batch, stored_refs)
        await bulk_upsert_legacy_events(session, batch)
        await session.commit()
        stored_total += len(stored_refs)
        streamed_total += await publish_hazard_events(batch, stored_refs)

    stats = {
        "fetched_sources": fetched_sources,
        "parsed": len(all_events),
        "valid_india_hotspots": len(valid),
        "duplicates": duplicates,
        "stored": stored_total,
        "wildfire_rows": source_rows,
        "streamed": streamed_total,
        "malformed_or_outside_india": len(all_events) - len(valid),
    }
    ingest_metrics.record(
        "nasa_firms",
        fetched=fetched_sources,
        parsed=len(all_events),
        valid=len(valid),
        malformed=len(all_events) - len(valid),
        duplicates=duplicates,
        stored=stored_total,
        streamed=streamed_total,
    )
    log_duplicate_payload(log, "nasa_firms", duplicates)
    log_ingestion_summary(log, "nasa_firms", **stats)
    return stats
