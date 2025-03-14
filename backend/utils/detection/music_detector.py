"""
Module de détection musicale pour les tests de simulation.

Ce module fournit une interface simplifiée pour la détection musicale
à partir de flux audio simulés ou réels, en utilisant les vrais services externes.
"""

import asyncio
import io
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests
from pydub import AudioSegment
from sqlalchemy.orm import Session

from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager.external_detection import (
    ExternalDetectionService,
)
from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.models.database import SessionLocal, get_db

# Configuration du logging
logger = logging.getLogger("sodav_monitor.music_detector")


class MusicDetector:
    """
    Détecteur de musique pour les tests de simulation.

    Cette classe fournit une interface simplifiée pour la détection musicale
    à partir de flux audio simulés ou réels.
    """

    def __init__(self, db_session: Session = None):
        """
        Initialise le détecteur de musique.

        Args:
            db_session: Session de base de données SQLAlchemy
        """
        self.feature_extractor = FeatureExtractor()
        self.db_session = db_session or next(get_db())
        self.track_manager = TrackManager(self.db_session)
        self.external_detection_service = ExternalDetectionService(self.db_session)
        logger.info("MusicDetector initialisé avec succès")

    async def process_track(
        self, station_id: int, stream_url: str, capture_duration: int = 15
    ) -> Dict[str, Any]:
        """
        Traite un flux audio pour détecter la musique.

        Args:
            station_id: ID de la station radio
            stream_url: URL du flux audio
            capture_duration: Durée de capture en secondes

        Returns:
            Dictionnaire contenant les informations de détection
        """
        logger.info(f"Début du traitement pour station_id={station_id}, url={stream_url}")

        # Capturer l'audio du flux
        audio_data = await self.capture_audio_stream(stream_url, capture_duration)
        if not audio_data:
            logger.error(f"Échec de la capture audio pour {stream_url}")
            return {"error": "Échec de la capture audio", "success": False}

        logger.info(f"Audio capturé: {len(audio_data)} octets")

        # Extraire les caractéristiques audio en utilisant analyze_audio
        features = await self.feature_extractor.analyze_audio(audio_data)
        if not features:
            logger.error("Échec de l'extraction des caractéristiques")
            return {"error": "Échec de l'extraction des caractéristiques", "success": False}

        # Vérifier si c'est de la musique
        is_music, confidence = self.feature_extractor.is_music(features)
        if not is_music:
            logger.info("Audio détecté comme non musical (parole ou silence)")
            return {"error": "Audio non musical", "success": False, "is_music": False}

        # Ajouter l'ID de la station aux caractéristiques pour le traitement
        features["station_id"] = station_id

        # Rechercher une correspondance locale
        local_match = await self.track_manager.find_local_match(features)
        if local_match:
            logger.info(
                f"Correspondance locale trouvée: {local_match.get('track', {}).get('title')}"
            )

            # Enregistrer la détection
            result = self.track_manager.stats_recorder.record_detection(local_match, station_id)

            return {
                "success": True,
                "detection_method": "local",
                "track_id": local_match.get("track", {}).get("id"),
                "title": local_match.get("track", {}).get("title"),
                "artist": local_match.get("track", {}).get("artist"),
                "confidence": local_match.get("confidence", 0.0),
                "is_music": True,
            }

        # Ajouter les données audio aux caractéristiques pour les services externes
        features["audio_data"] = audio_data

        # Rechercher une correspondance externe
        external_match = await self.external_detection_service.find_external_match(features)
        if external_match:
            logger.info(
                f"Correspondance externe trouvée via {external_match.get('detection_method')}"
            )

            # Enregistrer la détection
            result = self.track_manager.stats_recorder.record_detection(external_match, station_id)

            return {
                "success": True,
                "detection_method": external_match.get("detection_method"),
                "track_id": external_match.get("track", {}).get("id"),
                "title": external_match.get("track", {}).get("title"),
                "artist": external_match.get("track", {}).get("artist"),
                "confidence": external_match.get("confidence", 0.0),
                "is_music": True,
            }

        logger.warning("Aucune correspondance trouvée")
        return {"success": False, "error": "Aucune correspondance trouvée", "is_music": True}

    async def capture_audio_stream(self, stream_url: str, duration: int = 15) -> bytes:
        """
        Capture l'audio d'un flux streaming.

        Args:
            stream_url: URL du flux audio
            duration: Durée de capture en secondes

        Returns:
            Données audio brutes
        """
        logger.info(f"Capture audio de {stream_url} pendant {duration}s")

        try:
            # Télécharger un segment du flux
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            # Utiliser un timeout plus long que la durée de capture
            timeout = duration + 5

            response = requests.get(stream_url, headers=headers, stream=True, timeout=timeout)
            response.raise_for_status()

            # Lire les données pendant la durée spécifiée
            start_time = time.time()
            chunks = []

            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    chunks.append(chunk)

                # Arrêter après la durée spécifiée
                if time.time() - start_time > duration:
                    break

            # Convertir les chunks en données audio
            audio_data = b"".join(chunks)

            # Convertir en format audio utilisable
            audio = AudioSegment.from_file(io.BytesIO(audio_data))

            # Exporter en WAV pour le traitement
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            logger.info(f"Capture audio réussie: {len(wav_buffer.getvalue())} octets")
            return wav_buffer.getvalue()

        except Exception as e:
            logger.error(f"Erreur lors de la capture audio: {str(e)}")
            return None
