"""Parser-level tests for CWC flood ingestion.

Catches two failure modes that have historically silently broken the pipeline:
  1. Code drift — parser changes that drop fields or coordinates.
  2. Upstream drift — CWC renames columns / changes layout. detect_schema_drift
     flips True and the cron should fall back to a secondary source.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.flood.parser import (
    detect_schema_drift,
    fingerprint_html,
    parse_cwc_gauge_tables,
)

FIXTURES = Path(__file__).parent / "fixtures" / "flood"


@pytest.fixture
def cwc_sample_html() -> str:
    return (FIXTURES / "cwc_dashboard_sample.html").read_text(encoding="utf-8")


def test_parses_all_rows_from_fixture(cwc_sample_html: str) -> None:
    events = parse_cwc_gauge_tables(cwc_sample_html)
    assert len(events) == 3
    stations = {e.normalized_payload["station"] for e in events}
    assert stations == {"Patna (Gandhi Ghat)", "Hathidah", "Dholaikuan"}


def test_extracts_lat_lon_for_all_events(cwc_sample_html: str) -> None:
    events = parse_cwc_gauge_tables(cwc_sample_html)
    for event in events:
        assert event.latitude is not None and 6 < event.latitude < 38, event
        assert event.longitude is not None and 67 < event.longitude < 98, event


def test_severity_classification(cwc_sample_html: str) -> None:
    events = parse_cwc_gauge_tables(cwc_sample_html)
    by_station = {e.normalized_payload["station"]: e for e in events}
    # Patna 50.20 > warning 48.60 but < danger 50.45  → severity 2 (warning)
    assert by_station["Patna (Gandhi Ghat)"].intensity == 2.0
    # Hathidah 41.30 < warning 41.76                  → severity 1 (normal)
    assert by_station["Hathidah"].intensity == 1.0
    # Dholaikuan 205.10 > warning, < danger 205.33    → severity 2 (warning)
    assert by_station["Dholaikuan"].intensity == 2.0


def test_no_drift_on_known_layout(cwc_sample_html: str) -> None:
    drift, recognised = detect_schema_drift(cwc_sample_html)
    assert drift is False
    assert {"river", "basin", "warning level", "danger level"}.issubset(recognised)


def test_drift_flagged_on_unknown_layout() -> None:
    broken = """
    <html><body><table>
      <thead><tr><th>Foo</th><th>Bar</th><th>Baz</th></tr></thead>
      <tbody><tr><td>1</td><td>2</td><td>3</td></tr></tbody>
    </table></body></html>
    """
    drift, recognised = detect_schema_drift(broken)
    assert drift is True
    assert recognised == set()


def test_fingerprint_stable_across_data_changes(cwc_sample_html: str) -> None:
    """Fingerprint should hash on headers only, not row data."""
    different_data = cwc_sample_html.replace("50.20", "99.99").replace("Rising", "Steady")
    assert fingerprint_html(cwc_sample_html) == fingerprint_html(different_data)


def test_fingerprint_flips_when_header_renamed(cwc_sample_html: str) -> None:
    renamed = cwc_sample_html.replace("Warning Level", "Alert Threshold")
    assert fingerprint_html(cwc_sample_html) != fingerprint_html(renamed)
