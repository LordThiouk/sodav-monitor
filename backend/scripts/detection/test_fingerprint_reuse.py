#!/usr/bin/env python
"""
Script pour tester la réutilisation des empreintes digitales dans la détection hiérarchique.
Ce script vérifie que le système utilise correctement les empreintes digitales stockées
pour la détection locale avant de passer aux services externes.
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

import librosa

# Ajouter le répertoire racine du projet au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ajouter également le répertoire backend au chemin
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import SessionLocal
from backend.models.models import Artist, Track
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


async def test_fingerprint_reuse():
    """Teste la réutilisation des empreintes digitales dans la détection hiérarchique."""
    # Charger les variables d'environnement depuis le fichier .env
    env_path = Path("/Users/cex/Desktop/sodav-monitor/.env")
    log_with_category(logger, "GENERAL", "info", f"Looking for .env file at: {env_path}")

    env_vars = load_env_file(env_path)

    if not env_vars:
        log_with_category(logger, "GENERAL", "error", "Failed to load environment variables")
        return False

    # Vérifier les clés API
    acoustid_api_key = os.environ.get("ACOUSTID_API_KEY")
    audd_api_key = os.environ.get("AUDD_API_KEY")

    log_with_category(logger, "GENERAL", "info", f"ACOUSTID_API_KEY: {acoustid_api_key}")
    log_with_category(logger, "GENERAL", "info", f"AUDD_API_KEY: {audd_api_key}")

    # Créer une session de base de données
    db = SessionLocal()

    try:
        # Initialiser les composants nécessaires
        stream_handler = StreamHandler()
        feature_extractor = FeatureExtractor()
        track_manager = TrackManager(db_session=db, feature_extractor=feature_extractor)
        audio_processor = AudioProcessor(db_session=db)

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
        except Exception as e:
            log_with_category(logger, "GENERAL", "error", f"Error loading audio file: {str(e)}")
            return False

        # Étape 1 : Créer une piste de test avec une empreinte digitale unique
        log_with_category(
            logger, "GENERAL", "info", "Step 1: Creating test track with unique fingerprint"
        )

        # Générer une empreinte digitale unique
        timestamp = int(time.time())
        unique_fingerprint = hashlib.md5(f"test_fingerprint_{timestamp}".encode()).hexdigest()

        # Vérifier si l'artiste existe
        artist_name = "Test Fingerprint Artist"
        artist = db.query(Artist).filter(Artist.name == artist_name).first()
        if not artist:
            artist = Artist(name=artist_name)
            db.add(artist)
            db.flush()
            log_with_category(logger, "GENERAL", "info", f"Created test artist: {artist_name}")

        # Créer une piste de test avec l'empreinte digitale unique
        track_title = f"Test Fingerprint Track {timestamp}"
        track = Track(
            title=track_title,
            artist_id=artist.id,
            fingerprint=unique_fingerprint,
            duration=timedelta(seconds=librosa.get_duration(y=audio_data, sr=sample_rate)),
        )
        db.add(track)
        db.commit()
        log_with_category(
            logger,
            "GENERAL",
            "info",
            f"Created test track: {track_title} with fingerprint: {unique_fingerprint[:20]}...",
        )

        # Étape 2 : Simuler une détection avec la même empreinte digitale
        log_with_category(
            logger, "GENERAL", "info", "Step 2: Simulating detection with the same fingerprint"
        )

        # Créer un dictionnaire de métadonnées
        metadata = {
            "artist": "Michael Jackson",  # Métadonnées incorrectes pour forcer la détection par empreinte
            "title": "Thriller",
        }

        log_with_category(logger, "GENERAL", "info", f"Using metadata: {metadata}")

        # Traiter le flux audio
        log_with_category(logger, "GENERAL", "info", "Processing audio stream...")

        # Extraire les caractéristiques audio
        audio_features = feature_extractor.extract_features(audio_data)

        # Remplacer l'empreinte digitale par notre empreinte unique
        audio_features["fingerprint"] = unique_fingerprint

        # Détecter la piste
        detection_result = await audio_processor.process_stream(audio_data, features=audio_features)

        log_with_category(logger, "GENERAL", "info", f"Detection result: {detection_result}")

        # Vérifier si la détection a réussi et si la source est "local"
        if detection_result and detection_result.get("source") == "local":
            log_with_category(
                logger, "GENERAL", "info", "Fingerprint reuse test passed successfully!"
            )
            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"Detected track: {detection_result.get('track', {}).get('title')}",
            )
            log_with_category(
                logger, "GENERAL", "info", f"Source: {detection_result.get('source')}"
            )
            log_with_category(
                logger, "GENERAL", "info", f"Confidence: {detection_result.get('confidence')}"
            )
            return True
        else:
            log_with_category(logger, "GENERAL", "warning", "Fingerprint reuse test failed")
            log_with_category(
                logger,
                "GENERAL",
                "warning",
                f"Detection source: {detection_result.get('source') if detection_result else 'None'}",
            )
            return False

    except Exception as e:
        log_with_category(logger, "GENERAL", "error", f"Error testing fingerprint reuse: {e}")
        import traceback

        log_with_category(logger, "GENERAL", "error", f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        db.close()


async def main():
    """Fonction principale."""
    log_with_category(logger, "GENERAL", "info", "Starting fingerprint reuse test")

    result = await test_fingerprint_reuse()

    if result:
        log_with_category(logger, "GENERAL", "info", "Fingerprint reuse test passed successfully")
    else:
        log_with_category(logger, "GENERAL", "warning", "Fingerprint reuse test failed")


if __name__ == "__main__":
    asyncio.run(main())
