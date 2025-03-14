"""merge heads

Revision ID: 20240321_001_merge
Revises: 0f10f1b9f1cf, 20240321_add_progress
Create Date: 2024-03-21

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20240321_001_merge"
down_revision = ("0f10f1b9f1cf", "20240321_add_progress")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration, no upgrade needed
    pass


def downgrade() -> None:
    # This is a merge migration, no downgrade needed
    pass
