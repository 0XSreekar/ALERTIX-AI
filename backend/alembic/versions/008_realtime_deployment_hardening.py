"""Realtime deployment hardening.

Revision ID: 008
Revises: 007
Create Date: 2026-05-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_index(name: str) -> None:
    op.execute(f"DROP INDEX IF EXISTS {name}")


def _idx(name: str, table: str, cols: str, *, method: str = "btree") -> None:
    using = f" USING {method}" if method != "btree" else ""
    op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}{using} ({cols})")


def upgrade() -> None:
    # Remove duplicate indexes that were introduced while the schema was being
    # rebuilt. Keeping all of them slows every realtime insert/upsert.
    for index_name in [
        "idx_alerts_region",
        "alerts_created_idx",
        "idx_citizen_reports_location",
        "idx_cyclones_location",
        "uq_earthquakes_source_external_id",
        "earthquakes_created_idx",
        "earthquakes_location_gist_idx",
        "idx_earthquakes_location",
        "idx_events_region",
        "idx_events_location",
        "idx_hazard_events_location",
        "idx_regions_geometry",
        "idx_river_gauges_location",
        "river_gauges_location_gist_idx",
        "idx_sos_reports_location",
        "uq_weather_events_source_external_id",
        "idx_weather_events_location",
        "weather_events_location_gist_idx",
        "uq_wildfires_source_external_id",
        "wildfires_created_idx",
        "idx_wildfires_location",
        "wildfires_location_gist_idx",
    ]:
        _drop_index(index_name)

    # BRIN indexes keep large append-only time-series scans cheap without the
    # write amplification of additional btree duplicates.
    _idx("hazard_events_event_timestamp_brin_idx", "hazard_events", "event_timestamp", method="brin")
    _idx("events_occurred_brin_idx", "events", "occurred_at", method="brin")
    _idx("earthquakes_occurred_brin_idx", "earthquakes", "occurred_at", method="brin")
    _idx("river_gauges_observed_brin_idx", "river_gauges", "observed_at", method="brin")
    _idx("weather_events_observed_brin_idx", "weather_events", "observed_at", method="brin")
    _idx("wildfires_detected_brin_idx", "wildfires", "detected_at", method="brin")
    _idx("alerts_created_brin_idx", "alerts", "created_at", method="brin")
    _idx("audit_log_created_brin_idx", "audit_log", "created_at", method="brin")

    op.create_table(
        "retention_policies",
        sa.Column("table_name", sa.Text(), primary_key=True),
        sa.Column("timestamp_column", sa.Text(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("archive_before_delete", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute("""
        INSERT INTO retention_policies
            (table_name, timestamp_column, retention_days, archive_before_delete)
        VALUES
            ('hazard_events', 'event_timestamp', 180, true),
            ('events', 'occurred_at', 180, true),
            ('earthquakes', 'occurred_at', 180, true),
            ('river_gauges', 'observed_at', 180, true),
            ('weather_events', 'observed_at', 180, true),
            ('wildfires', 'detected_at', 180, true),
            ('alerts', 'created_at', 365, true),
            ('sos_reports', 'created_at', 365, true),
            ('audit_log', 'created_at', 365, true)
        ON CONFLICT (table_name) DO UPDATE SET
            timestamp_column = EXCLUDED.timestamp_column,
            retention_days = EXCLUDED.retention_days,
            archive_before_delete = EXCLUDED.archive_before_delete,
            updated_at = now()
    """)

    op.execute("""
        COMMENT ON TABLE retention_policies IS
        'Operational retention targets for realtime hazard tables. Apply through a scheduled archival job before deleting hot data.'
    """)
    op.execute("""
        COMMENT ON TABLE hazard_events IS
        'Canonical append-mostly realtime ingestion table. For very large deployments, migrate to range partitions by event_timestamp.'
    """)


def downgrade() -> None:
    op.drop_table("retention_policies")
    for index_name in [
        "audit_log_created_brin_idx",
        "alerts_created_brin_idx",
        "wildfires_detected_brin_idx",
        "weather_events_observed_brin_idx",
        "river_gauges_observed_brin_idx",
        "earthquakes_occurred_brin_idx",
        "events_occurred_brin_idx",
        "hazard_events_event_timestamp_brin_idx",
    ]:
        _drop_index(index_name)

    _idx("idx_alerts_region", "alerts", "region", method="gist")
    _idx("alerts_created_idx", "alerts", "created_at DESC")
    _idx("idx_citizen_reports_location", "citizen_reports", "location", method="gist")
    _idx("idx_cyclones_location", "cyclones", "location", method="gist")
    _idx("earthquakes_created_idx", "earthquakes", "occurred_at DESC")
    _idx("earthquakes_location_gist_idx", "earthquakes", "location", method="gist")
    _idx("idx_earthquakes_location", "earthquakes", "location", method="gist")
    _idx("idx_events_region", "events", "region", method="gist")
    _idx("idx_events_location", "events", "location", method="gist")
    _idx("idx_hazard_events_location", "hazard_events", "location", method="gist")
    _idx("idx_regions_geometry", "regions", "geometry", method="gist")
    _idx("idx_river_gauges_location", "river_gauges", "location", method="gist")
    _idx("river_gauges_location_gist_idx", "river_gauges", "location", method="gist")
    _idx("idx_sos_reports_location", "sos_reports", "location", method="gist")
    _idx("idx_weather_events_location", "weather_events", "location", method="gist")
    _idx("weather_events_location_gist_idx", "weather_events", "location", method="gist")
    _idx("wildfires_created_idx", "wildfires", "detected_at DESC")
    _idx("idx_wildfires_location", "wildfires", "location", method="gist")
    _idx("wildfires_location_gist_idx", "wildfires", "location", method="gist")
