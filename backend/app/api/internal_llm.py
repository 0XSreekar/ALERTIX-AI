"""Internal LLM endpoints — cron-token protected."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.llm import provider as llm
from app.llm.prompts import SOS_TRIAGE, get_template
from app.logging import get_logger

# Valid triage categories — kept in sync with the SOS_TRIAGE prompt in app/llm/prompts.py
_TRIAGE_CATEGORIES = (
    "injury",
    "trapped",
    "missing",
    "infrastructure",
    "medical",
    "resource_request",
    "information",
    "other",
)
TriageCategory = Literal[
    "injury",
    "trapped",
    "missing",
    "infrastructure",
    "medical",
    "resource_request",
    "information",
    "other",
]

log = get_logger(__name__)
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


class TriageOutput(BaseModel):
    """Schema the LLM is required to return. Validates urgency range and category."""

    urgency_score: int = Field(ge=1, le=5)
    category: TriageCategory
    summary: str = Field(min_length=1, max_length=500)
    recommended_action: str = Field(min_length=1, max_length=500)


class TriageResponse(TriageOutput):
    provider: str


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _try_parse_triage(raw: str) -> TriageOutput | None:
    """Parse LLM output as TriageOutput. Returns None on any failure.

    Tries strict JSON first, then falls back to extracting the first {...}
    block — providers sometimes wrap JSON in prose or code fences."""
    try:
        return TriageOutput.model_validate_json(raw)
    except (ValueError, ValidationError):
        pass
    match = _JSON_OBJECT_RE.search(raw)
    if not match:
        return None
    try:
        return TriageOutput.model_validate_json(match.group(0))
    except (ValueError, ValidationError):
        return None


_REPAIR_PROMPT = (
    "The previous response was not valid JSON for the SOS triage schema. "
    "Respond ONLY with a single JSON object — no prose, no markdown, no code fences — "
    "matching exactly this schema:\n"
    '{{"urgency_score": <int 1-5>, '
    '"category": <one of {categories}>, '
    '"summary": <string>, '
    '"recommended_action": <string>}}\n\n'
    "Original SOS message:\n"
    '"""{message}"""\n'
    "Location: {location}"
)


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

    parsed = _try_parse_triage(raw)
    if parsed is None:
        # One repair attempt with a stricter prompt before giving up. LLMs
        # often comply when explicitly told the previous output was invalid.
        log.warning("llm_triage_parse_failed", provider=provider, raw_preview=raw[:200])
        repair_prompt = _REPAIR_PROMPT.format(
            categories=json.dumps(list(_TRIAGE_CATEGORIES)),
            message=req.message,
            location=req.location or "unknown",
        )
        raw_retry, provider = await llm.generate(repair_prompt)
        if raw_retry:
            parsed = _try_parse_triage(raw_retry)

    if parsed is None:
        raise HTTPException(
            status_code=502,
            detail="LLM returned output that does not match the triage schema after retry",
        )

    return TriageResponse(**parsed.model_dump(), provider=provider)


@router.get("/health")
async def llm_health() -> dict:
    from app.llm.ollama_client import OllamaClient

    ollama_up = await OllamaClient().health()
    return {
        "ollama": ollama_up,
        "cerebras_configured": bool(settings.cerebras_api_key),
        "groq_configured": bool(settings.groq_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
    }
