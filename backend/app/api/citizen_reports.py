"""Citizen reporting and trust-system API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, current_user_optional, require_role
from app.citizen.service import create_report, get_reputation, verify_report
from app.db import get_session
from app.schemas.citizen import (
    CitizenReportCreate,
    CitizenReportOut,
    ReputationOut,
    VerifyReportRequest,
)

router = APIRouter(tags=["citizen-reports"])


@router.post("/report", response_model=CitizenReportOut)
async def report_hazard(
    payload: CitizenReportCreate,
    user: CurrentUser | None = Depends(current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> CitizenReportOut:
    row = await create_report(session, payload, user)
    await session.commit()
    return CitizenReportOut(**row)


@router.post("/verify")
async def verify(
    payload: VerifyReportRequest,
    user: CurrentUser = Depends(require_role("official", "admin")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await verify_report(session, payload.report_id, payload.decision, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc
    await session.commit()
    return {"status": "ok", "decision": payload.decision}


@router.get("/reputation/{user_id}", response_model=ReputationOut)
async def reputation(user_id: str, session: AsyncSession = Depends(get_session)) -> ReputationOut:
    rep = await get_reputation(session, user_id)
    await session.commit()
    return ReputationOut(
        user_id=user_id,
        score=rep.score,
        tier=rep.tier,
        verified_count=rep.verified_count,
        rejected_count=rep.rejected_count,
    )


@router.get("/report-status/{report_id}")
async def report_status(report_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    row = (
        await session.execute(
            text("""
                SELECT id, status, confidence_score, user_id
                FROM citizen_reports WHERE id = :report_id
            """),
            {"report_id": report_id},
        )
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": str(row.id),
        "status": row.status,
        "confidence_score": float(row.confidence_score),
    }
