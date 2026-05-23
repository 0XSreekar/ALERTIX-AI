"""Cyclone ingestion service for IMD/RSMC and JTWC bulletins."""

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
from app.ingestion.cyclone.client import fetch_imd_bulletins, fetch_jtwc_bulletins
from app.ingestion.cyclone.parser import CycloneParser, StormTracker
from app.ingestion.cyclone.validator import validate_cyclone

log = get_ingestion_logger("cyclone")


async def _bulk_upsert_cyclones(session: AsyncSession, events, stored_refs) -> int:
    ref_by_key = {ref.source_key: ref.id for ref in stored_refs}
    records = [
        {
            "hazard_event_id": ref_by_key[event.source_key],
            "source": event.source,
            "external_id": event.source_event_id,
            "bulletin_at": event.event_timestamp.isoformat(),
            "latitude": event.latitude,
            "longitude": event.longitude,
            "storm_name": event.normalized_payload.get("storm_name"),
            "wind_speed_kmh": event.normalized_payload.get("wind_speed_kmh"),
            "pressure_hpa": event.normalized_payload.get("pressure_hpa"),
            "movement_direction": event.normalized_payload.get("movement_direction"),
            "warning_level": event.normalized_payload.get("warning_level"),
            "forecast_path": event.normalized_payload.get("forecast_path"),
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
                    bulletin_at timestamptz,
                    latitude double precision,
                    longitude double precision,
                    storm_name text,
                    wind_speed_kmh double precision,
                    pressure_hpa double precision,
                    movement_direction text,
                    warning_level text,
                    forecast_path jsonb,
                    raw_payload jsonb
                )
            )
            INSERT INTO cyclones (
                hazard_event_id, source, external_id, bulletin_at,
                location, storm_name, wind_speed_kmh, pressure_hpa,
                movement_direction, warning_level, forecast_path, raw_payload
            )
            SELECT
                hazard_event_id, source, external_id, bulletin_at,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                storm_name, wind_speed_kmh, pressure_hpa,
                movement_direction, warning_level, forecast_path, raw_payload
            FROM payload
            ON CONFLICT (source, external_id) DO UPDATE SET
                hazard_event_id = EXCLUDED.hazard_event_id,
                bulletin_at = EXCLUDED.bulletin_at,
                location = EXCLUDED.location,
                storm_name = EXCLUDED.storm_name,
                wind_speed_kmh = EXCLUDED.wind_speed_kmh,
                pressure_hpa = EXCLUDED.pressure_hpa,
                movement_direction = EXCLUDED.movement_direction,
                warning_level = EXCLUDED.warning_level,
                forecast_path = EXCLUDED.forecast_path,
                raw_payload = EXCLUDED.raw_payload
            RETURNING id
        """),
        {"records": json.dumps(records, default=str)},
    )
    return len(result.fetchall())


async def ingest_cyclones(session: AsyncSession) -> dict:
    parser = CycloneParser()
    parsed = []

    for url, payload in await fetch_imd_bulletins():
        event = parser.parse_text(source="imd_rsmc", url=url, payload=payload)
        if event is not None:
            parsed.append(event)

    for url, payload in await fetch_jtwc_bulletins():
        event = parser.parse_text(source="jtwc", url=url, payload=payload)
        if event is not None:
            parsed.append(event)

    latest = list(StormTracker().latest_by_name(parsed).values())
    valid = [event for event in latest if validate_cyclone(event)]
    valid, duplicates = unique_by_source_event_id(valid, lambda event: event.source_key)

    stored_refs = await bulk_upsert_hazard_events(session, valid)
    cyclone_rows = await _bulk_upsert_cyclones(session, valid, stored_refs)
    await bulk_upsert_legacy_events(session, valid)
    await session.commit()
    published = await publish_hazard_events(valid, stored_refs)

    stats = {
        "parsed_bulletins": len(parsed),
        "tracked_storms": len(latest),
        "valid_storms": len(valid),
        "duplicates": duplicates,
        "stored": len(stored_refs),
        "cyclone_rows": cyclone_rows,
        "streamed": published,
        "dropped_malformed_or_outside_basin": len(parsed) - len(valid),
    }
    ingest_metrics.record(
        "cyclone",
        fetched=len(parsed),
        parsed=len(parsed),
        valid=len(valid),
        malformed=len(parsed) - len(valid),
        duplicates=duplicates,
        stored=len(stored_refs),
        streamed=published,
    )
    log_duplicate_payload(log, "cyclone", duplicates)
    log_ingestion_summary(log, "cyclone", **stats)
    return stats
