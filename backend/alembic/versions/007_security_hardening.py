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
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("target_table", new_column_name="entity_type", existing_type=sa.String())
        batch_op.alter_column("target_id", new_column_name="entity_id", existing_type=UUID(as_uuid=True))
        batch_op.alter_column("payload", new_column_name="details", existing_type=JSONB())
        batch_op.add_column(sa.Column("role", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("ip_hash", sa.String(64), nullable=True))

    # Indexes on audit_log — IF NOT EXISTS avoids abort inside a single txn
    op.execute("CREATE INDEX IF NOT EXISTS audit_log_actor_idx ON audit_log (actor_user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS audit_log_entity_idx ON audit_log (entity_type, entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS audit_log_created_idx ON audit_log (created_at)")

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
    op.execute("CREATE INDEX IF NOT EXISTS sos_status_idx ON sos_reports (status)")

    # ── Missing / supplemental indexes ────────────────────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS hazard_events_created_idx ON hazard_events (created_at DESC)")

    # earthquakes
    op.execute(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_earthquakes_source_external_id') THEN "
        "    ALTER TABLE earthquakes ADD CONSTRAINT uq_earthquakes_source_external_id UNIQUE (source, external_id); "
        "  END IF; "
        "END $$"
    )
    op.execute("CREATE INDEX IF NOT EXISTS earthquakes_created_idx ON earthquakes (occurred_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS earthquakes_location_gist_idx ON earthquakes USING gist (location)")

    # wildfires
    op.execute(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_wildfires_source_external_id') THEN "
        "    ALTER TABLE wildfires ADD CONSTRAINT uq_wildfires_source_external_id UNIQUE (source, external_id); "
        "  END IF; "
        "END $$"
    )
    op.execute("CREATE INDEX IF NOT EXISTS wildfires_created_idx ON wildfires (detected_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS wildfires_location_gist_idx ON wildfires USING gist (location)")

    # river_gauges (003 already creates river_gauges_observed_idx — IF NOT EXISTS is safe)
    op.execute("CREATE INDEX IF NOT EXISTS river_gauges_observed_idx ON river_gauges (observed_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS river_gauges_location_gist_idx ON river_gauges USING gist (location)")

    # weather_events (003 already creates weather_events_observed_idx — IF NOT EXISTS is safe)
    op.execute(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_weather_events_source_external_id') THEN "
        "    ALTER TABLE weather_events ADD CONSTRAINT uq_weather_events_source_external_id UNIQUE (source, external_id); "
        "  END IF; "
        "END $$"
    )
    op.execute("CREATE INDEX IF NOT EXISTS weather_events_observed_idx ON weather_events (observed_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS weather_events_location_gist_idx ON weather_events USING gist (location)")

    # alerts
    op.execute("CREATE INDEX IF NOT EXISTS alerts_created_desc_idx ON alerts (created_at DESC)")

    # sos_reports: created_at DESC
    op.execute("CREATE INDEX IF NOT EXISTS sos_created_idx ON sos_reports (created_at DESC)")


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
