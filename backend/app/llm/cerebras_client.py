"""Cerebras Cloud LLM client (primary in the fallback ladder).

Qwen 3 235B (MoE, 22B active) at wafer-scale speed — Cerebras's flagship
free model as of May 2026.  Frontier-class accuracy with excellent native
support for Hindi/Tamil/Bengali/Telugu — critical for SOS triage in India.
OpenAI-compatible chat-completions endpoint.

Free tier: 60K tokens/min, ~1,700 req/day, no credit card.
"""

from __future__ import annotations

import httpx

from app.config import get_settings


class CerebrasClient:
    BASE_URL = "https://api.cerebras.ai/v1/chat/completions"
    MODEL = "qwen-3-235b-a22b-instruct-2507"

    async def generate(self, prompt: str) -> str:
        settings = get_settings()
        if not settings.cerebras_api_key:
            raise RuntimeError("CEREBRAS_API_KEY not set")
        headers = {
            "Authorization": f"Bearer {settings.cerebras_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 512,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.BASE_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
