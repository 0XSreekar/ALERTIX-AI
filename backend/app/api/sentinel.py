"""Sentinel — Live Threat Theatre API.

All data here MUST trace to real DB rows or models we've trained. The AI
briefing is RAG-grounded: the prompt always carries the visible event list
so Gemini cites real event IDs instead of hallucinating.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, current_user
from app.config import get_settings
from app.db import get_session
from app.logging import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/sentinel", tags=["sentinel"])


# ─────────────────────────────────────────────────────────────────────────────
# Top threats — composite score per event
# ─────────────────────────────────────────────────────────────────────────────


def _threat_score(
    hazard: str, magnitude: float | None, intensity: float | None, metadata: dict | None
) -> float:
    """Single 0-1 composite score for ranking the most pressing live hazards."""
    meta = metadata or {}
    if hazard == "earthquake":
        return min(1.0, (magnitude or 0) / 8.0)
    if hazard == "flood":
        return min(1.0, (intensity or 0) / 4.0)
    if hazard == "cyclone":
        wind = float(meta.get("wind_kmh", 0) or 0)
        return min(1.0, wind / 220.0)
    if hazard == "wildfire":
        frp = float(intensity or meta.get("frp", 0) or 0)
        return min(1.0, frp / 100.0)
    if hazard == "landslide":
        return 0.45
    return 0.2


@router.get("/threats")
async def list_threats(
    minutes: int = Query(180, ge=5, le=10080),
    limit: int = Query(12, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    _: CurrentUser = Depends(current_user),
) -> dict:
    """Top-N live hazards across India, ranked by composite threat score."""
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    rows = (
        await session.execute(
            text("""
                SELECT id, hazard_type, source, occurred_at,
                       ST_Y(location::geometry) AS lat,
                       ST_X(location::geometry) AS lon,
                       magnitude, depth_km, intensity, metadata
                FROM events
                WHERE occurred_at >= :cutoff
                  AND location IS NOT NULL
                  AND ST_Y(location::geometry) BETWEEN 6 AND 38
                  AND ST_X(location::geometry) BETWEEN 67 AND 98
                ORDER BY occurred_at DESC
                LIMIT 500
            """),
            {"cutoff": cutoff},
        )
    ).fetchall()
    scored: list[dict] = []
    for r in rows:
        score = _threat_score(r.hazard_type, r.magnitude, r.intensity, r.metadata)
        scored.append(
            {
                "id": str(r.id),
                "hazard_type": r.hazard_type,
                "source": r.source,
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                "latitude": r.lat,
                "longitude": r.lon,
                "magnitude": r.magnitude,
                "intensity": r.intensity,
                "metadata": r.metadata or {},
                "threat_score": round(score, 3),
                "title": (r.metadata or {}).get("title")
                or (r.metadata or {}).get("place")
                or f"{r.hazard_type} M{r.magnitude or '?'}",
            }
        )
    scored.sort(key=lambda d: (d["threat_score"], d["occurred_at"] or ""), reverse=True)
    return {"threats": scored[:limit], "window_minutes": minutes}


# ─────────────────────────────────────────────────────────────────────────────
# Time-machine event stream
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/stream")
async def event_stream(
    from_iso: str | None = Query(default=None, alias="from"),
    to_iso: str | None = Query(default=None, alias="to"),
    limit: int = Query(2000, ge=1, le=5000),
    session: AsyncSession = Depends(get_session),
    _: CurrentUser = Depends(current_user),
) -> dict:
    """Compact event stream for the globe particle layer.

    Defaults to last 24h. Use `from`/`to` (ISO-8601) to scrub the time slider.
    """
    now = datetime.now(UTC)

    def parse(iso: str | None, default: datetime) -> datetime:
        if not iso:
            return default
        try:
            d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=UTC)
        except ValueError:
            return default

    start = parse(from_iso, now - timedelta(hours=24))
    end = parse(to_iso, now)
    rows = (
        await session.execute(
            text("""
                SELECT id, hazard_type, occurred_at,
                       ST_Y(location::geometry) AS lat,
                       ST_X(location::geometry) AS lon,
                       magnitude, intensity, metadata
                FROM events
                WHERE occurred_at BETWEEN :start AND :end
                  AND location IS NOT NULL
                  AND ST_Y(location::geometry) BETWEEN 6 AND 38
                  AND ST_X(location::geometry) BETWEEN 67 AND 98
                ORDER BY occurred_at ASC
                LIMIT :limit
            """),
            {"start": start, "end": end, "limit": limit},
        )
    ).fetchall()
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "events": [
            {
                "id": str(r.id),
                "hazard_type": r.hazard_type,
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                "lat": r.lat,
                "lon": r.lon,
                "mag": r.magnitude,
                "intensity": r.intensity,
                "meta": r.metadata or {},
            }
            for r in rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI Briefing — RAG over the events the user is currently looking at
# ─────────────────────────────────────────────────────────────────────────────


class BriefingRequest(BaseModel):
    question: str
    event_ids: list[UUID] = []
    region: str | None = None


_BRIEF_PROMPT = """You are Alertix AI, a disaster intelligence assistant for India's
state Disaster Management Authorities. Answer the user's question using ONLY the
events listed in the CONTEXT block. If the context does not contain enough
information, say so explicitly — do not invent events.

