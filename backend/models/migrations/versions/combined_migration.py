"""Combined migration for all tables

Revision ID: combined_migration
Revises: None
Create Date: 2025-02-15 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'combined_migration'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create all tables
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )

    op.create_table('radio_stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('stream_url', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('status', sa.String(length=8), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.Column('last_detection_time', sa.DateTime(), nullable=True),
        sa.Column('total_play_time', sa.Interval(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_radio_stations_name', 'radio_stations', ['name'])
    op.create_index('ix_radio_stations_id', 'radio_stations', ['id'])

    op.create_table('tracks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('artist', sa.String(), nullable=False),
        sa.Column('isrc', sa.String(), nullable=True),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('album', sa.String(), nullable=True),
        sa.Column('release_date', sa.DateTime(), nullable=True),
        sa.Column('play_count', sa.Integer(), nullable=True),
        sa.Column('total_play_time', sa.Interval(), nullable=True),
        sa.Column('last_played', sa.DateTime(), nullable=True),
        sa.Column('external_ids', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('fingerprint', sa.String(), nullable=True),
        sa.Column('fingerprint_raw', sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tracks_artist', 'tracks', ['artist'])
    op.create_index('ix_tracks_label', 'tracks', ['label'])

    op.create_table('detection_hourly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hour', sa.DateTime(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('artist_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_name', sa.String(), nullable=True),
        sa.Column('detection_count', sa.Integer(), nullable=True),
        sa.Column('last_detected', sa.DateTime(), nullable=True),
        sa.Column('total_play_time', sa.Interval(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('analytics_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('detection_count', sa.Integer(), nullable=True),
        sa.Column('detection_rate', sa.Float(), nullable=True),
        sa.Column('active_stations', sa.Integer(), nullable=True),
        sa.Column('average_confidence', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('detection_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('detection_monthly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('month', sa.DateTime(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('artist_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_name', sa.String(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('artist_monthly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_name', sa.String(), nullable=True),
        sa.Column('month', sa.DateTime(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('format', sa.String(), nullable=False, server_default='csv'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('filters', postgresql.JSON(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'generating', 'completed', 'failed')")
    )
    op.create_index('ix_reports_id', 'reports', ['id'])

    op.create_table('report_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('recipients', postgresql.JSON(), nullable=False),
        sa.Column('next_delivery', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_sent', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('track_detections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=True),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('play_duration', sa.Interval(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id']),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_track_detections_detected_at', 'track_detections', ['detected_at'])
    op.create_index('ix_track_detections_track_id', 'track_detections', ['track_id'])
    op.create_index('ix_track_detections_station_id', 'track_detections', ['station_id'])

    op.create_table('track_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('detection_count', sa.Integer(), nullable=True),
        sa.Column('average_confidence', sa.Float(), nullable=True),
        sa.Column('last_detected', sa.DateTime(), nullable=True),
        sa.Column('total_play_time', sa.Interval(), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('station_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=True),
        sa.Column('detection_count', sa.Integer(), nullable=True),
        sa.Column('last_detected', sa.DateTime(), nullable=True),
        sa.Column('average_confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('track_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('track_monthly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('month', sa.DateTime(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('station_track_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=True),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('play_count', sa.Integer(), nullable=True),
        sa.Column('total_play_time', sa.Interval(), nullable=True),
        sa.Column('last_played', sa.DateTime(), nullable=True),
        sa.Column('average_confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id']),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('station_track_stats')
    op.drop_table('track_monthly')
    op.drop_table('track_daily')
    op.drop_table('station_stats')
    op.drop_table('track_stats')
    op.drop_table('track_detections')
    op.drop_table('report_subscriptions')
    op.drop_table('reports')
    op.drop_table('artist_monthly')
    op.drop_table('artist_daily')
    op.drop_table('detection_monthly')
    op.drop_table('detection_daily')
    op.drop_table('analytics_data')
    op.drop_table('artist_stats')
    op.drop_table('detection_hourly')
    op.drop_table('tracks')
    op.drop_table('radio_stations')
    op.drop_table('users') 