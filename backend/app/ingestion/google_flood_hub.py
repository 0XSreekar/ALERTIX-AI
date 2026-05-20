"""Google Flood Hub API — riverine forecast ingestion for India."""

import json
from datetime import UTC, datetime

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)

GFH_API_URL = "https://floodhub.google.com/api/v1/gauges"


async def fetch_google_flood_hub(api_key: str) -> list[dict]:
    params = {
        "key": api_key,
        "country": "IN",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(GFH_API_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("gauges", [])


async def ingest_google_flood_hub(session: AsyncSession) -> dict:
    settings = get_settings()
    if not settings.google_flood_hub_key:
        log.warning("gfh_skip_no_key")
        return {"status": "skipped", "reason": "no Google Flood Hub key configured"}

    gauges = await fetch_google_flood_hub(settings.google_flood_hub_key)
    now = datetime.now(UTC)
    inserted = 0
    skipped = 0

    for gauge in gauges:
        gauge_id = gauge.get("gaugeId", "")
        lat = gauge.get("latitude")
        lon = gauge.get("longitude")
        if not gauge_id or lat is None or lon is None:
            skipped += 1
            continue

        external_id = f"gfh_{gauge_id}_{now.strftime('%Y%m%d')}"
        severity = gauge.get("severity", "")
        forecast = gauge.get("forecast", {})

        try:
            await session.execute(
                text("""
                    INSERT INTO events (
                        hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata
                    ) VALUES (
                        'flood', 'google_flood_hub', :external_id, :occurred_at,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :intensity, CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (source, external_id) DO NOTHING
                """),
                {
                    "external_id": external_id,
                    "occurred_at": now,
                    "lon": lon,
                    "lat": lat,
                    "intensity": {"danger": 3, "warning": 2, "watch": 1}.get(severity, 0),
                    "metadata": json.dumps({
                        "gauge_id": gauge_id,
                        "gauge_name": gauge.get("gaugeName"),
                        "river_name": gauge.get("riverName"),
                        "severity": severity,
                        "forecast": forecast,
                    }),
                },
            )
            inserted += 1
        except Exception as exc:
            log.error("gfh_upsert_error", error=str(exc))
            skipped += 1

    await session.commit()
    stats = {"gauges_fetched": len(gauges), "inserted": inserted, "skipped": skipped}
    log.info("gfh_ingestion_complete", **stats)
    return stats
