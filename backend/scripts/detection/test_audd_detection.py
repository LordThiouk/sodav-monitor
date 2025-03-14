#!/usr/bin/env python
"""
Script pour tester uniquement la détection AudD avec les nouvelles fonctionnalités.
"""

import asyncio
import hashlib
import logging
import os
import sys
from pathlib import Path

import librosa
import numpy as np

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import SessionLocal
from backend.utils.logging_config import log_with_category, setup_logging

# Configurer le logging
logger = setup_logging(__name__)


def load_env_file(env_path):
    """Charge les variables d'environnement depuis un fichier .env."""
    if not env_path.exists():
        return False

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            key, value = line.split("=", 1)
            os.environ[key] = value

    return True


async def test_audd_detection():
    """Teste uniquement la détection AudD avec les nouvelles fonctionnalités."""
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    log_with_category(logger, "GENERAL", "info", f"Looking for .env file at: {env_path}")

    env_vars = load_env_file(env_path)

    if not env_vars:
        log_with_category(logger, "GENERAL", "error", "Failed to load environment variables")
        return False

    # Vérifier la clé API AudD
    audd_api_key = os.environ.get("AUDD_API_KEY")
    log_with_category(logger, "GENERAL", "info", f"AUDD_API_KEY: {audd_api_key}")

    if not audd_api_key:
        log_with_category(
            logger, "GENERAL", "error", "AUDD_API_KEY not found in environment variables"
        )
        return False

    # Créer une session de base de données
    db = SessionLocal()

    try:
        # Initialiser le gestionnaire de pistes et l'extracteur de caractéristiques
        feature_extractor = FeatureExtractor()
        track_manager = TrackManager(db_session=db, feature_extractor=feature_extractor)

        # Utiliser un fichier audio de test
        test_file_path = Path(project_root) / "backend" / "tests" / "data" / "audio" / "sample1.mp3"
        if not test_file_path.exists():
            log_with_category(
                logger, "GENERAL", "error", f"Test audio file not found at {test_file_path}"
            )
            return False

        log_with_category(logger, "GENERAL", "info", f"Using test audio file: {test_file_path}")

        # Charger le fichier audio avec librosa
        try:
            audio_data, sample_rate = librosa.load(test_file_path, sr=None)
            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"Loaded audio file: {len(audio_data)} samples, {sample_rate} Hz",
            )

            # Créer un dictionnaire de features plus complet
            play_duration = len(audio_data) / sample_rate

            # Générer un fingerprint de test
            fingerprint = hashlib.md5(audio_data.tobytes()[:1000]).hexdigest()

            audio_features = {
                "play_duration": play_duration,
                "mfcc_mean": np.random.rand(20),  # Simuler des caractéristiques MFCC
                "chroma_mean": np.random.rand(12),  # Simuler des caractéristiques chroma
                "spectral_centroid_mean": 1000.0,  # Simuler le centroïde spectral
                "tempo": 120.0,  # Simuler le tempo
                "rhythm_strength": 0.8,  # Simuler la force du rythme
                "fingerprint": fingerprint,  # Utiliser un fingerprint généré
                "is_music": True,  # Indiquer que c'est de la musique
                "confidence": 0.9,  # Simuler un score de confiance
            }

            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"Created audio features with play_duration: {audio_features['play_duration']} seconds",
            )
            log_with_category(
                logger, "GENERAL", "info", f"Generated fingerprint: {fingerprint[:20]}..."
            )

        except Exception as e:
            log_with_category(logger, "GENERAL", "error", f"Error loading audio file: {str(e)}")
            return False

        # Simuler un ID de station pour tester l'enregistrement du temps de jeu
        station_id = 1

        # Appeler directement la méthode find_audd_match
        log_with_category(
            logger,
            "GENERAL",
            "info",
            f"Calling AudD detection directly with station_id={station_id}...",
        )
        audd_result = await track_manager.find_audd_match(audio_features, station_id=station_id)

        log_with_category(logger, "GENERAL", "info", f"AudD detection result: {audd_result}")

        # Vérifier le résultat
        if audd_result:
            log_with_category(logger, "GENERAL", "info", f"AudD detection successful")

            # Vérifier les informations de base
            track_info = audd_result.get("track", {})
            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"Track: {track_info.get('title')} by {track_info.get('artist')}",
            )
            log_with_category(logger, "GENERAL", "info", f"Album: {track_info.get('album')}")
            log_with_category(
                logger, "GENERAL", "info", f"Confidence: {audd_result.get('confidence')}"
            )

            # Vérifier les nouvelles informations
            log_with_category(logger, "GENERAL", "info", f"ISRC: {track_info.get('isrc')}")
            log_with_category(logger, "GENERAL", "info", f"Label: {track_info.get('label')}")
            log_with_category(
                logger, "GENERAL", "info", f"Release date: {track_info.get('release_date')}"
            )
            log_with_category(
                logger, "GENERAL", "info", f"Fingerprint: {track_info.get('fingerprint')}"
            )
            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"Play duration: {audd_result.get('play_duration')} seconds",
            )

            # Vérifier que le temps de jeu a été enregistré dans la base de données
            if station_id:
                # Récupérer la dernière détection pour cette station
                from backend.models.models import TrackDetection

                detection = (
                    db.query(TrackDetection)
                    .filter_by(station_id=station_id)
                    .order_by(TrackDetection.detected_at.desc())
                    .first()
                )

                if detection:
                    log_with_category(
                        logger,
                        "GENERAL",
                        "info",
                        f"Play time recorded in database: {detection.play_duration}",
                    )
                    log_with_category(
                        logger, "GENERAL", "info", f"Detection method: {detection.detection_method}"
                    )
                    log_with_category(
                        logger, "GENERAL", "info", f"Confidence: {detection.confidence}"
                    )
                else:
                    log_with_category(
                        logger, "GENERAL", "warning", "No detection record found in database"
                    )

            return True
        else:
            log_with_category(logger, "GENERAL", "warning", "AudD detection failed")
            return False

    except Exception as e:
        log_with_category(logger, "GENERAL", "error", f"Error testing AudD detection: {e}")
        import traceback

        log_with_category(logger, "GENERAL", "error", f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        db.close()


async def main():
    """Fonction principale."""
    log_with_category(logger, "GENERAL", "info", "Starting enhanced AudD detection test")

    result = await test_audd_detection()

    if result:
        log_with_category(
            logger, "GENERAL", "info", "Enhanced AudD detection test passed successfully"
        )
    else:
        log_with_category(logger, "GENERAL", "warning", "Enhanced AudD detection test failed")


if __name__ == "__main__":
    asyncio.run(main())
