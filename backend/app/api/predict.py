"""Prediction endpoints — ML models wired for earthquake, flood, wildfire, landslide."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.open_meteo import get_rainfall_forecast
from app.ml.landslide_rules import evaluate as landslide_evaluate
from app.ml.seismic_autoencoder import omori_aftershock_probability
from app.ml.wildfire_cluster import cluster_hotspots
from app.schemas.predict import (
    CyclonePrediction,
    EarthquakePrediction,
    FloodForecastPoint,
    FloodPrediction,
    LandslidePrediction,
    WildfireCluster,
    WildfirePrediction,
)

router = APIRouter(prefix="/api/predict", tags=["predict"])


@router.get("/earthquake", response_model=EarthquakePrediction)
async def predict_earthquake(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(200, ge=10, le=2000),
    session: AsyncSession = Depends(get_session),
) -> EarthquakePrediction:
    cutoff = datetime.now(UTC) - timedelta(days=30)
    result = await session.execute(
        text("""
            SELECT count(*) as cnt,
                   avg(magnitude) as avg_mag,
                   max(magnitude) as max_mag,
                   avg(anomaly_score) as avg_anomaly
            FROM events
            WHERE hazard_type = 'earthquake'
              AND occurred_at >= :cutoff
              AND ST_DWithin(
                  location,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  :radius_m
              )
        """),
        {"lat": lat, "lon": lon, "radius_m": radius_km * 1000, "cutoff": cutoff},
    )
    row = result.fetchone()

    mainshock = await session.execute(
        text("""
            SELECT id, magnitude, occurred_at FROM events
            WHERE hazard_type = 'earthquake' AND magnitude >= 4.5
              AND occurred_at >= :recent
              AND ST_DWithin(
                  location,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  :radius_m
              )
            ORDER BY magnitude DESC LIMIT 1
        """),
        {
            "lat": lat,
            "lon": lon,
            "radius_m": radius_km * 1000,
            "recent": datetime.now(UTC) - timedelta(days=7),
        },
    )
    ms = mainshock.fetchone()

    aftershock_24h = None
    aftershock_7d = None
    if ms:
        hours_since = (datetime.now(UTC) - ms.occurred_at).total_seconds() / 3600
        aftershock_24h = omori_aftershock_probability(ms.magnitude, hours_since)
        aftershock_7d = omori_aftershock_probability(ms.magnitude, max(0, hours_since - 144))

    return EarthquakePrediction(
        anomaly_score=float(row.avg_anomaly) if row.avg_anomaly else None,
        aftershock_24h_probability=aftershock_24h,
        aftershock_7d_probability=aftershock_7d,
        recent_event_count=row.cnt or 0,
        model_version="phase2-omori",
    )


@router.get("/flood", response_model=FloodPrediction)
async def predict_flood(
    basin_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> FloodPrediction:
    # Query recent CWC / GFH events for this basin (last 7 days)
    result = await session.execute(
        text("""
            SELECT occurred_at, intensity, metadata
            FROM events
            WHERE hazard_type = 'flood'
              AND occurred_at >= :cutoff
              AND (
                  metadata->>'basin' ILIKE :basin
                  OR metadata->>'gauge_name' ILIKE :basin
                  OR metadata->>'gauge_id' ILIKE :basin
              )
            ORDER BY occurred_at DESC
            LIMIT 24
        """),
        {
            "basin": f"%{basin_id}%",
            "cutoff": datetime.now(UTC) - timedelta(days=7),
        },
    )
    rows = result.fetchall()

    # Build forecast time-series from available gauge data.
    # intensity: GFH maps danger=3, warning=2, watch=1; CWC stores raw reading.
    # We use intensity as p50 and ±30% for uncertainty bands.
    forecast: list[FloodForecastPoint] = []
    for i, row in enumerate(reversed(rows)):
        val = float(row.intensity or 0.0)
        forecast.append(
            FloodForecastPoint(
                hour=i,
                discharge_p10=round(val * 0.7, 2),
                discharge_p50=round(val, 2),
                discharge_p90=round(val * 1.3, 2),
            )
        )

    # GFH agreement: any event with intensity >= 2 (warning/danger)
    gfh_agrees = any(r.intensity and r.intensity >= 2 for r in rows)

    basin_name = None
    if rows:
        meta = rows[0].metadata or {}
        basin_name = meta.get("basin") or meta.get("gauge_name") or basin_id

    return FloodPrediction(
        basin_id=basin_id,
        basin_name=basin_name or basin_id,
        forecast=forecast,
        google_flood_hub_agrees=gfh_agrees if rows else None,
        model_version="phase2-gfh-cwc-passthrough",
    )


@router.get("/cyclone", response_model=CyclonePrediction)
async def predict_cyclone(
    storm_id: str = Query("latest"),
    session: AsyncSession = Depends(get_session),
) -> CyclonePrediction:
    result = await session.execute(
        text("""
            SELECT id, metadata,
                   ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon,
                   occurred_at
            FROM events
            WHERE hazard_type = 'cyclone'
            ORDER BY occurred_at DESC LIMIT 1
        """),
    )
    row = result.fetchone()
    if not row:
        return CyclonePrediction()

    meta = row.metadata or {}
    return CyclonePrediction(
        storm_id=str(row.id),
        storm_name=meta.get("title", "Unknown"),
        current_lat=row.lat,
        current_lon=row.lon,
    )


@router.get("/wildfire", response_model=WildfirePrediction)
async def predict_wildfire(
    bbox: str = Query("65,5,100,40"),
    session: AsyncSession = Depends(get_session),
) -> WildfirePrediction:
    parts = bbox.split(",")
    if len(parts) != 4:
        return WildfirePrediction()

    minlon, minlat, maxlon, maxlat = (float(p) for p in parts)
    cutoff = datetime.now(UTC) - timedelta(hours=24)

    result = await session.execute(
        text("""
            SELECT ST_Y(location::geometry) as lat,
                   ST_X(location::geometry) as lon,
                   COALESCE(intensity, 0) as frp
            FROM events
            WHERE hazard_type = 'wildfire'
              AND occurred_at >= :cutoff
              AND location IS NOT NULL
              AND ST_Intersects(
                  location,
                  ST_MakeEnvelope(:minlon, :minlat, :maxlon, :maxlat, 4326)::geography
              )
        """),
        {"cutoff": cutoff, "minlon": minlon, "minlat": minlat, "maxlon": maxlon, "maxlat": maxlat},
    )
    rows = result.fetchall()

    points = [(float(r.lat), float(r.lon), float(r.frp)) for r in rows]
    raw_clusters = cluster_hotspots(points)

    clusters = [
        WildfireCluster(
            cluster_id=c.cluster_id,
            centroid_lat=c.centroid_lat,
            centroid_lon=c.centroid_lon,
            hotspot_count=c.hotspot_count,
            mean_frp=c.mean_frp,
            risk=c.risk,
        )
        for c in raw_clusters
    ]

    return WildfirePrediction(
        total_hotspots=len(points),
        clusters=clusters,
    )


@router.get("/landslide", response_model=LandslidePrediction)
async def predict_landslide(
    lat: float = Query(...),
    lon: float = Query(...),
    session: AsyncSession = Depends(get_session),
) -> LandslidePrediction:
    # Fetch 24h accumulated rainfall from Open-Meteo
    cumulative_mm: float | None = None
    try:
        data = await get_rainfall_forecast(lat, lon, hours=24)
        hourly = data.get("hourly", {})
        precip_list = hourly.get("precipitation", [])
        if precip_list:
            cumulative_mm = round(sum(precip_list[:24]), 2)
    except Exception:
        pass  # proceed without rainfall — zone classification still works

    result = landslide_evaluate(lat, lon, cumulative_mm)

    return LandslidePrediction(
        gsi_zone=result.gsi_zone,
        rainfall_threshold_exceeded=result.rainfall_threshold_exceeded,
        cumulative_rainfall_mm=result.cumulative_rainfall_mm,
        threshold_mm=result.threshold_mm,
        risk_level=result.risk_level,
    )
