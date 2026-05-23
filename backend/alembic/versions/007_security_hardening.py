"""Security hardening: audit_log columns, SOS status enum, missing indexes.

Revision ID: 007
Revises: 006
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── audit_log: rename columns, add new ones ────────────────────────────
    # Rename target_table -> entity_type, target_id -> entity_id, payload -> details
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("target_table", new_column_name="entity_type", existing_type=sa.String())
        batch_op.alter_column("target_id", new_column_name="entity_id", existing_type=UUID(as_uuid=True))
        batch_op.alter_column("payload", new_column_name="details", existing_type=JSONB())
        batch_op.add_column(sa.Column("role", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("ip_hash", sa.String(64), nullable=True))

    # Indexes on audit_log
    op.create_index("audit_log_actor_idx", "audit_log", ["actor_user_id"])
    op.create_index("audit_log_entity_idx", "audit_log", ["entity_type", "entity_id"])
    op.create_index("audit_log_created_idx", "audit_log", ["created_at"])

    # ── SOS reports: add status enum column ───────────────────────────────
    sos_status_enum = sa.Enum(
        "pending", "triaged", "dispatched", "resolved",
        name="sos_status",
        create_constraint=True,
    )
    sos_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "sos_reports",
        sa.Column(
            "status",
            sos_status_enum,
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index("sos_status_idx", "sos_reports", ["status"])

    # ── Missing database indexes (issue 21) ───────────────────────────────
    # hazard_events: composite unique already enforced by schema; add created_at index
    op.create_index(
        "hazard_events_created_idx",
        "hazard_events",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    # earthquakes: composite unique on (source, external_id) — ensure index exists
    try:
        op.create_unique_constraint(
            "uq_earthquakes_source_external_id", "earthquakes", ["source", "external_id"]
        )
    except Exception:
        pass  # already exists from earlier migration

    op.create_index(
        "earthquakes_created_idx",
        "earthquakes",
        ["occurred_at"],
        postgresql_ops={"occurred_at": "DESC"},
    )
    op.create_index(
        "earthquakes_location_gist_idx",
        "earthquakes",
        ["location"],
        postgresql_using="gist",
    )

    # wildfires
    try:
        op.create_unique_constraint(
            "uq_wildfires_source_external_id", "wildfires", ["source", "external_id"]
        )
    except Exception:
        pass

    op.create_index(
        "wildfires_created_idx",
        "wildfires",
        ["detected_at"],
        postgresql_ops={"detected_at": "DESC"},
    )
    op.create_index(
        "wildfires_location_gist_idx",
        "wildfires",
        ["location"],
        postgresql_using="gist",
    )

    # river_gauges
    op.create_index(
        "river_gauges_observed_idx",
        "river_gauges",
        ["observed_at"],
        postgresql_ops={"observed_at": "DESC"},
    )
    op.create_index(
        "river_gauges_location_gist_idx",
        "river_gauges",
        ["location"],
        postgresql_using="gist",
    )

    # weather_events
    try:
        op.create_unique_constraint(
            "uq_weather_events_source_external_id", "weather_events", ["source", "external_id"]
        )
    except Exception:
        pass

    op.create_index(
        "weather_events_observed_idx",
        "weather_events",
        ["observed_at"],
        postgresql_ops={"observed_at": "DESC"},
    )
    op.create_index(
        "weather_events_location_gist_idx",
        "weather_events",
        ["location"],
        postgresql_using="gist",
    )

    # alerts: created_at DESC index (already created by model but add if missing)
    try:
        op.create_index(
            "alerts_created_desc_idx",
            "alerts",
            ["created_at"],
            postgresql_ops={"created_at": "DESC"},
        )
    except Exception:
        pass

    # sos_reports: created_at DESC
    op.create_index(
        "sos_created_idx",
        "sos_reports",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    # Drop extra table indexes
    for idx, tbl in [
        ("hazard_events_created_idx", "hazard_events"),
        ("earthquakes_created_idx", "earthquakes"),
        ("earthquakes_location_gist_idx", "earthquakes"),
        ("wildfires_created_idx", "wildfires"),
        ("wildfires_location_gist_idx", "wildfires"),
        ("river_gauges_observed_idx", "river_gauges"),
        ("river_gauges_location_gist_idx", "river_gauges"),
        ("weather_events_observed_idx", "weather_events"),
        ("weather_events_location_gist_idx", "weather_events"),
    ]:
        try:
            op.drop_index(idx, table_name=tbl)
        except Exception:
            pass

    # sos_reports
    op.drop_index("sos_created_idx", table_name="sos_reports")
    op.drop_index("sos_status_idx", table_name="sos_reports")
    op.drop_column("sos_reports", "status")
    sa.Enum(name="sos_status").drop(op.get_bind(), checkfirst=True)

    # audit_log
    op.drop_index("audit_log_created_idx", table_name="audit_log")
    op.drop_index("audit_log_entity_idx", table_name="audit_log")
    op.drop_index("audit_log_actor_idx", table_name="audit_log")
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.drop_column("ip_hash")
        batch_op.drop_column("role")
        batch_op.alter_column("details", new_column_name="payload", existing_type=JSONB())
        batch_op.alter_column(
            "entity_id",
            new_column_name="target_id",
            existing_type=UUID(as_uuid=True),
        )
        batch_op.alter_column("entity_type", new_column_name="target_table", existing_type=sa.String())
