#!/usr/bin/env python
"""
Script pour nettoyer la base de données en supprimant toutes les données existantes
et en réinitialisant les tables.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# Ajouter le répertoire backend au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from sqlalchemy import text

from backend.logs.log_manager import LogManager

# Importer les modules nécessaires
from backend.models.database import Base, SessionLocal, engine
from backend.models.models import (
    AnalyticsData,
    Artist,
    ArtistDaily,
    ArtistMonthly,
    ArtistStats,
    DetectionDaily,
    DetectionHourly,
    DetectionMonthly,
    RadioStation,
    Report,
    ReportSubscription,
    StationHealth,
    StationStats,
    StationStatusHistory,
    StationTrackStats,
    Track,
    TrackDaily,
    TrackDetection,
    TrackMonthly,
    TrackStats,
    User,
)

# Initialiser le logger
log_manager = LogManager()
logger = log_manager.get_logger("scripts.database.clean_database")


def clean_database():
    """Nettoyer la base de données en supprimant toutes les données existantes."""
    try:
        logger.info("Début du nettoyage de la base de données...")

        # Créer une session
        db = SessionLocal()

        try:
            # Désactiver les contraintes de clé étrangère temporairement
            db.execute(text("SET CONSTRAINTS ALL DEFERRED"))

            # Supprimer toutes les données des tables dans l'ordre inverse des dépendances
            logger.info("Suppression des données des tables...")

            # Tables de statistiques et d'historique
            db.execute(text("TRUNCATE TABLE station_status_history CASCADE"))
            db.execute(text("TRUNCATE TABLE station_health CASCADE"))
            db.execute(text("TRUNCATE TABLE station_track_stats CASCADE"))
            db.execute(text("TRUNCATE TABLE artist_monthly CASCADE"))
            db.execute(text("TRUNCATE TABLE artist_daily CASCADE"))
            db.execute(text("TRUNCATE TABLE track_monthly CASCADE"))
            db.execute(text("TRUNCATE TABLE track_daily CASCADE"))
            db.execute(text("TRUNCATE TABLE station_stats CASCADE"))
            db.execute(text("TRUNCATE TABLE detection_monthly CASCADE"))
            db.execute(text("TRUNCATE TABLE detection_daily CASCADE"))
            db.execute(text("TRUNCATE TABLE analytics_data CASCADE"))
            db.execute(text("TRUNCATE TABLE track_stats CASCADE"))
            db.execute(text("TRUNCATE TABLE artist_stats CASCADE"))
            db.execute(text("TRUNCATE TABLE detection_hourly CASCADE"))

            # Tables principales
            db.execute(text("TRUNCATE TABLE track_detections CASCADE"))
            db.execute(text("TRUNCATE TABLE tracks CASCADE"))
            db.execute(text("TRUNCATE TABLE artists CASCADE"))
            db.execute(text("TRUNCATE TABLE radio_stations CASCADE"))
            db.execute(text("TRUNCATE TABLE report_subscriptions CASCADE"))
            db.execute(text("TRUNCATE TABLE reports CASCADE"))

            # Conserver l'utilisateur admin
            # db.execute(text("DELETE FROM users WHERE username != 'admin'"))

            # Réactiver les contraintes de clé étrangère
            db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

            # Valider les changements
            db.commit()
            logger.info("Toutes les données ont été supprimées avec succès.")

            # Réinitialiser les séquences d'ID
            logger.info("Réinitialisation des séquences d'ID...")
            tables = [
                "users",
                "reports",
                "report_subscriptions",
                "radio_stations",
                "artists",
                "tracks",
                "track_detections",
                "detection_hourly",
                "artist_stats",
                "track_stats",
                "analytics_data",
                "detection_daily",
                "detection_monthly",
                "station_stats",
                "track_daily",
                "track_monthly",
                "artist_daily",
                "artist_monthly",
                "station_track_stats",
                "station_health",
                "station_status_history",
            ]

            for table in tables:
                db.execute(text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1"))

            db.commit()
            logger.info("Séquences d'ID réinitialisées avec succès.")

            # Créer un utilisateur admin si nécessaire
            admin = db.query(User).filter(User.username == "admin").first()
            if not admin:
                logger.info("Création de l'utilisateur admin...")
                admin = User(username="admin", email="admin@sodav.sn", role="admin", is_active=True)
                admin.set_password("sodav123")
                db.add(admin)
                db.commit()
                logger.info("Utilisateur admin créé avec succès.")

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du nettoyage de la base de données: {str(e)}")
            raise
        finally:
            db.close()

        logger.info("Nettoyage de la base de données terminé avec succès.")
        return True

    except Exception as e:
        logger.error(f"Erreur lors du nettoyage de la base de données: {str(e)}")
        return False


if __name__ == "__main__":
    # Exécuter le nettoyage de la base de données
    success = clean_database()

    if success:
        logger.info("Le script de nettoyage de la base de données s'est terminé avec succès.")
        sys.exit(0)
    else:
        logger.error("Le script de nettoyage de la base de données a échoué.")
        sys.exit(1)
