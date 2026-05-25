"""Gemini Vision client for damage assessment from imagery.

Uses gemini-2.0-flash (or whatever's in settings.gemini_vision_model) — the
free tier serves vision-capable Flash models at ~15 req/min, 1500 req/day.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)

DAMAGE_CLASSES = ("no_damage", "minor", "major", "destroyed")

_PROMPT = """You are an expert disaster damage assessor analyzing post-event imagery from India.

Classify the building/scene damage into exactly ONE of these four categories and return per-class probabilities (must sum to ~1.0):
- no_damage: intact structures, no visible damage
- minor: superficial damage, minor flooding, cracks, debris
- major: significant structural damage, partial collapse, deep flooding affecting buildings
- destroyed: total or near-total destruction, complete collapse, washed away

Also return a 1-2 sentence description of what you see (visible hazards, affected structures, flood/fire/debris extent).

Return ONLY valid JSON in this exact schema, no markdown fences, no extra text:
{
  "class_label": "no_damage" | "minor" | "major" | "destroyed",
  "confidence": 0.0-1.0,
  "class_probs": {"no_damage": 0.0, "minor": 0.0, "major": 0.0, "destroyed": 0.0},
  "description": "1-2 sentence description",
  "visible_hazards": ["flood" | "fire" | "structural_damage" | "debris" | "landslide" | ...]
}"""


@dataclass(frozen=True, slots=True)
class GeminiDamageResult:
    class_label: str
    confidence: float
    class_probs: dict[str, float]
    description: str
    visible_hazards: list[str]
    raw_response: str


class GeminiVisionClient:
    def _url(self, model: str) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    async def analyze_damage(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> GeminiDamageResult:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        model = getattr(settings, "gemini_vision_model", None) or "gemini-2.0-flash"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": _PROMPT},
                        {"inline_data": {"mime_type": mime_type, "data": b64}},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url(model),
                params={"key": settings.gemini_api_key},
                json=payload,
            )
            if resp.status_code >= 400:
                log.warning(
                    "gemini_vision_http_error", status=resp.status_code, body=resp.text[:300]
                )
            resp.raise_for_status()
            data = resp.json()

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Gemini returned no text: {data}") from exc

        return self._parse(text)

    @staticmethod
    def _parse(text: str) -> GeminiDamageResult:
        # Try strict JSON first; fall back to first {...} block
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise RuntimeError(f"Could not extract JSON from: {text[:200]}") from exc
            obj = json.loads(match.group(0))

        label = str(obj.get("class_label", "")).lower().strip()
        if label not in DAMAGE_CLASSES:
            # Coerce to nearest valid label
            label = "minor" if "minor" in label else ("major" if "major" in label else "no_damage")

        # Normalize probabilities so they sum to ~1.0
        raw_probs = obj.get("class_probs", {}) or {}
        probs = {c: float(raw_probs.get(c, 0.0)) for c in DAMAGE_CLASSES}
        total = sum(probs.values())
        if total <= 1e-6:
            probs = {c: (1.0 if c == label else 0.0) for c in DAMAGE_CLASSES}
        else:
            probs = {c: v / total for c, v in probs.items()}

        confidence = float(obj.get("confidence", probs.get(label, 0.0)))
        confidence = max(0.0, min(1.0, confidence))

        return GeminiDamageResult(
            class_label=label,
            confidence=confidence,
            class_probs=probs,
            description=str(obj.get("description", "")).strip(),
            visible_hazards=[str(h) for h in (obj.get("visible_hazards") or []) if h],
            raw_response=text,
        )
