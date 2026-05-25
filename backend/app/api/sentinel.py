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
from app.ml.cyclone_track import extrapolate_track
from app.sentinel.population import cities_within

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


# ─────────────────────────────────────────────────────────────────────────────
# Population at risk per event
# ─────────────────────────────────────────────────────────────────────────────


def _impact_radius_km(
    hazard: str, magnitude: float | None, intensity: float | None, metadata: dict | None
) -> float:
    """Plausible warning radius per hazard type."""
    meta = metadata or {}
    if hazard == "earthquake":
        # MMI VI roughly scales with magnitude; PSHA-style heuristic
        return min(800.0, 30 + (magnitude or 4) ** 2 * 12)
    if hazard == "flood":
        return 80.0 + (intensity or 0) * 25
    if hazard == "cyclone":
        wind = float(meta.get("wind_kmh", 0) or 0)
        return min(600.0, 100 + wind * 1.5)
    if hazard == "wildfire":
        return 20.0
    if hazard == "landslide":
        return 25.0
    return 50.0


@router.get("/impact")
async def event_impact(
    event_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
    _: CurrentUser = Depends(current_user),
) -> dict:
    row = (
        await session.execute(
            text("""
                SELECT id, hazard_type, occurred_at,
                       ST_Y(location::geometry) AS lat,
                       ST_X(location::geometry) AS lon,
                       magnitude, intensity, metadata
                FROM events WHERE id = :id
            """),
            {"id": event_id},
        )
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")

    radius = _impact_radius_km(row.hazard_type, row.magnitude, row.intensity, row.metadata)
    cities = cities_within(row.lat, row.lon, radius)
    pop_thousand = sum(c.population_thousands for c in cities)

    return {
        "event_id": str(row.id),
        "hazard_type": row.hazard_type,
        "center": {"lat": row.lat, "lon": row.lon},
        "radius_km": round(radius, 1),
        "population_at_risk_thousand": pop_thousand,
        "city_count": len(cities),
        "cities": [
            {
                "name": c.name,
                "state": c.state,
                "population_thousand": c.population_thousands,
                "distance_km": c.distance_km,
                "lat": c.lat,
                "lon": c.lon,
            }
            for c in cities[:20]
        ],
        "estimate_note": (
            "Urban-centric estimate based on ~80 Indian cities (2024 projected). "
            "Rural population inside the radius is not included."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SitRep — Gemini-grounded situation report for a single event
# ─────────────────────────────────────────────────────────────────────────────


class SitRepRequest(BaseModel):
    event_id: UUID
    audience: str = "official"  # "official" | "public"


_SITREP_PROMPT = """You are a disaster intelligence analyst writing a situation report
for {audience} stakeholders in India. Output a SitRep grounded ONLY in the structured
event payload and impact data below. Do not invent additional events or numbers.

Return a 4-section report in Markdown:
## Situation
## Population & Critical Infrastructure at Risk
## Recommended Actions (next 6 / 24 / 72 hours)
## Confidence & Caveats

Keep total length under 300 words. Cite the event ID inline as [evt-{short_id}] at least once.

EVENT:
{event_json}

IMPACT ESTIMATE:
{impact_json}
"""


@router.post("/sitrep")
async def sitrep(
    req: SitRepRequest,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(current_user),
) -> dict:
    row = (
        await session.execute(
            text("""
                SELECT id, hazard_type, source, occurred_at,
                       ST_Y(location::geometry) AS lat,
                       ST_X(location::geometry) AS lon,
                       magnitude, intensity, metadata
                FROM events WHERE id = :id
            """),
            {"id": req.event_id},
        )
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")

    radius = _impact_radius_km(row.hazard_type, row.magnitude, row.intensity, row.metadata)
    cities = cities_within(row.lat, row.lon, radius)
    pop_thousand = sum(c.population_thousands for c in cities)

    import json as _json

    short = str(row.id)[:8]
    event_json = _json.dumps(
        {
            "id": short,
            "hazard": row.hazard_type,
            "source": row.source,
            "when_utc": row.occurred_at.isoformat() if row.occurred_at else None,
            "lat": row.lat,
            "lon": row.lon,
            "magnitude": row.magnitude,
            "intensity": row.intensity,
            "metadata": row.metadata or {},
        },
        indent=2,
        default=str,
    )
    impact_json = _json.dumps(
        {
            "warning_radius_km": round(radius, 1),
            "population_at_risk_thousand": pop_thousand,
            "city_count": len(cities),
            "top_cities": [
                {
                    "name": c.name,
                    "state": c.state,
                    "distance_km": c.distance_km,
                    "population_thousand": c.population_thousands,
                }
                for c in cities[:10]
            ],
        },
        indent=2,
    )
    prompt = _SITREP_PROMPT.format(
        audience=req.audience,
        short_id=short,
        event_json=event_json,
        impact_json=impact_json,
    )

    from app.llm import provider as llm

    try:
        text_out, used = await llm.generate(prompt)
    except Exception as exc:
        log.warning("sitrep_failed", event_id=str(row.id), exc=str(exc))
        raise HTTPException(status_code=502, detail="LLM providers failed") from exc

    if not text_out:
        raise HTTPException(status_code=502, detail="LLM returned empty SitRep")

    log.info(
        "sentinel_sitrep",
        event_id=str(row.id),
        user_id=user.user_id,
        audience=req.audience,
        provider=used,
    )
    return {
        "event_id": str(row.id),
        "short_id": short,
        "sitrep_markdown": text_out.strip(),
        "provider": used,
        "audience": req.audience,
        "impact_population_thousand": pop_thousand,
        "impact_radius_km": round(radius, 1),
        "city_count": len(cities),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Forecast geometries — cyclone tracks, quake aftershock halos, flood ribbons
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/forecasts")
async def forecasts(
    minutes: int = Query(720, ge=15, le=10080),
    session: AsyncSession = Depends(get_session),
    _: CurrentUser = Depends(current_user),
) -> dict:
    """Forecast polylines/halos for the 3D globe overlay layer.

    Cyclone: 12h extrapolated track via app.ml.cyclone_track.
    Earthquake: aftershock-radius halo (Omori).
    Flood: warning-radius halo from intensity.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    rows = (
        await session.execute(
            text("""
                SELECT id, hazard_type, occurred_at,
                       ST_Y(location::geometry) AS lat,
                       ST_X(location::geometry) AS lon,
                       magnitude, intensity, metadata
                FROM events
                WHERE occurred_at >= :cutoff
                  AND location IS NOT NULL
                  AND ST_Y(location::geometry) BETWEEN 6 AND 38
                  AND ST_X(location::geometry) BETWEEN 67 AND 98
                ORDER BY occurred_at DESC
                LIMIT 300
            """),
            {"cutoff": cutoff},
        )
    ).fetchall()

    cyclones: list[dict] = []
    halos: list[dict] = []
    for r in rows:
        if r.hazard_type == "cyclone":
            track_input = [
                {
                    "lat": r.lat,
                    "lon": r.lon,
                    "occurred_at": r.occurred_at,
                    "wind_kmh": (r.metadata or {}).get("wind_kmh"),
                }
            ]
            track = extrapolate_track(track_input, horizon_hours=24, step_hours=3)
            points = [
                {"lat": p["lat"], "lon": p["lon"], "t_plus_h": p.get("t_plus_h", 0)}
                for p in track.get("extrapolated", [])
            ]
            cyclones.append(
                {
                    "event_id": str(r.id),
                    "current": {"lat": r.lat, "lon": r.lon},
                    "track": points,
                    "impact_radius_km": track.get("impact_radius_km") or 200,
                    "title": (r.metadata or {}).get("title", "Cyclone"),
                }
            )
        elif r.hazard_type in ("earthquake", "flood"):
            radius = _impact_radius_km(r.hazard_type, r.magnitude, r.intensity, r.metadata)
            halos.append(
                {
                    "event_id": str(r.id),
                    "hazard_type": r.hazard_type,
                    "lat": r.lat,
                    "lon": r.lon,
                    "radius_km": round(radius, 1),
                    "magnitude": r.magnitude,
                    "intensity": r.intensity,
                }
            )

    return {"cyclones": cyclones, "halos": halos, "window_minutes": minutes}


# ─────────────────────────────────────────────────────────────────────────────
# Cascading hazards — events within Δd km and Δt hours form a graph edge
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/cascades")
async def cascades(
    hours: int = Query(48, ge=1, le=168),
    max_distance_km: float = Query(300.0, ge=50, le=1500),
    session: AsyncSession = Depends(get_session),
    _: CurrentUser = Depends(current_user),
) -> dict:
    """Spatio-temporal cascade graph: nodes are events, edges link events that
    occurred within max_distance_km and (1..hours) hours of each other.

    A directed edge (A → B) means B happened *after* A within the window —
    suggesting cascade potential (e.g. cyclone → coastal flood)."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    rows = (
        await session.execute(
            text("""
                SELECT id, hazard_type, occurred_at,
                       ST_Y(location::geometry) AS lat,
                       ST_X(location::geometry) AS lon,
                       magnitude, intensity, metadata
                FROM events
                WHERE occurred_at >= :cutoff
                  AND location IS NOT NULL
                  AND ST_Y(location::geometry) BETWEEN 6 AND 38
                  AND ST_X(location::geometry) BETWEEN 67 AND 98
                ORDER BY occurred_at ASC
                LIMIT 200
            """),
            {"cutoff": cutoff},
        )
    ).fetchall()

    from math import asin, cos, radians, sin, sqrt

    def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        p1, p2 = radians(lat1), radians(lat2)
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
        return 2 * r * asin(sqrt(a))

    nodes = []
    for r in rows:
        nodes.append(
            {
                "id": str(r.id),
                "hazard_type": r.hazard_type,
                "lat": r.lat,
                "lon": r.lon,
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                "title": (r.metadata or {}).get("title")
                or (r.metadata or {}).get("place")
                or r.hazard_type,
            }
        )

    # Plausible cascade pairs by hazard type (parent → child)
    plausible: dict[tuple[str, str], str] = {
        ("cyclone", "flood"): "storm surge / coastal inundation",
        ("cyclone", "landslide"): "saturated slopes",
        ("flood", "landslide"): "soil saturation",
        ("earthquake", "landslide"): "shaking-triggered slope failure",
        ("earthquake", "flood"): "dam / embankment damage",
        ("wildfire", "landslide"): "post-fire soil erosion",
    }

    edges: list[dict] = []
    for i, a in enumerate(rows):
        for b in rows[i + 1 :]:
            dt = (b.occurred_at - a.occurred_at).total_seconds() / 3600.0
            if dt <= 0 or dt > hours:
                continue
            d = km(a.lat, a.lon, b.lat, b.lon)
            if d > max_distance_km:
                continue
            label = plausible.get((a.hazard_type, b.hazard_type))
            if not label and a.hazard_type == b.hazard_type:
                label = f"clustered {a.hazard_type}"
            if not label:
                continue
            # Weight: closer + sooner = stronger
            weight = max(0.1, 1.0 - (d / max_distance_km) * 0.6 - (dt / hours) * 0.4)
            edges.append(
                {
                    "source": str(a.id),
                    "target": str(b.id),
                    "label": label,
                    "distance_km": round(d, 1),
                    "delta_hours": round(dt, 1),
                    "weight": round(weight, 3),
                }
            )

    # Keep only the top-N edges by weight to avoid graph noise
    edges.sort(key=lambda e: e["weight"], reverse=True)
    edges = edges[:60]
    node_ids_in_edges = {e["source"] for e in edges} | {e["target"] for e in edges}
    filtered_nodes = [n for n in nodes if n["id"] in node_ids_in_edges]

    return {"nodes": filtered_nodes, "edges": edges, "window_hours": hours}
