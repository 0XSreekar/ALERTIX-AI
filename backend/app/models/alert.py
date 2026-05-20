import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import Float, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hazard_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str | None] = mapped_column(Geography("POLYGON", srid=4326))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    explanation_lang: Mapped[str] = mapped_column(String, default="en")
    explanation_status: Mapped[str] = mapped_column(String, default="pending")
    probability: Mapped[float | None] = mapped_column(Float)
    event_ids: Mapped[list | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    model_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column()

    __table_args__ = (
        Index("alerts_region_idx", "region", postgresql_using="gist"),
        Index("alerts_created_idx", "created_at"),
    )
