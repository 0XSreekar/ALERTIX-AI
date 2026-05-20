"""Add citizen reporting, uploads, and damage result tables.

Revision ID: 005
Revises: 004
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "citizen_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("hazard_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", geoalchemy2.Geography("POINT", srid=4326), nullable=False),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("extracted_entities", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("citizen_reports_location_idx", "citizen_reports", ["location"], postgresql_using="gist")
    op.create_index("citizen_reports_status_idx", "citizen_reports", ["status"])
    op.create_index("citizen_reports_user_idx", "citizen_reports", ["user_id"])

    op.create_table(
        "user_reputation",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("verified_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="stored"),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("sha256", name="uq_uploads_sha256"),
    )

    op.create_table(
        "damage_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", UUID(as_uuid=True), nullable=True),
        sa.Column("class_label", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bounding_boxes", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("damage_results")
    op.drop_table("uploads")
    op.drop_table("user_reputation")
    op.drop_table("citizen_reports")
