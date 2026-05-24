"""Prediction endpoints wired to statistical and ML-derived hazard intelligence."""

import logging
from datetime import UTC, datetime, timedelta

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.ingestion.open_meteo import get_rainfall_forecast
from app.ml.cyclone_track import extrapolate_track
from app.ml.flood_lstm import FloodLSTM
from app.ml.landslide_rules import evaluate as landslide_evaluate
from app.ml.seismic_autoencoder import omori_aftershock_probability
from app.ml.wildfire_cluster import cluster_hotspots
from app.schemas.predict import (
    CyclonePrediction,
    EarthquakePrediction,
    FloodForecastPoint,
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
    cutoff = datetime.now(UTC) - timedelta(days=30)
    result = await session.execute(
        text("""
            SELECT count(*) as cnt, avg(anomaly_score) as avg_anomaly
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
        anomaly_score=float(row.avg_anomaly) if row and row.avg_anomaly else None,
        aftershock_24h_probability=aftershock_24h,
        aftershock_7d_probability=aftershock_7d,
        recent_event_count=int(row.cnt) if row else 0,
        model_version="phase2-omori",
    )


_flood_lstm: FloodLSTM | None = None
_flood_log = logging.getLogger(__name__)


def _get_flood_lstm() -> FloodLSTM | None:
    global _flood_lstm
    if _flood_lstm is not None:
        return _flood_lstm
    checkpoint = get_settings().flood_lstm_checkpoint
    if not checkpoint:
        return None
    try:
        model = FloodLSTM(checkpoint=checkpoint)
        if model.loaded:
            _flood_lstm = model
            _flood_log.info("flood_lstm_loaded checkpoint=%s", checkpoint)
            return _flood_lstm
    except Exception as exc:
        _flood_log.warning("flood_lstm_load_failed: %s", exc)
    return None


@router.get("/flood", response_model=FloodPrediction)
async def predict_flood(
    basin_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> FloodPrediction:
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
        {"basin": f"%{basin_id}%", "cutoff": datetime.now(UTC) - timedelta(days=7)},
    )
    rows = result.fetchall()

    basin_name = basin_id
    if rows:
        meta = rows[0].metadata or {}
        basin_name = meta.get("basin") or meta.get("gauge_name") or basin_id

    # Try FloodLSTM if checkpoint is configured and we have enough history
    lstm = _get_flood_lstm()
    if lstm is not None and len(rows) >= 7:
        try:
            history_rows = list(reversed(rows))[-7:]
            history = np.array(
                [[float(r.intensity or 0.0), float(r.intensity or 0.0)] for r in history_rows],
                dtype=np.float32,
            )
            fc = lstm.predict(history)
            forecast = [
                FloodForecastPoint(hour=24, discharge_p10=round(fc.forecast_24h * 0.75, 3),
                                   discharge_p50=round(fc.forecast_24h, 3),
                                   discharge_p90=round(fc.forecast_24h * 1.25, 3)),
                FloodForecastPoint(hour=48, discharge_p10=round(fc.forecast_48h * 0.75, 3),
                                   discharge_p50=round(fc.forecast_48h, 3),
                                   discharge_p90=round(fc.forecast_48h * 1.25, 3)),
                FloodForecastPoint(hour=72, discharge_p10=round(fc.forecast_72h * 0.75, 3),
                                   discharge_p50=round(fc.forecast_72h, 3),
                                   discharge_p90=round(fc.forecast_72h * 1.25, 3)),
            ]
            return FloodPrediction(
                basin_id=basin_id,
                basin_name=basin_name,
                forecast=forecast,
                official_bulletin_agrees=fc.risk_tier in ("HIGH", "CRITICAL"),
                model_version="flood-lstm-v1",
            )
        except Exception as exc:
            _flood_log.warning("flood_lstm_predict_failed basin=%s: %s", basin_id, exc)

    # Fallback: passthrough CWC readings as forecast points
    forecast = []
    for i, row in enumerate(reversed(rows)):
        value = float(row.intensity or 0.0)
        forecast.append(
            FloodForecastPoint(
                hour=i,
                discharge_p10=round(value * 0.7, 2),
                discharge_p50=round(value, 2),
                discharge_p90=round(value * 1.3, 2),
            )
        )
    return FloodPrediction(
        basin_id=basin_id,
        basin_name=basin_name,
        forecast=forecast,
        official_bulletin_agrees=any(r.intensity and r.intensity >= 2 for r in rows)
        if rows
        else None,
        model_version="phase2-cwc-passthrough",
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
            WHERE hazard_type = 'cyclone' AND location IS NOT NULL
            ORDER BY occurred_at DESC LIMIT 10
        """),
    )
    rows = result.fetchall()
    if not rows:
        return CyclonePrediction()
    latest = rows[0]
    meta = latest.metadata or {}
    positions = [
        {
            "lat": row.lat,
            "lon": row.lon,
            "occurred_at": row.occurred_at,
            "wind_kmh": (row.metadata or {}).get("wind_kmh"),
        }
        for row in rows
    ]
    track = extrapolate_track(positions, horizon_hours=12, step_hours=3)
    return CyclonePrediction(
        storm_id=str(latest.id),
        storm_name=meta.get("title", "Unknown"),
        current_lat=latest.lat,
        current_lon=latest.lon,
        wind_speed_kmh=meta.get("wind_kmh"),
        track_points=track["extrapolated"],
        impact_radius_km=track["impact_radius_km"] or None,
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
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    result = await session.execute(
        text("""
            SELECT ST_Y(location::geometry) as lat,
                   ST_X(location::geometry) as lon,
                   intensity, occurred_at
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
    hotspots = [
        {"lat": row.lat, "lon": row.lon, "frp": row.intensity, "occurred_at": row.occurred_at}
        for row in rows
    ]
    return WildfirePrediction(total_hotspots=len(hotspots), clusters=cluster_hotspots(hotspots))


@router.get("/landslide", response_model=LandslidePrediction)
async def predict_landslide(
    lat: float = Query(...),
    lon: float = Query(...),
    session: AsyncSession = Depends(get_session),
) -> LandslidePrediction:
    cumulative_mm: float | None = None
    try:
        data = await get_rainfall_forecast(lat, lon, hours=24)
        precipitation = data.get("hourly", {}).get("precipitation", [])
        if precipitation:
            cumulative_mm = round(sum(float(p or 0.0) for p in precipitation[:24]), 2)
    except Exception:
        cumulative_mm = None
    result = landslide_evaluate(lat, lon, cumulative_mm)
    return LandslidePrediction(
        gsi_zone=result.gsi_zone,
        rainfall_threshold_exceeded=result.rainfall_threshold_exceeded,
        cumulative_rainfall_mm=result.cumulative_rainfall_mm,
        threshold_mm=result.threshold_mm,
        risk_level=result.risk_level,
    )
