"""Prediction endpoints — Phase 2 wires in ML models and LLM explanations."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ml.seismic_autoencoder import omori_aftershock_probability
from app.schemas.predict import (
    CyclonePrediction,
    EarthquakePrediction,
    FloodPrediction,
    LandslidePrediction,
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
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
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

    # Check for recent mainshock (M >= 4.5) for aftershock probability placeholder
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
            "recent": datetime.now(timezone.utc) - timedelta(days=7),
        },
    )
    ms = mainshock.fetchone()

    aftershock_24h = None
    aftershock_7d = None
    if ms:
        hours_since = (datetime.now(timezone.utc) - ms.occurred_at).total_seconds() / 3600
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
    # Phase 1: return latest CWC/GFH data for the basin
    result = await session.execute(
        text("""
            SELECT metadata FROM events
            WHERE hazard_type = 'flood'
              AND (metadata->>'basin' = :basin OR metadata->>'gauge_id' = :basin)
            ORDER BY occurred_at DESC LIMIT 1
        """),
        {"basin": basin_id},
    )
    row = result.fetchone()
    return FloodPrediction(
        basin_id=basin_id,
        basin_name=row.metadata.get("basin") if row and row.metadata else basin_id,
        forecast=[],  # Phase 2: LSTM discharge forecast
        model_version="phase1-passthrough",
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

    minlon, minlat, maxlon, maxlat = [float(p) for p in parts]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    result = await session.execute(
        text("""
            SELECT count(*) as cnt, avg(intensity) as avg_frp
            FROM events
            WHERE hazard_type = 'wildfire'
              AND occurred_at >= :cutoff
              AND ST_Intersects(
                  location,
                  ST_MakeEnvelope(:minlon, :minlat, :maxlon, :maxlat, 4326)::geography
              )
        """),
        {"cutoff": cutoff, "minlon": minlon, "minlat": minlat, "maxlon": maxlon, "maxlat": maxlat},
    )
    row = result.fetchone()
    return WildfirePrediction(
        total_hotspots=row.cnt or 0,
        clusters=[],  # Phase 2: DBSCAN clustering
    )


@router.get("/landslide", response_model=LandslidePrediction)
async def predict_landslide(
    lat: float = Query(...),
    lon: float = Query(...),
    session: AsyncSession = Depends(get_session),
) -> LandslidePrediction:
    # Phase 1: static lookup — no real inference yet
    return LandslidePrediction(
        gsi_zone=None,  # Phase 2: GSI overlay lookup
        rainfall_threshold_exceeded=False,
        risk_level="unknown",
    )
