"""Redis stream publication for normalized hazard events."""

from __future__ import annotations

import json
from typing import TypeAlias

from app.ingestion.common.logger import get_ingestion_logger
from app.ingestion.common.schemas import NormalizedEvent, StoredEventRef
from app.redis_client import get_redis

log = get_ingestion_logger("stream")

HAZARD_EVENTS_STREAM = "hazard:events"
RedisField: TypeAlias = bytes | memoryview | str | int | float


async def publish_hazard_events(
    events: list[NormalizedEvent],
    stored_refs: list[StoredEventRef],
) -> int:
    if not events or not stored_refs:
        return 0

    ref_by_key = {ref.source_key: ref for ref in stored_refs}
    try:
        redis = get_redis()
        pipe = redis.pipeline(transaction=False)
        published = 0

        for event in events:
            ref = ref_by_key.get(event.source_key)
            if ref is None:
                continue

            payload: dict[RedisField, RedisField] = {
                "id": ref.id,
                "event_id": ref.id,
                "source": event.source,
                "hazard_type": event.hazard_type,
                "timestamp": event.event_timestamp.isoformat(),
                "latitude": "" if event.latitude is None else str(event.latitude),
                "longitude": "" if event.longitude is None else str(event.longitude),
                "magnitude": "" if event.magnitude is None else str(event.magnitude),
                "depth": "" if event.depth_km is None else str(event.depth_km),
                "confidence": "" if event.confidence is None else str(event.confidence),
                "processing_state": event.processing_state,
                "retry_count": str(event.retry_count),
                "raw_payload": json.dumps(event.raw_payload, default=str),
            }
            pipe.xadd(HAZARD_EVENTS_STREAM, payload)
            published += 1

        if published:
            await pipe.execute()
        return published
    except Exception:
        log.exception("redis_stream_publish_failed", stream=HAZARD_EVENTS_STREAM)
        return 0
