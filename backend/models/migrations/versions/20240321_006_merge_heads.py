"""Merge multiple heads

Revision ID: 20240321_006
Revises: 20240321_005, 20240321_add_progress
Create Date: 2024-03-21 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20240321_006"
down_revision = None
branch_labels = None
depends_on = None

# Multiple revisions being merged
revisions = ("20240321_005", "20240321_add_progress")


def upgrade():
    pass


def downgrade():
    pass
