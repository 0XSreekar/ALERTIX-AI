"""USGS earthquake ingestion service."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.common.dedupe import unique_by_source_event_id
from app.ingestion.common.logger import (
    get_ingestion_logger,
    log_duplicate_payload,
    log_ingestion_summary,
)
from app.ingestion.metrics import metrics as ingest_metrics
from app.ingestion.common.storage import bulk_upsert_hazard_events, bulk_upsert_legacy_events
from app.ingestion.common.stream import publish_hazard_events
from app.ingestion.earthquake.client import fetch_usgs_geojson
from app.ingestion.earthquake.parser import parse_geojson
from app.ingestion.earthquake.validator import validate_earthquake

log = get_ingestion_logger("earthquake")


async def _bulk_upsert_earthquakes(session: AsyncSession, events, stored_refs) -> int:
    ref_by_key = {ref.source_key: ref.id for ref in stored_refs}
    records = [
        {
            "hazard_event_id": ref_by_key[event.source_key],
            "source": event.source,
            "external_id": event.source_event_id,
            "occurred_at": event.event_timestamp.isoformat(),
            "latitude": event.latitude,
            "longitude": event.longitude,
            "magnitude": event.magnitude,
            "depth_km": event.depth_km,
            "confidence": event.confidence,
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
                    occurred_at timestamptz,
                    latitude double precision,
                    longitude double precision,
                    magnitude double precision,
                    depth_km double precision,
                    confidence double precision,
                    raw_payload jsonb
                )
            )
            INSERT INTO earthquakes (
                hazard_event_id, source, external_id, occurred_at,
                location, magnitude, depth_km, confidence, raw_payload
            )
            SELECT
                hazard_event_id, source, external_id, occurred_at,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                magnitude, depth_km, confidence, raw_payload
            FROM payload
            ON CONFLICT (source, external_id) DO UPDATE SET
                hazard_event_id = EXCLUDED.hazard_event_id,
                occurred_at = EXCLUDED.occurred_at,
                location = EXCLUDED.location,
                magnitude = EXCLUDED.magnitude,
                depth_km = EXCLUDED.depth_km,
                confidence = EXCLUDED.confidence,
                raw_payload = EXCLUDED.raw_payload
            RETURNING id
        """),
        {"records": json.dumps(records, default=str)},
    )
    return len(result.fetchall())


async def ingest_usgs(session: AsyncSession, feed: str = "all_hour") -> dict:
    payload = await fetch_usgs_geojson(feed)
    parsed = parse_geojson(payload)
    valid = [event for event in parsed if validate_earthquake(event)]
    valid, duplicates = unique_by_source_event_id(valid, lambda event: event.source_key)

    stored_refs = await bulk_upsert_hazard_events(session, valid)
    source_rows = await _bulk_upsert_earthquakes(session, valid, stored_refs)
    await bulk_upsert_legacy_events(session, valid)
    await session.commit()

    published = await publish_hazard_events(valid, stored_refs)

    stats = {
        "feed": feed,
        "fetched": len(payload.get("features") or []),
        "parsed": len(parsed),
        "valid": len(valid),
        "duplicates": duplicates,
        "stored": len(stored_refs),
        "earthquake_rows": source_rows,
        "streamed": published,
        "malformed": len(parsed) - len(valid),
    }
    ingest_metrics.record(
        "usgs",
        fetched=len(payload.get("features") or []),
        parsed=len(parsed),
        valid=len(valid),
        malformed=len(parsed) - len(valid),
        duplicates=duplicates,
        stored=len(stored_refs),
        streamed=published,
    )
    log_duplicate_payload(log, "usgs", duplicates)
    log_ingestion_summary(log, "usgs", **stats)
    return stats
