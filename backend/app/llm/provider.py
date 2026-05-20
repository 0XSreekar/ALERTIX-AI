"""LLM provider -- Ollama -> Groq -> Gemini fallback ladder."""
from __future__ import annotations

import logging

from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient
from app.llm.ollama_client import OllamaClient

log = logging.getLogger(__name__)
_ollama = OllamaClient()
_groq = GroqClient()
_gemini = GeminiClient()


async def generate(prompt: str) -> tuple[str, str]:
    """Return (text, provider_used). Never raises."""
    try:
        if await _ollama.health():
            text = await _ollama.generate(prompt)
            if text:
                return text, "ollama"
    except Exception as exc:
        log.warning("Ollama failed: %s", exc)
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
