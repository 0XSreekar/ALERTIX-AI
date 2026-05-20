"""Internal LLM endpoints — Phase 2.

POST /internal/llm/explain — generates alert explanation
POST /internal/llm/triage_sos — scores and summarizes SOS report
"""

from fastapi import APIRouter, Depends

from app.auth.deps import verify_cron_token

router = APIRouter(prefix="/internal/llm", tags=["internal"])


@router.post("/explain", dependencies=[Depends(verify_cron_token)])
async def explain_event(event_id: str, lang: str = "en") -> dict:
    # Phase 2: call Ollama/Groq/Gemini fallback ladder
    return {
        "status": "phase2",
        "message": "LLM explanation will be available in Phase 2",
        "event_id": event_id,
        "lang": lang,
    }


@router.post("/triage_sos", dependencies=[Depends(verify_cron_token)])
async def triage_sos(sos_id: str) -> dict:
    # Phase 2: call LLM for urgency scoring + summary
    return {
        "status": "phase2",
        "message": "SOS triage will be available in Phase 2",
        "sos_id": sos_id,
    }
