#!/usr/bin/env python
"""
Script pour vérifier les détections récentes dans la base de données.
Ce script affiche les détections les plus récentes, ainsi que les pistes et artistes enregistrés.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from backend.models.database import get_database_url
from backend.models.models import Artist, RadioStation, Track, TrackDetection
from backend.utils.logging_config import log_with_category, setup_logging

# Configurer le logging
logger = setup_logging(__name__)


def check_recent_detections(hours=24):
    """Vérifie les détections récentes dans la base de données."""
    try:
        # Obtenir l'URL de la base de données
        db_url = get_database_url()
        log_with_category(logger, "GENERAL", "info", f"Connecting to database: {db_url}")

        # Créer le moteur et la session
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Compter les entrées
            track_count = session.query(Track).count()
            artist_count = session.query(Artist).count()
            detection_count = session.query(TrackDetection).count()
            station_count = session.query(RadioStation).count()

            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"Database summary: {track_count} tracks, {artist_count} artists, {detection_count} detections, {station_count} stations",
            )

            # Récupérer les détections récentes
            since = datetime.utcnow() - timedelta(hours=hours)
            recent_detections = (
                session.query(TrackDetection)
                .filter(TrackDetection.detected_at >= since)
                .order_by(TrackDetection.detected_at.desc())
                .all()
            )

            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"Found {len(recent_detections)} detections in the last {hours} hours",
            )

            # Afficher les détections récentes
            if recent_detections:
                log_with_category(logger, "GENERAL", "info", "Recent detections:")
                for i, detection in enumerate(recent_detections, 1):
                    track = session.query(Track).filter(Track.id == detection.track_id).first()
                    artist = None
                    if track and track.artist_id:
                        artist = session.query(Artist).filter(Artist.id == track.artist_id).first()

                    station = (
                        session.query(RadioStation)
                        .filter(RadioStation.id == detection.station_id)
                        .first()
                    )

                    artist_name = artist.name if artist else "Unknown Artist"
                    track_title = track.title if track else "Unknown Track"
                    station_name = station.name if station else "Unknown Station"

                    log_with_category(
                        logger,
                        "GENERAL",
                        "info",
                        f"{i}. {artist_name} - {track_title} on {station_name}",
                    )
                    log_with_category(
                        logger, "GENERAL", "info", f"   Detected at: {detection.detected_at}"
                    )
                    log_with_category(
                        logger, "GENERAL", "info", f"   Play duration: {detection.play_duration}"
                    )
                    log_with_category(
                        logger, "GENERAL", "info", f"   Confidence: {detection.confidence}"
                    )
                    log_with_category(
                        logger,
                        "GENERAL",
                        "info",
                        f"   Detection method: {detection.detection_method}",
                    )
                    log_with_category(
                        logger,
                        "GENERAL",
                        "info",
                        f"   Fingerprint: {detection.fingerprint[:20]}..."
                        if detection.fingerprint
                        else "   Fingerprint: None",
                    )
            else:
                log_with_category(logger, "GENERAL", "info", "No recent detections found")

            # Récupérer les pistes récentes
            recent_tracks = session.query(Track).order_by(Track.created_at.desc()).limit(10).all()

            log_with_category(logger, "GENERAL", "info", f"Recent tracks ({len(recent_tracks)}):")
            for i, track in enumerate(recent_tracks, 1):
                artist = (
                    session.query(Artist).filter(Artist.id == track.artist_id).first()
                    if track.artist_id
                    else None
                )
                artist_name = artist.name if artist else "Unknown Artist"

                log_with_category(logger, "GENERAL", "info", f"{i}. {artist_name} - {track.title}")
                log_with_category(logger, "GENERAL", "info", f"   Created at: {track.created_at}")
                log_with_category(logger, "GENERAL", "info", f"   ISRC: {track.isrc}")
                log_with_category(logger, "GENERAL", "info", f"   Label: {track.label}")
                log_with_category(
                    logger, "GENERAL", "info", f"   Release date: {track.release_date}"
                )
                log_with_category(
                    logger,
                    "GENERAL",
                    "info",
                    f"   Fingerprint: {track.fingerprint[:20]}..."
                    if track.fingerprint
                    else "   Fingerprint: None",
                )

            return True
        except Exception as e:
            log_with_category(logger, "GENERAL", "error", f"Error checking database: {str(e)}")
            import traceback

            log_with_category(logger, "GENERAL", "error", f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            session.close()
    except Exception as e:
        log_with_category(logger, "GENERAL", "error", f"Error connecting to database: {str(e)}")
        import traceback

        log_with_category(logger, "GENERAL", "error", f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    log_with_category(logger, "GENERAL", "info", "Checking recent detections")

    # Vérifier les détections des dernières 24 heures par défaut
    hours = 24
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            log_with_category(logger, "GENERAL", "error", f"Invalid hours value: {sys.argv[1]}")

    result = check_recent_detections(hours)

    if result:
        log_with_category(logger, "GENERAL", "info", "Database check completed successfully")
    else:
        log_with_category(logger, "GENERAL", "error", "Database check failed")
