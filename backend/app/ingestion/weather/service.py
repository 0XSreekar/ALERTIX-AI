"""Weather ingestion service."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingestion.common.dedupe import unique_by_source_event_id
from app.ingestion.common.logger import (
    get_ingestion_logger,
    log_duplicate_payload,
    log_ingestion_summary,
)
from app.ingestion.common.storage import bulk_upsert_hazard_events
from app.ingestion.common.stream import publish_hazard_events
from app.ingestion.metrics import metrics as ingest_metrics
from app.ingestion.weather.client import fetch_open_meteo_rainfall
from app.ingestion.weather.parser import parse_open_meteo_rainfall
from app.ingestion.weather.validator import validate_weather_event

log = get_ingestion_logger("weather")


async def _bulk_upsert_weather(session: AsyncSession, events, stored_refs) -> int:
    ref_by_key = {ref.source_key: ref.id for ref in stored_refs}
    records = [
        {
            "hazard_event_id": ref_by_key[event.source_key],
            "source": event.source,
            "external_id": event.source_event_id,
            "observed_at": event.event_timestamp.isoformat(),
            "latitude": event.latitude,
            "longitude": event.longitude,
            "precipitation_mm": event.normalized_payload.get("precipitation_mm"),
            "rain_mm": event.normalized_payload.get("rain_mm"),
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
                    observed_at timestamptz,
                    latitude double precision,
                    longitude double precision,
                    precipitation_mm double precision,
                    rain_mm double precision,
                    raw_payload jsonb
                )
            )
            INSERT INTO weather_events (
                hazard_event_id, source, external_id, observed_at, location,
                precipitation_mm, rain_mm, raw_payload
            )
            SELECT
                hazard_event_id, source, external_id, observed_at,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                precipitation_mm, rain_mm, raw_payload
            FROM payload
            ON CONFLICT (source, external_id) DO UPDATE SET
                hazard_event_id = EXCLUDED.hazard_event_id,
                observed_at = EXCLUDED.observed_at,
                location = EXCLUDED.location,
                precipitation_mm = EXCLUDED.precipitation_mm,
                rain_mm = EXCLUDED.rain_mm,
                raw_payload = EXCLUDED.raw_payload
            RETURNING id
        """),
        {"records": json.dumps(records, default=str)},
    )
    return len(result.fetchall())


async def ingest_weather(session: AsyncSession) -> dict:
    settings = get_settings()
    points = settings.weather_ingest_point_list
    if not points:
        return {"status": "skipped", "reason": "WEATHER_INGEST_POINTS is not configured"}

    parsed = []
    for latitude, longitude in points:
        payload = await fetch_open_meteo_rainfall(latitude, longitude)
        parsed.extend(parse_open_meteo_rainfall(payload, latitude=latitude, longitude=longitude))

    valid = [event for event in parsed if validate_weather_event(event)]
    valid, duplicates = unique_by_source_event_id(valid, lambda event: event.source_key)
    stored_refs = await bulk_upsert_hazard_events(session, valid)
    weather_rows = await _bulk_upsert_weather(session, valid, stored_refs)
    await session.commit()
    published = await publish_hazard_events(valid, stored_refs)

    stats = {
        "points": len(points),
        "parsed": len(parsed),
        "valid": len(valid),
        "duplicates": duplicates,
        "stored": len(stored_refs),
        "weather_rows": weather_rows,
        "streamed": published,
    }
    ingest_metrics.record(
        "open_meteo",
        fetched=len(points),
        parsed=len(parsed),
        valid=len(valid),
        duplicates=duplicates,
        stored=len(stored_refs),
        streamed=published,
    )
    log_duplicate_payload(log, "weather", duplicates)
    log_ingestion_summary(log, "weather", **stats)
    return stats
