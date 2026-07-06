"""Standalone processing worker entrypoint."""

from __future__ import annotations

import asyncio
import socket
from typing import Any

from redis.exceptions import ResponseError

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.ingestion.common.stream import HAZARD_EVENTS_STREAM
from app.logging import configure_logging, get_logger
from app.processing.dispatcher import HazardDispatcher
from app.processing.events import ProcessingEvent
from app.redis_client import close_redis, get_redis

log = get_logger(__name__)
settings = get_settings()


async def ensure_consumer_group(redis: Any, group_name: str) -> None:
    try:
        await redis.xgroup_create(
            HAZARD_EVENTS_STREAM,
            group_name,
            id="0",
            mkstream=True,
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _dispatch_entries(redis: Any, entries: list[tuple[str, dict[str, Any]]]) -> int:
    if not entries:
        return 0

    processed = 0
    ack_ids: list[str] = []
    async with AsyncSessionLocal() as session:
        dispatcher = HazardDispatcher(redis=redis, session=session)
        for stream_id, payload in entries:
            event = ProcessingEvent.from_stream(stream_id, payload)
            await dispatcher.dispatch(event)
            ack_ids.append(stream_id)
            processed += 1
        await session.commit()
    if ack_ids:
        await redis.xack(HAZARD_EVENTS_STREAM, settings.redis_stream_group, *ack_ids)
    return processed


async def recover_stale_pending(redis: Any, consumer_name: str) -> int:
    """Claim abandoned entries so a crashed worker does not permanently stall them."""
    try:
        claimed = await redis.xautoclaim(
            HAZARD_EVENTS_STREAM,
            settings.redis_stream_group,
            consumer_name,
            min_idle_time=settings.redis_stream_pending_idle_ms,
            start_id="0-0",
            count=50,
        )
    except ResponseError:
        return 0

    entries = claimed[1] if len(claimed) > 1 else []
    return await _dispatch_entries(redis, entries)


async def run_processing_worker(block_ms: int = 5000) -> None:
    configure_logging()
    redis = get_redis()
    consumer_name = f"{settings.redis_stream_consumer}-{socket.gethostname()}"
    await ensure_consumer_group(redis, settings.redis_stream_group)
    log.info(
        "processing_worker_started",
        stream=HAZARD_EVENTS_STREAM,
        group=settings.redis_stream_group,
        consumer=consumer_name,
    )
    try:
        while True:
            await recover_stale_pending(redis, consumer_name)
            response: list[Any] = await redis.xreadgroup(
                settings.redis_stream_group,
                consumer_name,
                {HAZARD_EVENTS_STREAM: ">"},
                count=50,
                block=block_ms,
            )
            if not response:
                await asyncio.sleep(0)
                continue

            for _, entries in response:
                await _dispatch_entries(redis, entries)
    finally:
        await close_redis()


def main() -> None:
    asyncio.run(run_processing_worker())


if __name__ == "__main__":
    main()
