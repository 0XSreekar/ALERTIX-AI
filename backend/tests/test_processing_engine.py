from datetime import UTC, datetime

import pytest

from app.processing.consumers import EarthquakeConsumer
from app.processing.dispatcher import HazardDispatcher
from app.processing.events import ProcessingEvent
from app.processing.risk import score_event
from app.processing.state import AlertTier, ProcessingState


def _event(**overrides) -> ProcessingEvent:
    values = {
        "event_id": "11111111-1111-1111-1111-111111111111",
        "source": "usgs",
        "hazard_type": "earthquake",
        "timestamp": datetime(2026, 5, 20, tzinfo=UTC),
        "latitude": 20.0,
        "longitude": 78.0,
        "magnitude": 6.6,
        "depth_km": 12.0,
        "confidence": 1.0,
        "raw_payload": {"id": "eq-1"},
    }
    values.update(overrides)
    return ProcessingEvent(**values)


def test_processing_event_parses_redis_payload():
    event = ProcessingEvent.from_stream(
        "1-0",
        {
            "event_id": "abc",
            "source": "usgs",
            "hazard_type": "earthquake",
            "timestamp": "2026-05-20T12:00:00+00:00",
            "latitude": "17.4",
            "longitude": "78.4",
            "magnitude": "5.2",
            "depth": "18",
            "confidence": "0.9",
            "raw_payload": '{"place":"Telangana"}',
        },
    )

    assert event.event_id == "abc"
    assert event.latitude == 17.4
    assert event.raw_payload["place"] == "Telangana"
    assert event.state == ProcessingState.NEW


def test_earthquake_risk_uses_magnitude_and_depth():
    score, tier = score_event(_event(magnitude=7.2, depth_km=8.0))

    assert score >= 0.85
    assert tier == AlertTier.CRITICAL


@pytest.mark.asyncio
async def test_consumer_advances_event_to_stored_without_io():
    consumer = EarthquakeConsumer(redis=None, session=None)

    event = await consumer.process_event(_event())

    assert event.state == ProcessingState.STORED
    assert event.alert_tier in {AlertTier.HIGH, AlertTier.CRITICAL}
    assert event.risk_score > 0.0


@pytest.mark.asyncio
async def test_validation_failure_moves_to_dead_letter():
    consumer = EarthquakeConsumer(redis=None, session=None)

    event = await consumer.process_event(_event(magnitude=None))

    assert event.state == ProcessingState.DEAD_LETTER


@pytest.mark.asyncio
async def test_dispatcher_selects_hazard_consumer():
    dispatcher = HazardDispatcher(redis=None, session=None)

    event = await dispatcher.dispatch(_event(hazard_type="earthquake"))

    assert event.state == ProcessingState.STORED
