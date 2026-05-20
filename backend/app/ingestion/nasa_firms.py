"""NASA FIRMS — VIIRS/MODIS active fire detection ingestion."""

import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging import get_logger
from app.redis_client import get_redis

log = get_logger(__name__)

FIRMS_CSV_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/world/1"


async def fetch_firms_data(map_key: str) -> list[dict]:
    url = FIRMS_CSV_URL.format(key=map_key)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    lines = resp.text.strip().split("\n")
    if len(lines) < 2:
        return []

    headers = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        vals = line.split(",")
        if len(vals) != len(headers):
            continue
        rows.append(dict(zip(headers, vals)))
    return rows


def _parse_hotspot(row: dict) -> dict | None:
    try:
        lat = float(row.get("latitude", ""))
        lon = float(row.get("longitude", ""))
    except (ValueError, TypeError):
        return None

    acq_date = row.get("acq_date", "")
    acq_time = row.get("acq_time", "0000")
    try:
        occurred_at = datetime.strptime(
            f"{acq_date} {acq_time.zfill(4)}", "%Y-%m-%d %H%M"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    external_id = f"firms_{lat}_{lon}_{acq_date}_{acq_time}"

    return {
        "hazard_type": "wildfire",
        "source": "firms",
        "external_id": external_id,
        "occurred_at": occurred_at,
        "latitude": lat,
        "longitude": lon,
        "intensity": float(row.get("frp", 0) or 0),
        "metadata": {
            "brightness": row.get("bright_ti4"),
            "confidence": row.get("confidence"),
            "frp": row.get("frp"),
            "satellite": row.get("satellite"),
            "instrument": row.get("instrument"),
            "daynight": row.get("daynight"),
        },
    }


async def ingest_firms(session: AsyncSession) -> dict:
    settings = get_settings()
    if not settings.nasa_firms_map_key:
        log.warning("firms_skip_no_key")
        return {"status": "skipped", "reason": "no FIRMS MAP_KEY configured"}

    rows = await fetch_firms_data(settings.nasa_firms_map_key)
    inserted = 0
    skipped = 0
    errors = 0

    for row in rows:
        parsed = _parse_hotspot(row)
        if not parsed:
            skipped += 1
            continue

        try:
            result = await session.execute(
                text("""
                    INSERT INTO events (
                        hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata
                    ) VALUES (
                        :hazard_type, :source, :external_id, :occurred_at,
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                        :intensity, :metadata::jsonb
                    )
                    ON CONFLICT (source, external_id) DO NOTHING
                    RETURNING id
                """),
                {
                    **parsed,
                    "metadata": json.dumps(parsed["metadata"]),
                },
            )
            if result.fetchone():
                inserted += 1
        except Exception as exc:
            log.error("firms_upsert_error", error=str(exc))
            errors += 1

    await session.commit()
    stats = {"total": len(rows), "inserted": inserted, "skipped": skipped, "errors": errors}
    log.info("firms_ingestion_complete", **stats)
    return stats
