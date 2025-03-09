#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester spécifiquement la détection avec les empreintes Chromaprint.
Usage: python test_chromaprint_detection.py <audio_file_path>

Ce script effectue les opérations suivantes :
1. Charge un fichier audio
2. Génère une empreinte Chromaprint à partir du fichier
3. Ajoute l'empreinte aux caractéristiques audio
4. Teste la détection locale avec l'empreinte Chromaprint
5. Vérifie que la méthode _calculate_chromaprint_similarity fonctionne correctement
6. Crée ou met à jour la piste dans la base de données avec l'empreinte Chromaprint
7. Vérifie que l'empreinte est correctement sauvegardée dans la base de données
"""

import os
import sys
import asyncio
import logging
import argparse
import tempfile
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pydub import AudioSegment

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist, Fingerprint
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.utils.logging_config import log_with_category

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def generate_chromaprint(audio_file_path: str) -> Optional[str]:
    """
    Génère une empreinte Chromaprint à partir d'un fichier audio.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        
    Returns:
        Empreinte Chromaprint ou None si l'extraction échoue
    """
    try:
        # Définir le chemin vers fpcalc
        fpcalc_path = os.path.join(current_dir.parent, "bin", "fpcalc")
        
        # Vérifier si fpcalc existe à cet emplacement
        if not os.path.exists(fpcalc_path):
            logger.warning(f"fpcalc non trouvé à l'emplacement {fpcalc_path}")
            # Essayer de trouver fpcalc dans le PATH
            try:
                result = subprocess.run(['fpcalc', '--version'], capture_output=True, text=True)
                fpcalc_path = 'fpcalc'  # Utiliser la commande directement
                logger.info(f"Chromaprint version: {result.stdout.strip()}")
            except FileNotFoundError:
                logger.error("fpcalc (Chromaprint) n'est pas installé ou n'est pas dans le PATH.")
                return None
        else:
            # Vérifier la version de fpcalc
            try:
                result = subprocess.run([fpcalc_path, '--version'], capture_output=True, text=True)
                logger.info(f"Chromaprint version: {result.stdout.strip()}")
            except Exception as e:
                logger.warning(f"Impossible de vérifier la version de fpcalc: {str(e)}")
        
        # Générer l'empreinte avec fpcalc
        result = subprocess.run(
            [fpcalc_path, '-raw', audio_file_path],
            capture_output=True,
            text=True
        )
        
        # Extraire l'empreinte
        for line in result.stdout.splitlines():
            if line.startswith('FINGERPRINT='):
                fingerprint = line[12:]
                logger.info(f"Empreinte Chromaprint générée: {fingerprint[:20]}...")
                return fingerprint
        
        logger.warning("Aucune empreinte Chromaprint trouvée dans la sortie de fpcalc")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'empreinte Chromaprint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def test_chromaprint_similarity(track_manager: TrackManager, chromaprint1: str, chromaprint2: str) -> float:
    """
    Teste la fonction _calculate_chromaprint_similarity du TrackManager.
    
    Args:
        track_manager: Instance de TrackManager
        chromaprint1: Première empreinte Chromaprint
        chromaprint2: Deuxième empreinte Chromaprint
        
    Returns:
        Score de similarité entre 0.0 et 1.0
    """
    try:
        similarity = track_manager._calculate_chromaprint_similarity(chromaprint1, chromaprint2)
        logger.info(f"Similarité Chromaprint: {similarity:.4f}")
        return similarity
    except Exception as e:
        logger.error(f"Erreur lors du calcul de similarité Chromaprint: {str(e)}")
        return 0.0

async def create_test_track_with_chromaprint(db_session, track_manager: TrackManager, title: str, artist_name: str, chromaprint: str) -> Optional[Track]:
    """
    Crée une piste de test avec une empreinte Chromaprint.
    
    Args:
        db_session: Session de base de données
        track_manager: Instance de TrackManager
        title: Titre de la piste
        artist_name: Nom de l'artiste
        chromaprint: Empreinte Chromaprint
        
    Returns:
        Objet Track créé ou None en cas d'erreur
    """
    try:
        # Créer un dictionnaire de caractéristiques avec l'empreinte Chromaprint
        features = {
            "title": title,
            "artist": artist_name,
            "chromaprint": chromaprint
        }
        
        # Créer ou mettre à jour la piste
        track = await track_manager._get_or_create_track(
            title=title,
            artist_name=artist_name,
            features=features
        )
        
        if track:
            logger.info(f"Piste créée ou mise à jour avec succès: {track.title} (ID: {track.id})")
            return track
        else:
            logger.error("Échec de la création ou mise à jour de la piste")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la création de la piste de test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db_session.rollback()
        return None

async def verify_chromaprint_in_database(db_session, track_id: int) -> bool:
    """
    Vérifie que l'empreinte Chromaprint est correctement sauvegardée dans la base de données.
    
    Args:
        db_session: Session de base de données
        track_id: ID de la piste à vérifier
        
    Returns:
        True si l'empreinte est correctement sauvegardée, False sinon
    """
    try:
        # Vérifier la colonne chromaprint dans la table tracks
        track = db_session.query(Track).filter_by(id=track_id).first()
        if not track:
            logger.error(f"Piste avec ID {track_id} non trouvée")
            return False
        
        if not track.chromaprint:
            logger.error(f"Empreinte Chromaprint non trouvée dans la table tracks pour la piste {track_id}")
            return False
        
        logger.info(f"Empreinte Chromaprint trouvée dans la table tracks: {track.chromaprint[:20]}...")
        
        # Vérifier la table fingerprints
        fingerprints = db_session.query(Fingerprint).filter_by(
            track_id=track_id,
            algorithm="chromaprint"
        ).all()
        
        if not fingerprints:
            logger.error(f"Aucune empreinte Chromaprint trouvée dans la table fingerprints pour la piste {track_id}")
            return False
        
        logger.info(f"Nombre d'empreintes Chromaprint trouvées dans la table fingerprints: {len(fingerprints)}")
        for fp in fingerprints:
            logger.info(f"Empreinte ID: {fp.id}, Hash: {fp.hash[:20]}..., Algorithme: {fp.algorithm}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de l'empreinte Chromaprint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_chromaprint_detection(audio_file_path: str):
    """
    Teste la détection avec les empreintes Chromaprint.
    
    Args:
        audio_file_path: Chemin vers le fichier audio à tester
    """
    db_session = None
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
        
        # 2. Générer l'empreinte Chromaprint
        logger.info("=== ÉTAPE 2: Génération de l'empreinte Chromaprint ===")
        chromaprint_fingerprint = None
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
            
            chromaprint_fingerprint = generate_chromaprint(temp_path)
            
            # Supprimer le fichier temporaire
            os.unlink(temp_path)
        
        if not chromaprint_fingerprint:
            logger.error("Échec de la génération de l'empreinte Chromaprint")
            return
        
        logger.info(f"Empreinte Chromaprint générée: {chromaprint_fingerprint[:20]}...")
        
        # 3. Créer une piste de test avec l'empreinte Chromaprint
        logger.info("=== ÉTAPE 3: Création d'une piste de test ===")
        test_track = await create_test_track_with_chromaprint(
            db_session,
            track_manager,
            "Test Chromaprint Track",
            "Test Artist",
            chromaprint_fingerprint
        )
        
        if not test_track:
            logger.error("Échec de la création de la piste de test")
            return
        
        # 4. Vérifier que l'empreinte est correctement sauvegardée
        logger.info("=== ÉTAPE 4: Vérification de l'empreinte dans la base de données ===")
        if not await verify_chromaprint_in_database(db_session, test_track.id):
            logger.error("Échec de la vérification de l'empreinte Chromaprint")
            return
        
        # 5. Tester la détection avec l'empreinte Chromaprint
        logger.info("=== ÉTAPE 5: Test de la détection avec l'empreinte Chromaprint ===")
        
        # Créer un dictionnaire de caractéristiques avec l'empreinte Chromaprint
        features = {
            "chromaprint": chromaprint_fingerprint
        }
        
        # Tester la détection locale
        local_result = await track_manager.find_local_match(features)
        
        if local_result:
            logger.info(f"Détection locale réussie: {local_result.get('title')} par {local_result.get('artist')}")
            logger.info(f"Confiance: {local_result.get('confidence')}")
            logger.info(f"Source: {local_result.get('source')}")
            
            # Vérifier que la piste détectée est bien celle que nous avons créée
            if local_result.get('id') == test_track.id:
                logger.info("La piste détectée correspond à la piste de test")
            else:
                logger.warning(f"La piste détectée (ID: {local_result.get('id')}) ne correspond pas à la piste de test (ID: {test_track.id})")
        else:
            logger.error("Échec de la détection locale avec l'empreinte Chromaprint")
            return
        
        # 6. Tester la similarité entre deux empreintes Chromaprint
        logger.info("=== ÉTAPE 6: Test de la similarité entre empreintes Chromaprint ===")
        
        # Générer une empreinte légèrement modifiée pour le test
        modified_fingerprint = chromaprint_fingerprint[:len(chromaprint_fingerprint)-10] + "1234567890"
        
        similarity = test_chromaprint_similarity(track_manager, chromaprint_fingerprint, modified_fingerprint)
        logger.info(f"Similarité avec empreinte modifiée: {similarity:.4f}")
        
        # Tester avec une empreinte complètement différente
        random_fingerprint = "".join([str(np.random.randint(0, 10)) for _ in range(len(chromaprint_fingerprint))])
        similarity = test_chromaprint_similarity(track_manager, chromaprint_fingerprint, random_fingerprint)
        logger.info(f"Similarité avec empreinte aléatoire: {similarity:.4f}")
        
        logger.info("=== TEST CHROMAPRINT RÉUSSI ===")
        
    except Exception as e:
        logger.error(f"Erreur lors du test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Annuler la transaction en cours en cas d'erreur
        if db_session:
            db_session.rollback()
    finally:
        # Fermer la session dans tous les cas
        if db_session:
            db_session.close()

async def main():
    """
    Fonction principale.
    """
    parser = argparse.ArgumentParser(description="Test de la détection avec les empreintes Chromaprint")
    parser.add_argument("audio_file_path", help="Chemin vers le fichier audio à tester")
    args = parser.parse_args()
    
    await test_chromaprint_detection(args.audio_file_path)

if __name__ == "__main__":
    asyncio.run(main()) 