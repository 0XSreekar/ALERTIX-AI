"""Extend damage_results for per-user history and richer outputs.

Revision ID: 008
Revises: 007
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE damage_results
            ADD COLUMN IF NOT EXISTS user_id TEXT,
            ADD COLUMN IF NOT EXISTS upload_sha256 TEXT,
            ADD COLUMN IF NOT EXISTS class_probs JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS nearest_event_id UUID,
            ADD COLUMN IF NOT EXISTS notes TEXT
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS damage_results_user_idx "
        "ON damage_results (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS damage_results_sha_idx ON damage_results (upload_sha256)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS damage_results_user_idx")
    op.execute("DROP INDEX IF EXISTS damage_results_sha_idx")
    for col in (
        "user_id",
        "upload_sha256",
        "class_probs",
        "latitude",
        "longitude",
        "nearest_event_id",
        "notes",
    ):
        op.drop_column("damage_results", col)
    _ = sa  # keep import for downgrades that need it
    _ = JSONB
