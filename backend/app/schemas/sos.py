from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.sos import SosStatus


class SosCreate(BaseModel):
    raw_text: str = Field(..., min_length=10, max_length=5000)
    language: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    consent_given: bool = False


class SosOut(BaseModel):
    id: UUID
    user_id: UUID | None = None
    raw_text: str
    language: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    extracted_location_text: str | None = None
    urgency_score: float | None = None
    triaged: bool = False
    status: SosStatus = SosStatus.pending
    llm_summary: str | None = None
    related_event_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
