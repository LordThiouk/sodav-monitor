import asyncio
import logging
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules du backend
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))

from detection.audio_processor.external_services import AcoustIDService
from detection.audio_processor.track_manager import TrackManager
from detection.detect_music import MusicDetector
from models.database import get_db
from utils.logging_config import setup_logging

# Configuration du logger
setup_logging()
logger = logging.getLogger(__name__)


async def test_station_detection():
    """
    Test la détection de pistes à partir des données audio d'une station.
    """
    # Chemin vers un fichier audio de test
    test_audio_file = Path(__file__).parent / "data" / "audio" / "melody.mp3"

    if not test_audio_file.exists():
        logger.error(f"Fichier audio de test non trouvé: {test_audio_file}")
        return

    # Lire les données audio
    with open(test_audio_file, "rb") as f:
        audio_data = f.read()

    logger.info(f"Fichier audio chargé: {test_audio_file} ({len(audio_data)} bytes)")

    # Obtenir une session de base de données
    db_session = next(get_db())

    try:
        # Créer un détecteur de musique avec la session de base de données
        detector = MusicDetector(db_session)

        # Simuler les données d'une station
        station_id = 1
        station_name = "Station de Test"

        # Traiter les données audio
        try:
            result = await detector.process_audio_data(
                station_id=station_id, audio_data=audio_data, station_name=station_name
            )

            logger.info(f"Résultat de la détection: {result}")

            if result.get("success"):
                detection = result.get("detection", {})
                logger.info(f"Piste détectée: {detection.get('title')} - {detection.get('artist')}")
                logger.info(f"Confiance: {detection.get('confidence')}%")
            else:
                logger.warning(
                    f"Aucune piste détectée: {result.get('message', result.get('error', 'Raison inconnue'))}"
                )

        except Exception as e:
            logger.error(f"Erreur lors de la détection: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

    finally:
        # Fermer la session de base de données
        db_session.close()


if __name__ == "__main__":
    asyncio.run(test_station_detection())
