"""LLM provider — Cerebras -> Groq -> Gemini fallback ladder.

All three providers run Llama 3.3 70B (or Gemini 2.5 Flash) on free hosted
infrastructure: no local server, no Cloudflare Tunnel, no laptop dependency.

Ollama is supported as an optional override when OLLAMA_PRIMARY=true is set
in the environment, but is NOT in the default path so the system stays
production-online even when the developer machine is off.
"""

from __future__ import annotations

import logging
import os

from app.llm.cerebras_client import CerebrasClient
from app.llm.gemini_client import GeminiClient
from app.llm.groq_client import GroqClient
from app.llm.ollama_client import OllamaClient

log = logging.getLogger(__name__)

_cerebras = CerebrasClient()
_groq = GroqClient()
_gemini = GeminiClient()
_ollama = OllamaClient()

_OLLAMA_FIRST = os.getenv("OLLAMA_PRIMARY", "false").lower() in ("1", "true", "yes")


async def generate(prompt: str) -> tuple[str, str]:
    """Return (text, provider_used). Never raises."""
    # Optional local-first override for offline dev
    if _OLLAMA_FIRST:
        try:
            if await _ollama.health():
                text = await _ollama.generate(prompt)
                if text:
                    return text, "ollama"
        except Exception as exc:
            log.warning("Ollama failed: %s", exc)

    # Tier 1 — Cerebras (fastest, most generous free tier)
    try:
        text = await _cerebras.generate(prompt)
        if text:
            return text, "cerebras"
    except Exception as exc:
        log.warning("Cerebras failed: %s", exc)

    # Tier 2 — Groq (also Llama 3.3 70B, proven fallback)
    try:
        text = await _groq.generate(prompt)
        if text:
            return text, "groq"
    except Exception as exc:
        log.warning("Groq failed: %s", exc)

    # Tier 3 — Gemini Flash (different model family, true independence)
    try:
        text = await _gemini.generate(prompt)
        if text:
            return text, "gemini"
    except Exception as exc:
        log.warning("Gemini failed: %s", exc)

    log.error("All LLM providers failed — returning templated fallback")
    return "", "none"
