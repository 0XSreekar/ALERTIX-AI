import hashlib
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String)  # formerly target_table
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # formerly target_id
    role: Mapped[str | None] = mapped_column(String)
    ip_hash: Mapped[str | None] = mapped_column(String(64))  # sha256 hex digest
    details: Mapped[dict | None] = mapped_column(JSONB)  # formerly payload
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("audit_log_actor_idx", "actor_user_id"),
        Index("audit_log_entity_idx", "entity_type", "entity_id"),
        Index("audit_log_created_idx", "created_at"),
    )


def hash_ip(ip: str | None) -> str | None:
    """Return SHA-256 hex digest of an IP address, or None if ip is falsy."""
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()


async def write_audit_log(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: Any = None,
    user_id: Any = None,
    role: str | None = None,
    ip: str | None = None,
    details: dict | None = None,
) -> None:
    """Write a single audit log row.

    Callers should NOT pass raw IPs — pass the raw IP here and this function
    will hash it before persisting.
    """
    entry = AuditLog(
        actor_user_id=uuid.UUID(str(user_id)) if user_id else None,
        action=action,
        entity_type=entity_type,
        entity_id=uuid.UUID(str(entity_id)) if entity_id else None,
        role=role,
        ip_hash=hash_ip(ip),
        details=details,
    )
    session.add(entry)
