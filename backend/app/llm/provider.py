"""LLM provider -- Cerebras -> Groq -> Gemini -> (Ollama dev override) fallback ladder.

Cerebras is the primary cloud provider (fastest, free tier). Groq + Gemini
are warm backups. Ollama is checked first only if it is actually running
locally — useful for offline / privacy-sensitive dev work.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.llm.cerebras_client import CerebrasClient
from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient
from app.llm.ollama_client import OllamaClient

log = logging.getLogger(__name__)
_ollama = OllamaClient()
_cerebras = CerebrasClient()
_groq = GroqClient()
_gemini = GeminiClient()


async def generate(prompt: str) -> tuple[str, str]:
    """Return (text, provider_used). Never raises."""
    settings = get_settings()

    # Ollama (optional local primary — only if running)
    try:
        if await _ollama.health():
            text = await _ollama.generate(prompt)
            if text:
                return text, "ollama"
    except Exception as exc:
        log.debug("ollama unavailable: %s", exc)

    # Cerebras (primary cloud)
    if settings.cerebras_api_key:
        try:
            text = await _cerebras.generate(prompt)
            if text:
                return text, "cerebras"
        except Exception as exc:
            log.warning("cerebras_failed: %s", exc)

    # Groq (fallback)
    if settings.groq_api_key:
        try:
            text = await _groq.generate(prompt)
            if text:
                return text, "groq"
        except Exception as exc:
            log.warning("groq_failed: %s", exc)

    # Gemini (final fallback)
    if settings.gemini_api_key:
        try:
            text = await _gemini.generate(prompt)
            if text:
                return text, "gemini"
        except Exception as exc:
            log.warning("gemini_failed: %s", exc)

    log.error("all_llm_providers_failed — returning templated fallback")
    return "", "none"
