from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    hazard_type: str
    source: str
    external_id: str | None = None
    occurred_at: datetime
    latitude: float | None = None
    longitude: float | None = None
    magnitude: float | None = None
    depth_km: float | None = None
    intensity: float | None = None
    metadata: dict | None = None


class EventOut(BaseModel):
    id: UUID
    hazard_type: str
    source: str
    external_id: str | None = None
    occurred_at: datetime
    latitude: float | None = None
    longitude: float | None = None
    magnitude: float | None = None
    depth_km: float | None = None
    intensity: float | None = None
    metadata: dict | None = None
    anomaly_score: float | None = None
    probability: float | None = None
    model_version: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListParams(BaseModel):
    hazard_type: str | None = None
    from_dt: datetime | None = Field(None, alias="from")
    to_dt: datetime | None = Field(None, alias="to")
    bbox: str | None = None  # "minlon,minlat,maxlon,maxlat"
    severity: str | None = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
