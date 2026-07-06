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


def _idx(name: str, table: str, cols: str, *, method: str = "btree") -> None:
    """CREATE INDEX IF NOT EXISTS — safe for re-runs."""
    using = f" USING {method}" if method != "btree" else ""
    op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}{using} ({cols})")


def _uq(name: str, table: str, cols: str) -> None:
    """CREATE UNIQUE INDEX IF NOT EXISTS."""
    op.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table} ({cols})")


def upgrade() -> None:
    conn = op.get_bind()

    # ── audit_log: rename columns (idempotent via DO blocks) ──────────────────
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='audit_log' AND column_name='target_table'
            ) THEN
                ALTER TABLE audit_log RENAME COLUMN target_table TO entity_type;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='audit_log' AND column_name='target_id'
            ) THEN
                ALTER TABLE audit_log RENAME COLUMN target_id TO entity_id;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='audit_log' AND column_name='payload'
            ) THEN
                ALTER TABLE audit_log RENAME COLUMN payload TO details;
            END IF;
        END $$
    """))
    conn.execute(sa.text(
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS role VARCHAR"
    ))
    conn.execute(sa.text(
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ip_hash VARCHAR(64)"
    ))

    # Indexes on audit_log
    _idx("audit_log_actor_idx",  "audit_log", "actor_user_id")
    _idx("audit_log_entity_idx", "audit_log", "entity_type, entity_id")
    _idx("audit_log_created_idx","audit_log", "created_at")

    # ── SOS reports: add status enum + column ────────────────────────────────
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sos_status') THEN
                CREATE TYPE sos_status AS ENUM ('pending','triaged','dispatched','resolved');
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        ALTER TABLE sos_reports
            ADD COLUMN IF NOT EXISTS status sos_status NOT NULL DEFAULT 'pending'
    """))
    _idx("sos_status_idx",  "sos_reports", "status")
    _idx("sos_created_idx", "sos_reports", "created_at DESC")

    # ── Performance indexes ───────────────────────────────────────────────────
    _idx("hazard_events_created_idx",      "hazard_events", "created_at DESC")

    _uq("uq_earthquakes_source_external_id", "earthquakes", "source, external_id")
    _idx("earthquakes_created_idx",          "earthquakes", "occurred_at DESC")
    _idx("earthquakes_location_gist_idx",    "earthquakes", "location", method="gist")

    _uq("uq_wildfires_source_external_id",   "wildfires",  "source, external_id")
    _idx("wildfires_created_idx",            "wildfires",  "detected_at DESC")
    _idx("wildfires_location_gist_idx",      "wildfires",  "location", method="gist")

    # river_gauges — river_gauges_observed_idx already exists from migration 003
    _idx("river_gauges_observed_idx",        "river_gauges", "observed_at DESC")
    _idx("river_gauges_location_gist_idx",   "river_gauges", "location", method="gist")

    _uq("uq_weather_events_source_external_id", "weather_events", "source, external_id")
    # weather_events_observed_idx already exists from migration 003
    _idx("weather_events_observed_idx",      "weather_events", "observed_at DESC")
    _idx("weather_events_location_gist_idx", "weather_events", "location", method="gist")

    _idx("alerts_created_desc_idx", "alerts", "created_at DESC")


def downgrade() -> None:
    for idx, tbl in [
        ("alerts_created_desc_idx",              "alerts"),
        ("weather_events_location_gist_idx",     "weather_events"),
        ("weather_events_observed_idx",          "weather_events"),
        ("river_gauges_location_gist_idx",       "river_gauges"),
        ("wildfires_location_gist_idx",          "wildfires"),
        ("wildfires_created_idx",                "wildfires"),
        ("earthquakes_location_gist_idx",        "earthquakes"),
        ("earthquakes_created_idx",              "earthquakes"),
        ("hazard_events_created_idx",            "hazard_events"),
        ("sos_created_idx",                      "sos_reports"),
        ("sos_status_idx",                       "sos_reports"),
        ("audit_log_created_idx",                "audit_log"),
        ("audit_log_entity_idx",                 "audit_log"),
        ("audit_log_actor_idx",                  "audit_log"),
    ]:
        op.execute(f"DROP INDEX IF EXISTS {idx}")

    op.execute("ALTER TABLE sos_reports DROP COLUMN IF EXISTS status")
    op.execute("DROP TYPE IF EXISTS sos_status")

    conn = op.get_bind()
    conn.execute(sa.text(
        "ALTER TABLE audit_log DROP COLUMN IF EXISTS ip_hash"
    ))
    conn.execute(sa.text(
        "ALTER TABLE audit_log DROP COLUMN IF EXISTS role"
    ))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='audit_log' AND column_name='details'
            ) THEN
                ALTER TABLE audit_log RENAME COLUMN details TO payload;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='audit_log' AND column_name='entity_id'
            ) THEN
                ALTER TABLE audit_log RENAME COLUMN entity_id TO target_id;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='audit_log' AND column_name='entity_type'
            ) THEN
                ALTER TABLE audit_log RENAME COLUMN entity_type TO target_table;
            END IF;
        END $$
    """))
