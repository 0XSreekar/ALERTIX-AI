"""Seed Telangana and Andhra river gauge locations.

Revision ID: 006
Revises: 005
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GAUGES = (
    ("seed", "CWC-BHADRACHALAM", "Bhadrachalam", "Godavari", "Godavari", "Telangana", "Bhadradri Kothagudem", 17.6688, 80.8936),
    ("seed", "CWC-PERUR", "Perur", "Godavari", "Godavari", "Telangana", "Mulugu", 18.3462, 80.3795),
    ("seed", "CWC-DOWLESWARAM", "Dowleswaram", "Godavari", "Godavari", "Andhra Pradesh", "East Godavari", 16.9436, 81.7838),
    ("seed", "CWC-POLAVARAM", "Polavaram", "Godavari", "Godavari", "Andhra Pradesh", "Eluru", 17.2473, 81.6426),
    ("seed", "CWC-PRAKASAM-BARRAGE", "Prakasam Barrage", "Krishna", "Krishna", "Andhra Pradesh", "NTR", 16.5062, 80.6175),
    ("seed", "CWC-SRISAILAM", "Srisailam", "Krishna", "Krishna", "Andhra Pradesh", "Nandyal", 16.0738, 78.8684),
    ("seed", "CWC-NAGARJUNA-SAGAR", "Nagarjuna Sagar", "Krishna", "Krishna", "Telangana", "Nalgonda", 16.5753, 79.3129),
    ("seed", "CWC-JURALA", "Jurala", "Krishna", "Krishna", "Telangana", "Jogulamba Gadwal", 16.3308, 77.7328),
    ("seed", "CWC-SOMASILA", "Somasila", "Pennar", "Pennar", "Andhra Pradesh", "Nellore", 14.4885, 79.3065),
    ("seed", "CWC-TUNGABHADRA-KURNOOL", "Kurnool", "Tungabhadra", "Krishna", "Andhra Pradesh", "Kurnool", 15.8281, 78.0373),
)


def upgrade() -> None:
    for source, station_id, station_name, river, basin, state, district, lat, lon in GAUGES:
        op.execute(
            f"""
            INSERT INTO river_gauges (
                source, station_id, station_name, river_name, basin, state, district,
                observed_at, location, raw_payload
            )
            VALUES (
                '{source}', '{station_id}', '{station_name}', '{river}', '{basin}', '{state}', '{district}',
                '2026-05-20T00:00:00+00:00',
                ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography,
                '{{"seed": true}}'::jsonb
            )
            ON CONFLICT (source, station_id, observed_at) DO UPDATE SET
                station_name = EXCLUDED.station_name,
                river_name = EXCLUDED.river_name,
                basin = EXCLUDED.basin,
                state = EXCLUDED.state,
                district = EXCLUDED.district,
                location = EXCLUDED.location
            """
        )


def downgrade() -> None:
    ids = ", ".join(f"'{station_id}'" for _, station_id, *_ in GAUGES)
    op.execute(f"DELETE FROM river_gauges WHERE source = 'seed' AND station_id IN ({ids})")
