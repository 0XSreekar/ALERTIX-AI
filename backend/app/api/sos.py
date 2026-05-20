"""SOS citizen report API — POST /api/sos, GET /api/sos/mine, GET /api/sos/feed."""

import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, current_user, current_user_optional, require_role
from app.db import async_session_factory, get_session
from app.logging import get_logger
from app.schemas.sos import SosCreate

log = get_logger(__name__)
router = APIRouter(prefix="/api/sos", tags=["sos"])

limiter = Limiter(key_func=get_remote_address)


async def _run_llm_triage(sos_id: str, raw_text: str, location_text: str) -> None:
    """Background task: LLM triage scoring written back to DB."""
    try:
        from app.llm import provider as llm
        from app.llm.prompts import SOS_TRIAGE

        prompt = SOS_TRIAGE.format(message=raw_text, location=location_text or "unknown")
        raw, _provider = await llm.generate(prompt)
        if not raw:
            return
        import re

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return
        data = json.loads(match.group(0))
        async with async_session_factory() as sess:
            await sess.execute(
                text("""
                    UPDATE sos_reports
                    SET urgency_score = :score,
                        llm_summary   = :summary,
                        triaged       = TRUE
                    WHERE id = :id
                """),
                {"score": data.get("urgency_score"), "summary": data.get("summary"), "id": sos_id},
            )
            await sess.commit()
    except Exception as exc:
        log.warning("sos_triage_failed sos_id=%s err=%s", sos_id, exc)


@router.post("")
@limiter.limit("5/hour")
async def submit_sos(
    request: Request,
    body: SosCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser | None = Depends(current_user_optional),
) -> dict:
    if not body.consent_given:
        raise HTTPException(
            status_code=400,
            detail="Consent checkbox is required per DPDPA 2023",
        )

    user_id = user.user_id if user else None

    params: dict = {
        "user_id": user_id,
        "raw_text": body.raw_text,
        "language": body.language,
    }
    location_clause = "NULL"
    if body.latitude is not None and body.longitude is not None:
        location_clause = "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography"
        params["lon"] = body.longitude
        params["lat"] = body.latitude

    result = await session.execute(
        text(f"""
            INSERT INTO sos_reports (user_id, raw_text, language, location)
            VALUES (:user_id, :raw_text, :language, {location_clause})
            RETURNING id, created_at
        """),
        params,
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="SOS insert failed")
    await session.commit()

    # Audit log
    await session.execute(
        text("""
            INSERT INTO audit_log (actor_user_id, action, target_table, target_id, payload)
            VALUES (:uid, 'sos_submitted', 'sos_reports', :target_id, CAST(:payload AS jsonb))
        """),
        {
            "uid": user_id,
            "target_id": row.id,
            "payload": json.dumps({"language": body.language}),
        },
    )
    await session.commit()

    log.info("sos_submitted", sos_id=str(row.id), has_location=body.latitude is not None)

    # Kick off async LLM triage (non-blocking)
    background_tasks.add_task(_run_llm_triage, str(row.id), body.raw_text, "")

    return {"id": str(row.id), "created_at": row.created_at.isoformat(), "status": "received"}


@router.get("/mine")
async def my_sos_reports(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(current_user),
) -> dict:
    result = await session.execute(
        text("""
            SELECT id, user_id, raw_text, language,
                   ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon,
                   extracted_location_text, urgency_score, triaged,
                   llm_summary, related_event_id, created_at
            FROM sos_reports
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"uid": user.user_id, "limit": limit},
    )
    rows = result.fetchall()
    return {
        "reports": [
            {
                "id": str(r.id),
                "raw_text": r.raw_text,
                "language": r.language,
                "latitude": r.lat,
                "longitude": r.lon,
                "urgency_score": r.urgency_score,
                "triaged": r.triaged,
                "llm_summary": r.llm_summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/feed")
async def sos_feed(
    min_urgency: float = Query(3.0, ge=0, le=5),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(require_role("official", "admin")),
) -> dict:
    result = await session.execute(
        text("""
            SELECT id, user_id, raw_text, language,
                   ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon,
                   extracted_location_text, urgency_score, triaged,
                   llm_summary, related_event_id, created_at
            FROM sos_reports
            WHERE urgency_score >= :min_urgency OR urgency_score IS NULL
            ORDER BY urgency_score DESC NULLS LAST, created_at DESC
            LIMIT :limit
        """),
        {"min_urgency": min_urgency, "limit": limit},
    )
    rows = result.fetchall()
    return {
        "reports": [
            {
                "id": str(r.id),
                "raw_text": r.raw_text,
                "language": r.language,
                "latitude": r.lat,
                "longitude": r.lon,
                "extracted_location_text": r.extracted_location_text,
                "urgency_score": r.urgency_score,
                "triaged": r.triaged,
                "llm_summary": r.llm_summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.delete("/mine/{sos_id}")
async def delete_my_sos(
    sos_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(current_user),
) -> dict:
    result = await session.execute(
        text("DELETE FROM sos_reports WHERE id = :id AND user_id = :uid RETURNING id"),
        {"id": sos_id, "uid": user.user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Report not found or not yours")
    await session.commit()
    return {"deleted": True}
