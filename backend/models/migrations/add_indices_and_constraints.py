"""Migration pour ajouter les indices et les contraintes

Revision ID: add_indices_and_constraints
Revises: None
Create Date: 2025-02-21

"""
from datetime import datetime, timedelta

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "add_indices_and_constraints"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Ajout des indices pour les requêtes analytiques
    op.create_index("idx_track_detections_detected_at", "track_detections", ["detected_at"])
    op.create_index("idx_track_detections_track_id", "track_detections", ["track_id"])
    op.create_index("idx_track_detections_station_id", "track_detections", ["station_id"])
    op.create_index(
        "idx_track_detections_composite",
        "track_detections",
        ["station_id", "track_id", "detected_at"],
    )

    # Indices pour la table tracks
    op.create_index("idx_tracks_title_artist", "tracks", ["title", "artist_id"])
    op.create_index("idx_tracks_isrc", "tracks", ["isrc"])
    op.create_index("idx_tracks_label", "tracks", ["label"])
    op.create_index("idx_tracks_created", "tracks", ["created_at"])

    # Indices pour la table artists
    op.create_index("idx_artists_name", "artists", ["name"])
    op.create_index("idx_artists_label", "artists", ["label"])

    # Indices pour les statistiques
    op.create_index("idx_artist_stats_artist_id", "artist_stats", ["artist_id"])
    op.create_index("idx_track_stats_track_id", "track_stats", ["track_id"])
    op.create_index("idx_track_stats_detection_count", "track_stats", ["detection_count"])

    # Indices pour les statistiques par station
    op.create_index(
        "idx_station_track_stats_composite", "station_track_stats", ["station_id", "track_id"]
    )

    # Indices pour les détections temporelles
    op.create_index("idx_detection_hourly_hour", "detection_hourly", ["hour"])
    op.create_index("idx_detection_daily_date", "detection_daily", ["date"])
    op.create_index("idx_detection_monthly_month", "detection_monthly", ["month"])

    # Indices pour les statistiques quotidiennes et mensuelles
    op.create_index("idx_track_daily_composite", "track_daily", ["track_id", "date"])
    op.create_index("idx_track_monthly_composite", "track_monthly", ["track_id", "month"])
    op.create_index("idx_artist_daily_composite", "artist_daily", ["artist_id", "date"])
    op.create_index("idx_artist_monthly_composite", "artist_monthly", ["artist_id", "month"])

    # Ajout de la contrainte unique sur detection_hourly.hour
    op.create_unique_constraint("uq_detection_hourly_hour", "detection_hourly", ["hour"])


def downgrade():
    # Suppression des indices
    op.drop_index("idx_track_detections_detected_at", "track_detections")
    op.drop_index("idx_track_detections_track_id", "track_detections")
    op.drop_index("idx_track_detections_station_id", "track_detections")
    op.drop_index("idx_track_detections_composite", "track_detections")

    op.drop_index("idx_tracks_title_artist", "tracks")
    op.drop_index("idx_tracks_isrc", "tracks")
    op.drop_index("idx_tracks_label", "tracks")
    op.drop_index("idx_tracks_created", "tracks")

    op.drop_index("idx_artists_name", "artists")
    op.drop_index("idx_artists_label", "artists")

    op.drop_index("idx_artist_stats_artist_id", "artist_stats")
    op.drop_index("idx_track_stats_track_id", "track_stats")
    op.drop_index("idx_track_stats_detection_count", "track_stats")

    op.drop_index("idx_station_track_stats_composite", "station_track_stats")

    op.drop_index("idx_detection_hourly_hour", "detection_hourly")
    op.drop_index("idx_detection_daily_date", "detection_daily")
    op.drop_index("idx_detection_monthly_month", "detection_monthly")

    op.drop_index("idx_track_daily_composite", "track_daily")
    op.drop_index("idx_track_monthly_composite", "track_monthly")
    op.drop_index("idx_artist_daily_composite", "artist_daily")
    op.drop_index("idx_artist_monthly_composite", "artist_monthly")

    # Suppression de la contrainte unique
    op.drop_constraint("uq_detection_hourly_hour", "detection_hourly", type_="unique")
