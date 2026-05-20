"""Add password_hash column to profiles."""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("email", sa.Text(), nullable=True))
    # Create unique index on email if not exists
    op.create_index("ix_profiles_email", "profiles", ["email"], unique=True, if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_profiles_email", table_name="profiles")
    op.drop_column("profiles", "email")
    op.drop_column("profiles", "password_hash")
