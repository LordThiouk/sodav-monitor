"""add analytics indexes

Revision ID: add_analytics_indexes
Revises: a314b5c7ff28
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'add_analytics_indexes'
down_revision = 'a314b5c7ff28'
branch_labels = None
depends_on = None


def has_index(table_name, index_name):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    indexes = inspector.get_indexes(table_name)
    return any(index['name'] == index_name for index in indexes)


def upgrade() -> None:
    # Add indexes for analytics queries
    if not has_index('radio_stations', 'ix_radio_stations_is_active'):
        op.create_index('ix_radio_stations_is_active', 'radio_stations', ['is_active'])
    if not has_index('radio_stations', 'ix_radio_stations_last_checked'):
        op.create_index('ix_radio_stations_last_checked', 'radio_stations', ['last_checked'])
    if not has_index('tracks', 'ix_tracks_artist'):
        op.create_index('ix_tracks_artist', 'tracks', ['artist'])
    if not has_index('tracks', 'ix_tracks_label'):
        op.create_index('ix_tracks_label', 'tracks', ['label'])
    if not has_index('track_detections', 'ix_track_detections_station_id'):
        op.create_index('ix_track_detections_station_id', 'track_detections', ['station_id'])
    if not has_index('track_detections', 'ix_track_detections_track_id'):
        op.create_index('ix_track_detections_track_id', 'track_detections', ['track_id'])
    if not has_index('track_detections', 'ix_track_detections_detected_at'):
        op.create_index('ix_track_detections_detected_at', 'track_detections', ['detected_at'])


def downgrade() -> None:
    # Remove indexes
    if has_index('radio_stations', 'ix_radio_stations_is_active'):
        op.drop_index('ix_radio_stations_is_active', 'radio_stations')
    if has_index('radio_stations', 'ix_radio_stations_last_checked'):
        op.drop_index('ix_radio_stations_last_checked', 'radio_stations')
    if has_index('tracks', 'ix_tracks_artist'):
        op.drop_index('ix_tracks_artist', 'tracks')
    if has_index('tracks', 'ix_tracks_label'):
        op.drop_index('ix_tracks_label', 'tracks')
    if has_index('track_detections', 'ix_track_detections_station_id'):
        op.drop_index('ix_track_detections_station_id', 'track_detections')
    if has_index('track_detections', 'ix_track_detections_track_id'):
        op.drop_index('ix_track_detections_track_id', 'track_detections')
    if has_index('track_detections', 'ix_track_detections_detected_at'):
        op.drop_index('ix_track_detections_detected_at', 'track_detections') 