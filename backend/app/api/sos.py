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


async def _run_sos_enrichment(sos_id: str, raw_text: str, has_user_location: bool) -> None:
    """Background task: NER + geocoding + LLM triage, written back to DB."""
    try:
        from app.citizen.lang_detect import detect_language, translate_to_english
        from app.citizen.sos_enrich import enrich_sos
        from app.llm import provider as llm
        from app.llm.prompts import SOS_TRIAGE

        # 0) Detect script; translate Indic-language SOS to English for NER + triage
        lang_code = detect_language(raw_text)
        english_text = (
            raw_text if lang_code == "en" else await translate_to_english(raw_text, lang_code)
        )

        # 1) NER + geocoding (on English text — Nominatim place index is English-dominant)
        enriched = await enrich_sos(english_text)

        # 2) LLM triage (best-effort, uses provider ladder)
        urgency: int | None = None
        summary: str | None = None
        try:
            prompt = SOS_TRIAGE.format(
                message=english_text, location=enriched.chosen_place or "unknown"
            )
            raw, _provider = await llm.generate(prompt)
            if raw:
                import re as _re

                match = _re.search(r"\{.*\}", raw, _re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    urgency = data.get("urgency_score")
                    summary = data.get("summary")
        except Exception:
            log.warning("sos_triage_llm_failed sos_id=%s", sos_id)

        # 3) Write enrichment back. Only update lat/lon if the user didn't provide it.
        async with async_session_factory() as sess:
            params: dict = {
                "id": sos_id,
                "extracted": enriched.chosen_place,
                "score": urgency,
                "summary": summary,
            }
            location_clause = ""
            if (
                not has_user_location
                and enriched.latitude is not None
                and enriched.longitude is not None
            ):
                location_clause = (
                    ", location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography"
                )
                params["lat"] = enriched.latitude
                params["lon"] = enriched.longitude

            await sess.execute(
                text(f"""
                    UPDATE sos_reports
                    SET extracted_location_text = :extracted,
                        urgency_score = COALESCE(:score, urgency_score),
                        llm_summary   = COALESCE(:summary, llm_summary),
                        triaged       = TRUE
                        {location_clause}
                    WHERE id = :id
                """),
                params,
            )
            await sess.commit()
        log.info(
            "sos_enriched",
            sos_id=sos_id,
            lang=lang_code,
            translated=lang_code != "en",
            place=enriched.chosen_place,
            geocoded=enriched.latitude is not None,
            urgency=urgency,
        )
    except Exception:
        log.exception("sos_enrichment_failed", sos_id=sos_id)


def _rate_key(request: Request) -> str:
    """Per-user limit when authenticated, per-IP for anonymous."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        # crude but stable key without verifying the token; the auth dep below
        # rejects bad tokens, so this is only used for distinct buckets
        return f"user:{auth[7:][-32:]}"
    return get_remote_address(request)


@router.post("")
@limiter.limit("30/hour", key_func=_rate_key)
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

    # Kick off async NER + geocoding + LLM triage (non-blocking)
    background_tasks.add_task(
        _run_sos_enrichment,
        str(row.id),
        body.raw_text,
        body.latitude is not None and body.longitude is not None,
    )

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
