"""Initial persistent post-game schema.

Revision ID: 0001_postgame
Revises:
"""
from alembic import op

from postgame.models import Base

revision = "0001_postgame"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
