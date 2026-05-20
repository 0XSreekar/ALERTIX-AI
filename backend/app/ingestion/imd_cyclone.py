"""IMD — India Meteorological Department cyclone bulletin scraper."""

import json
import re
from datetime import UTC, datetime

import feedparser
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger

log = get_logger(__name__)

IMD_RSS_URL = "https://mausam.imd.gov.in/imd_latest/rss/rss_bulletin_en.xml"
IMD_CYCLONE_URL = "https://mausam.imd.gov.in/Forecast/cyclone_bulletin.html"


async def _fetch_rss_entries() -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(IMD_RSS_URL)
        resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    return feed.get("entries", [])


async def _fetch_cyclone_bulletin() -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(IMD_CYCLONE_URL)
            resp.raise_for_status()
            return resp.text
        except Exception:
            return ""


def _extract_coords(text_block: str) -> tuple[float | None, float | None]:
    pattern = r"(\d+\.?\d*)\s*[°]?\s*([NS])[,\s]+(\d+\.?\d*)\s*[°]?\s*([EW])"
    match = re.search(pattern, text_block, re.IGNORECASE)
    if not match:
        return None, None
    lat = float(match.group(1))
    if match.group(2).upper() == "S":
        lat = -lat
    lon = float(match.group(3))
    if match.group(4).upper() == "W":
        lon = -lon
    return lat, lon


async def ingest_imd(session: AsyncSession) -> dict:
    entries = await _fetch_rss_entries()
    # Bulletin HTML is fetched to warm the cache; parsing is Phase 2.
    await _fetch_cyclone_bulletin()
    inserted = 0
    skipped = 0

    for entry in entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        link = entry.get("link", "")
        published = entry.get("published_parsed")

        if not any(kw in title.lower() for kw in ["cyclone", "depression", "storm"]):
            continue

        if published:
            occurred_at = datetime(*published[:6], tzinfo=UTC)
        else:
            occurred_at = datetime.now(UTC)

        lat, lon = _extract_coords(summary)
        external_id = f"imd_{title[:60]}_{occurred_at.date()}"

        try:
            params = {
                "hazard_type": "cyclone",
                "source": "imd",
                "external_id": external_id,
                "occurred_at": occurred_at,
                "metadata": json.dumps({"title": title, "summary": summary, "link": link}),
            }

            if lat is not None and lon is not None:
                await session.execute(
                    text("""
                        INSERT INTO events (hazard_type, source, external_id, occurred_at, location, metadata)
                        VALUES (:hazard_type, :source, :external_id, :occurred_at,
                                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                                CAST(:metadata AS jsonb))
                        ON CONFLICT (source, external_id) DO NOTHING
                    """),
                    {**params, "lat": lat, "lon": lon},
                )
            else:
                await session.execute(
                    text("""
                        INSERT INTO events (hazard_type, source, external_id, occurred_at, metadata)
                        VALUES (:hazard_type, :source, :external_id, :occurred_at, CAST(:metadata AS jsonb))
                        ON CONFLICT (source, external_id) DO NOTHING
                    """),
                    params,
                )
            inserted += 1
        except Exception as exc:
            log.error("imd_upsert_error", error=str(exc))
            skipped += 1

    await session.commit()
    stats = {"entries_scanned": len(entries), "inserted": inserted, "skipped": skipped}
    log.info("imd_ingestion_complete", **stats)
    return stats
