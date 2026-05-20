"""Hazard dispatcher that selects the concrete processing consumer."""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.processing.consumers import (
    CycloneConsumer,
    EarthquakeConsumer,
    FloodConsumer,
    HazardConsumer,
    WildfireConsumer,
)
from app.processing.events import ProcessingEvent


class HazardDispatcher:
    def __init__(self, redis: Redis | None = None, session: AsyncSession | None = None) -> None:
        self.consumers: dict[str, HazardConsumer] = {
            "earthquake": EarthquakeConsumer(redis=redis, session=session),
            "flood": FloodConsumer(redis=redis, session=session),
            "wildfire": WildfireConsumer(redis=redis, session=session),
            "cyclone": CycloneConsumer(redis=redis, session=session),
        }
        self.default_consumer = HazardConsumer(redis=redis, session=session)

    async def dispatch(self, event: ProcessingEvent) -> ProcessingEvent:
        consumer = self.consumers.get(event.hazard_type, self.default_consumer)
        return await consumer.process_event(event)
