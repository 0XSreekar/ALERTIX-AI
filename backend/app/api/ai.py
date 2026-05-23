"""Grounded AI endpoints for summaries, explanations, and recommendations."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.llm.rag import generate_grounded_response
from app.config import get_settings
import logging

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


class AIRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    region: str | None = Field(None, max_length=120)
    hazard_type: str | None = Field(None, max_length=32)


class AIResponse(BaseModel):
    label: str
    provider: str
    text: str
    citations: list[dict]


async def _run(task: str, req: AIRequest, session: AsyncSession) -> AIResponse:
    settings = get_settings()
    if settings.enable_ai_guardrails:
        forbidden_phrases = (
            "predict",
            "exact",
            "when will",
            "what will be the magnitude",
            "give me evacuation orders",
        )
        q_low = req.question.lower()
        for phrase in forbidden_phrases:
            if phrase in q_low:
                log.info("ai_guardrail_blocked_question phrase=%s", phrase)
                return AIResponse(
                    label="guarded",
                    provider="local",
                    text=(
                        "Request blocked by AI guardrails. For exact predictions or official orders, "
                        "consult authoritative agencies (IMD, NDRF, CWC)."
                    ),
                    citations=[],
                )
    else:
        log.warning("ai_guardrails_disabled; proceeding without guardrails")
    result = await generate_grounded_response(
        session,
        task=task,
        question=req.question,
        region=req.region,
        hazard_type=req.hazard_type,
    )
    return AIResponse(
        label=result.label,
        provider=result.provider,
        text=result.text,
        citations=result.citations,
    )


@router.post("/summarize", response_model=AIResponse)
async def summarize(req: AIRequest, session: AsyncSession = Depends(get_session)) -> AIResponse:
    return await _run("summarize active hazard context", req, session)


@router.post("/explain", response_model=AIResponse)
async def explain(req: AIRequest, session: AsyncSession = Depends(get_session)) -> AIResponse:
    return await _run("explain risk in plain language", req, session)


@router.post("/recommend", response_model=AIResponse)
async def recommend(req: AIRequest, session: AsyncSession = Depends(get_session)) -> AIResponse:
    return await _run("recommend public safety actions grounded in context", req, session)
