"""Standalone processing worker entrypoint."""

from __future__ import annotations

import asyncio
from typing import Any

from app.db import AsyncSessionLocal
from app.ingestion.common.stream import HAZARD_EVENTS_STREAM
from app.logging import configure_logging, get_logger
from app.processing.dispatcher import HazardDispatcher
from app.processing.events import ProcessingEvent
from app.redis_client import close_redis, get_redis

log = get_logger(__name__)


async def run_in_process(block_ms: int = 5000) -> None:
    """Run worker as a background task inside the FastAPI process.

    Uses the shared Redis client; does NOT call close_redis() on exit so
    the rest of the app keeps its connection.  Designed to run until the
    asyncio task is cancelled.
    """
    redis = get_redis()
    last_id = "$"
    log.info("processing_worker_started_in_process", stream=HAZARD_EVENTS_STREAM)
    while True:
        try:
            response: list[Any] = await redis.xread(
                {HAZARD_EVENTS_STREAM: last_id},
                count=50,
                block=block_ms,
            )
            if not response:
                await asyncio.sleep(0)
                continue
            async with AsyncSessionLocal() as session:
                dispatcher = HazardDispatcher(redis=redis, session=session)
                for _, entries in response:
                    for stream_id, payload in entries:
                        last_id = stream_id
                        event = ProcessingEvent.from_stream(stream_id, payload)
                        await dispatcher.dispatch(event)
                await session.commit()
        except asyncio.CancelledError:
            log.info("processing_worker_cancelled")
            raise
        except Exception:
            log.exception("processing_worker_error_recovering")
            await asyncio.sleep(5)


async def run_processing_worker(block_ms: int = 5000) -> None:
    """Standalone entrypoint — manages its own Redis lifecycle."""
    configure_logging()
    redis = get_redis()
    last_id = "$"
    log.info("processing_worker_started", stream=HAZARD_EVENTS_STREAM)
    try:
        while True:
            response: list[Any] = await redis.xread(
                {HAZARD_EVENTS_STREAM: last_id},
                count=50,
                block=block_ms,
            )
            if not response:
                await asyncio.sleep(0)
                continue

            async with AsyncSessionLocal() as session:
                dispatcher = HazardDispatcher(redis=redis, session=session)
                for _, entries in response:
                    for stream_id, payload in entries:
                        last_id = stream_id
                        event = ProcessingEvent.from_stream(stream_id, payload)
                        await dispatcher.dispatch(event)
                await session.commit()
    finally:
        await close_redis()


def main() -> None:
    asyncio.run(run_processing_worker())


if __name__ == "__main__":
    main()
