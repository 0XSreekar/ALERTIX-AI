"""LLM provider -- Groq -> Gemini fallback ladder (no local LLM)."""
from __future__ import annotations

import logging

from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient

log = logging.getLogger(__name__)
_groq = GroqClient()
_gemini = GeminiClient()


async def generate(prompt: str) -> tuple[str, str]:
    """Return (text, provider_used). Never raises."""
    try:
        text = await _groq.generate(prompt)
        if text:
            return text, "groq"
    except Exception as exc:
        log.warning("Groq failed: %s", exc)
    try:
        text = await _gemini.generate(prompt)
        if text:
            return text, "gemini"
    except Exception as exc:
        log.warning("Gemini failed: %s", exc)
    log.error("All LLM providers failed — returning templated fallback")
    return "", "none"
