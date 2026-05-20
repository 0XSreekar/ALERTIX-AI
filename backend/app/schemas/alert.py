from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AlertOut(BaseModel):
    id: UUID
    hazard_type: str
    severity: str
    title: str
    explanation: str | None = None
    explanation_lang: str = "en"
    explanation_status: str = "pending"
    probability: float | None = None
    event_ids: list[UUID] | None = None
    model_version: str | None = None
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class AlertListParams(BaseModel):
    hazard_type: str | None = None
    severity: str | None = None
    active_only: bool = True
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
