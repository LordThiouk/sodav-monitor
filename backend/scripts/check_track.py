#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier les détails d'une piste dans la base de données.
Usage: python check_track.py <track_id>
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, TrackDetection, StationTrackStats, Artist
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_track(track_id):
    """
    Vérifie les détails d'une piste dans la base de données.
    
    Args:
        track_id (int): L'ID de la piste à vérifier.
    """
    # Initialiser la base de données
    init_db()
    
    # Créer une session de base de données
    db_session = SessionLocal()
    
    try:
        # Récupérer la piste de la base de données
        track = db_session.query(Track).filter_by(id=track_id).first()
        
        if not track:
            logger.error(f"Piste avec ID {track_id} non trouvée dans la base de données.")
            return
        
        # Récupérer l'artiste associé
        artist = db_session.query(Artist).filter_by(id=track.artist_id).first()
        artist_name = artist.name if artist else "Inconnu"
        
        # Afficher les détails de la piste
        logger.info(f"=== Détails de la piste ID {track_id} ===")
        logger.info(f"Titre: {track.title}")
        logger.info(f"Artiste: {artist_name} (ID: {track.artist_id})")
        logger.info(f"ISRC: {track.isrc or 'Non disponible'}")
        logger.info(f"Label: {track.label or 'Non disponible'}")
        logger.info(f"Album: {track.album or 'Non disponible'}")
        logger.info(f"Date de sortie: {track.release_date or 'Non disponible'}")
        logger.info(f"Durée: {track.duration or 'Non disponible'} secondes")
        logger.info(f"Fingerprint: {track.fingerprint[:20] + '...' if track.fingerprint else 'Non disponible'}")
        
        # Récupérer les détections de la piste
        detections = db_session.query(TrackDetection).filter_by(track_id=track_id).all()
        
        if not detections:
            logger.info("Aucune détection enregistrée pour cette piste.")
        else:
            logger.info(f"\n=== Détections ({len(detections)}) ===")
            for i, detection in enumerate(detections):
                logger.info(f"Détection {i+1}:")
                logger.info(f"  Station ID: {detection.station_id}")
                logger.info(f"  Détectée à: {detection.detected_at}")
                logger.info(f"  Durée de lecture: {detection.play_duration} secondes")
                logger.info(f"  Confiance: {detection.confidence}")
                logger.info(f"  Méthode de détection: {detection.detection_method}")
        
        # Récupérer les statistiques par station
        stats = db_session.query(StationTrackStats).filter_by(track_id=track_id).all()
        
        if not stats:
            logger.info("Aucune statistique enregistrée pour cette piste.")
        else:
            logger.info(f"\n=== Statistiques par station ({len(stats)}) ===")
            for i, stat in enumerate(stats):
                logger.info(f"Statistique pour la station {stat.station_id}:")
                logger.info(f"  Nombre de lectures: {stat.play_count}")
                logger.info(f"  Temps total de lecture: {stat.total_play_time} secondes")
                logger.info(f"  Dernière lecture: {stat.last_played}")
                logger.info(f"  Confiance moyenne: {stat.average_confidence}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de la piste: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Fermer la session de base de données
        db_session.close()

def main():
    """
    Fonction principale.
    """
    if len(sys.argv) < 2:
        logger.error("Usage: python check_track.py <track_id>")
        sys.exit(1)
    
    try:
        track_id = int(sys.argv[1])
    except ValueError:
        logger.error("L'ID de la piste doit être un nombre entier.")
        sys.exit(1)
    
    check_track(track_id)

if __name__ == "__main__":
    main() 