"""Cerebras Inference client (primary cloud LLM).

Cerebras serves Llama-3.3-70B at ~2000 tokens/sec via an OpenAI-compatible
API. Free tier: 30 req/min, 14,400 req/day. Docs: https://inference-docs.cerebras.ai
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
            "model": settings.cerebras_model or self.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 512,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.BASE_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
