"""Groq cloud LLM client (first fallback)."""
from __future__ import annotations
import httpx
from app.config import settings


class GroqClient:
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.1-70b-versatile"

    async def generate(self, prompt: str) -> str:
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not set")
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}",
                   "Content-Type": "application/json"}
        payload = {"model": self.MODEL,
                   "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.3, "max_tokens": 512}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.BASE_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
