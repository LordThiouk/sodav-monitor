#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester le cycle complet de détection avec AcoustID et AudD.
Ce script permet de vérifier que les métadonnées (ISRC, label, etc.) sont correctement
extraites et sauvegardées dans la base de données.
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# Importer les modules nécessaires
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.models.models import Base, Track, Artist, TrackDetection, Fingerprint
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.external_services import AcoustIDService, AuddService

# Charger les variables d'environnement
load_dotenv()

def get_db_session() -> Session:
    """Crée et retourne une session de base de données."""
    # Récupérer l'URL de la base de données
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost/sodav_dev')
    
    # Créer le moteur SQLAlchemy
    engine = create_engine(db_url)
    
    # Créer une session
    Session = sessionmaker(bind=engine)
    return Session()

async def test_detection_with_acoustid(audio_file_path: str, track_manager: TrackManager) -> Optional[Dict[str, Any]]:
    """
    Teste la détection avec AcoustID.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        track_manager: Instance de TrackManager
        
    Returns:
        Résultat de la détection ou None en cas d'échec
    """
    logger.info(f"Testing AcoustID detection with file: {audio_file_path}")
    
    try:
        # Lire le fichier audio
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        # Créer les caractéristiques audio
        features = {
            "raw_audio": audio_data,
            "audio_file": audio_file_path,
            "duration": 30,  # Durée par défaut
            "play_duration": 30,  # Durée de lecture par défaut
        }
        
        # Tester la détection avec AcoustID
        result = await track_manager.find_acoustid_match(features, station_id=1)
        
        if result:
            logger.info(f"AcoustID detection successful: {result['track']['title']} by {result['track']['artist']}")
            logger.info(f"ISRC: {result['track'].get('isrc', 'Not available')}")
            logger.info(f"Label: {result['track'].get('label', 'Not available')}")
            logger.info(f"Album: {result['track'].get('album', 'Not available')}")
            logger.info(f"Release date: {result['track'].get('release_date', 'Not available')}")
            logger.info(f"Confidence: {result.get('confidence', 0)}")
            logger.info(f"Detection method: {result.get('detection_method', 'Unknown')}")
            return result
        else:
            logger.warning("AcoustID detection failed")
            return None
    
    except Exception as e:
        logger.error(f"Error in AcoustID detection: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

async def test_detection_with_audd(audio_file_path: str, track_manager: TrackManager) -> Optional[Dict[str, Any]]:
    """
    Teste la détection avec AudD.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        track_manager: Instance de TrackManager
        
    Returns:
        Résultat de la détection ou None en cas d'échec
    """
    logger.info(f"Testing AudD detection with file: {audio_file_path}")
    
    try:
        # Lire le fichier audio
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        # Créer les caractéristiques audio
        features = {
            "raw_audio": audio_data,
            "audio_file": audio_file_path,
            "duration": 30,  # Durée par défaut
            "play_duration": 30,  # Durée de lecture par défaut
        }
        
        # Tester la détection avec AudD
        result = await track_manager.find_audd_match(features, station_id=1)
        
        if result:
            logger.info(f"AudD detection successful: {result['track']['title']} by {result['track']['artist']}")
            logger.info(f"ISRC: {result['track'].get('isrc', 'Not available')}")
            logger.info(f"Label: {result['track'].get('label', 'Not available')}")
            logger.info(f"Album: {result['track'].get('album', 'Not available')}")
            logger.info(f"Release date: {result['track'].get('release_date', 'Not available')}")
            logger.info(f"Confidence: {result.get('confidence', 0)}")
            logger.info(f"Detection method: {result.get('detection_method', 'Unknown')}")
            return result
        else:
            logger.warning("AudD detection failed")
            return None
    
    except Exception as e:
        logger.error(f"Error in AudD detection: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

async def verify_track_in_database(db_session: Session, track_id: int) -> bool:
    """
    Vérifie si la piste est correctement enregistrée dans la base de données.
    
    Args:
        db_session: Session de base de données
        track_id: ID de la piste à vérifier
        
    Returns:
        True si la piste est correctement enregistrée, False sinon
    """
    logger.info(f"Verifying track in database: {track_id}")
    
    try:
        # Récupérer la piste
        track = db_session.query(Track).filter_by(id=track_id).first()
        
        if not track:
            logger.error(f"Track with ID {track_id} not found in database")
            return False
        
        # Afficher les informations de la piste
        logger.info(f"Track found: {track.title} by {track.artist.name if track.artist else 'Unknown'}")
        logger.info(f"ISRC: {track.isrc or 'Not available'}")
        logger.info(f"Label: {track.label or 'Not available'}")
        logger.info(f"Album: {track.album or 'Not available'}")
        logger.info(f"Release date: {track.release_date or 'Not available'}")
        
        # Vérifier les empreintes
        fingerprints = db_session.query(Fingerprint).filter_by(track_id=track_id).all()
        logger.info(f"Number of fingerprints: {len(fingerprints)}")
        
        for fp in fingerprints:
            logger.info(f"Fingerprint ID: {fp.id}, Algorithm: {fp.algorithm}, Hash: {fp.hash[:20]}...")
        
        # Vérifier les détections
        detections = db_session.query(TrackDetection).filter_by(track_id=track_id).all()
        logger.info(f"Number of detections: {len(detections)}")
        
        for detection in detections:
            logger.info(f"Detection ID: {detection.id}, Detected at: {detection.detected_at}, Duration: {detection.play_duration}, Method: {detection.detection_method}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error verifying track in database: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Test the complete detection process with AcoustID and AudD")
    parser.add_argument("audio_file", help="Path to the audio file to test")
    parser.add_argument("--acoustid", action="store_true", help="Test AcoustID detection")
    parser.add_argument("--audd", action="store_true", help="Test AudD detection")
    parser.add_argument("--verify", action="store_true", help="Verify track in database after detection")
    
    args = parser.parse_args()
    
    # Vérifier si le fichier audio existe
    if not os.path.exists(args.audio_file):
        logger.error(f"Audio file not found: {args.audio_file}")
        return 1
    
    # Créer une session de base de données
    db_session = get_db_session()
    
    # Créer une instance de TrackManager
    track_manager = TrackManager(db_session)
    
    # Tester la détection avec AcoustID
    acoustid_result = None
    if args.acoustid or not args.audd:
        acoustid_result = await test_detection_with_acoustid(args.audio_file, track_manager)
    
    # Tester la détection avec AudD
    audd_result = None
    if args.audd or not args.acoustid:
        audd_result = await test_detection_with_audd(args.audio_file, track_manager)
    
    # Vérifier la piste dans la base de données
    if args.verify:
        if acoustid_result and "track" in acoustid_result and "id" in acoustid_result["track"]:
            await verify_track_in_database(db_session, acoustid_result["track"]["id"])
        elif audd_result and "track" in audd_result and "id" in audd_result["track"]:
            await verify_track_in_database(db_session, audd_result["track"]["id"])
        else:
            logger.warning("No track ID available for verification")
    
    # Fermer la session de base de données
    db_session.close()
    
    # Afficher un résumé
    logger.info("Detection test completed")
    logger.info(f"AcoustID detection: {'Successful' if acoustid_result else 'Failed'}")
    logger.info(f"AudD detection: {'Successful' if audd_result else 'Failed'}")
    
    return 0

if __name__ == "__main__":
    asyncio.run(main()) 