"""Grounded AI endpoints for summaries, explanations, and recommendations."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.llm.rag import generate_grounded_response

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
