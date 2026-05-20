import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SosReport(Base):
    __tablename__ = "sos_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(Geography("POINT", srid=4326))
    extracted_location_text: Mapped[str | None] = mapped_column(Text)
    urgency_score: Mapped[float | None] = mapped_column(Float)
    triaged: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_summary: Mapped[str | None] = mapped_column(Text)
    related_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("sos_location_idx", "location", postgresql_using="gist"),
        Index("sos_urgency_idx", "urgency_score"),
    )
