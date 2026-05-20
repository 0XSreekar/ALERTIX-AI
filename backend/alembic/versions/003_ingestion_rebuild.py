"""Add optimized ingestion tables.

Revision ID: 003
Revises: 002
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "hazard_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_event_id", sa.String(), nullable=False),
        sa.Column("hazard_type", sa.String(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", geoalchemy2.Geography("POINT", srid=4326), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("processing_state", sa.String(), nullable=False, server_default="ingested"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("normalized_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "source_event_id", name="uq_hazard_events_source_event"),
    )
    op.create_index("hazard_events_location_idx", "hazard_events", ["location"], postgresql_using="gist")
    op.create_index("hazard_events_type_time_idx", "hazard_events", ["hazard_type", sa.text("event_timestamp DESC")])
    op.create_index("hazard_events_state_idx", "hazard_events", ["processing_state"])

    op.create_table(
        "earthquakes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazard_event_id", UUID(as_uuid=True), sa.ForeignKey("hazard_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", geoalchemy2.Geography("POINT", srid=4326), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=True),
        sa.Column("depth_km", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("raw_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "external_id", name="uq_earthquakes_source_external"),
    )
    op.create_index("earthquakes_location_idx", "earthquakes", ["location"], postgresql_using="gist")
    op.create_index("earthquakes_occurred_idx", "earthquakes", [sa.text("occurred_at DESC")])
    op.create_index("earthquakes_magnitude_idx", "earthquakes", ["magnitude"])

    op.create_table(
        "wildfires",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazard_event_id", UUID(as_uuid=True), sa.ForeignKey("hazard_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", geoalchemy2.Geography("POINT", srid=4326), nullable=False),
        sa.Column("frp", sa.Float(), nullable=True),
        sa.Column("brightness", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("confidence_label", sa.String(), nullable=True),
        sa.Column("satellite", sa.String(), nullable=True),
        sa.Column("instrument", sa.String(), nullable=True),
        sa.Column("daynight", sa.String(), nullable=True),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("raw_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "external_id", name="uq_wildfires_source_external"),
    )
    op.create_index("wildfires_location_idx", "wildfires", ["location"], postgresql_using="gist")
    op.create_index("wildfires_detected_idx", "wildfires", [sa.text("detected_at DESC")])
    op.create_index("wildfires_cluster_idx", "wildfires", ["cluster_id"])

    op.create_table(
        "river_gauges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazard_event_id", UUID(as_uuid=True), sa.ForeignKey("hazard_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("station_id", sa.String(), nullable=False),
        sa.Column("station_name", sa.Text(), nullable=False),
        sa.Column("river_name", sa.Text(), nullable=True),
        sa.Column("basin", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("district", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", geoalchemy2.Geography("POINT", srid=4326), nullable=False),
        sa.Column("water_level_m", sa.Float(), nullable=True),
        sa.Column("warning_level_m", sa.Float(), nullable=True),
        sa.Column("danger_level_m", sa.Float(), nullable=True),
        sa.Column("discharge_cumec", sa.Float(), nullable=True),
        sa.Column("severity", sa.Float(), nullable=True),
        sa.Column("raw_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "station_id", "observed_at", name="uq_river_gauges_source_station_time"),
    )
    op.create_index("river_gauges_location_idx", "river_gauges", ["location"], postgresql_using="gist")
    op.create_index("river_gauges_observed_idx", "river_gauges", [sa.text("observed_at DESC")])
    op.create_index("river_gauges_station_idx", "river_gauges", ["station_id"])

    op.create_table(
        "cyclones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazard_event_id", UUID(as_uuid=True), sa.ForeignKey("hazard_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("bulletin_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", geoalchemy2.Geography("POINT", srid=4326), nullable=False),
        sa.Column("storm_name", sa.Text(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=True),
        sa.Column("pressure_hpa", sa.Float(), nullable=True),
        sa.Column("movement_direction", sa.Text(), nullable=True),
        sa.Column("warning_level", sa.String(), nullable=True),
        sa.Column("forecast_path", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "external_id", name="uq_cyclones_source_external"),
    )
    op.create_index("cyclones_location_idx", "cyclones", ["location"], postgresql_using="gist")
    op.create_index("cyclones_bulletin_idx", "cyclones", [sa.text("bulletin_at DESC")])
    op.create_index("cyclones_storm_name_idx", "cyclones", ["storm_name"])

    op.create_table(
        "weather_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazard_event_id", UUID(as_uuid=True), sa.ForeignKey("hazard_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", geoalchemy2.Geography("POINT", srid=4326), nullable=False),
        sa.Column("precipitation_mm", sa.Float(), nullable=True),
        sa.Column("rain_mm", sa.Float(), nullable=True),
        sa.Column("raw_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "external_id", name="uq_weather_events_source_external"),
    )
    op.create_index("weather_events_location_idx", "weather_events", ["location"], postgresql_using="gist")
    op.create_index("weather_events_observed_idx", "weather_events", [sa.text("observed_at DESC")])


def downgrade() -> None:
    op.drop_table("weather_events")
    op.drop_table("cyclones")
    op.drop_table("river_gauges")
    op.drop_table("wildfires")
    op.drop_table("earthquakes")
    op.drop_table("hazard_events")

