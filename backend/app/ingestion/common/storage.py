"""Bulk database persistence helpers for ingestion services."""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.common.schemas import NormalizedEvent, StoredEventRef


def _records(events: Iterable[NormalizedEvent]) -> list[dict]:
    return [
        {
            "source": event.source,
            "source_event_id": event.source_event_id,
            "hazard_type": event.hazard_type,
            "event_timestamp": event.event_timestamp.isoformat(),
            "latitude": event.latitude,
            "longitude": event.longitude,
            "confidence": event.confidence,
            "processing_state": event.processing_state,
            "retry_count": event.retry_count,
            "raw_payload": event.raw_payload,
            "normalized_payload": event.normalized_payload,
            "magnitude": event.magnitude,
            "depth_km": event.depth_km,
            "intensity": event.intensity,
        }
        for event in events
    ]


async def bulk_upsert_hazard_events(
    session: AsyncSession,
    events: list[NormalizedEvent],
) -> list[StoredEventRef]:
    if not events:
        return []

    result = await session.execute(
        text("""
            WITH payload AS (
                SELECT *
                FROM jsonb_to_recordset(CAST(:records AS jsonb)) AS x(
                    source text,
                    source_event_id text,
                    hazard_type text,
                    event_timestamp timestamptz,
                    latitude double precision,
                    longitude double precision,
                    confidence double precision,
                    processing_state text,
                    retry_count integer,
                    raw_payload jsonb,
                    normalized_payload jsonb
                )
            )
            INSERT INTO hazard_events (
                source, source_event_id, hazard_type, event_timestamp,
                location, confidence, processing_state, retry_count,
                raw_payload, normalized_payload
            )
            SELECT
                source, source_event_id, hazard_type, event_timestamp,
                CASE
                    WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                    THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
                    ELSE NULL
                END,
                confidence, processing_state, retry_count,
                raw_payload, normalized_payload
            FROM payload
            ON CONFLICT (source, source_event_id) DO UPDATE SET
                event_timestamp = EXCLUDED.event_timestamp,
                location = EXCLUDED.location,
                confidence = EXCLUDED.confidence,
                processing_state = EXCLUDED.processing_state,
                raw_payload = EXCLUDED.raw_payload,
                normalized_payload = EXCLUDED.normalized_payload,
                updated_at = now()
            RETURNING id::text AS id, source, source_event_id, hazard_type
        """),
        {"records": json.dumps(_records(events), default=str)},
    )
    return [
        StoredEventRef(
            id=row.id,
            source=row.source,
            source_event_id=row.source_event_id,
            hazard_type=row.hazard_type,
        )
        for row in result.fetchall()
    ]


async def bulk_upsert_legacy_events(session: AsyncSession, events: list[NormalizedEvent]) -> None:
    """Keep the existing /api/events dashboard contract working while v2 tables roll out."""
    if not events:
        return

    await session.execute(
        text("""
            WITH payload AS (
                SELECT *
                FROM jsonb_to_recordset(CAST(:records AS jsonb)) AS x(
                    source text,
                    source_event_id text,
                    hazard_type text,
                    event_timestamp timestamptz,
                    latitude double precision,
                    longitude double precision,
                    magnitude double precision,
                    depth_km double precision,
                    intensity double precision,
                    normalized_payload jsonb
                )
            )
            INSERT INTO events (
                hazard_type, source, external_id, occurred_at,
                location, magnitude, depth_km, intensity, metadata
            )
            SELECT
                hazard_type, source, source_event_id, event_timestamp,
                CASE
                    WHEN latitude IS NOT NULL AND longitude IS NOT NULL
                    THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
                    ELSE NULL
                END,
                magnitude, depth_km, intensity, normalized_payload
            FROM payload
            ON CONFLICT (source, external_id) DO UPDATE SET
                occurred_at = EXCLUDED.occurred_at,
                location = EXCLUDED.location,
                magnitude = EXCLUDED.magnitude,
                depth_km = EXCLUDED.depth_km,
                intensity = EXCLUDED.intensity,
                metadata = EXCLUDED.metadata
        """),
        {"records": json.dumps(_records(events), default=str)},
    )
