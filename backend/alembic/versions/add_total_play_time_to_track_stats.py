"""add total_play_time to track_stats

Revision ID: add_total_play_time_to_track_stats
Revises: 77dcdff50480
Create Date: 2025-02-15 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import timedelta

# revision identifiers, used by Alembic.
revision = 'add_total_play_time_to_track_stats'
down_revision = '77dcdff50480'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add total_play_time column to track_stats
    op.add_column('track_stats',
        sa.Column('total_play_time', sa.Interval(), nullable=True, default=timedelta(0))
    )

def downgrade() -> None:
    # Remove total_play_time column from track_stats
    op.drop_column('track_stats', 'total_play_time') 