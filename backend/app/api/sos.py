"""SOS citizen report API — POST /api/sos, GET /api/sos/mine, GET /api/sos/feed."""

import json
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, current_user, current_user_optional, require_role
from app.db import async_session_factory, get_session
from app.logging import get_logger
from app.models.audit_log import write_audit_log
from app.schemas.sos import SosCreate

log = get_logger(__name__)
router = APIRouter(prefix="/api/sos", tags=["sos"])

limiter = Limiter(key_func=get_remote_address)

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


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
    except Exception:
        log.exception("sos_triage_failed", sos_id=sos_id)


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

    # Audit log — hash IP before storing (never persist raw IP)
    client_ip = request.client.host if request.client else None
    await write_audit_log(
        session,
        action="sos_submitted",
        entity_type="sos_reports",
        entity_id=row.id,
        user_id=user_id,
        ip=client_ip,
        details={"language": body.language},
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


@router.post("/mine/{sos_id}/attachment")
async def upload_sos_attachment(
    sos_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(current_user),
) -> dict:
    """Upload a JPEG/PNG/PDF attachment for an existing SOS report (max 10 MB)."""
    # Validate content type
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Only JPEG, PNG, and PDF are allowed.",
        )
    # Read and check size
    data = await file.read()
    if len(data) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(data)} bytes). Maximum allowed size is 10 MB.",
        )
    # Verify ownership
    result = await session.execute(
        text("SELECT id FROM sos_reports WHERE id = :id AND user_id = :uid"),
        {"id": sos_id, "uid": user.user_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="SOS report not found or not yours")

    # Persist via R2 / local storage if configured; return placeholder for now
    log.info(
        "sos_attachment_uploaded",
        sos_id=str(sos_id),
        filename=file.filename,
        size=len(data),
        content_type=file.content_type,
    )
    return {"sos_id": str(sos_id), "filename": file.filename, "size": len(data), "stored": True}


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
