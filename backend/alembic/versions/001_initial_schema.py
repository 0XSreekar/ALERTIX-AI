"""Initial schema — all tables per Section 8 of spec

Revision ID: 001
Revises:
Create Date: 2026-05-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
import geoalchemy2

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── profiles ───────────────────────────────────────────────
    op.create_table(
        "profiles",
        sa.Column("user_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.Text, nullable=True),
        sa.Column("role", sa.String, nullable=False, server_default="citizen"),
        sa.Column(
            "home_location",
            geoalchemy2.Geography("POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("preferred_lang", sa.String, server_default="en"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── events ─────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("hazard_type", sa.String, nullable=False),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("external_id", sa.String, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geography("POINT", srid=4326),
            nullable=True,
        ),
        sa.Column(
            "region",
            geoalchemy2.Geography("POLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column("magnitude", sa.Float, nullable=True),
        sa.Column("depth_km", sa.Float, nullable=True),
        sa.Column("intensity", sa.Float, nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("anomaly_score", sa.Float, nullable=True),
        sa.Column("probability", sa.Float, nullable=True),
        sa.Column("model_version", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("source", "external_id", name="uq_events_source_external_id"),
    )
    op.create_index(
        "events_location_idx", "events", ["location"], postgresql_using="gist"
    )
    op.create_index(
        "events_region_idx", "events", ["region"], postgresql_using="gist"
    )
    op.create_index("events_occurred_idx", "events", [sa.text("occurred_at DESC")])
    op.create_index("events_hazard_idx", "events", ["hazard_type"])

    # ── alerts ─────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("hazard_type", sa.String, nullable=False),
        sa.Column("severity", sa.String, nullable=False),
        sa.Column(
            "region",
            geoalchemy2.Geography("POLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("explanation_lang", sa.String, server_default="en"),
        sa.Column("explanation_status", sa.String, server_default="pending"),
        sa.Column("probability", sa.Float, nullable=True),
        sa.Column("event_ids", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("model_version", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "alerts_region_idx", "alerts", ["region"], postgresql_using="gist"
    )
    op.create_index("alerts_created_idx", "alerts", [sa.text("created_at DESC")])

    # ── sos_reports ────────────────────────────────────────────
    op.create_table(
        "sos_reports",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("language", sa.String, nullable=True),
        sa.Column(
            "location",
            geoalchemy2.Geography("POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("extracted_location_text", sa.Text, nullable=True),
        sa.Column("urgency_score", sa.Float, nullable=True),
        sa.Column("triaged", sa.Boolean, server_default=sa.text("false")),
        sa.Column("llm_summary", sa.Text, nullable=True),
        sa.Column(
            "related_event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "sos_location_idx", "sos_reports", ["location"], postgresql_using="gist"
    )
    op.create_index("sos_urgency_idx", "sos_reports", [sa.text("urgency_score DESC")])

    # ── audit_log ──────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("target_table", sa.String, nullable=True),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── model_versions ─────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("model_name", sa.String, nullable=False),
        sa.Column("version", sa.String, nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", JSONB, nullable=True),
        sa.Column("artifact_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("false")),
        sa.UniqueConstraint("model_name", "version", name="uq_model_name_version"),
    )

    # ── regions ────────────────────────────────────────────────
    op.create_table(
        "regions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("region_type", sa.String, nullable=False),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("regions.id"),
            nullable=True,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.Geography("MULTIPOLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("metadata", JSONB, nullable=True),
    )
    op.create_index(
        "regions_geom_idx", "regions", ["geometry"], postgresql_using="gist"
    )
    op.create_index("regions_type_idx", "regions", ["region_type"])


def downgrade() -> None:
    op.drop_table("regions")
    op.drop_table("model_versions")
    op.drop_table("audit_log")
    op.drop_table("sos_reports")
    op.drop_table("alerts")
    op.drop_table("events")
    op.drop_table("profiles")
