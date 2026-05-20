from app.llm.rag import _guard


def test_ai_guard_prefixes_generated_summary():
    guarded = _guard("Move to higher ground if local authorities advise evacuation.")

    assert guarded.startswith("AI-generated summary, not an official alert:")


def test_ai_guard_replaces_forbidden_official_warning_language():
    guarded = _guard("This is an official warning and exact magnitude will occur at 4 PM.")

    assert "official warning and exact magnitude" not in guarded
    assert "not an official alert" in guarded
