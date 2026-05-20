"""Tests for USGS ingestion module — parsing logic (no DB required)."""

from app.ingestion.usgs import _parse_feature


class TestParseFeature:
    def test_valid_earthquake_feature(self):
        feature = {
            "id": "us7000test",
            "properties": {
                "mag": 5.2,
                "place": "10km NE of Test City",
                "time": 1700000000000,
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000test",
                "felt": 100,
                "cdi": 5.0,
                "mmi": 4.5,
                "alert": "green",
                "status": "reviewed",
                "tsunami": 0,
                "sig": 450,
                "net": "us",
                "type": "earthquake",
                "title": "M 5.2 - 10km NE of Test City",
                "code": "7000test",
            },
            "geometry": {"type": "Point", "coordinates": [78.5, 20.3, 10.0]},
        }

        result = _parse_feature(feature)
        assert result is not None
        assert result["hazard_type"] == "earthquake"
        assert result["source"] == "usgs"
        assert result["external_id"] == "us7000test"
        assert result["longitude"] == 78.5
        assert result["latitude"] == 20.3
        assert result["depth_km"] == 10.0
        assert result["magnitude"] == 5.2
        assert result["metadata"]["tsunami"] is False

    def test_missing_coordinates_returns_none(self):
        feature = {
            "id": "test1",
            "properties": {"mag": 3.0, "time": 1700000000000},
            "geometry": {"type": "Point", "coordinates": []},
        }
        assert _parse_feature(feature) is None

    def test_missing_time_returns_none(self):
        feature = {
            "id": "test2",
            "properties": {"mag": 3.0},
            "geometry": {"type": "Point", "coordinates": [78.0, 20.0]},
        }
        assert _parse_feature(feature) is None

    def test_tsunami_flag_true(self):
        feature = {
            "id": "ts1",
            "properties": {"mag": 7.0, "time": 1700000000000, "tsunami": 1},
            "geometry": {"type": "Point", "coordinates": [90.0, 10.0, 30.0]},
        }
        result = _parse_feature(feature)
        assert result is not None
        assert result["metadata"]["tsunami"] is True
