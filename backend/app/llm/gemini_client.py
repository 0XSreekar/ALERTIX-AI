"""Google Gemini client (second fallback)."""
from __future__ import annotations

import httpx

from app.config import get_settings

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)


class GeminiClient:
    async def generate(self, prompt: str) -> str:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GEMINI_URL, params={"key": settings.gemini_api_key}, json=payload)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
