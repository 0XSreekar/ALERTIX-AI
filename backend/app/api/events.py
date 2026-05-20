"""Public events API — GET /api/events, /api/events/{id}, /api/events/recent."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


def _row_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "hazard_type": row.hazard_type,
        "source": row.source,
        "external_id": row.external_id,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "latitude": row.lat,
        "longitude": row.lon,
        "magnitude": row.magnitude,
        "depth_km": row.depth_km,
        "intensity": row.intensity,
        "metadata": row.metadata,
        "anomaly_score": row.anomaly_score,
        "probability": row.probability,
        "model_version": row.model_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
async def list_events(
    hazard_type: str | None = None,
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    bbox: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict:
    conditions = []
    params: dict = {"limit": limit, "offset": offset}

    if hazard_type:
        conditions.append("hazard_type = :hazard_type")
        params["hazard_type"] = hazard_type
    if from_dt:
        conditions.append("occurred_at >= :from_dt")
        params["from_dt"] = from_dt
    if to_dt:
        conditions.append("occurred_at <= :to_dt")
        params["to_dt"] = to_dt
    if bbox:
        parts = bbox.split(",")
        if len(parts) == 4:
            try:
                minlon, minlat, maxlon, maxlat = [float(p) for p in parts]
                conditions.append(
                    "ST_Intersects(location, ST_MakeEnvelope(:minlon, :minlat, :maxlon, :maxlat, 4326)::geography)"
                )
                params.update(
                    {"minlon": minlon, "minlat": minlat, "maxlon": maxlon, "maxlat": maxlat}
                )
            except ValueError:
                pass

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT id, hazard_type, source, external_id, occurred_at,
               ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon,
               magnitude, depth_km, intensity, metadata,
               anomaly_score, probability, model_version, created_at
        FROM events {where}
        ORDER BY occurred_at DESC
        LIMIT :limit OFFSET :offset
    """
    result = await session.execute(text(query), params)
    rows = result.fetchall()

    count_query = f"SELECT count(*) FROM events {where}"
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_query), count_params)).scalar()

    return {
        "events": [_row_to_dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/recent")
async def recent_events(
    hazard_type: str | None = None,
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    params: dict = {"cutoff": cutoff}
    type_filter = ""
    if hazard_type:
        type_filter = "AND hazard_type = :hazard_type"
        params["hazard_type"] = hazard_type

    result = await session.execute(
        text(f"""
            SELECT id, hazard_type, source, external_id, occurred_at,
                   ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon,
                   magnitude, depth_km, intensity, metadata,
                   anomaly_score, probability, model_version, created_at
            FROM events
            WHERE occurred_at >= :cutoff {type_filter}
            ORDER BY occurred_at DESC
            LIMIT 500
        """),
        params,
    )
    rows = result.fetchall()
    return {"events": [_row_to_dict(r) for r in rows], "hours": hours}


@router.get("/{event_id}")
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        text("""
            SELECT id, hazard_type, source, external_id, occurred_at,
                   ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon,
                   magnitude, depth_km, intensity, metadata,
                   anomaly_score, probability, model_version, created_at
            FROM events WHERE id = :id
        """),
        {"id": event_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    return _row_to_dict(row)
