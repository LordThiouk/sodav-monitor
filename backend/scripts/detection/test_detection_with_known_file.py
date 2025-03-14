#!/usr/bin/env python
"""
Script pour tester la détection musicale avec un fichier audio connu.
Ce script utilise un fichier audio connu pour tester le processus de détection complet
et vérifier si le système peut correctement détecter et enregistrer une piste.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
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

from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import SessionLocal
from backend.models.models import Artist, RadioStation, Track, TrackDetection
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


async def test_detection_with_known_file():
    """Teste la détection musicale avec un fichier audio connu."""
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

        # Créer une station de test si elle n'existe pas
        station_name = "Test Station"
        station = db.query(RadioStation).filter(RadioStation.name == station_name).first()
        if not station:
            station = RadioStation(
                name=station_name,
                stream_url="http://test.stream.url",
                country="Test Country",
                language="Test Language",
                region="Test Region",
                type="test",
                status="active",
                is_active=True,
                last_check=datetime.utcnow(),
            )
            db.add(station)
            db.commit()
            log_with_category(logger, "GENERAL", "info", f"Created test station: {station_name}")

        # Traiter le flux audio
        log_with_category(logger, "GENERAL", "info", "Processing audio stream...")

        # Détecter la piste
        detection_result = await audio_processor.process_stream(audio_data, station_id=station.id)

        log_with_category(logger, "GENERAL", "info", f"Detection result: {detection_result}")

        # Vérifier si la détection a réussi
        if detection_result and detection_result.get("type") == "music":
            log_with_category(logger, "GENERAL", "info", "Detection successful!")
            log_with_category(
                logger, "GENERAL", "info", f"Source: {detection_result.get('source')}"
            )
            log_with_category(
                logger, "GENERAL", "info", f"Confidence: {detection_result.get('confidence')}"
            )

            track_info = detection_result.get("track", {})
            log_with_category(
                logger, "GENERAL", "info", f"Track: {track_info.get('title', 'Unknown')}"
            )
            log_with_category(
                logger, "GENERAL", "info", f"Artist: {track_info.get('artist', 'Unknown')}"
            )

            # Vérifier si la piste a été enregistrée dans la base de données
            track_count = db.query(Track).count()
            log_with_category(logger, "GENERAL", "info", f"Tracks in database: {track_count}")

            # Vérifier si une détection a été créée
            detection_count = db.query(TrackDetection).count()
            log_with_category(
                logger, "GENERAL", "info", f"Detections in database: {detection_count}"
            )

            # Vérifier explicitement si la transaction a été validée
            db.commit()

            # Rafraîchir la session pour s'assurer que nous avons les données les plus récentes
            db.expire_all()

            # Vérifier à nouveau après le commit explicite
            new_track_count = db.query(Track).count()
            new_detection_count = db.query(TrackDetection).count()
            log_with_category(
                logger,
                "GENERAL",
                "info",
                f"After explicit commit - Tracks: {new_track_count}, Detections: {new_detection_count}",
            )

            # Vérifier si les pistes et détections ont été correctement enregistrées
            if new_track_count > 0 and new_detection_count > 0:
                log_with_category(logger, "GENERAL", "info", "Detection test passed successfully")
                return True
            else:
                log_with_category(
                    logger,
                    "GENERAL",
                    "warning",
                    "Detection test failed: No tracks or detections found in database",
                )
                return False
        else:
            log_with_category(logger, "GENERAL", "warning", "Detection failed")
            log_with_category(logger, "GENERAL", "warning", f"Detection result: {detection_result}")
            return False

    except Exception as e:
        log_with_category(logger, "GENERAL", "error", f"Error testing detection: {e}")
        import traceback

        log_with_category(logger, "GENERAL", "error", f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        db.close()


async def main():
    """Fonction principale."""
    log_with_category(logger, "GENERAL", "info", "Starting detection test with known file")

    result = await test_detection_with_known_file()

    if result:
        log_with_category(logger, "GENERAL", "info", "Detection test passed successfully")
    else:
        log_with_category(logger, "GENERAL", "warning", "Detection test failed")


if __name__ == "__main__":
    asyncio.run(main())
