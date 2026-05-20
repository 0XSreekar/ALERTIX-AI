"""Internal LLM endpoints — cron-token protected."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from app.config import get_settings
from app.llm import provider as llm
from app.llm.prompts import get_template, SOS_TRIAGE

log = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/internal/llm", tags=["llm-internal"])


def _require_cron_token(x_cron_token: str = Header(...)) -> None:
    if x_cron_token != settings.cron_token:
        raise HTTPException(status_code=403, detail="invalid cron token")


class ExplainRequest(BaseModel):
    hazard_type: str
    event_data: dict[str, Any]


class ExplainResponse(BaseModel):
    explanation: str
    provider: str
    hazard_type: str


class TriageRequest(BaseModel):
    message: str
    location: str = ""


class TriageResponse(BaseModel):
    urgency_score: int
    category: str
    summary: str
    recommended_action: str
    provider: str


@router.post("/explain", response_model=ExplainResponse)
async def explain_event(
    req: ExplainRequest,
    _: None = Depends(_require_cron_token),
) -> ExplainResponse:
    template = get_template(req.hazard_type)
    prompt = template.format(event_json=json.dumps(req.event_data, indent=2))
    text, provider = await llm.generate(prompt)
    if not text:
        raise HTTPException(status_code=503, detail="all LLM providers failed")
    return ExplainResponse(explanation=text, provider=provider, hazard_type=req.hazard_type)


@router.post("/triage", response_model=TriageResponse)
async def triage_sos(
    req: TriageRequest,
    _: None = Depends(_require_cron_token),
) -> TriageResponse:
    prompt = SOS_TRIAGE.format(message=req.message, location=req.location or "unknown")
    raw, provider = await llm.generate(prompt)
    if not raw:
        raise HTTPException(status_code=503, detail="all LLM providers failed")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
        data = json.loads(match.group(0))
    return TriageResponse(**data, provider=provider)


@router.get("/health")
async def llm_health() -> dict:
    from app.llm.ollama_client import OllamaClient
    ollama_up = await OllamaClient().health()
    return {
        "ollama": ollama_up,
        "groq_configured": bool(settings.groq_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
    }
