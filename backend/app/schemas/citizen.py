from uuid import UUID

from pydantic import BaseModel, Field


class CitizenReportCreate(BaseModel):
    hazard_type: str = Field(..., min_length=3, max_length=32)
    description: str = Field(..., min_length=3, max_length=2000)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    media_url: str | None = Field(None, max_length=2048)


class CitizenReportOut(BaseModel):
    id: UUID
    hazard_type: str
    status: str
    confidence_score: float
    extracted_entities: dict


class VerifyReportRequest(BaseModel):
    report_id: UUID
    decision: str = Field(..., pattern="^(verified|rejected)$")
    reason: str | None = Field(None, max_length=1000)


class ReputationOut(BaseModel):
    user_id: str
    score: int
    tier: str
    verified_count: int
    rejected_count: int