For every claim, cite the source event by its short ID in square brackets, like
[evt-3f8b]. Keep the answer under 180 words. Bullet points are fine.

CONTEXT (live event payload — last 24h):
{context}

QUESTION:
{question}
"""


@router.post("/brief")
async def ai_briefing(
    req: BriefingRequest,
    session: AsyncSession = Depends(get_session),
    _: CurrentUser = Depends(current_user),
) -> dict:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")

    # Fetch the on-screen events (or fall back to last-24h top events)
    if req.event_ids:
        ids = [str(uid) for uid in req.event_ids[:50]]
        rows = (
            await session.execute(
                text("""
                    SELECT id, hazard_type, source, occurred_at,
                           ST_Y(location::geometry) AS lat,
                           ST_X(location::geometry) AS lon,
                           magnitude, intensity, metadata
                    FROM events
                    WHERE id = ANY(CAST(:ids AS uuid[]))
                """),
                {"ids": ids},
            )
        ).fetchall()
    else:
        rows = (
            await session.execute(
                text("""
                    SELECT id, hazard_type, source, occurred_at,
                           ST_Y(location::geometry) AS lat,
                           ST_X(location::geometry) AS lon,
                           magnitude, intensity, metadata
                    FROM events
                    WHERE occurred_at >= :cutoff
                      AND location IS NOT NULL
                      AND ST_Y(location::geometry) BETWEEN 6 AND 38
                      AND ST_X(location::geometry) BETWEEN 67 AND 98
                    ORDER BY occurred_at DESC
                    LIMIT 40
                """),
                {"cutoff": datetime.now(UTC) - timedelta(hours=24)},
            )
        ).fetchall()

    if not rows:
        return {
            "answer": "No live events in the requested window. Cannot brief without data.",
            "citations": [],
            "provider": "no-context",
        }

    # Compact, model-friendly serialisation
    ctx_lines: list[str] = []
    citations: list[dict[str, Any]] = []
    for r in rows:
        short = str(r.id)[:8]
        meta = r.metadata or {}
        title = meta.get("title") or meta.get("place") or r.hazard_type
        ctx_lines.append(
            f"[evt-{short}] {r.hazard_type} | when={r.occurred_at:%Y-%m-%d %H:%MZ} | "
            f"loc=({r.lat:.2f},{r.lon:.2f}) | mag={r.magnitude} | "
            f"int={r.intensity} | {title}"
        )
        citations.append(
            {
                "short_id": f"evt-{short}",
                "event_id": str(r.id),
                "hazard_type": r.hazard_type,
                "title": title,
            }
        )
    context = "\n".join(ctx_lines)
    prompt = _BRIEF_PROMPT.format(context=context, question=req.question.strip())

    # Route through the existing LLM ladder
    from app.llm import provider as llm

    try:
        answer, used = await llm.generate(prompt)
    except Exception as exc:
        log.warning("sentinel_brief_failed", exc=str(exc))
        raise HTTPException(status_code=502, detail="All LLM providers failed") from exc

    if not answer:
        raise HTTPException(status_code=502, detail="LLM returned empty answer")

    return {
        "answer": answer.strip(),
        "citations": citations,
        "provider": used,
        "model": get_settings().cerebras_model if used == "cerebras" else used,
        "context_events": len(rows),
    }
