from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from app.ingestion.common.retry_handler import RetryConfig, retry_async
from app.ingestion.common.schemas import NormalizedEvent, StoredEventRef
from app.ingestion.common.storage import bulk_upsert_hazard_events
from app.ingestion.common.stream import publish_hazard_events
from app.ingestion.cyclone.parser import CycloneParser
from app.ingestion.cyclone.validator import validate_cyclone
from app.ingestion.flood.parser import parse_cwc_gauge_tables
from app.ingestion.flood.validator import validate_flood_event
from app.ingestion.wildfire.client import india_area_coordinates
from app.ingestion.wildfire.parser import parse_firms_csv
from app.ingestion.wildfire.validator import validate_wildfire


def test_firms_area_is_india_bbox():
    assert india_area_coordinates() == "68.0,6.0,98.0,38.0"


def test_firms_parser_and_validator_reject_outside_india():
    csv_text = """latitude,longitude,acq_date,acq_time,frp,confidence,satellite,instrument,daynight
20.1,77.2,2026-05-20,1030,12.3,h,N,VIIRS,D
50.0,10.0,2026-05-20,1030,9.1,h,N,VIIRS,D
"""
    events = parse_firms_csv(csv_text)
    assert len(events) == 2
    assert validate_wildfire(events[0]) is True
    assert validate_wildfire(events[1]) is False


def test_cwc_parser_extracts_geotagged_gauge():
    html = """
    <table>
      <tr>
        <th>Station</th><th>River</th><th>Basin</th><th>Latitude</th><th>Longitude</th>
        <th>Water Level</th><th>Warning Level</th><th>Danger Level</th><th>Discharge</th>
        <th>Date</th><th>Time</th>
      </tr>
      <tr>
        <td>Patna</td><td>Ganga</td><td>Ganga</td><td>25.61</td><td>85.14</td>
        <td>51.2</td><td>50.0</td><td>51.0</td><td>1200</td>
        <td>20-05-2026</td><td>10:30</td>
      </tr>
    </table>
    """
    events = parse_cwc_gauge_tables(html, fetched_at=datetime(2026, 5, 20, tzinfo=UTC))
    assert len(events) == 1
    assert events[0].normalized_payload["station"] == "Patna"
    assert events[0].intensity == 3.0
    assert validate_flood_event(events[0]) is True


def test_cyclone_parser_extracts_bulletin_fields():
    text = """
    TROPICAL CYCLONE 01A (TEST) WARNING.
    Located near 15.0N 70.0E with maximum sustained winds 45 KT.
    Central pressure 990 hPa. The system is moving northwest.
    Forecast position 16.0N 71.0E.
    """
    event = CycloneParser().parse_text(
        source="jtwc", url="https://example.test/warn.txt", payload=text
    )
    assert event is not None
    assert event.normalized_payload["wind_speed_kmh"] == 83.3
    assert event.normalized_payload["pressure_hpa"] == 990.0
    assert event.normalized_payload["movement_direction"] == "northwest"
    assert validate_cyclone(event) is True


@pytest.mark.asyncio
async def test_retry_async_recovers_after_timeout():
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.TimeoutException("timeout")
        return "ok"

    result = await retry_async(flaky, config=RetryConfig(attempts=2, base_delay_seconds=0))
    assert result == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_publish_hazard_events_writes_required_stream_fields(monkeypatch):
    class FakePipeline:
        def __init__(self) -> None:
            self.entries = []

        def xadd(self, stream_name, payload):
            self.entries.append((stream_name, payload))

        async def execute(self):
            return ["1-0"]

    class FakeRedis:
        def __init__(self) -> None:
            self.pipeline_instance = FakePipeline()

        def pipeline(self, transaction=False):
            assert transaction is False
            return self.pipeline_instance

    fake_redis = FakeRedis()
    monkeypatch.setattr("app.ingestion.common.stream.get_redis", lambda: fake_redis)
    event = NormalizedEvent(
        source="usgs",
        source_event_id="eq-1",
        hazard_type="earthquake",
        event_timestamp=datetime(2026, 5, 20, tzinfo=UTC),
        latitude=20.0,
        longitude=78.0,
        confidence=1.0,
        raw_payload={"id": "eq-1"},
        magnitude=5.0,
        depth_km=12.0,
    )
    ref = StoredEventRef(
        id="event-id", source="usgs", source_event_id="eq-1", hazard_type="earthquake"
    )

    published = await publish_hazard_events([event], [ref])

    assert published == 1
    stream_name, payload = fake_redis.pipeline_instance.entries[0]
    assert stream_name == "hazard:events"
    assert payload["id"] == "event-id"
    assert payload["source"] == "usgs"
    assert payload["hazard_type"] == "earthquake"
    assert payload["processing_state"] == "ingested"
    assert payload["retry_count"] == "0"


@pytest.mark.asyncio
async def test_bulk_storage_uses_single_jsonb_recordset_statement():
    session = AsyncMock()

    class Result:
        def fetchall(self):
            return []

    result = Result()
    session.execute.return_value = result
    event = NormalizedEvent(
        source="usgs",
        source_event_id="eq-1",
        hazard_type="earthquake",
        event_timestamp=datetime(2026, 5, 20, tzinfo=UTC),
        latitude=20.0,
        longitude=78.0,
        confidence=1.0,
        raw_payload={"id": "eq-1"},
    )

    await bulk_upsert_hazard_events(session, [event])

    statement = str(session.execute.call_args.args[0])
    assert "jsonb_to_recordset" in statement
    assert "ON CONFLICT (source, source_event_id)" in statement
