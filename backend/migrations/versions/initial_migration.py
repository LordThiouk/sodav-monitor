"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create RadioStation table
    op.create_table('radio_stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('stream_url', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('last_checked', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_detection_time', sa.DateTime(), nullable=True),
        sa.Column('total_play_time', sa.Interval(), nullable=True, server_default=sa.text("'0 seconds'")),
        sa.Column('status', sa.String(), nullable=True, server_default=sa.text("'active'")),
        sa.PrimaryKeyConstraint('id')
    )

    # Create Track table
    op.create_table('tracks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('artist', sa.String(), nullable=False),
        sa.Column('album', sa.String(), nullable=True),
        sa.Column('isrc', sa.String(), nullable=True),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('release_date', sa.String(), nullable=True),
        sa.Column('play_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_play_time', sa.Interval(), nullable=True, server_default=sa.text("'0 seconds'")),
        sa.Column('last_played', sa.DateTime(), nullable=True),
        sa.Column('external_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('fingerprint', sa.String(), nullable=True),
        sa.Column('fingerprint_raw', sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create User table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default=sa.text("'user'")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Create TrackDetection table
    op.create_table('track_detections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('play_duration', sa.Interval(), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create Report table
    op.create_table('reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('format', sa.String(), nullable=False, server_default=sa.text("'csv'")),
        sa.Column('status', sa.String(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ReportSubscription table
    op.create_table('report_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('recipients', sa.JSON(), nullable=False),
        sa.Column('next_delivery', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('last_sent', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create DetectionHourly table
    op.create_table('detection_hourly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hour', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ArtistStats table
    op.create_table('artist_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_name', sa.String(), nullable=False),
        sa.Column('detection_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_detected', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist_name')
    )

    # Create TrackStats table
    op.create_table('track_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('detection_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_detected', sa.DateTime(), nullable=True),
        sa.Column('average_confidence', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('track_id')
    )

    # Create AnalyticsData table
    op.create_table('analytics_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('detection_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('detection_rate', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('active_stations', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('average_confidence', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create DetectionDaily table
    op.create_table('detection_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # Create DetectionMonthly table
    op.create_table('detection_monthly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('month', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # Create StationStats table
    op.create_table('station_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('detection_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_detected', sa.DateTime(), nullable=False),
        sa.Column('average_confidence', sa.Float(), nullable=False, default=0.0),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create TrackDaily table
    op.create_table('track_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create TrackMonthly table
    op.create_table('track_monthly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('month', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ArtistDaily table
    op.create_table('artist_daily',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_name', sa.String(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ArtistMonthly table
    op.create_table('artist_monthly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_name', sa.String(), nullable=False),
        sa.Column('month', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # Create StationTrackStats table
    op.create_table('station_track_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('play_count', sa.Integer(), nullable=False, default=0),
        sa.Column('total_play_time', sa.Interval(), nullable=False, default=timedelta(0)),
        sa.Column('last_played', sa.DateTime(), nullable=False),
        sa.Column('average_confidence', sa.Float(), nullable=False, default=0.0),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id']),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indices for better performance
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_reports_user', 'reports', ['user_id'])
    op.create_index('idx_reports_status', 'reports', ['status'])
    op.create_index('idx_tracks_isrc', 'tracks', ['isrc'])
    op.create_index('idx_tracks_label', 'tracks', ['label'])
    op.create_index('idx_detections_station', 'track_detections', ['station_id'])
    op.create_index('idx_detections_track', 'track_detections', ['track_id'])
    op.create_index('idx_detections_time', 'track_detections', ['detected_at'])
    op.create_index('idx_analytics_timestamp', 'analytics_data', ['timestamp'])
    op.create_index('idx_detection_hourly_hour', 'detection_hourly', ['hour'])
    op.create_index('idx_artist_stats_count', 'artist_stats', ['detection_count'])
    op.create_index('idx_track_stats_count', 'track_stats', ['detection_count'])


def downgrade() -> None:
    # Drop indices first
    op.drop_index('idx_track_stats_count')
    op.drop_index('idx_artist_stats_count')
    op.drop_index('idx_detection_hourly_hour')
    op.drop_index('idx_analytics_timestamp')
    op.drop_index('idx_detections_time')
    op.drop_index('idx_detections_track')
    op.drop_index('idx_detections_station')
    op.drop_index('idx_tracks_label')
    op.drop_index('idx_tracks_isrc')
    op.drop_index('idx_reports_status')
    op.drop_index('idx_reports_user')
    op.drop_index('idx_users_email')
    op.drop_index('idx_users_username')

    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('station_track_stats')
    op.drop_table('artist_monthly')
    op.drop_table('artist_daily')
    op.drop_table('track_monthly')
    op.drop_table('track_daily')
    op.drop_table('station_stats')
    op.drop_table('detection_monthly')
    op.drop_table('detection_daily')
    op.drop_table('analytics_data')
    op.drop_table('track_stats')
    op.drop_table('artist_stats')
    op.drop_table('detection_hourly')
    op.drop_table('report_subscriptions')
    op.drop_table('reports')
    op.drop_table('track_detections')
    op.drop_table('users')
    op.drop_table('tracks')
    op.drop_table('radio_stations') 