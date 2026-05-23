"""Flood ingestion service using CWC and configured official bulletins."""

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
from app.ingestion.flood.client import fetch_cwc_dashboard, fetch_state_bulletins
from app.ingestion.flood.parser import parse_cwc_gauge_tables, parse_state_bulletin
from app.ingestion.flood.validator import validate_flood_event

log = get_ingestion_logger("flood")


async def _bulk_upsert_river_gauges(session: AsyncSession, events, stored_refs) -> int:
    ref_by_key = {ref.source_key: ref.id for ref in stored_refs}
    records = [
        {
            "hazard_event_id": ref_by_key[event.source_key],
            "source": event.source,
            "station_id": event.source_event_id,
            "station_name": event.normalized_payload.get("station"),
            "river_name": event.normalized_payload.get("river"),
            "basin": event.normalized_payload.get("basin"),
            "state": event.normalized_payload.get("state"),
            "district": event.normalized_payload.get("district"),
            "observed_at": event.event_timestamp.isoformat(),
            "latitude": event.latitude,
            "longitude": event.longitude,
            "water_level_m": event.normalized_payload.get("water_level_m"),
            "warning_level_m": event.normalized_payload.get("warning_level_m"),
            "danger_level_m": event.normalized_payload.get("danger_level_m"),
            "discharge_cumec": event.normalized_payload.get("discharge_cumec"),
            "severity": event.intensity,
            "raw_payload": event.raw_payload,
        }
        for event in events
        if event.source == "cwc" and event.source_key in ref_by_key
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
                    station_id text,
                    station_name text,
                    river_name text,
                    basin text,
                    state text,
                    district text,
                    observed_at timestamptz,
                    latitude double precision,
                    longitude double precision,
                    water_level_m double precision,
                    warning_level_m double precision,
                    danger_level_m double precision,
                    discharge_cumec double precision,
                    severity double precision,
                    raw_payload jsonb
                )
            )
            INSERT INTO river_gauges (
                hazard_event_id, source, station_id, station_name, river_name,
                basin, state, district, observed_at, location,
                water_level_m, warning_level_m, danger_level_m,
                discharge_cumec, severity, raw_payload
            )
            SELECT
                hazard_event_id, source, station_id, station_name, river_name,
                basin, state, district, observed_at,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                water_level_m, warning_level_m, danger_level_m,
                discharge_cumec, severity, raw_payload
            FROM payload
            ON CONFLICT (source, station_id, observed_at) DO UPDATE SET
                hazard_event_id = EXCLUDED.hazard_event_id,
                station_name = EXCLUDED.station_name,
                river_name = EXCLUDED.river_name,
                basin = EXCLUDED.basin,
                state = EXCLUDED.state,
                district = EXCLUDED.district,
                location = EXCLUDED.location,
                water_level_m = EXCLUDED.water_level_m,
                warning_level_m = EXCLUDED.warning_level_m,
                danger_level_m = EXCLUDED.danger_level_m,
                discharge_cumec = EXCLUDED.discharge_cumec,
                severity = EXCLUDED.severity,
                raw_payload = EXCLUDED.raw_payload
            RETURNING id
        """),
        {"records": json.dumps(records, default=str)},
    )
    return len(result.fetchall())


async def ingest_cwc(session: AsyncSession) -> dict:
    html = await fetch_cwc_dashboard()
    gauge_events = parse_cwc_gauge_tables(html)
    bulletin_events = []
    for url, bulletin_html in await fetch_state_bulletins():
        bulletin_events.extend(parse_state_bulletin(url, bulletin_html))

    parsed = [*gauge_events, *bulletin_events]
    valid = [event for event in parsed if validate_flood_event(event)]
    valid, duplicates = unique_by_source_event_id(valid, lambda event: event.source_key)

    stored_refs = await bulk_upsert_hazard_events(session, valid)
    gauge_rows = await _bulk_upsert_river_gauges(session, valid, stored_refs)
    await bulk_upsert_legacy_events(session, valid)
    await session.commit()
    published = await publish_hazard_events(valid, stored_refs)

    stats = {
        "parsed_gauges": len(gauge_events),
        "parsed_bulletins": len(bulletin_events),
        "valid_geo_events": len(valid),
        "duplicates": duplicates,
        "stored": len(stored_refs),
        "river_gauge_rows": gauge_rows,
        "streamed": published,
        "dropped_malformed_or_ungeotagged": len(parsed) - len(valid),
    }
    ingest_metrics.record(
        "cwc",
        fetched=len(gauge_events) + len(bulletin_events),
        parsed=len(parsed),
        valid=len(valid),
        malformed=len(parsed) - len(valid),
        duplicates=duplicates,
        stored=len(stored_refs),
        streamed=published,
    )
    log_duplicate_payload(log, "flood", duplicates)
    log_ingestion_summary(log, "flood", **stats)
    return stats


async def ingest_flood(session: AsyncSession) -> dict:
    return await ingest_cwc(session)
