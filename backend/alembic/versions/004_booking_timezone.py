"""Preserve the timezone of existing and future bookings independently of profile edits."""

import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("bookings", sa.Column("timezone_snapshot", sa.String(64), nullable=True))
    op.execute(
        "UPDATE bookings SET timezone_snapshot = master_profiles.timezone "
        "FROM master_profiles WHERE master_profiles.id = bookings.master_id"
    )
    op.alter_column("bookings", "timezone_snapshot", nullable=False)


def downgrade():
    op.drop_column("bookings", "timezone_snapshot")
