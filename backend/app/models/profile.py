import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    full_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String, nullable=False, default="citizen")
    home_location: Mapped[str | None] = mapped_column(Geography("POINT", srid=4326))
    preferred_lang: Mapped[str] = mapped_column(String, default="en")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
