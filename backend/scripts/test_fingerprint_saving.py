#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester la sauvegarde des empreintes digitales lors de la détection.
Usage: python test_fingerprint_saving.py <audio_file_path>
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import time
import json
import hashlib

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.external_services import AuddService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fingerprint_saving(audio_file_path: str):
    """
    Teste la sauvegarde des empreintes digitales lors de la détection.
    
    Args:
        audio_file_path: Chemin vers le fichier audio à tester
    """
    # Initialiser la base de données
    init_db()
    
    # Créer une session de base de données
    db_session = SessionLocal()
    
    try:
        # Créer un gestionnaire de pistes
        track_manager = TrackManager(db_session)
        
        # Vérifier que le fichier existe
        if not os.path.exists(audio_file_path):
            logger.error(f"Le fichier {audio_file_path} n'existe pas")
            return
        
        # Lire le fichier audio
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        # 1. Tester la détection directe avec AudD
        logger.info("=== ÉTAPE 1: Test de détection avec AudD ===")
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
        
        # 2. Créer ou mettre à jour la piste avec les données d'AudD
        logger.info("=== ÉTAPE 2: Création ou mise à jour de la piste ===")
        
        # Générer une empreinte digitale à partir des données de détection
        fingerprint_data = {
            "title": audd_detection.get('title'),
            "artist": audd_detection.get('artist'),
            "isrc": audd_detection.get('isrc'),
            "timestamp": time.time()
        }
        
        # Convertir en chaîne JSON pour les données brutes
        fingerprint_raw_str = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint_raw = fingerprint_raw_str.encode('utf-8')
        
        # Calculer le hash MD5 pour l'empreinte de recherche
        fingerprint_hash = hashlib.md5(fingerprint_raw).hexdigest()
        
        # Ajouter les empreintes digitales aux données de détection
        audd_detection["fingerprint"] = fingerprint_hash
        audd_detection["fingerprint_raw"] = fingerprint_raw
        
        # Créer ou mettre à jour la piste
        track = await track_manager._get_or_create_track(
            title=audd_detection.get('title'),
            artist_name=audd_detection.get('artist'),
            features=audd_detection
        )
        
        if not track:
            logger.error("Échec de la création ou mise à jour de la piste")
            return
        
        logger.info(f"Piste créée ou mise à jour: {track.title} (ID: {track.id})")
        
        # 3. Vérifier que les empreintes digitales ont été sauvegardées
        logger.info("=== ÉTAPE 3: Vérification des empreintes digitales ===")
        
        # Récupérer la piste de la base de données
        track = db_session.query(Track).filter_by(id=track.id).first()
        
        if not track:
            logger.error(f"Piste avec ID {track.id} non trouvée dans la base de données")
            return
        
        # Vérifier le fingerprint hash
        if not track.fingerprint:
            logger.error("Fingerprint hash non sauvegardé")
        else:
            logger.info(f"Fingerprint hash sauvegardé: {track.fingerprint[:20]}...")
            
            # Vérifier que le hash sauvegardé correspond au hash généré
            if track.fingerprint == fingerprint_hash:
                logger.info("Le fingerprint hash sauvegardé correspond au hash généré")
            else:
                logger.warning(f"Le fingerprint hash sauvegardé ({track.fingerprint[:10]}...) ne correspond pas au hash généré ({fingerprint_hash[:10]}...)")
        
        # Vérifier le fingerprint raw
        if not track.fingerprint_raw:
            logger.error("Fingerprint raw non sauvegardé")
        else:
            logger.info(f"Fingerprint raw sauvegardé: {len(track.fingerprint_raw)} bytes")
            
            # Calculer le hash à partir du fingerprint raw sauvegardé
            calculated_hash = hashlib.md5(track.fingerprint_raw).hexdigest()
            
            # Vérifier que le hash calculé correspond au hash sauvegardé
            if calculated_hash == track.fingerprint:
                logger.info("Le hash calculé à partir du fingerprint raw correspond au fingerprint hash sauvegardé")
            else:
                logger.warning(f"Le hash calculé ({calculated_hash[:10]}...) ne correspond pas au fingerprint hash sauvegardé ({track.fingerprint[:10]}...)")
        
        logger.info("Test terminé avec succès")
        
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
    if len(sys.argv) < 2:
        logger.error("Usage: python test_fingerprint_saving.py <audio_file_path>")
        sys.exit(1)
    
    audio_file_path = sys.argv[1]
    await test_fingerprint_saving(audio_file_path)

if __name__ == "__main__":
    asyncio.run(main()) 