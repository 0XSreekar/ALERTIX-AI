"""Citizen reporting trust, validation, and NER-lite extraction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser
from app.schemas.citizen import CitizenReportCreate

HAZARD_KEYWORDS = {
    "earthquake": {"earthquake", "quake", "tremor", "aftershock"},
    "flood": {"flood", "waterlogging", "inundation", "river", "overflow"},
    "wildfire": {"wildfire", "fire", "smoke", "forest fire"},
    "cyclone": {"cyclone", "storm", "landfall", "wind"},
    "landslide": {"landslide", "slope", "debris"},
}


@dataclass(frozen=True, slots=True)
class Reputation:
    score: int
    tier: str
    verified_count: int
    rejected_count: int


def reputation_tier(score: int) -> str:
    if score >= 80:
        return "trusted"
    if score >= 40:
        return "normal"
    if score >= 10:
        return "flagged"
    return "blocked"


def extract_entities(description: str, hazard_type: str) -> dict:
    lowered = description.lower()
    hazards = [
        hazard
        for hazard, terms in HAZARD_KEYWORDS.items()
        if hazard == hazard_type.lower() or any(term in lowered for term in terms)
    ]
    places = sorted(set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", description)))
    return {"hazards": hazards, "places": places}


def score_report(
    report: CitizenReportCreate, entities: dict, user_tier: str, duplicate: bool
) -> float:
    score = 0.35
    if report.hazard_type.lower() in entities.get("hazards", []):
        score += 0.25
    if report.media_url:
        score += 0.15
    if entities.get("places"):
        score += 0.1
    if user_tier == "trusted":
        score += 0.2
    if user_tier == "flagged":
        score -= 0.2
    if user_tier == "blocked":
        score -= 0.5
    if duplicate:
        score -= 0.35
    return round(max(0.0, min(1.0, score)), 4)


async def get_reputation(session: AsyncSession, user_id: str) -> Reputation:
    result = await session.execute(
        text("""
            INSERT INTO user_reputation (user_id, score, verified_count, rejected_count, updated_at)
            VALUES (:user_id, 50, 0, 0, now())
            ON CONFLICT (user_id) DO NOTHING
            RETURNING score, verified_count, rejected_count
        """),
        {"user_id": user_id},
    )
    row = result.fetchone()
    if row is None:
        row = (
            await session.execute(
                text("""
                    SELECT score, verified_count, rejected_count
                    FROM user_reputation WHERE user_id = :user_id
                """),
                {"user_id": user_id},
            )
        ).fetchone()
    if row is None:
        return Reputation(score=50, tier="normal", verified_count=0, rejected_count=0)
    score = int(row.score)
    return Reputation(
        score=score,
        tier=reputation_tier(score),
        verified_count=int(row.verified_count),
        rejected_count=int(row.rejected_count),
    )


async def has_duplicate_report(session: AsyncSession, report: CitizenReportCreate) -> bool:
    result = await session.execute(
        text("""
            SELECT 1
            FROM citizen_reports
            WHERE hazard_type = :hazard_type
              AND created_at >= now() - interval '30 minutes'
              AND ST_DWithin(
                  location,
                  ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                  1000
              )
            LIMIT 1
        """),
        {
            "hazard_type": report.hazard_type.lower(),
            "lat": report.latitude,
            "lon": report.longitude,
        },
    )
    return result.fetchone() is not None


async def create_report(
    session: AsyncSession, report: CitizenReportCreate, user: CurrentUser | None
) -> dict:
    user_id = user.user_id if user else None
    reputation = (
        await get_reputation(session, user_id) if user_id else Reputation(35, "flagged", 0, 0)
    )
    duplicate = await has_duplicate_report(session, report)
    entities = extract_entities(report.description, report.hazard_type)
    confidence = score_report(report, entities, reputation.tier, duplicate)
    status = "verified" if confidence >= 0.85 and reputation.tier == "trusted" else "pending"
    if reputation.tier == "blocked":
        status = "rejected"

    result = await session.execute(
        text("""
            INSERT INTO citizen_reports (
                user_id, hazard_type, description, location, media_url,
                extracted_entities, confidence_score, status, created_at, updated_at
            )
            VALUES (
                :user_id, :hazard_type, :description,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :media_url, CAST(:entities AS jsonb), :confidence, :status, now(), now()
            )
            RETURNING id, hazard_type, status, confidence_score, extracted_entities
        """),
        {
            "user_id": user_id,
            "hazard_type": report.hazard_type.lower(),
            "description": report.description,
            "lat": report.latitude,
            "lon": report.longitude,
            "media_url": report.media_url,
            "entities": json.dumps(entities),
            "confidence": confidence,
            "status": status,
        },
    )
    row = result.fetchone()
    if row is None:
        raise RuntimeError("INSERT ... RETURNING returned no row")
    return {
        "id": row.id,
        "hazard_type": row.hazard_type,
        "status": row.status,
        "confidence_score": float(row.confidence_score),
        "extracted_entities": row.extracted_entities,
    }


async def verify_report(
    session: AsyncSession, report_id: UUID, decision: str, actor: CurrentUser
) -> None:
    report = (
        await session.execute(
            text("SELECT user_id FROM citizen_reports WHERE id = :report_id"),
            {"report_id": report_id},
        )
    ).fetchone()
    if not report:
        raise LookupError("report not found")
    await session.execute(
        text(
            "UPDATE citizen_reports SET status = :decision, updated_at = now() WHERE id = :report_id"
        ),
        {"decision": decision, "report_id": report_id},
    )
    if report.user_id:
        delta = 10 if decision == "verified" else -15
        count_col = "verified_count" if decision == "verified" else "rejected_count"
        await session.execute(
            text(f"""
                INSERT INTO user_reputation (user_id, score, verified_count, rejected_count, updated_at)
                VALUES (:user_id, 50 + :delta, :verified_inc, :rejected_inc, now())
                ON CONFLICT (user_id) DO UPDATE SET
                    score = greatest(0, least(100, user_reputation.score + :delta)),
                    {count_col} = user_reputation.{count_col} + 1,
                    updated_at = now()
            """),
            {
                "user_id": report.user_id,
                "delta": delta,
                "verified_inc": 1 if decision == "verified" else 0,
                "rejected_inc": 1 if decision == "rejected" else 0,
            },
        )
    await session.execute(
        text("""
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, details, created_at)
            VALUES (:actor_user_id, :action, 'citizen_reports', :report_id, '{}'::jsonb, now())
        """),
        {"actor_user_id": actor.user_id, "action": f"report_{decision}", "report_id": report_id},
    )
