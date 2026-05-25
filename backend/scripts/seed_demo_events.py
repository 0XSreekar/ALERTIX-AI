"""Seed demonstration events for India across all hazard types.

Inserts ~50 synthetic but plausible events spread across India so each
dashboard tab has something to show when external ingestion is offline.
Idempotent: re-running upserts on (source, external_id).

Run:
    python backend/scripts/seed_demo_events.py
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_BACKEND))

from sqlalchemy import text  # noqa: E402

from app.db import async_session_factory  # noqa: E402


def _utc(hours_ago: float) -> datetime:
    return datetime.now(UTC) - timedelta(hours=hours_ago)


FLOODS = [
    ("Krishna at Vijayawada", 16.51, 80.62, 2.4, {"basin": "Krishna", "gauge_name": "Vijayawada", "rainfall_mm": 85}),
    ("Godavari at Bhadrachalam", 17.67, 80.89, 3.1, {"basin": "Godavari", "gauge_name": "Bhadrachalam", "rainfall_mm": 110}),
    ("Mahanadi at Cuttack", 20.46, 85.88, 1.8, {"basin": "Mahanadi", "gauge_name": "Cuttack", "rainfall_mm": 60}),
    ("Yamuna at Delhi Rly Bridge", 28.66, 77.25, 2.6, {"basin": "Yamuna", "gauge_name": "Old Rail Bridge", "rainfall_mm": 70}),
    ("Brahmaputra at Guwahati", 26.14, 91.74, 3.5, {"basin": "Brahmaputra", "gauge_name": "Guwahati", "rainfall_mm": 145}),
    ("Ganga at Patna", 25.61, 85.14, 2.2, {"basin": "Ganga", "gauge_name": "Patna", "rainfall_mm": 55}),
    ("Kosi at Birpur", 26.51, 86.97, 2.9, {"basin": "Kosi", "gauge_name": "Birpur", "rainfall_mm": 95}),
    ("Tapi at Surat", 21.17, 72.83, 1.9, {"basin": "Tapi", "gauge_name": "Surat", "rainfall_mm": 50}),
]

CYCLONES = [
    ("Cyclone Demo BOB-01", 14.5, 84.2, {"wind_kmh": 95, "category": "Cyclonic Storm", "title": "BOB-01"}),
    ("Cyclone Demo BOB-02", 18.0, 86.5, {"wind_kmh": 130, "category": "Severe Cyclonic Storm", "title": "BOB-02"}),
    ("Cyclone Demo ARB-01", 17.2, 71.8, {"wind_kmh": 75, "category": "Deep Depression", "title": "ARB-01"}),
]

WILDFIRES = [
    (28.45, 79.10, 32.1),   # Uttarakhand
    (29.10, 79.50, 41.0),
    (29.50, 78.80, 28.5),
    (30.20, 78.20, 35.2),
    (12.30, 76.80, 22.0),   # Karnataka
    (12.50, 77.10, 18.7),
    (24.20, 86.50, 28.0),   # Jharkhand
    (23.80, 85.30, 24.5),
    (19.00, 82.40, 31.0),   # Odisha
    (21.10, 81.60, 26.2),
]

LANDSLIDES = [
    ("Uttarkashi-Gangotri NH-34", 30.73, 78.45, {"district": "Uttarkashi", "trigger": "rainfall"}),
    ("Manali-Leh NH-3", 32.24, 77.19, {"district": "Lahaul-Spiti", "trigger": "rainfall"}),
    ("Idukki Hills", 9.85, 76.97, {"district": "Idukki", "trigger": "rainfall"}),
    ("Darjeeling NH-55", 27.04, 88.27, {"district": "Darjeeling", "trigger": "rainfall"}),
    ("Sikkim NH-10", 27.33, 88.61, {"district": "East Sikkim", "trigger": "rainfall"}),
]


async def main() -> None:
    rng = random.Random(42)
    async with async_session_factory() as sess:
        inserted = 0

        # Floods
        for i, (name, lat, lon, intensity, meta) in enumerate(FLOODS):
            await sess.execute(
                text("""
                    INSERT INTO events (hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata)
                    VALUES ('flood', 'demo_seed', :ext, :ts,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :intensity, CAST(:meta AS JSONB))
                    ON CONFLICT (source, external_id) DO UPDATE
                        SET intensity = EXCLUDED.intensity,
                            metadata = EXCLUDED.metadata,
                            occurred_at = EXCLUDED.occurred_at
                """),
                {
                    "ext": f"flood-{i}",
                    "ts": _utc(rng.uniform(0.5, 30)),
                    "lat": lat, "lon": lon, "intensity": intensity,
                    "meta": __import__("json").dumps({**meta, "title": name}),
                },
            )
            inserted += 1

        # Multi-point flood time series for the LSTM forecast (Krishna)
        for h in range(12):
            await sess.execute(
                text("""
                    INSERT INTO events (hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata)
                    VALUES ('flood', 'demo_seed', :ext, :ts,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :intensity, CAST(:meta AS JSONB))
                    ON CONFLICT (source, external_id) DO NOTHING
                """),
                {
                    "ext": f"flood-krishna-ts-{h}",
                    "ts": _utc(h * 6 + 3),
                    "lat": 16.51, "lon": 80.62,
                    "intensity": 2.0 + rng.uniform(-0.3, 0.6),
                    "meta": __import__("json").dumps({
                        "basin": "Krishna", "gauge_name": "Vijayawada",
                        "rainfall_mm": 60 + rng.uniform(0, 50),
                        "title": f"Krishna gauge reading t-{h * 6}h",
                    }),
                },
            )
            inserted += 1

        # Cyclones
        for i, (name, lat, lon, meta) in enumerate(CYCLONES):
            await sess.execute(
                text("""
                    INSERT INTO events (hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata)
                    VALUES ('cyclone', 'demo_seed', :ext, :ts,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :intensity, CAST(:meta AS JSONB))
                    ON CONFLICT (source, external_id) DO UPDATE
                        SET intensity = EXCLUDED.intensity,
                            metadata = EXCLUDED.metadata,
                            occurred_at = EXCLUDED.occurred_at
                """),
                {
                    "ext": f"cyclone-{i}",
                    "ts": _utc(rng.uniform(1, 24)),
                    "lat": lat, "lon": lon, "intensity": float(meta["wind_kmh"]) / 50.0,
                    "meta": __import__("json").dumps({**meta, "title": name}),
                },
            )
            inserted += 1

        # Wildfires
        for i, (lat, lon, frp) in enumerate(WILDFIRES):
            await sess.execute(
                text("""
                    INSERT INTO events (hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata)
                    VALUES ('wildfire', 'demo_seed', :ext, :ts,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :intensity, CAST(:meta AS JSONB))
                    ON CONFLICT (source, external_id) DO UPDATE
                        SET intensity = EXCLUDED.intensity, occurred_at = EXCLUDED.occurred_at
                """),
                {
                    "ext": f"wildfire-{i}",
                    "ts": _utc(rng.uniform(0.5, 18)),
                    "lat": lat, "lon": lon, "intensity": frp,
                    "meta": __import__("json").dumps({"frp": frp, "confidence": "h"}),
                },
            )
            inserted += 1

        # Landslides
        for i, (name, lat, lon, meta) in enumerate(LANDSLIDES):
            await sess.execute(
                text("""
                    INSERT INTO events (hazard_type, source, external_id, occurred_at,
                        location, intensity, metadata)
                    VALUES ('landslide', 'demo_seed', :ext, :ts,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :intensity, CAST(:meta AS JSONB))
                    ON CONFLICT (source, external_id) DO UPDATE
                        SET intensity = EXCLUDED.intensity, occurred_at = EXCLUDED.occurred_at
                """),
                {
                    "ext": f"landslide-{i}",
                    "ts": _utc(rng.uniform(2, 48)),
                    "lat": lat, "lon": lon, "intensity": 1.0,
                    "meta": __import__("json").dumps({**meta, "title": name}),
                },
            )
            inserted += 1

        # Mid-magnitude India earthquakes so the heatmap has signal
        india_quakes = [
            (28.71, 77.10, 4.2, "Delhi region"),
            (34.08, 74.80, 5.1, "near Srinagar"),
            (31.10, 77.17, 4.4, "Shimla region"),
            (27.18, 88.61, 4.8, "Sikkim"),
            (26.14, 91.74, 5.2, "near Guwahati"),
            (15.31, 75.71, 3.8, "Karnataka interior"),
            (23.03, 72.58, 3.9, "Gujarat"),
        ]
        for i, (lat, lon, mag, place) in enumerate(india_quakes):
            await sess.execute(
                text("""
                    INSERT INTO events (hazard_type, source, external_id, occurred_at,
                        location, magnitude, depth_km, intensity, metadata)
                    VALUES ('earthquake', 'demo_seed', :ext, :ts,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :mag, :depth, :mag, CAST(:meta AS JSONB))
                    ON CONFLICT (source, external_id) DO UPDATE
                        SET magnitude = EXCLUDED.magnitude, occurred_at = EXCLUDED.occurred_at
                """),
                {
                    "ext": f"quake-india-{i}",
                    "ts": _utc(rng.uniform(2, 240)),
                    "lat": lat, "lon": lon,
                    "mag": mag, "depth": rng.uniform(8, 30),
                    "meta": __import__("json").dumps({"place": place, "title": f"M {mag:.1f} — {place}"}),
                },
            )
            inserted += 1

        await sess.commit()
        print(f"Seeded {inserted} demo events across hazard types.")


if __name__ == "__main__":
    asyncio.run(main())
