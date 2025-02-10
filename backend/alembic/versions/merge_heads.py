"""merge heads

Revision ID: merge_heads
Revises: 77dcdff50480, add_analytics_indexes
Create Date: 2024-03-19 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('77dcdff50480', 'add_analytics_indexes')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 