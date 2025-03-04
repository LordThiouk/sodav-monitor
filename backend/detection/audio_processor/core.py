"""Core audio processing functionality for music detection."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import asyncio
import numpy as np
from backend.models.models import RadioStation, Track, TrackDetection
from backend.utils.logging_config import setup_logging
from backend.utils.analytics.stats_updater import StatsUpdater
from .stream_handler import StreamHandler
from .feature_extractor import FeatureExtractor
from .track_manager import TrackManager
from .station_monitor import StationMonitor

# Configure logging
logger = setup_logging(__name__)

class AudioProcessor:
    """Class for processing audio streams and detecting music."""
    
    def __init__(self, db_session: Session, sample_rate: int = 44100):
        """Initialize the audio processor.
        
        Args:
            db_session: SQLAlchemy database session
            sample_rate: Sampling frequency in Hz
            
        Raises:
            ValueError: If sample_rate is less than or equal to 0
        """
        if sample_rate <= 0:
            raise ValueError("Sample rate must be greater than 0")
        self.db = db_session
        self.sample_rate = sample_rate
        self.stream_handler = StreamHandler()
        self.feature_extractor = FeatureExtractor()
        self.track_manager = TrackManager(db_session)
        self.station_monitor = StationMonitor(db_session)
        self.stats_updater = StatsUpdater(db_session)
        
        logger.info(f"AudioProcessor initialized with sample_rate={sample_rate}")
        
    async def process_stream(self, audio_data: np.ndarray, station_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Traite un segment audio pour détecter la présence de musique.
        
        Cette méthode implémente le processus de détection hiérarchique:
        1. Identifie le type de contenu (musique ou parole)
        2. Si c'est de la musique, tente une détection locale
        3. Si la détection locale échoue, tente une détection via MusicBrainz
        4. Si MusicBrainz échoue, tente une détection via AudD
        
        Args:
            audio_data: Données audio sous forme de tableau numpy
            station_id: ID de la station (optionnel)
            
        Returns:
            Dictionnaire contenant les résultats de la détection avec:
            - type: "music" ou "speech"
            - source: "local", "musicbrainz", "audd" ou "unknown"
            - confidence: Score de confiance entre 0 et 1
            - track: Informations sur la piste (si détectée)
            - play_duration: Durée de lecture en secondes
            - station_id: ID de la station
        """
        try:
            # 1. Extraire les caractéristiques audio
            features = self.feature_extractor.extract_features(audio_data)
            
            # Récupérer la durée de lecture
            play_duration = features.get("play_duration", 0.0)
            
            # Vérifier si c'est de la musique
            is_music = features.get("is_music", False)
            
            if not is_music:
                return {
                    "type": "speech",
                    "confidence": 0.0,
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # 2. Détection hiérarchique
            # a) Détection locale
            local_match = await self.track_manager.find_local_match(features)
            if local_match:
                # Ajouter la durée de lecture au résultat
                local_match["play_duration"] = play_duration
                return {
                    "type": "music",
                    "source": "local",
                    "confidence": local_match["confidence"],
                    "track": local_match["track"],
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # b) Détection MusicBrainz
            mb_match = await self.track_manager.find_musicbrainz_match(features)
            if mb_match:
                # Ajouter la durée de lecture au résultat
                mb_match["play_duration"] = play_duration
                return {
                    "type": "music",
                    "source": "musicbrainz",
                    "confidence": mb_match["confidence"],
                    "track": mb_match["track"],
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # c) Détection AudD
            audd_match = await self.track_manager.find_audd_match(features)
            if audd_match:
                # Ajouter la durée de lecture au résultat
                audd_match["play_duration"] = play_duration
                return {
                    "type": "music",
                    "source": "audd",
                    "confidence": audd_match["confidence"],
                    "track": audd_match["track"],
                    "station_id": station_id,
                    "play_duration": play_duration
                }
            
            # Aucune correspondance trouvée
            return {
                "type": "music",
                "source": "unknown",
                "confidence": features.get("confidence", 0.0),
                "station_id": station_id,
                "play_duration": play_duration
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du flux: {str(e)}")
            return {
                "type": "error",
                "error": str(e),
                "station_id": station_id,
                "play_duration": 0.0  # Durée par défaut en cas d'erreur
            }
    
    async def start_monitoring(self, station_id: int) -> bool:
        """Start monitoring a station.
        
        Args:
            station_id: ID of the station to monitor
            
        Returns:
            True if monitoring started successfully
        """
        try:
            return await self.station_monitor.start_monitoring(
                self.stream_handler,
                self.feature_extractor,
                self.track_manager
            )
        except Exception as e:
            logger.error(f"Error starting monitoring: {str(e)}")
            return False
    
    async def stop_monitoring(self, station_id: int) -> bool:
        """Stop monitoring a station.
        
        Args:
            station_id: ID of the station
            
        Returns:
            True if monitoring stopped successfully
        """
        try:
            return await self.station_monitor.stop_monitoring()
        except Exception as e:
            logger.error(f"Error stopping monitoring: {str(e)}")
            return False
    
    def _check_memory_usage(self) -> bool:
        """Check memory usage.
        
        Returns:
            True if memory usage is acceptable
        """
        # TODO: Implement memory usage check
        return True

    def process_stream(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """Process an audio segment to detect the presence of music.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Tuple containing:
                - bool: True if music is detected
                - float: Confidence score between 0 and 1
                
        Raises:
            ValueError: If audio_data is empty
            TypeError: If audio_data is not a np.ndarray
        """
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
            
        # Detection simulation for now
        confidence = np.random.random()
        is_music = confidence > 0.5
        
        logger.debug(f"Audio processing: music={is_music}, confidence={confidence:.2f}")
        return is_music, confidence
        
    def extract_features(self, audio_data: np.ndarray) -> np.ndarray:
        """Extract audio features for fingerprinting.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Numpy array of extracted features
            
        Raises:
            ValueError: If audio_data is empty
            TypeError: If audio_data is not a np.ndarray
        """
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
        if audio_data.size == 0:
            raise ValueError("Audio data cannot be empty")
            
        # Feature extraction simulation
        features = np.random.random((128,))
        logger.debug(f"Features extracted: shape={features.shape}")
        return features
        
    def match_fingerprint(self, features: np.ndarray, database: List[np.ndarray]) -> Optional[int]:
        """Compare a fingerprint with a database.
        
        Args:
            features: Features of the audio to identify
            database: List of reference fingerprints
            
        Returns:
            Index of the found match or None
            
        Raises:
            ValueError: If features don't have the correct shape
            TypeError: If arguments are not of the correct type
        """
        if not isinstance(features, np.ndarray):
            raise TypeError("Features must be a numpy array")
        if not isinstance(database, list):
            raise TypeError("Database must be a list")
        if features.shape != (128,):
            raise ValueError("Features must have shape (128,)")
            
        # Match simulation
        if len(database) > 0 and np.random.random() > 0.5:
            match_idx = np.random.randint(0, len(database))
            logger.info(f"Match found at index {match_idx}")
            return match_idx
        return None 