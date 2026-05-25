"""Lightweight Indic language detection via Unicode script ranges.

We do not ship IndicTrans2 weights — the cloud LLM (Cerebras Llama) handles
translation when needed. This module just decides *whether* to translate.
"""

from __future__ import annotations

_RANGES: list[tuple[str, str, range]] = [
    ("hi", "Hindi", range(0x0900, 0x0980)),  # Devanagari
    ("bn", "Bengali", range(0x0980, 0x0A00)),  # Bengali
    ("pa", "Punjabi", range(0x0A00, 0x0A80)),  # Gurmukhi
    ("gu", "Gujarati", range(0x0A80, 0x0B00)),  # Gujarati
    ("or", "Odia", range(0x0B00, 0x0B80)),  # Odia
    ("ta", "Tamil", range(0x0B80, 0x0C00)),  # Tamil
    ("te", "Telugu", range(0x0C00, 0x0C80)),  # Telugu
    ("kn", "Kannada", range(0x0C80, 0x0D00)),  # Kannada
    ("ml", "Malayalam", range(0x0D00, 0x0D80)),  # Malayalam
]

_LANG_NAMES = {code: name for code, name, _ in _RANGES}


def detect_language(text: str) -> str:
    """Return ISO 639-1 code: 'en' if mostly ASCII, otherwise the dominant Indic script."""
    if not text:
        return "en"
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for code, _name, rng in _RANGES:
            if cp in rng:
                counts[code] = counts.get(code, 0) + 1
                break
    if not counts:
        return "en"
    # Require at least 4 Indic characters to call it non-English (avoid false positives on stray glyphs)
    top_code, top_count = max(counts.items(), key=lambda kv: kv[1])
    if top_count < 4:
        return "en"
    return top_code


def language_name(code: str) -> str:
    return _LANG_NAMES.get(code, code)


TRANSLATE_PROMPT = """Translate the following {language} disaster-report message into clear English.
Preserve place names exactly. Output ONLY the English translation, no quotes, no commentary.

Message:
{text}"""


async def translate_to_english(text: str, lang_code: str) -> str:
    """Translate via the LLM provider ladder. Returns original text on failure."""
    if lang_code == "en" or not text.strip():
        return text
    try:
        from app.llm import provider as llm

        prompt = TRANSLATE_PROMPT.format(language=language_name(lang_code), text=text)
        out, _provider = await llm.generate(prompt)
        if out:
            return out.strip().strip('"').strip("'")
    except Exception:
        pass
    return text
