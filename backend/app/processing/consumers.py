"""Redis-backed consumers for realtime hazard processing."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.common.stream import HAZARD_EVENTS_STREAM
from app.logging import get_logger
from app.processing.events import ProcessingEvent
from app.processing.metrics import metrics
from app.processing.risk import score_event
from app.processing.state import AlertTier, ProcessingState, assert_next_state

log = get_logger(__name__)

PROCESSING_RETRY_STREAM = "hazard:events:retry"
PROCESSING_DLQ_STREAM = "hazard:events:dlq"
PROCESSING_PRIORITY_STREAM = "hazard:events:priority"


class ValidationError(ValueError):
    """Raised when an event cannot safely enter the alerting pipeline."""


class HazardConsumer:
    hazard_type = "generic"
    group_name = "alertix-processing"
    consumer_name = "hazard-consumer"
    max_retries = 5

    def __init__(self, redis: Redis | None = None, session: AsyncSession | None = None) -> None:
        self.redis = redis
        self.session = session

    def validate(self, event: ProcessingEvent) -> None:
        if not event.event_id:
            raise ValidationError("missing event id")
        if event.latitude is not None and not -90.0 <= event.latitude <= 90.0:
            raise ValidationError("latitude out of range")
        if event.longitude is not None and not -180.0 <= event.longitude <= 180.0:
            raise ValidationError("longitude out of range")

    async def normalize(self, event: ProcessingEvent) -> ProcessingEvent:
        event.normalized = dict(event.raw_payload)
        return event

    async def dedupe(self, event: ProcessingEvent) -> bool:
        if self.redis is None:
            return False
        inserted = await self.redis.set(f"processing:dedupe:{event.dedupe_key}", "1", nx=True, ex=86400)
        return inserted is None

    async def persist_state(self, event: ProcessingEvent) -> None:
        if self.session is None:
            return
        await self.session.execute(
            text("""
                INSERT INTO processed_events (
                    event_id, source, hazard_type, processing_state, retry_count,
                    risk_score, alert_tier, payload, updated_at
                )
                VALUES (
                    :event_id, :source, :hazard_type, :state, :retry_count,
                    :risk_score, :alert_tier, CAST(:payload AS jsonb), now()
                )
                ON CONFLICT (event_id) DO UPDATE SET
                    processing_state = EXCLUDED.processing_state,
                    retry_count = EXCLUDED.retry_count,
                    risk_score = EXCLUDED.risk_score,
                    alert_tier = EXCLUDED.alert_tier,
                    payload = EXCLUDED.payload,
                    updated_at = now()
            """),
            {
                "event_id": event.event_id,
                "source": event.source,
                "hazard_type": event.hazard_type,
                "state": event.state.value,
                "retry_count": event.retry_count,
                "risk_score": event.risk_score,
                "alert_tier": event.alert_tier.value,
                "payload": json.dumps(event.raw_payload, default=str),
            },
        )

    async def route_priority(self, event: ProcessingEvent) -> None:
        if self.redis is None or event.alert_tier not in {AlertTier.HIGH, AlertTier.CRITICAL}:
            return
        await self.redis.xadd(
            PROCESSING_PRIORITY_STREAM,
            {
                "event_id": event.event_id,
                "hazard_type": event.hazard_type,
                "alert_tier": event.alert_tier.value,
                "risk_score": str(event.risk_score),
                "payload": json.dumps(event.raw_payload, default=str),
            },
        )

    async def emit_alert(self, event: ProcessingEvent) -> None:
        if self.session is None:
            return
        title = f"{event.alert_tier.value.title()} {event.hazard_type} event"
        explanation = f"Automated sensor/model risk score: {event.risk_score:.2f}"
        await self.session.execute(
            text("""
                INSERT INTO alerts (
                    hazard_type, severity, title, explanation, explanation_status,
                    probability, event_ids, model_version, created_at
                )
                VALUES (
                    :hazard_type, :severity, :title, :explanation, 'generated',
                    :probability, ARRAY[:event_id]::uuid[], 'processing-v1', now()
                )
            """),
            {
                "hazard_type": event.hazard_type,
                "severity": event.alert_tier.value,
                "title": title,
                "explanation": explanation,
                "probability": event.risk_score,
                "event_id": event.event_id,
            },
        )

    async def move_to_retry(self, event: ProcessingEvent, reason: str) -> None:
        event.state = ProcessingState.RETRY
        event.retry_count += 1
        metrics.record_failure(self.consumer_name)
        if self.redis is None:
            return
        delay = min(900, 2 ** max(0, event.retry_count - 1))
        await self.redis.xadd(
            PROCESSING_RETRY_STREAM,
            {
                "event_id": event.event_id,
                "hazard_type": event.hazard_type,
                "retry_count": str(event.retry_count),
                "available_at_epoch": str(time.time() + delay),
                "reason": reason,
                "payload": json.dumps(asdict(event), default=str),
            },
        )

    async def move_to_dlq(self, event: ProcessingEvent, reason: str) -> None:
        event.state = ProcessingState.DEAD_LETTER
        metrics.record_dlq(self.consumer_name)
        if self.redis is None:
            return
        await self.redis.xadd(
            PROCESSING_DLQ_STREAM,
            {
                "event_id": event.event_id,
                "hazard_type": event.hazard_type,
                "reason": reason,
                "payload": json.dumps(asdict(event), default=str),
            },
        )

    def _advance(self, event: ProcessingEvent, next_state: ProcessingState) -> None:
        assert_next_state(event.state, next_state)
        event.state = next_state

    async def process_event(self, event: ProcessingEvent) -> ProcessingEvent:
        started = time.perf_counter()
        try:
            self._advance(event, ProcessingState.PROCESSING)
            event = await self.normalize(event)
            if await self.dedupe(event):
                metrics.record_duplicate(self.consumer_name)
                return event
            self.validate(event)
            self._advance(event, ProcessingState.VALIDATED)
            event.risk_score, event.alert_tier = score_event(event)
            self._advance(event, ProcessingState.ROUTED)
            await self.route_priority(event)
            if event.alert_tier in {AlertTier.MEDIUM, AlertTier.HIGH, AlertTier.CRITICAL}:
                await self.emit_alert(event)
            self._advance(event, ProcessingState.ALERTED)
            await self.persist_state(event)
            self._advance(event, ProcessingState.STORED)
            await self.persist_state(event)
            metrics.record_success(self.consumer_name, (time.perf_counter() - started) * 1000.0)
            return event
        except ValidationError as exc:
            await self.move_to_dlq(event, str(exc))
            return event
        except Exception as exc:
            if event.retry_count >= self.max_retries:
                await self.move_to_dlq(event, str(exc))
            else:
                await self.move_to_retry(event, str(exc))
            log.warning("processing_event_failed", error=str(exc), event_id=event.event_id)
            return event

    async def run_forever(self, block_ms: int = 5000) -> None:
        if self.redis is None:
            raise RuntimeError("redis client required for stream consumer")
        last_id = "$"
        while True:
            response: list[Any] = await self.redis.xread({HAZARD_EVENTS_STREAM: last_id}, count=25, block=block_ms)
            for _, entries in response:
                for stream_id, payload in entries:
                    last_id = stream_id
                    event = ProcessingEvent.from_stream(stream_id, payload)
                    if self.hazard_type != "generic" and event.hazard_type != self.hazard_type:
                        continue
                    await self.process_event(event)
            await asyncio.sleep(0)


class EarthquakeConsumer(HazardConsumer):
    hazard_type = "earthquake"
    consumer_name = "earthquake-consumer"

    def validate(self, event: ProcessingEvent) -> None:
        super().validate(event)
        if event.magnitude is None:
            raise ValidationError("earthquake magnitude missing")
        if event.magnitude < 0.0 or event.magnitude > 10.0:
            raise ValidationError("earthquake magnitude out of range")


class FloodConsumer(HazardConsumer):
    hazard_type = "flood"
    consumer_name = "flood-consumer"


class WildfireConsumer(HazardConsumer):
    hazard_type = "wildfire"
    consumer_name = "wildfire-consumer"


class CycloneConsumer(HazardConsumer):
    hazard_type = "cyclone"
    consumer_name = "cyclone-consumer"
