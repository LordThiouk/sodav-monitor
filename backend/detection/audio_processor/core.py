"""Module principal pour le traitement audio."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import asyncio
import numpy as np
from models.models import RadioStation, Track, TrackDetection
from utils.logging_config import setup_logging
from utils.stats_updater import StatsUpdater
from .stream_handler import StreamHandler
from .feature_extractor import FeatureExtractor
from .track_manager import TrackManager
from .station_monitor import StationMonitor

# Configure logging
logger = setup_logging(__name__)

class AudioProcessor:
    """Classe principale pour le traitement audio des flux radio."""
    
    def __init__(self, db_session: Session, sample_rate: int = 44100):
        """Initialise le processeur audio.
        
        Args:
            db_session: Session de base de données SQLAlchemy
            sample_rate: Fréquence d'échantillonnage en Hz
        """
        self.db = db_session
        self.sample_rate = sample_rate
        self.stream_handler = StreamHandler()
        self.feature_extractor = FeatureExtractor()
        self.track_manager = TrackManager()
        self.station_monitor = StationMonitor()
        self.stats_updater = StatsUpdater(db_session)
        
        logger.info(f"AudioProcessor initialisé avec sample_rate={sample_rate}")
        
    async def process_stream(self, audio_data: np.ndarray, station_id: Optional[int] = None) -> Dict[str, Any]:
        """Traite un segment audio pour détecter la présence de musique.
        
        Args:
            audio_data: Données audio sous forme de tableau numpy
            station_id: ID de la station (optionnel)
            
        Returns:
            Dictionnaire contenant les résultats de la détection
        """
        try:
            # 1. Identifier le type de contenu
            features = self.feature_extractor.extract_features(audio_data)
            is_music = self.feature_extractor.is_music(features)
            
            if not is_music:
                return {
                    "type": "speech",
                    "confidence": 0.0,
                    "station_id": station_id
                }
            
            # 2. Détection hiérarchique
            # a) Détection locale
            local_match = await self.track_manager.find_local_match(features)
            if local_match:
                return {
                    "type": "music",
                    "source": "local",
                    "confidence": local_match["confidence"],
                    "track": local_match["track"],
                    "station_id": station_id
                }
            
            # b) Détection avec MusicBrainz
            mb_match = await self.track_manager.find_musicbrainz_match(features)
            if mb_match:
                return {
                    "type": "music",
                    "source": "musicbrainz",
                    "confidence": mb_match["confidence"],
                    "track": mb_match["track"],
                    "station_id": station_id
                }
            
            # c) Détection avec Audd
            audd_match = await self.track_manager.find_audd_match(features)
            if audd_match:
                return {
                    "type": "music",
                    "source": "audd",
                    "confidence": audd_match["confidence"],
                    "track": audd_match["track"],
                    "station_id": station_id
                }
            
            # Aucune correspondance trouvée
            return {
                "type": "music",
                "source": "unknown",
                "confidence": 0.0,
                "station_id": station_id
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du flux: {str(e)}")
            return {
                "type": "error",
                "error": str(e),
                "station_id": station_id
            }
    
    async def start_monitoring(self, station_id: int) -> bool:
        """Démarre le monitoring d'une station.
        
        Args:
            station_id: ID de la station à monitorer
            
        Returns:
            True si le monitoring est démarré avec succès
        """
        try:
            return await self.station_monitor.start_monitoring(
                self.stream_handler,
                self.feature_extractor,
                self.track_manager
            )
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du monitoring: {str(e)}")
            return False
    
    async def stop_monitoring(self, station_id: int) -> bool:
        """Arrête le monitoring d'une station.
        
        Args:
            station_id: ID de la station
            
        Returns:
            True si le monitoring est arrêté avec succès
        """
        try:
            return await self.station_monitor.stop_monitoring()
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du monitoring: {str(e)}")
            return False
    
    def _check_memory_usage(self) -> bool:
        """Vérifie l'utilisation de la mémoire.
        
        Returns:
            True si l'utilisation de la mémoire est acceptable
        """
        # TODO: Implémenter la vérification de la mémoire
        return True 