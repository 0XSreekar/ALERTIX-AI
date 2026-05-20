"""Grounded retrieval and summarization helpers for local AI endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import provider as llm

FORBIDDEN_TERMS = (
    "official alert",
    "official warning",
    "will occur at",
    "exact magnitude",
    "autonomously issued",
)


@dataclass(frozen=True, slots=True)
class GroundedAIResponse:
    label: str
    provider: str
    text: str
    citations: list[dict[str, Any]]


async def retrieve_hazard_context(
    session: AsyncSession,
    *,
    region: str | None = None,
    hazard_type: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    clauses = ["occurred_at >= now() - interval '24 hours'"]
    params: dict[str, Any] = {"limit": limit}
    if hazard_type:
        clauses.append("hazard_type = :hazard_type")
        params["hazard_type"] = hazard_type
    if region:
        clauses.append("metadata::text ILIKE :region")
        params["region"] = f"%{region}%"
    where = " AND ".join(clauses)
    result = await session.execute(
        text(f"""
            SELECT id::text AS id, hazard_type, source, occurred_at,
                   magnitude, intensity, probability, metadata
            FROM events
            WHERE {where}
            ORDER BY occurred_at DESC
            LIMIT :limit
        """),
        params,
    )
    events = [
        {
            "kind": "event",
            "id": row.id,
            "hazard_type": row.hazard_type,
            "source": row.source,
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            "magnitude": row.magnitude,
            "intensity": row.intensity,
            "probability": row.probability,
            "metadata": row.metadata or {},
        }
        for row in result.fetchall()
    ]

    reports = await session.execute(
        text("""
            SELECT id::text AS id, hazard_type, status, confidence_score, created_at,
                   extracted_entities
            FROM citizen_reports
            WHERE created_at >= now() - interval '24 hours'
            ORDER BY created_at DESC
            LIMIT 5
        """)
    )
    events.extend(
        {
            "kind": "citizen_report",
            "id": row.id,
            "hazard_type": row.hazard_type,
            "status": row.status,
            "confidence_score": row.confidence_score,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "entities": row.extracted_entities or {},
        }
        for row in reports.fetchall()
    )
    return events


def _guard(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in FORBIDDEN_TERMS):
        return (
            "AI-generated summary: The available context was insufficient for a safe generated "
            "answer. This is not an official alert. Follow IMD, NCS, CWC, and local authority guidance."
        )
    prefix = "AI-generated summary, not an official alert: "
    return text if text.startswith(prefix) else prefix + text


async def generate_grounded_response(
    session: AsyncSession,
    *,
    task: str,
    question: str,
    region: str | None,
    hazard_type: str | None,
) -> GroundedAIResponse:
    context = await retrieve_hazard_context(session, region=region, hazard_type=hazard_type)
    prompt = f"""
You are ALERTIX's local AI assistant. Use only the JSON context below.
Allowed: event summaries, plain-language explanations, public safety actions, response guidance.
Forbidden: autonomous alerts, quantitative hazard predictions, exact earthquake prediction, official warnings.
Always say the output is AI-generated and not official.

Task: {task}
User question: {question}
Context JSON:
{json.dumps(context, default=str, indent=2)}
"""
    text_out, provider = await llm.generate(prompt)
    if not text_out:
        text_out = "No local model response was available. Review the cited sensor and report context directly."
        provider = "none"
    return GroundedAIResponse(
        label="AI-generated summary, not an official alert",
        provider=provider,
        text=_guard(text_out),
        citations=[{"kind": item["kind"], "id": item["id"]} for item in context],
    )
