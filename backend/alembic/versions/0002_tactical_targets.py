"""Persist per-match tactical target ranges.

Revision ID: 0002_targets
Revises: 0001_postgame
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_targets"
down_revision = "0001_postgame"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("tactical_targets", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("matches", "tactical_targets")
