"""Add realtime processing tables and indexes.

Revision ID: 004
Revises: 003
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("hazard_type", sa.String(), nullable=False),
        sa.Column("processing_state", sa.String(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("alert_tier", sa.String(), nullable=False, server_default="LOW"),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index(
        "processed_events_hazard_state_idx",
        "processed_events",
        ["hazard_type", "processing_state"],
    )
    op.create_index("processed_events_tier_idx", "processed_events", ["alert_tier"])

    op.create_table(
        "risk_scores",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("hazard_type", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("explanation", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("risk_scores_event_idx", "risk_scores", ["event_id"])
    op.create_index("risk_scores_hazard_created_idx", "risk_scores", ["hazard_type", sa.text("created_at DESC")])

    op.create_index(
        "alerts_hazard_severity_created_idx",
        "alerts",
        ["hazard_type", "severity", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("alerts_hazard_severity_created_idx", table_name="alerts")
    op.drop_table("risk_scores")
    op.drop_table("processed_events")
