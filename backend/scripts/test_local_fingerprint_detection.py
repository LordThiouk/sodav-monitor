#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester la détection locale avec les empreintes digitales.
Usage: python test_local_fingerprint_detection.py <audio_file_path>

Ce script effectue les opérations suivantes :
1. Charge un fichier audio
2. Extrait les caractéristiques audio et génère une empreinte digitale
3. Sauvegarde l'empreinte dans la base de données avec une piste de test
4. Simule une détection avec le même fichier audio
5. Vérifie que la piste est correctement identifiée via la détection locale
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import time
import json
import hashlib
import argparse
import numpy as np

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.external_services import AuddService
from backend.core.logging_config import log_with_category

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def test_local_fingerprint_detection(audio_file_path: str):
    """
    Teste la détection locale avec les empreintes digitales.
    
    Args:
        audio_file_path: Chemin vers le fichier audio à tester
    """
    try:
        # Initialiser la base de données
        init_db()
        db_session = SessionLocal()
        
        # Initialiser les composants nécessaires
        feature_extractor = FeatureExtractor()
        track_manager = TrackManager(db_session, feature_extractor)
        
        # 1. Charger le fichier audio
        logger.info("=== ÉTAPE 1: Chargement du fichier audio ===")
        if not os.path.exists(audio_file_path):
            logger.error(f"Le fichier {audio_file_path} n'existe pas")
            return
        
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        logger.info(f"Fichier audio chargé: {audio_file_path} ({len(audio_data)} bytes)")
        
        # 2. Extraire les caractéristiques audio
        logger.info("=== ÉTAPE 2: Extraction des caractéristiques audio ===")
        audio_features = feature_extractor.extract_features(audio_data)
        
        if not audio_features:
            logger.error("Échec de l'extraction des caractéristiques audio")
            return
        
        logger.info("Caractéristiques audio extraites avec succès")
        
        # 3. Générer une empreinte digitale
        logger.info("=== ÉTAPE 3: Génération de l'empreinte digitale ===")
        fingerprint_hash, fingerprint_raw = track_manager._extract_fingerprint(audio_features)
        
        if not fingerprint_hash or not fingerprint_raw:
            logger.error("Échec de la génération de l'empreinte digitale")
            return
        
        logger.info(f"Empreinte digitale générée: {fingerprint_hash[:20]}...")
        
        # 4. Créer une piste de test avec l'empreinte
        logger.info("=== ÉTAPE 4: Création d'une piste de test ===")
        
        # Vérifier si une piste avec cette empreinte existe déjà
        existing_track = db_session.query(Track).filter_by(fingerprint=fingerprint_hash).first()
        
        if existing_track:
            logger.info(f"Une piste avec cette empreinte existe déjà: {existing_track.title} (ID: {existing_track.id})")
            track = existing_track
        else:
            # Créer un artiste de test s'il n'existe pas
            artist_name = "Artiste Test"
            artist = db_session.query(Artist).filter_by(name=artist_name).first()
            
            if not artist:
                artist = Artist(name=artist_name)
                db_session.add(artist)
                db_session.commit()
                logger.info(f"Artiste créé: {artist_name} (ID: {artist.id})")
            else:
                logger.info(f"Artiste existant: {artist_name} (ID: {artist.id})")
            
            # Créer une piste de test
            track_title = f"Piste Test {time.strftime('%Y%m%d%H%M%S')}"
            track = Track(
                title=track_title,
                artist_id=artist.id,
                fingerprint=fingerprint_hash,
                fingerprint_raw=fingerprint_raw
            )
            db_session.add(track)
            db_session.commit()
            logger.info(f"Piste créée: {track_title} (ID: {track.id})")
        
        # 5. Simuler une détection avec le même fichier audio
        logger.info("=== ÉTAPE 5: Simulation d'une détection ===")
        
        # Attendre un peu pour s'assurer que la piste est bien enregistrée
        await asyncio.sleep(1)
        
        # Appeler directement la méthode find_local_match
        local_result = await track_manager.find_local_match(audio_features)
        
        if not local_result:
            logger.error("Échec de la détection locale")
            return
        
        logger.info("=== ÉTAPE 6: Vérification des résultats ===")
        logger.info(f"Piste détectée: {local_result.get('title')} par {local_result.get('artist')}")
        logger.info(f"ID de la piste: {local_result.get('id')}")
        logger.info(f"Empreinte: {local_result.get('fingerprint')}")
        logger.info(f"Confiance: {local_result.get('confidence')}")
        logger.info(f"Source: {local_result.get('source')}")
        
        # Vérifier que la piste détectée est bien celle que nous avons créée
        if local_result.get('id') == track.id:
            logger.info("✅ TEST RÉUSSI: La piste a été correctement identifiée via la détection locale")
        else:
            logger.warning(f"❌ TEST ÉCHOUÉ: La piste détectée (ID: {local_result.get('id')}) ne correspond pas à la piste créée (ID: {track.id})")
        
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
    parser = argparse.ArgumentParser(description="Test de la détection locale avec les empreintes digitales")
    parser.add_argument("audio_file_path", help="Chemin vers le fichier audio à tester")
    args = parser.parse_args()
    
    await test_local_fingerprint_detection(args.audio_file_path)

if __name__ == "__main__":
    asyncio.run(main()) 