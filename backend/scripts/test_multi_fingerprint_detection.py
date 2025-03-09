#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester la détection locale avec les empreintes multiples.
Usage: python test_multi_fingerprint_detection.py <audio_file_path>

Ce script effectue les opérations suivantes :
1. Charge un fichier audio
2. Extrait plusieurs empreintes digitales à partir de différentes sections du fichier
3. Sauvegarde les empreintes dans la nouvelle table fingerprints
4. Simule une détection avec chaque section du fichier
5. Vérifie que la piste est correctement identifiée via la détection locale
"""

import os
import sys
import asyncio
import logging
import argparse
import json
import hashlib
import time
import tempfile
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal, engine
from backend.models.models import Track, Artist, Fingerprint
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.utils.logging_config import setup_logging, log_with_category

# Configuration du logging
logger = setup_logging(__name__)

# Fonction pour logger avec catégorie si disponible, sinon utiliser le logger standard
def log_info(category, message):
    try:
        log_with_category(logger, category, "info", message)
    except:
        logger.info(f"[{category}] {message}")

def audio_to_numpy(audio_data: bytes) -> np.ndarray:
    """
    Convertit des données audio brutes en tableau numpy.
    
    Args:
        audio_data: Données audio brutes
        
    Returns:
        Tableau numpy contenant les données audio
    """
    try:
        import librosa
        import io
        
        # Écrire les données dans un fichier temporaire
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # Charger l'audio avec librosa
            audio_array, sample_rate = librosa.load(temp_path, sr=None)
            return audio_array
        finally:
            # Supprimer le fichier temporaire
            os.unlink(temp_path)
    except Exception as e:
        logger.error(f"Erreur lors de la conversion audio en numpy: {str(e)}")
        return np.array([])

def extract_multiple_fingerprints(audio_data: bytes, num_segments: int = 5) -> List[Dict[str, Any]]:
    """
    Extrait plusieurs empreintes à partir de différentes sections de l'audio.
    
    Args:
        audio_data: Données audio brutes
        num_segments: Nombre de segments à extraire
        
    Returns:
        Liste de dictionnaires contenant les empreintes et leurs métadonnées
    """
    try:
        # Convertir les données audio en tableau numpy
        audio_array = audio_to_numpy(audio_data)
        
        if len(audio_array) == 0:
            logger.error("Échec de la conversion audio en numpy")
            return []
        
        # Calculer la longueur de chaque segment
        segment_length = len(audio_array) // num_segments
        
        # Initialiser le feature extractor
        feature_extractor = FeatureExtractor()
        
        # Extraire une empreinte pour chaque segment
        fingerprints = []
        for i in range(num_segments):
            start = i * segment_length
            end = start + segment_length
            segment = audio_array[start:end]
            
            # Extraire les caractéristiques directement à partir du segment numpy
            features = feature_extractor.extract_features(segment)
            
            if not features:
                logger.warning(f"Échec de l'extraction des caractéristiques pour le segment {i+1}")
                continue
            
            # Générer l'empreinte
            fingerprint_data = {}
            if "mfcc_mean" in features:
                fingerprint_data["mfcc"] = features["mfcc_mean"]
            if "chroma_mean" in features:
                fingerprint_data["chroma"] = features["chroma_mean"]
            if "spectral_centroid_mean" in features:
                fingerprint_data["spectral"] = features["spectral_centroid_mean"]
            
            # Convertir en chaîne JSON pour les données brutes
            fingerprint_raw_str = json.dumps(fingerprint_data, sort_keys=True)
            fingerprint_raw = fingerprint_raw_str.encode('utf-8')
            
            # Calculer le hash MD5 pour l'empreinte de recherche
            fingerprint_hash = hashlib.md5(fingerprint_raw).hexdigest()
            
            fingerprints.append({
                "hash": fingerprint_hash,
                "raw_data": fingerprint_raw,
                "offset": i * (len(audio_array) / num_segments / 22050),  # Offset en secondes
                "algorithm": "md5"
            })
            
            logger.info(f"Empreinte générée pour le segment {i+1}: {fingerprint_hash[:20]}...")
        
        return fingerprints
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des empreintes multiples: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def generate_chromaprint(audio_file_path: str) -> Optional[str]:
    """
    Génère une empreinte Chromaprint à partir d'un fichier audio.
    
    Args:
        audio_file_path: Chemin vers le fichier audio
        
    Returns:
        Empreinte Chromaprint ou None si l'extraction échoue
    """
    try:
        # Vérifier si fpcalc est disponible
        try:
            result = subprocess.run(['fpcalc', '--version'], capture_output=True, text=True)
            logger.info(f"Chromaprint version: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.warning("fpcalc (Chromaprint) n'est pas installé. L'empreinte Chromaprint ne sera pas générée.")
            return None
        
        # Générer l'empreinte avec fpcalc
        result = subprocess.run(
            ['fpcalc', '-raw', audio_file_path],
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
        return None

async def find_track_by_fingerprint(db_session, fingerprint_hash: str) -> Optional[Track]:
    """
    Recherche une piste par son empreinte dans la nouvelle table fingerprints.
    
    Args:
        db_session: Session de base de données
        fingerprint_hash: Hash de l'empreinte à rechercher
        
    Returns:
        Piste correspondante ou None si aucune correspondance n'est trouvée
    """
    try:
        # Vérifier si la table fingerprints existe
        if not engine.dialect.has_table(engine.connect(), "fingerprints"):
            logger.warning("La table fingerprints n'existe pas encore. Utilisez update_db_schema_for_fingerprints.py --apply pour la créer.")
            return None
        
        # Rechercher l'empreinte
        fingerprint = db_session.query(Fingerprint).filter_by(hash=fingerprint_hash).first()
        
        if fingerprint:
            # Récupérer la piste associée
            track = db_session.query(Track).filter_by(id=fingerprint.track_id).first()
            logger.info(f"Piste trouvée par empreinte: {track.title} (ID: {track.id})")
            return track
        else:
            logger.info(f"Aucune empreinte correspondante trouvée pour le hash {fingerprint_hash[:20]}...")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de piste par empreinte: {str(e)}")
        return None

async def test_multi_fingerprint_detection(audio_file_path: str):
    """
    Teste la détection locale avec les empreintes multiples.
    
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
        
        # 2. Extraire les empreintes multiples
        logger.info("=== ÉTAPE 2: Extraction des empreintes multiples ===")
        fingerprints = extract_multiple_fingerprints(audio_data, num_segments=5)
        
        if not fingerprints:
            logger.error("Échec de l'extraction des empreintes multiples")
            return
        
        logger.info(f"{len(fingerprints)} empreintes extraites avec succès")
        
        # 3. Générer l'empreinte Chromaprint
        logger.info("=== ÉTAPE 3: Génération de l'empreinte Chromaprint ===")
        chromaprint_fingerprint = None
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
            
            chromaprint_fingerprint = generate_chromaprint(temp_path)
            
            # Supprimer le fichier temporaire
            os.unlink(temp_path)
        
        # 4. Créer une piste de test avec les empreintes
        logger.info("=== ÉTAPE 4: Création d'une piste de test ===")
        
        # Vérifier si une piste avec ces empreintes existe déjà
        existing_track = None
        for fp in fingerprints:
            track = await find_track_by_fingerprint(db_session, fp["hash"])
            if track:
                existing_track = track
                break
        
        if existing_track:
            logger.info(f"Une piste avec ces empreintes existe déjà: {existing_track.title} (ID: {existing_track.id})")
            track = existing_track
        else:
            # Créer un artiste de test s'il n'existe pas
            artist_name = "Artiste Test Multi-Fingerprint"
            artist = db_session.query(Artist).filter_by(name=artist_name).first()
            
            if not artist:
                artist = Artist(name=artist_name)
                db_session.add(artist)
                db_session.commit()
                logger.info(f"Artiste créé: {artist_name} (ID: {artist.id})")
            else:
                logger.info(f"Artiste existant: {artist_name} (ID: {artist.id})")
            
            # Créer une piste de test
            track_title = f"Piste Test Multi-Fingerprint {time.strftime('%Y%m%d%H%M%S')}"
            track = Track(
                title=track_title,
                artist_id=artist.id,
                fingerprint=fingerprints[0]["hash"],  # Utiliser la première empreinte comme empreinte principale
                fingerprint_raw=fingerprints[0]["raw_data"]
            )
            
            # Ajouter l'empreinte Chromaprint si disponible
            if chromaprint_fingerprint:
                track.chromaprint = chromaprint_fingerprint
            
            db_session.add(track)
            db_session.commit()
            logger.info(f"Piste créée: {track_title} (ID: {track.id})")
            
            # Ajouter toutes les empreintes à la table fingerprints
            for fp in fingerprints:
                fingerprint = Fingerprint(
                    track_id=track.id,
                    hash=fp["hash"],
                    raw_data=fp["raw_data"],
                    offset=fp["offset"],
                    algorithm=fp["algorithm"]
                )
                db_session.add(fingerprint)
            
            # Ajouter l'empreinte Chromaprint si disponible
            if chromaprint_fingerprint:
                fingerprint = Fingerprint(
                    track_id=track.id,
                    hash=chromaprint_fingerprint[:32],  # Utiliser les 32 premiers caractères comme hash
                    raw_data=chromaprint_fingerprint.encode('utf-8'),
                    offset=0.0,
                    algorithm='chromaprint'
                )
                db_session.add(fingerprint)
            
            db_session.commit()
            logger.info(f"Empreintes ajoutées à la table fingerprints pour la piste {track.id}")
        
        # 5. Tester la détection avec chaque segment
        logger.info("=== ÉTAPE 5: Test de la détection avec chaque segment ===")
        
        # Diviser l'audio en segments
        audio_array = audio_to_numpy(audio_data)
        segment_length = len(audio_array) // len(fingerprints)
        
        success_count = 0
        
        for i in range(len(fingerprints)):
            start = i * segment_length
            end = start + segment_length
            segment = audio_array[start:end]
            
            # Extraire les caractéristiques directement à partir du segment numpy
            features = feature_extractor.extract_features(segment)
            
            if not features:
                logger.warning(f"Échec de l'extraction des caractéristiques pour le segment {i+1}")
                continue
            
            # Générer l'empreinte pour ce segment
            fingerprint_data = {}
            if "mfcc_mean" in features:
                fingerprint_data["mfcc"] = features["mfcc_mean"]
            if "chroma_mean" in features:
                fingerprint_data["chroma"] = features["chroma_mean"]
            if "spectral_centroid_mean" in features:
                fingerprint_data["spectral"] = features["spectral_centroid_mean"]
            
            # Convertir en chaîne JSON pour les données brutes
            fingerprint_raw_str = json.dumps(fingerprint_data, sort_keys=True)
            fingerprint_raw = fingerprint_raw_str.encode('utf-8')
            
            # Calculer le hash MD5 pour l'empreinte de recherche
            fingerprint_hash = hashlib.md5(fingerprint_raw).hexdigest()
            
            # Rechercher directement dans la table fingerprints
            detected_track = await find_track_by_fingerprint(db_session, fingerprint_hash)
            
            if detected_track and detected_track.id == track.id:
                logger.info(f"✅ Segment {i+1}: Détection réussie")
                success_count += 1
            else:
                logger.warning(f"❌ Segment {i+1}: Échec de la détection")
        
        # 6. Résumé des résultats
        logger.info("=== ÉTAPE 6: Résumé des résultats ===")
        logger.info(f"Résultat: {success_count}/{len(fingerprints)} segments détectés avec succès")
        
        if success_count == len(fingerprints):
            logger.info("✅ TEST RÉUSSI: Tous les segments ont été correctement identifiés")
        elif success_count > 0:
            logger.info(f"⚠️ TEST PARTIELLEMENT RÉUSSI: {success_count}/{len(fingerprints)} segments identifiés")
        else:
            logger.warning("❌ TEST ÉCHOUÉ: Aucun segment n'a été identifié")
        
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
    parser = argparse.ArgumentParser(description="Test de la détection locale avec les empreintes multiples")
    parser.add_argument("audio_file_path", help="Chemin vers le fichier audio à tester")
    args = parser.parse_args()
    
    await test_multi_fingerprint_detection(args.audio_file_path)

if __name__ == "__main__":
    asyncio.run(main()) 