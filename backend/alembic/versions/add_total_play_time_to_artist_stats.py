"""add total_play_time to artist_stats

Revision ID: add_total_play_time_to_artist_stats
Revises: add_total_play_time_to_track_stats
Create Date: 2025-02-15 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import timedelta

# revision identifiers, used by Alembic.
revision = 'add_total_play_time_to_artist_stats'
down_revision = 'add_total_play_time_to_track_stats'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add total_play_time column to artist_stats
    op.add_column('artist_stats',
        sa.Column('total_play_time', sa.Interval(), nullable=True, default=timedelta(0))
    )

def downgrade() -> None:
    # Remove total_play_time column from artist_stats
    op.drop_column('artist_stats', 'total_play_time') 