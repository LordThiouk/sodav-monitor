#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester le processus complet de détection musicale avec les améliorations recommandées.
Usage: python test_complete_detection_process.py <audio_file_path>

Ce script effectue les opérations suivantes :
1. Charge un fichier audio
2. Extrait les caractéristiques audio et génère des empreintes digitales (standard et Chromaprint si disponible)
3. Teste la détection locale avec les empreintes
4. Si la détection locale échoue, teste la détection avec AcoustID
5. Si AcoustID échoue, teste la détection avec AudD
6. Crée ou met à jour la piste dans la base de données avec toutes les métadonnées
7. Simule le cycle complet de détection (début, suivi, fin)
8. Vérifie que l'ISRC, les empreintes et les statistiques sont correctement sauvegardés
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
import librosa
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pydub import AudioSegment

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist, TrackDetection, TrackStats, StationTrackStats
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.external_services import AuddService, AcoustIDService
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

def normalize_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise les caractéristiques audio pour améliorer la robustesse des empreintes.
    
    Args:
        features: Dictionnaire de caractéristiques audio
        
    Returns:
        Dictionnaire de caractéristiques normalisées
    """
    normalized = features.copy()
    
    # Normaliser les MFCC
    if "mfcc_mean" in features:
        mfcc = np.array(features["mfcc_mean"])
        if np.std(mfcc) > 0:
            normalized["mfcc_mean"] = ((mfcc - np.mean(mfcc)) / np.std(mfcc)).tolist()
    
    # Normaliser le chroma
    if "chroma_mean" in features:
        chroma = np.array(features["chroma_mean"])
        if np.sum(chroma) > 0:
            normalized["chroma_mean"] = (chroma / np.sum(chroma)).tolist()
    
    # Normaliser le centroïde spectral
    if "spectral_centroid_mean" in features:
        centroid = features["spectral_centroid_mean"]
        if isinstance(centroid, (int, float)) and centroid > 0:
            normalized["spectral_centroid_mean"] = centroid / 22050  # Normaliser par rapport à la fréquence d'échantillonnage
    
    return normalized

async def test_complete_detection_process(audio_file_path: str):
    """
    Teste le processus complet de détection musicale.
    
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
        
        # Configurer les services externes
        audd_api_key = os.environ.get("AUDD_API_KEY")
        acoustid_api_key = os.environ.get("ACOUSTID_API_KEY")
        
        audd_service = None
        acoustid_service = None
        
        if audd_api_key:
            audd_service = AuddService(audd_api_key)
            logger.info("Service AudD initialisé")
        else:
            logger.warning("AUDD_API_KEY non définie, le service AudD ne sera pas utilisé")
        
        if acoustid_api_key:
            acoustid_service = AcoustIDService(acoustid_api_key)
            logger.info("Service AcoustID initialisé")
        else:
            logger.warning("ACOUSTID_API_KEY non définie, le service AcoustID ne sera pas utilisé")
        
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
        try:
            # Convertir MP3 en WAV avec pydub
            logger.info("Conversion du fichier MP3 en WAV avec pydub...")
            audio_segment = AudioSegment.from_file(audio_file_path)
            
            # Créer un fichier temporaire WAV
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                wav_path = temp_file.name
                audio_segment.export(wav_path, format="wav")
                logger.info(f"Fichier WAV temporaire créé: {wav_path}")
                
                # Charger l'audio avec librosa
                logger.info("Chargement de l'audio avec librosa...")
                audio_array, sr = librosa.load(wav_path, sr=22050, mono=True)
                logger.info(f"Audio chargé: {len(audio_array)} échantillons à {sr}Hz")
                
                # Supprimer le fichier temporaire
                os.unlink(wav_path)
            
            # Extraire les caractéristiques
            audio_features = feature_extractor.extract_features(audio_array)
            
            # Ajouter les données audio brutes aux caractéristiques
            audio_features['raw_audio'] = audio_data
            
            if not audio_features:
                logger.error("Échec de l'extraction des caractéristiques audio")
                return
            
            logger.info("Caractéristiques audio extraites avec succès")
            
            # Normaliser les caractéristiques
            normalized_features = normalize_features(audio_features)
            logger.info("Caractéristiques audio normalisées")
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des caractéristiques: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return
        
        # 3. Générer les empreintes digitales
        logger.info("=== ÉTAPE 3: Génération des empreintes digitales ===")
        
        # Empreinte standard (MD5)
        fingerprint_result = track_manager._extract_fingerprint(normalized_features)
        if isinstance(fingerprint_result, tuple) and len(fingerprint_result) == 2:
            fingerprint_hash, fingerprint_raw = fingerprint_result
        else:
            logger.error("Format d'empreinte digitale inattendu")
            return
        
        if not fingerprint_hash or not fingerprint_raw:
            logger.error("Échec de la génération de l'empreinte digitale standard")
            return
        
        logger.info(f"Empreinte digitale standard générée: {fingerprint_hash[:20]}...")
        
        # Empreinte Chromaprint (si disponible)
        chromaprint_fingerprint = None
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
            
            chromaprint_fingerprint = generate_chromaprint(temp_path)
            
            # Supprimer le fichier temporaire
            os.unlink(temp_path)
        
        if chromaprint_fingerprint:
            # Ajouter l'empreinte Chromaprint aux caractéristiques
            normalized_features["chromaprint"] = chromaprint_fingerprint
            logger.info("Empreinte Chromaprint ajoutée aux caractéristiques")
        
        # Ajouter l'empreinte aux caractéristiques normalisées
        normalized_features["fingerprint"] = fingerprint_hash
        normalized_features["fingerprint_raw"] = fingerprint_raw
        
        # 4. Tester la détection locale
        logger.info("=== ÉTAPE 4: Test de la détection locale ===")
        try:
            local_result = await track_manager.find_local_match(normalized_features)
            
            detection_result = None
            detection_source = None
            
            if local_result:
                logger.info(f"Détection locale réussie: {local_result.get('title')} par {local_result.get('artist')}")
                detection_result = local_result
                detection_source = "local"
            else:
                logger.info("Aucune correspondance locale trouvée, passage aux services externes")
        except Exception as e:
            logger.error(f"Erreur lors de la détection locale: {str(e)}")
            # Annuler la transaction en cours en cas d'erreur
            db_session.rollback()
            logger.info("Transaction annulée, poursuite avec les services externes")
            local_result = None
            detection_result = None
            detection_source = None
            
        # Si pas de détection locale, essayer les services externes
        if not detection_result:
            # 5. Tester la détection avec AcoustID
            if acoustid_service:
                logger.info("=== ÉTAPE 5: Test de la détection avec AcoustID ===")
                try:
                    acoustid_result = await track_manager.find_acoustid_match(normalized_features)
                    
                    if acoustid_result:
                        logger.info(f"Détection AcoustID réussie: {acoustid_result.get('title')} par {acoustid_result.get('artist')}")
                        detection_result = acoustid_result
                        detection_source = "acoustid"
                    else:
                        logger.info("Aucune correspondance AcoustID trouvée")
                except Exception as e:
                    logger.error(f"Erreur lors de la détection AcoustID: {str(e)}")
                    db_session.rollback()
            
            # 6. Tester la détection avec AudD
            if not detection_result and audd_service:
                logger.info("=== ÉTAPE 6: Test de la détection avec AudD ===")
                try:
                    audd_result = await audd_service.detect_track(audio_data)
                    
                    if audd_result and audd_result.get("success"):
                        detection = audd_result.get("result", {})
                        logger.info(f"Détection AudD réussie: {detection.get('title')} par {detection.get('artist')}")
                        
                        # Ajouter l'empreinte aux résultats AudD
                        detection["fingerprint"] = fingerprint_hash
                        detection["fingerprint_raw"] = fingerprint_raw
                        
                        # Ajouter l'ISRC si disponible
                        if "apple_music" in detection and "isrc" in detection["apple_music"]:
                            detection["isrc"] = detection["apple_music"]["isrc"]
                        elif "spotify" in detection and "external_ids" in detection["spotify"] and "isrc" in detection["spotify"]["external_ids"]:
                            detection["isrc"] = detection["spotify"]["external_ids"]["isrc"]
                        elif "deezer" in detection and "isrc" in detection["deezer"]:
                            detection["isrc"] = detection["deezer"]["isrc"]
                            
                        detection_result = detection
                        detection_source = "audd"
                    else:
                        logger.info("Aucune correspondance AudD trouvée")
                except Exception as e:
                    logger.error(f"Erreur lors de la détection AudD: {str(e)}")
        
        # 7. Création ou mise à jour de la piste
        if detection_result:
            logger.info("=== ÉTAPE 7: Création ou mise à jour de la piste ===")
            try:
                # Ajouter les caractéristiques audio au résultat de détection
                detection_result["features"] = normalized_features
                
                # Créer ou mettre à jour la piste
                track = await track_manager._get_or_create_track(
                    title=detection_result.get('title'),
                    artist_name=detection_result.get('artist'),
                    features=detection_result
                )
                
                if track:
                    logger.info(f"Piste créée ou mise à jour avec succès: {track.title} (ID: {track.id})")
                    logger.info(f"ISRC: {track.isrc or 'Non disponible'}")
                    logger.info(f"Empreinte: {track.fingerprint[:20] if track.fingerprint else 'Non disponible'}...")
                    
                    # 8. Simuler une détection complète
                    logger.info("=== ÉTAPE 8: Simulation d'une détection complète ===")
                    
                    # Créer une détection
                    station_id = 1
                    station_name = "Test Station"
                    timestamp = datetime.now()
                    
                    detection = TrackDetection(
                        track_id=track.id,
                        station_id=station_id,
                        timestamp=timestamp,
                        play_duration=normalized_features.get("play_duration", 0),
                        confidence=0.8,
                        method=detection_source
                    )
                    
                    db_session.add(detection)
                    db_session.commit()
                    
                    logger.info(f"Détection enregistrée: ID {detection.id}, Station {station_name}, Timestamp {timestamp}")
                    
                    # Vérifier les statistiques
                    stats = db_session.query(TrackStats).filter_by(track_id=track.id).first()
                    if not stats:
                        stats = TrackStats(track_id=track.id)
                        db_session.add(stats)
                    
                    stats.total_plays += 1
                    stats.total_play_time += normalized_features.get("play_duration", 0)
                    
                    # Mettre à jour les statistiques par station
                    station_stats = db_session.query(StationTrackStats).filter_by(
                        track_id=track.id, station_id=station_id
                    ).first()
                    
                    if not station_stats:
                        station_stats = StationTrackStats(
                            track_id=track.id,
                            station_id=station_id,
                            plays=0,
                            play_time=0
                        )
                        db_session.add(station_stats)
                    
                    station_stats.plays += 1
                    station_stats.play_time += normalized_features.get("play_duration", 0)
                    
                    db_session.commit()
                    
                    logger.info(f"Statistiques mises à jour: {stats.total_plays} lectures, {stats.total_play_time:.2f} secondes")
                    logger.info(f"Statistiques de station: {station_stats.plays} lectures, {station_stats.play_time:.2f} secondes")
                    
                    logger.info("=== TEST COMPLET RÉUSSI ===")
                    return True
                else:
                    logger.error("Échec de la création ou mise à jour de la piste")
            except Exception as e:
                logger.error(f"Erreur lors de la création ou mise à jour de la piste: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                db_session.rollback()
        else:
            logger.error("Aucune correspondance trouvée avec aucune méthode de détection")
        
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
    parser = argparse.ArgumentParser(description="Test du processus complet de détection musicale")
    parser.add_argument("audio_file_path", help="Chemin vers le fichier audio à tester")
    args = parser.parse_args()
    
    await test_complete_detection_process(args.audio_file_path)

if __name__ == "__main__":
    asyncio.run(main()) 