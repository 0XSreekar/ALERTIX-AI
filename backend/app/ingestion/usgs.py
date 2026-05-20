"""USGS Earthquake Hazards Program — GeoJSON feed ingestion.

Pulls `all_hour` (every 60s cron) and upserts into events table by (source, external_id).
"""

from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.redis_client import get_redis

log = get_logger(__name__)

USGS_FEEDS = {
    "all_hour": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "all_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "significant_week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson",
}


async def fetch_usgs_geojson(feed: str = "all_hour") -> dict:
    url = USGS_FEEDS.get(feed, USGS_FEEDS["all_hour"])
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def _parse_feature(feature: dict) -> dict | None:
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])

    if not coords or len(coords) < 2:
        return None

    lon, lat = coords[0], coords[1]
    depth = coords[2] if len(coords) > 2 else None
    time_ms = props.get("time")
    if time_ms is None:
        return None

    occurred_at = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
    external_id = feature.get("id") or props.get("code")

    tsunami_flag = bool(props.get("tsunami", 0))

    return {
        "hazard_type": "earthquake",
        "source": "usgs",
        "external_id": str(external_id),
        "occurred_at": occurred_at,
        "longitude": lon,
        "latitude": lat,
        "magnitude": props.get("mag"),
        "depth_km": depth,
        "intensity": props.get("mmi"),
        "metadata": {
            "place": props.get("place"),
            "url": props.get("url"),
            "felt": props.get("felt"),
            "cdi": props.get("cdi"),
            "mmi": props.get("mmi"),
            "alert": props.get("alert"),
            "status": props.get("status"),
            "tsunami": tsunami_flag,
            "sig": props.get("sig"),
            "net": props.get("net"),
            "type": props.get("type"),
            "title": props.get("title"),
        },
    }


async def ingest_usgs(session: AsyncSession, feed: str = "all_hour") -> dict:
    """Fetch USGS GeoJSON and upsert events. Returns stats."""
    data = await fetch_usgs_geojson(feed)
    features = data.get("features", [])

    inserted = 0
    skipped = 0
    errors = 0

    for feature in features:
        parsed = _parse_feature(feature)
        if parsed is None:
            skipped += 1
            continue

        try:
            result = await session.execute(
                text("""
                    INSERT INTO events (
                        hazard_type, source, external_id, occurred_at,
                        location, magnitude, depth_km, intensity, metadata
                    ) VALUES (
                        :hazard_type, :source, :external_id, :occurred_at,
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                        :magnitude, :depth_km, :intensity,
                        :metadata::jsonb
                    )
                    ON CONFLICT (source, external_id) DO UPDATE SET
                        magnitude = EXCLUDED.magnitude,
                        depth_km = EXCLUDED.depth_km,
                        intensity = EXCLUDED.intensity,
                        metadata = EXCLUDED.metadata
                    RETURNING id
                """),
                {
                    "hazard_type": parsed["hazard_type"],
                    "source": parsed["source"],
                    "external_id": parsed["external_id"],
                    "occurred_at": parsed["occurred_at"],
                    "longitude": parsed["longitude"],
                    "latitude": parsed["latitude"],
                    "magnitude": parsed["magnitude"],
                    "depth_km": parsed["depth_km"],
                    "intensity": parsed["intensity"],
                    "metadata": __import__("json").dumps(parsed["metadata"]),
                },
            )
            row = result.fetchone()
            if row:
                inserted += 1
                # Push to Redis stream for downstream processing
                try:
                    redis = get_redis()
                    await redis.xadd(
                        "hazard:events",
                        {
                            "event_id": str(row[0]),
                            "hazard_type": "earthquake",
                            "source": "usgs",
                        },
                    )
                except Exception:
                    log.warning("redis_push_failed", event_id=str(row[0]))
        except Exception as exc:
            log.error("usgs_upsert_error", external_id=parsed["external_id"], error=str(exc))
            errors += 1

    await session.commit()

    stats = {
        "feed": feed,
        "total_features": len(features),
        "inserted_or_updated": inserted,
        "skipped": skipped,
        "errors": errors,
    }
    log.info("usgs_ingestion_complete", **stats)
    return stats
