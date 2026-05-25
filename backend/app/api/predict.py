"""Prediction endpoints wired to statistical and ML-derived hazard intelligence."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.open_meteo import get_rainfall_forecast
from app.ml.cyclone_track import extrapolate_track
from app.ml.landslide_rules import evaluate as landslide_evaluate
from app.ml.risk_index import score as risk_index_score
from app.ml.seismic_autoencoder import omori_aftershock_probability, score_sequence
from app.ml.wildfire_cluster import cluster_hotspots
from app.schemas.predict import (
    CyclonePrediction,
    EarthquakePrediction,
    FloodForecastPoint,
    FloodPrediction,
    LandslidePrediction,
    RiskGridCell,
    RiskGridResponse,
    RiskIndexFeatures,
    RiskIndexPrediction,
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

    # Live LSTM anomaly score over the last 30 events in this region
    seq_result = await session.execute(
        text("""
            SELECT
              ST_Y(location::geometry) AS lat,
              ST_X(location::geometry) AS lon,
              COALESCE(depth_km, 0) AS depth,
              COALESCE(magnitude, 0) AS magnitude
            FROM events
            WHERE hazard_type = 'earthquake'
              AND occurred_at >= :cutoff
              AND ST_DWithin(
                  location,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  :radius_m
              )
            ORDER BY occurred_at DESC
            LIMIT 30
        """),
        {"lat": lat, "lon": lon, "radius_m": radius_km * 1000, "cutoff": cutoff},
    )
    seq_rows = seq_result.fetchall()
    lstm_score: float | None = None
    if len(seq_rows) >= 5:
        # 8 features: lat, lon, depth, magnitude, rms=0, gap=0, horizontalError=0, count_30d
        n = len(seq_rows)
        seq = [[r.lat, r.lon, r.depth, r.magnitude, 0.0, 0.0, 0.0, float(n)] for r in seq_rows]
        raw = score_sequence(seq)
        if raw >= 0:
            lstm_score = raw

    return EarthquakePrediction(
        anomaly_score=lstm_score
        if lstm_score is not None
        else (float(row.avg_anomaly) if row and row.avg_anomaly else None),
        aftershock_24h_probability=aftershock_24h,
        aftershock_7d_probability=aftershock_7d,
        recent_event_count=int(row.cnt) if row else 0,
        model_version="phase2-lstm-ae+omori",
    )


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

    # Build 7-day history (rainfall_mm, river_level_m) for LSTM
    forecast: list[FloodForecastPoint] = []
    model_version = "phase2-cwc-passthrough"

    if len(rows) >= 7:
        try:
            import numpy as np

            from app.config import get_settings
            from app.ml.flood_lstm import FloodLSTM

            ckpt = get_settings().flood_lstm_checkpoint
            if ckpt:
                last7 = list(reversed(rows[:7]))
                history = np.array(
                    [
                        [
                            float((r.metadata or {}).get("rainfall_mm", 0.0)),
                            float(r.intensity or 0.0),
                        ]
                        for r in last7
                    ],
                    dtype=np.float32,
                )
                lstm = FloodLSTM(checkpoint=ckpt)
                if lstm.loaded:
                    fc = lstm.predict(history)
                    for hour_offset, level in zip(
                        (24, 48, 72),
                        (fc.forecast_24h, fc.forecast_48h, fc.forecast_72h),
                        strict=False,
                    ):
                        forecast.append(
                            FloodForecastPoint(
                                hour=hour_offset,
                                discharge_p10=round(level * 0.8, 2),
                                discharge_p50=round(level, 2),
                                discharge_p90=round(level * 1.2, 2),
                            )
                        )
                    model_version = "phase2-flood-lstm"
        except Exception as exc:  # pragma: no cover — degrade to passthrough
            from app.logging import get_logger

            get_logger(__name__).warning("flood_lstm_inference_failed: %s", exc)

    if not forecast:
        # Fallback: passthrough of observed intensities
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

    basin_name = basin_id
    if rows:
        meta = rows[0].metadata or {}
        basin_name = meta.get("basin") or meta.get("gauge_name") or basin_id
    return FloodPrediction(
        basin_id=basin_id,
        basin_name=basin_name,
        forecast=forecast,
        official_bulletin_agrees=any(r.intensity and r.intensity >= 2 for r in rows)
        if rows
        else None,
        model_version=model_version,
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


def _risk_tier(score: float) -> str:
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.55:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


@router.get("/risk", response_model=RiskIndexPrediction)
async def predict_risk(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(150, ge=10, le=2000),
    session: AsyncSession = Depends(get_session),
) -> RiskIndexPrediction:
    """Composite multi-hazard risk index for a point + radius."""
    radius_m = radius_km * 1000
    now = datetime.now(UTC)

    eq_row = (
        await session.execute(
            text("""
                SELECT count(*) AS cnt, COALESCE(max(magnitude), 0) AS mx
                FROM events
                WHERE hazard_type = 'earthquake'
                  AND occurred_at >= :cutoff
                  AND ST_DWithin(
                      location,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                      :radius_m
                  )
            """),
            {"lon": lon, "lat": lat, "radius_m": radius_m, "cutoff": now - timedelta(days=30)},
        )
    ).fetchone()

    flood_row = (
        await session.execute(
            text("""
                SELECT COALESCE(max(intensity), 0) AS mx
                FROM events
                WHERE hazard_type = 'flood'
                  AND occurred_at >= :cutoff
                  AND ST_DWithin(
                      location,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                      :radius_m
                  )
            """),
            {"lon": lon, "lat": lat, "radius_m": radius_m, "cutoff": now - timedelta(days=3)},
        )
    ).fetchone()

    fire_row = (
        await session.execute(
            text("""
                SELECT count(*) AS cnt
                FROM events
                WHERE hazard_type = 'wildfire'
                  AND occurred_at >= :cutoff
                  AND ST_DWithin(
                      location,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                      :radius_m
                  )
            """),
            {"lon": lon, "lat": lat, "radius_m": radius_m, "cutoff": now - timedelta(hours=24)},
        )
    ).fetchone()

    cyc_row = (
        await session.execute(
            text("""
                SELECT COALESCE(max((metadata->>'wind_kmh')::float), 0) AS mx
                FROM events
                WHERE hazard_type = 'cyclone'
                  AND occurred_at >= :cutoff
                  AND ST_DWithin(
                      location,
                      ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                      :radius_m
                  )
            """),
            {"lon": lon, "lat": lat, "radius_m": radius_m, "cutoff": now - timedelta(hours=48)},
        )
    ).fetchone()

    rainfall_72h = 0.0
    try:
        meteo = await get_rainfall_forecast(lat, lon, hours=72)
        precips = meteo.get("hourly", {}).get("precipitation", [])
        rainfall_72h = float(sum((p or 0.0) for p in precips[:72]))
    except Exception:
        pass

    landslide_score = 0.0
    try:
        landslide_score = float(landslide_evaluate(lat, lon, rainfall_72h).risk_level == "high")
    except Exception:
        pass

    features = RiskIndexFeatures(
        eq_count_30d=float(eq_row.cnt or 0),
        eq_max_magnitude=float(eq_row.mx or 0),
        flood_max_intensity=float(flood_row.mx or 0),
        rainfall_72h_mm=rainfall_72h,
        wildfire_count_24h=float(fire_row.cnt or 0),
        cyclone_wind_kmh=float(cyc_row.mx or 0),
        landslide_rule_score=landslide_score,
    )
    raw = risk_index_score(features.model_dump())
    risk = None if raw < 0 else raw
    return RiskIndexPrediction(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        risk_index=risk,
        tier=_risk_tier(risk if risk is not None else 0.0),
        features=features,
    )


@router.get("/risk/grid", response_model=RiskGridResponse)
async def predict_risk_grid(
    minlat: float = Query(6.0, ge=-90, le=90),
    minlon: float = Query(68.0, ge=-180, le=180),
    maxlat: float = Query(36.0, ge=-90, le=90),
    maxlon: float = Query(98.0, ge=-180, le=180),
    step_deg: float = Query(2.0, ge=0.5, le=10.0),
    session: AsyncSession = Depends(get_session),
) -> RiskGridResponse:
    """Coarse risk grid over a bbox (default: India). Skips per-cell rainfall
    lookup for speed; relies on cached event tables only."""
    radius_km = max(step_deg * 60.0, 60.0)
    radius_m = radius_km * 1000
    now = datetime.now(UTC)
    cutoff_30d = now - timedelta(days=30)
    cutoff_3d = now - timedelta(days=3)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_48h = now - timedelta(hours=48)

    cells: list[RiskGridCell] = []
    lat = minlat
    while lat <= maxlat:
        lon = minlon
        while lon <= maxlon:
            eq = (
                await session.execute(
                    text("""
                        SELECT count(*) AS cnt, COALESCE(max(magnitude), 0) AS mx
                        FROM events
                        WHERE hazard_type = 'earthquake'
                          AND occurred_at >= :cutoff
                          AND ST_DWithin(location,
                              ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :r)
                    """),
                    {"lon": lon, "lat": lat, "r": radius_m, "cutoff": cutoff_30d},
                )
            ).fetchone()
            fl = (
                await session.execute(
                    text("""
                        SELECT COALESCE(max(intensity), 0) AS mx FROM events
                        WHERE hazard_type = 'flood' AND occurred_at >= :cutoff
                          AND ST_DWithin(location,
                              ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :r)
                    """),
                    {"lon": lon, "lat": lat, "r": radius_m, "cutoff": cutoff_3d},
                )
            ).fetchone()
            wf = (
                await session.execute(
                    text("""
                        SELECT count(*) AS cnt FROM events
                        WHERE hazard_type = 'wildfire' AND occurred_at >= :cutoff
                          AND ST_DWithin(location,
                              ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :r)
                    """),
                    {"lon": lon, "lat": lat, "r": radius_m, "cutoff": cutoff_24h},
                )
            ).fetchone()
            cy = (
                await session.execute(
                    text("""
                        SELECT COALESCE(max((metadata->>'wind_kmh')::float), 0) AS mx
                        FROM events WHERE hazard_type = 'cyclone'
                          AND occurred_at >= :cutoff
                          AND ST_DWithin(location,
                              ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :r)
                    """),
                    {"lon": lon, "lat": lat, "r": radius_m, "cutoff": cutoff_48h},
                )
            ).fetchone()

            feats = {
                "eq_count_30d": float(eq.cnt or 0),
                "eq_max_magnitude": float(eq.mx or 0),
                "flood_max_intensity": float(fl.mx or 0),
                "rainfall_72h_mm": 0.0,
                "wildfire_count_24h": float(wf.cnt or 0),
                "cyclone_wind_kmh": float(cy.mx or 0),
                "landslide_rule_score": 0.0,
            }
            raw = risk_index_score(feats)
            if raw < 0:
                # XGBoost weights missing — derive a heuristic so grid is non-empty
                raw = min(
                    1.0,
                    feats["eq_max_magnitude"] / 8.0 * 0.4
                    + min(feats["eq_count_30d"], 30) / 30.0 * 0.2
                    + feats["flood_max_intensity"] / 5.0 * 0.2
                    + min(feats["wildfire_count_24h"], 50) / 50.0 * 0.1
                    + feats["cyclone_wind_kmh"] / 220.0 * 0.1,
                )
            if raw > 0.02:
                cells.append(
                    RiskGridCell(lat=lat, lon=lon, risk_index=round(raw, 3), tier=_risk_tier(raw))
                )
            lon += step_deg
        lat += step_deg

    return RiskGridResponse(cells=cells, radius_km=radius_km)


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
