#!/usr/bin/env python
"""
Script pour nettoyer les tables tracks et track_detections de la base de données.
Ce script supprime toutes les entrées de ces tables pour permettre de tester le système avec de nouvelles données.
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.models.database import get_database_url
from backend.models.models import Track, TrackDetection, StationTrackStats, TrackStats, Artist, ArtistStats
from backend.utils.logging_config import setup_logging, log_with_category

# Configurer le logging
logger = setup_logging(__name__)

def clean_tracks_and_detections():
    """Supprime toutes les entrées des tables liées aux tracks et détections."""
    try:
        # Obtenir l'URL de la base de données
        db_url = get_database_url()
        log_with_category(logger, "DATABASE", "info", f"Connecting to database: {db_url}")
        
        # Créer le moteur et la session
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Compter les entrées avant suppression
            track_count = session.query(Track).count()
            detection_count = session.query(TrackDetection).count()
            stats_count = session.query(TrackStats).count()
            station_stats_count = session.query(StationTrackStats).count()
            
            log_with_category(logger, "DATABASE", "info", f"Found {track_count} tracks, {detection_count} detections, {stats_count} track stats, and {station_stats_count} station track stats")
            
            # Supprimer les entrées dans l'ordre pour éviter les violations de contraintes de clé étrangère
            log_with_category(logger, "DATABASE", "info", "Deleting track detections...")
            session.query(TrackDetection).delete()
            
            log_with_category(logger, "DATABASE", "info", "Deleting station track stats...")
            session.query(StationTrackStats).delete()
            
            log_with_category(logger, "DATABASE", "info", "Deleting track stats...")
            session.query(TrackStats).delete()
            
            log_with_category(logger, "DATABASE", "info", "Deleting tracks...")
            session.query(Track).delete()
            
            # Supprimer les artistes qui n'ont plus de tracks
            log_with_category(logger, "DATABASE", "info", "Deleting artist stats...")
            session.query(ArtistStats).delete()
            
            log_with_category(logger, "DATABASE", "info", "Deleting artists...")
            session.query(Artist).delete()
            
            # Valider les changements
            session.commit()
            log_with_category(logger, "DATABASE", "info", "Successfully cleaned tracks and detections from database")
            
            return True
        except Exception as e:
            session.rollback()
            log_with_category(logger, "DATABASE", "error", f"Error cleaning database: {str(e)}")
            import traceback
            log_with_category(logger, "DATABASE", "error", f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            session.close()
    except Exception as e:
        log_with_category(logger, "DATABASE", "error", f"Error connecting to database: {str(e)}")
        import traceback
        log_with_category(logger, "DATABASE", "error", f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    log_with_category(logger, "DATABASE", "info", "Starting database cleanup")
    
    # Demander confirmation à l'utilisateur
    confirm = input("Êtes-vous sûr de vouloir supprimer TOUTES les pistes et détections de la base de données ? (oui/non): ")
    
    if confirm.lower() == "oui":
        result = clean_tracks_and_detections()
        
        if result:
            log_with_category(logger, "DATABASE", "info", "Database cleanup completed successfully")
        else:
            log_with_category(logger, "DATABASE", "error", "Database cleanup failed")
    else:
        log_with_category(logger, "DATABASE", "info", "Database cleanup cancelled by user") 