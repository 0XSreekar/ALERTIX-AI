"""Public alerts API — GET /api/alerts, /api/alerts/{id}, /api/alerts/region."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _row_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "hazard_type": row.hazard_type,
        "severity": row.severity,
        "title": row.title,
        "explanation": row.explanation,
        "explanation_lang": row.explanation_lang,
        "explanation_status": row.explanation_status,
        "probability": row.probability,
        "event_ids": [str(e) for e in row.event_ids] if row.event_ids else [],
        "model_version": row.model_version,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


@router.get("")
async def list_alerts(
    hazard_type: str | None = None,
    severity: str | None = None,
    active_only: bool = True,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict:
    conditions = []
    params: dict = {"limit": limit, "offset": offset}

    if hazard_type:
        conditions.append("hazard_type = :hazard_type")
        params["hazard_type"] = hazard_type
    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity
    if active_only:
        conditions.append("(expires_at IS NULL OR expires_at > :now)")
        params["now"] = datetime.now(UTC)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    count_result = await session.execute(
        text(f"SELECT COUNT(*) FROM alerts {where}"),
        count_params,
    )
    total: int = count_result.scalar() or 0

    result = await session.execute(
        text(f"""
            SELECT id, hazard_type, severity, title, explanation,
                   explanation_lang, explanation_status, probability,
                   event_ids, model_version, created_at, expires_at
            FROM alerts {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.fetchall()
    return {
        "alerts": [_row_to_dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/region")
async def alerts_by_region(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(50, ge=1, le=500),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict:
    count_result = await session.execute(
        text("""
            SELECT COUNT(*) FROM alerts
            WHERE (expires_at IS NULL OR expires_at > :now)
              AND ST_DWithin(
                  region,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  :radius_m
              )
        """),
        {"lat": lat, "lon": lon, "radius_m": radius_km * 1000, "now": datetime.now(UTC)},
    )
    total: int = count_result.scalar() or 0

    result = await session.execute(
        text("""
            SELECT id, hazard_type, severity, title, explanation,
                   explanation_lang, explanation_status, probability,
                   event_ids, model_version, created_at, expires_at
            FROM alerts
            WHERE (expires_at IS NULL OR expires_at > :now)
              AND ST_DWithin(
                  region,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  :radius_m
              )
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "lat": lat,
            "lon": lon,
            "radius_m": radius_km * 1000,
            "now": datetime.now(UTC),
            "limit": limit,
            "offset": offset,
        },
    )
    rows = result.fetchall()
    return {
        "alerts": [_row_to_dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{alert_id}")
async def get_alert(
    alert_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        text("""
            SELECT id, hazard_type, severity, title, explanation,
                   explanation_lang, explanation_status, probability,
                   event_ids, model_version, created_at, expires_at
            FROM alerts WHERE id = :id
        """),
        {"id": alert_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _row_to_dict(row)
