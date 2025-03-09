#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester le cycle complet de détection et d'enregistrement.
Ce script simule la détection d'une piste, attend un certain temps, puis simule la fin de la détection.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import time
import json

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist, TrackDetection
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.external_services import AuddService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_detection():
    """
    Teste le cycle complet de détection et d'enregistrement.
    """
    # Initialiser la base de données
    init_db()
    
    # Créer une session de base de données
    db_session = SessionLocal()
    
    try:
        # Créer un gestionnaire de pistes
        track_manager = TrackManager(db_session)
        
        # Chemin vers le fichier audio de test
        audio_file_path = os.path.join(parent_dir, "samples_test", "Dakar_Musique_20250309_023146.mp3")
        
        if not os.path.exists(audio_file_path):
            logger.error(f"Le fichier {audio_file_path} n'existe pas")
            return
        
        # Lire le fichier audio
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        # 1. Tester la détection directe avec AudD
        logger.info("=== ÉTAPE 1: Test de détection directe avec AudD ===")
        api_key = os.environ.get("AUDD_API_KEY")
        if not api_key:
            logger.warning("AudD API key not found")
            return
        
        audd_service = AuddService(api_key)
        audd_result = await audd_service.detect_track(audio_data)
        
        if not audd_result.get("success"):
            logger.error(f"Erreur lors de la détection avec AudD: {audd_result.get('error')}")
            return
        
        audd_detection = audd_result.get("detection")
        if not audd_detection:
            logger.error("Aucune détection trouvée dans le résultat d'AudD")
            return
        
        logger.info(f"AudD a détecté: {audd_detection.get('title')} par {audd_detection.get('artist')}")
        logger.info(f"ISRC trouvé par AudD: {audd_detection.get('isrc')}")
        
        # Afficher les données complètes pour le débogage
        if "apple_music" in audd_detection:
            logger.info(f"Données Apple Music: {json.dumps(audd_detection['apple_music'], indent=2)}")
        
        if "spotify" in audd_detection:
            logger.info(f"Données Spotify: {json.dumps(audd_detection['spotify'], indent=2)}")
        
        if "deezer" in audd_detection:
            logger.info(f"Données Deezer: {json.dumps(audd_detection['deezer'], indent=2)}")
        
        # 2. Créer ou mettre à jour la piste avec les données d'AudD
        logger.info("=== ÉTAPE 2: Création ou mise à jour de la piste avec les données d'AudD ===")
        track = await track_manager._get_or_create_track(
            title=audd_detection.get('title'),
            artist_name=audd_detection.get('artist'),
            features=audd_detection
        )
        
        if not track:
            logger.error("Échec de la création ou mise à jour de la piste")
            return
        
        logger.info(f"Piste créée ou mise à jour: {track.title} (ID: {track.id})")
        logger.info(f"ISRC: {track.isrc or 'Non disponible'}")
        logger.info(f"Label: {track.label or 'Non disponible'}")
        logger.info(f"Album: {track.album or 'Non disponible'}")
        logger.info(f"Date de sortie: {track.release_date or 'Non disponible'}")
        
        # 3. Simuler un temps de lecture
        logger.info("=== ÉTAPE 3: Simulation du temps de lecture ===")
        station_id = 1
        play_duration = 10.0  # 10 secondes
        
        # Démarrer le suivi de la piste
        detection_result = track_manager._start_track_detection(track, station_id, audd_detection)
        logger.info(f"Détection démarrée pour la piste {track.id} sur la station {station_id}")
        logger.info(f"Simulation d'une lecture de {play_duration} secondes...")
        
        # Attendre un peu pour simuler le temps de lecture
        time.sleep(2)
        
        # 4. Finaliser la détection
        logger.info("=== ÉTAPE 4: Finalisation de la détection ===")
        track_manager._end_current_track(station_id)
        logger.info("Détection finalisée")
        
        # 5. Vérifier que la détection a été enregistrée
        logger.info("=== ÉTAPE 5: Vérification de l'enregistrement ===")
        detections = db_session.query(TrackDetection).filter_by(track_id=track.id).all()
        logger.info(f"Nombre de détections pour la piste: {len(detections)}")
        
        for i, detection in enumerate(detections):
            logger.info(f"Détection {i+1}:")
            logger.info(f"  Station ID: {detection.station_id}")
            logger.info(f"  Détectée à: {detection.detected_at}")
            logger.info(f"  Durée de lecture: {detection.play_duration}")
            logger.info(f"  Confiance: {detection.confidence}")
        
        # 6. Vérifier à nouveau les détails de la piste
        logger.info("=== ÉTAPE 6: Vérification des détails de la piste ===")
        track = db_session.query(Track).filter_by(id=track.id).first()
        logger.info(f"Piste: {track.title} (ID: {track.id})")
        logger.info(f"ISRC: {track.isrc or 'Non disponible'}")
        logger.info(f"Label: {track.label or 'Non disponible'}")
        logger.info(f"Album: {track.album or 'Non disponible'}")
        logger.info(f"Date de sortie: {track.release_date or 'Non disponible'}")
        
    except Exception as e:
        logger.error(f"Erreur lors du test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Fermer la session de base de données
        db_session.close()

async def main():
    """
    Fonction principale.
    """
    await test_complete_detection()

if __name__ == "__main__":
    asyncio.run(main()) 