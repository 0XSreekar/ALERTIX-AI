import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hazard_type: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    location: Mapped[str | None] = mapped_column(Geography("POINT", srid=4326))
    region: Mapped[str | None] = mapped_column(Geography("POLYGON", srid=4326))
    magnitude: Mapped[float | None] = mapped_column(Float)
    depth_km: Mapped[float | None] = mapped_column(Float)
    intensity: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    probability: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_events_source_external_id"),
        Index("events_location_idx", "location", postgresql_using="gist"),
        Index("events_region_idx", "region", postgresql_using="gist"),
        Index("events_occurred_idx", "occurred_at"),
        Index("events_hazard_idx", "hazard_type"),
    )
