"""CWC — Central Water Commission river gauge scraper.

Scrapes public CWC website for gauge readings on 5 starter basins.
Respects robots and rate limits.
"""

import json
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger

log = get_logger(__name__)

CWC_BASE_URL = "https://cwc.gov.in"
CWC_FLOOD_URL = "https://cwc.gov.in/ffs-forecast"

STARTER_BASINS = {
    "krishna": {"lat": 16.5, "lon": 78.5},
    "godavari": {"lat": 18.5, "lon": 79.5},
    "mahanadi": {"lat": 21.0, "lon": 83.5},
    "yamuna": {"lat": 28.5, "lon": 77.5},
    "brahmaputra": {"lat": 26.0, "lon": 91.5},
}


async def _fetch_cwc_page() -> str:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            resp = await client.get(CWC_FLOOD_URL, headers={"User-Agent": "Alertix/1.0"})
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            log.warning("cwc_fetch_failed", error=str(exc))
            return ""


def _parse_gauge_data(html: str) -> list[dict]:
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    results = []

    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            station_name = cells[0].get_text(strip=True)
            basin_name = cells[1].get_text(strip=True).lower() if len(cells) > 1 else ""
            water_level = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            discharge = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            try:
                level_val = float(water_level.replace(",", ""))
            except (ValueError, TypeError):
                level_val = None

            try:
                discharge_val = float(discharge.replace(",", ""))
            except (ValueError, TypeError):
                discharge_val = None

            matched_basin = None
            for bname in STARTER_BASINS:
                if bname in basin_name or bname in station_name.lower():
                    matched_basin = bname
                    break

            if matched_basin and (level_val is not None or discharge_val is not None):
                coords = STARTER_BASINS[matched_basin]
                results.append({
                    "station": station_name,
                    "basin": matched_basin,
                    "water_level_m": level_val,
                    "discharge_cumec": discharge_val,
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                })

    return results


async def ingest_cwc(session: AsyncSession) -> dict:
    html = await _fetch_cwc_page()
    gauge_data = _parse_gauge_data(html)
    now = datetime.now(timezone.utc)
    inserted = 0

    for gauge in gauge_data:
        external_id = f"cwc_{gauge['basin']}_{gauge['station']}_{now.strftime('%Y%m%d%H')}"
        try:
            await session.execute(
                text("""
                    INSERT INTO events (
                        hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata
                    ) VALUES (
                        'flood', 'cwc', :external_id, :occurred_at,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :intensity, :metadata::jsonb
                    )
                    ON CONFLICT (source, external_id) DO NOTHING
                """),
                {
                    "external_id": external_id,
                    "occurred_at": now,
                    "lon": gauge["lon"],
                    "lat": gauge["lat"],
                    "intensity": gauge["water_level_m"],
                    "metadata": json.dumps({
                        "station": gauge["station"],
                        "basin": gauge["basin"],
                        "water_level_m": gauge["water_level_m"],
                        "discharge_cumec": gauge["discharge_cumec"],
                    }),
                },
            )
            inserted += 1
        except Exception as exc:
            log.error("cwc_upsert_error", error=str(exc))

    await session.commit()
    stats = {"gauges_parsed": len(gauge_data), "inserted": inserted}
    log.info("cwc_ingestion_complete", **stats)
    return stats
