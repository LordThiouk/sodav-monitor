"""Module principal pour le traitement audio."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import asyncio
from ..music_recognition import MusicRecognizer
from ...models.models import RadioStation
from ...utils.logging_config import setup_logging
from ...utils.stats_updater import StatsUpdater
from .stream_handler import StreamHandler
from .feature_extractor import FeatureExtractor
from .track_manager import TrackManager
from .station_monitor import StationMonitor

# Configure logging
logger = setup_logging(__name__)

class AudioProcessor:
    """Classe principale pour le traitement audio des flux radio."""
    
    def __init__(self, db_session: Session, music_recognizer: MusicRecognizer):
        """Initialise le processeur audio avec les dépendances nécessaires."""
        self.db_session = db_session
        self.music_recognizer = music_recognizer
        self.logger = logging.getLogger(__name__)
        
        # Configuration des limites de ressources
        self.max_concurrent_stations = 10
        self.max_memory_usage = 1024 * 1024 * 250  # 250 MB maximum
        self.processing_timeout = 30  # 30 secondes par station
        self.chunk_duration = 20  # 20 secondes d'échantillonnage
        
        # Sémaphores pour le contrôle des ressources
        self.processing_semaphore = asyncio.Semaphore(self.max_concurrent_stations)
        self.memory_semaphore = asyncio.Semaphore(self.max_concurrent_stations)
        
        # Composants
        self.stream_handler = StreamHandler()
        self.feature_extractor = FeatureExtractor()
        self.track_manager = TrackManager(db_session)
        self.station_monitor = StationMonitor(db_session)
        
        # État de traitement
        self.current_tracks = {}
        self.stats_updater = StatsUpdater(db_session)
        self.processing_stations = set()
    
    async def process_all_stations(self, stations: List[RadioStation]) -> Dict[str, Any]:
        """Traite tous les flux radio en parallèle."""
        results_queue = asyncio.Queue()
        tasks = []
        
        for station in stations:
            if not station.is_active:
                continue
            
            task = asyncio.create_task(
                self._process_station_safe(station, results_queue)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        results = {}
        while not results_queue.empty():
            station_result = await results_queue.get()
            results.update(station_result)
        
        return results
    
    async def _process_station_safe(self, station: RadioStation, results_queue: asyncio.Queue) -> Dict[str, Any]:
        """Traite une station de manière sécurisée avec gestion des ressources."""
        try:
            async with self.processing_semaphore:
                if not self._check_memory_usage():
                    self.logger.warning(f"Mémoire insuffisante pour traiter la station {station.name}")
                    return {station.name: {"error": "Mémoire insuffisante"}}
                
                if station.id in self.processing_stations:
                    self.logger.info(f"Station {station.name} déjà en cours de traitement")
                    return {station.name: {"status": "En cours de traitement"}}
                
                self.processing_stations.add(station.id)
                try:
                    result = await self.stream_handler.process_stream(
                        station.stream_url,
                        self.feature_extractor,
                        self.track_manager,
                        station.id
                    )
                    await results_queue.put({station.name: result})
                finally:
                    self.processing_stations.remove(station.id)
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de {station.name}: {str(e)}")
            await results_queue.put({station.name: {"error": str(e)}})
    
    def _check_memory_usage(self) -> bool:
        """Vérifie si l'utilisation de la mémoire est dans les limites acceptables."""
        try:
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss
            return memory_usage < self.max_memory_usage
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de la mémoire: {str(e)}")
            return True  # En cas d'erreur, on suppose que la mémoire est suffisante
    
    async def start_monitoring(self):
        """Démarre le monitoring des stations."""
        await self.station_monitor.start_monitoring(
            self.stream_handler,
            self.feature_extractor,
            self.track_manager
        ) 