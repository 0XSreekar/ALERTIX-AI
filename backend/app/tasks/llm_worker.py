"""Background worker that backfills LLM-generated explanations for pending alerts.

Polls `alerts WHERE explanation_status = 'pending'`, calls the LLM provider
ladder, and writes the result back. Marks unrecoverable failures as
'degraded' with a templated fallback so the dashboard never shows null.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from app.db import AsyncSessionLocal
from app.llm import provider as llm
from app.llm.prompts import get_template
from app.logging import get_logger

log = get_logger(__name__)

BATCH_SIZE = 5


def _templated_fallback(hazard_type: str, title: str) -> str:
    return (
        f"{title}. Alertix AI received this {hazard_type} alert but the AI "
        "explanation service is currently unavailable. Please consult IMD, "
        "NCS, or NDRF for official guidance."
    )


async def _gather_event_payload(session: Any, event_ids: list) -> dict[str, Any]:
    """Pull the linked events as a list of dicts for the prompt."""
    if not event_ids:
        return {}
    result = await session.execute(
        text("""
            SELECT id, hazard_type, source, occurred_at, magnitude, depth_km,
                   intensity, metadata,
                   ST_Y(location::geometry) AS lat,
                   ST_X(location::geometry) AS lon
            FROM events
            WHERE id = ANY(:ids)
            ORDER BY occurred_at DESC
            LIMIT 5
        """),
        {"ids": event_ids},
    )
    events = []
    for row in result.fetchall():
        events.append(
            {
                "id": str(row.id),
                "source": row.source,
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                "magnitude": row.magnitude,
                "depth_km": row.depth_km,
                "intensity": row.intensity,
                "lat": row.lat,
                "lon": row.lon,
                "metadata": row.metadata or {},
            }
        )
    return {"events": events}


async def process_pending_alerts() -> dict[str, int]:
    """Process up to BATCH_SIZE pending alerts. Returns counts for logging."""
    counts = {"processed": 0, "completed": 0, "degraded": 0, "errors": 0}
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, hazard_type, severity, title, event_ids
                FROM alerts
                WHERE explanation_status = 'pending'
                ORDER BY created_at DESC
                LIMIT :n
            """),
            {"n": BATCH_SIZE},
        )
        rows = result.fetchall()
        for row in rows:
            counts["processed"] += 1
            try:
                payload = await _gather_event_payload(session, row.event_ids or [])
                payload["alert"] = {
                    "hazard_type": row.hazard_type,
                    "severity": row.severity,
                    "title": row.title,
                }
                template = get_template(row.hazard_type)
                prompt = template.format(event_json=json.dumps(payload, default=str, indent=2))
                text_out, provider = await llm.generate(prompt)

                if text_out:
                    new_status = "complete"
                    counts["completed"] += 1
                    explanation = text_out
                    log.info(
                        "llm_worker_alert_explained",
                        alert_id=str(row.id),
                        provider=provider,
                    )
                else:
                    new_status = "degraded"
                    counts["degraded"] += 1
                    explanation = _templated_fallback(row.hazard_type, row.title)
                    log.warning("llm_worker_all_providers_failed", alert_id=str(row.id))

                await session.execute(
                    text("""
                        UPDATE alerts
                        SET explanation = :explanation,
                            explanation_status = :status
                        WHERE id = :id
                    """),
                    {"explanation": explanation, "status": new_status, "id": row.id},
                )
            except Exception:
                counts["errors"] += 1
                log.exception("llm_worker_alert_failed", alert_id=str(row.id))

        await session.commit()
    return counts
