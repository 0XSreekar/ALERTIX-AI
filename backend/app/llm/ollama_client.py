"""Ollama local LLM client (primary in the fallback ladder)."""

from __future__ import annotations

import httpx

from app.config import get_settings


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = get_settings().ollama_url.rstrip("/")
        self.model = "qwen2.5:7b"
        self.timeout = 60.0

    async def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.9},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
