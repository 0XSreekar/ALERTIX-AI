from app.citizen.service import extract_entities, reputation_tier, score_report
from app.schemas.citizen import CitizenReportCreate


def test_reputation_tiers_match_spec():
    assert reputation_tier(80) == "trusted"
    assert reputation_tier(40) == "normal"
    assert reputation_tier(10) == "flagged"
    assert reputation_tier(9) == "blocked"


def test_entity_extraction_finds_hazard_and_places():
    entities = extract_entities("Flood near Vijayawada Krishna River bridge", "flood")

    assert "flood" in entities["hazards"]
    assert "Vijayawada Krishna River" in entities["places"]


def test_trusted_report_with_media_scores_for_auto_approval():
    report = CitizenReportCreate(
        hazard_type="flood",
        description="Flood near Vijayawada Krishna River bridge",
        latitude=16.5,
        longitude=80.6,
        media_url="https://example.test/image.jpg",
    )
    entities = extract_entities(report.description, report.hazard_type)

    assert score_report(report, entities, "trusted", duplicate=False) >= 0.85


def test_duplicate_report_penalty_prevents_high_confidence():
    report = CitizenReportCreate(
        hazard_type="flood",
        description="Flood near Vijayawada Krishna River bridge",
        latitude=16.5,
        longitude=80.6,
        media_url="https://example.test/image.jpg",
    )
    entities = extract_entities(report.description, report.hazard_type)

    assert score_report(report, entities, "trusted", duplicate=True) < 0.85
