"""Module de monitoring des stations radio."""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ...models.models import RadioStation
from ...utils.logging_config import setup_logging

logger = setup_logging(__name__)

class StationMonitor:
    """Moniteur des stations radio."""
    
    def __init__(self, db_session: Session):
        """Initialise le moniteur de stations."""
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.monitoring = False
        self.monitoring_tasks = {}
        
        # Handlers et extracteurs
        self.stream_handler = None
        self.feature_extractor = None
        self.track_manager = None
        
        # Configuration
        self.check_interval = 300  # 5 minutes
        self.retry_attempts = 3
        self.retry_delay = 5  # secondes
        self.health_check_interval = 60  # 1 minute
    
    async def start_monitoring(
        self,
        stream_handler: 'StreamHandler',
        feature_extractor: 'FeatureExtractor',
        track_manager: 'TrackManager'
    ):
        """Démarre le monitoring des stations."""
        try:
            if self.monitoring:
                self.logger.warning("Le monitoring est déjà en cours")
                return
            
            self.monitoring = True
            self.stream_handler = stream_handler
            self.feature_extractor = feature_extractor
            self.track_manager = track_manager
            
            self.logger.info("Démarrage du monitoring des stations")
            
            # Récupère toutes les stations actives
            stations = self.db_session.query(RadioStation).filter_by(is_active=True).all()
            
            # Crée une tâche de monitoring pour chaque station
            for station in stations:
                if station.id not in self.monitoring_tasks:
                    task = asyncio.create_task(
                        self.monitor_station(
                            station,
                            stream_handler,
                            feature_extractor,
                            track_manager
                        )
                    )
                    self.monitoring_tasks[station.id] = task
            
            # Démarre la tâche de surveillance de la santé des stations
            health_task = asyncio.create_task(
                self.monitor_stations_health(stations)
            )
            self.monitoring_tasks["health"] = health_task
            
            # Attend que toutes les tâches soient terminées
            await asyncio.gather(*self.monitoring_tasks.values())
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du monitoring: {str(e)}")
            self.monitoring = False
    
    async def stop_monitoring(self):
        """Arrête le monitoring des stations."""
        try:
            if not self.monitoring:
                return
            
            self.monitoring = False
            self.logger.info("Arrêt du monitoring des stations")
            
            # Annule toutes les tâches en cours
            for task in self.monitoring_tasks.values():
                if not task.done():
                    task.cancel()
            
            # Attend que toutes les tâches soient terminées
            await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
            self.monitoring_tasks.clear()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt du monitoring: {str(e)}")
    
    async def monitor_station(
        self,
        station: RadioStation,
        stream_handler: 'StreamHandler',
        feature_extractor: 'FeatureExtractor',
        track_manager: 'TrackManager'
    ):
        """Monitore une station spécifique."""
        try:
            self.logger.info(f"Démarrage du monitoring pour {station.name}")
            
            while self.monitoring:
                try:
                    # Vérifie l'état du flux
                    stream_status = await stream_handler.check_stream_status(station.stream_url)
                    
                    if stream_status["is_alive"]:
                        # Traite le flux audio
                        result = await stream_handler.process_stream(
                            station.stream_url,
                            feature_extractor,
                            track_manager,
                            station.id
                        )
                        
                        if result.get("error"):
                            self.logger.error(f"Erreur pour {station.name}: {result['error']}")
                            await self._handle_station_error(station)
                    else:
                        self.logger.warning(f"Flux inactif pour {station.name}")
                        await self._handle_station_error(station)
                    
                    # Attend avant la prochaine vérification
                    await asyncio.sleep(self.check_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Erreur lors du monitoring de {station.name}: {str(e)}")
                    await asyncio.sleep(self.retry_delay)
            
        except Exception as e:
            self.logger.error(f"Erreur fatale pour {station.name}: {str(e)}")
    
    async def monitor_stations_health(self, stations: List[RadioStation]):
        """Surveille la santé de toutes les stations."""
        try:
            while self.monitoring:
                for station in stations:
                    try:
                        # Vérifie le dernier état connu
                        last_error = station.last_error_time
                        if last_error:
                            time_since_error = datetime.utcnow() - last_error
                            if time_since_error > timedelta(minutes=30):
                                # Réinitialise le compteur d'erreurs après 30 minutes sans erreur
                                station.error_count = 0
                                station.last_error_time = None
                                self.db_session.commit()
                        
                        # Vérifie si la station doit être désactivée
                        if station.error_count >= self.retry_attempts:
                            self.logger.warning(f"Désactivation de {station.name} après {station.error_count} erreurs")
                            station.is_active = False
                            station.status = "inactive"
                            self.db_session.commit()
                            
                            # Annule la tâche de monitoring si elle existe
                            if station.id in self.monitoring_tasks:
                                self.monitoring_tasks[station.id].cancel()
                                del self.monitoring_tasks[station.id]
                    
                    except Exception as e:
                        self.logger.error(f"Erreur lors de la vérification de santé de {station.name}: {str(e)}")
                
                await asyncio.sleep(self.health_check_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Erreur lors de la surveillance de santé: {str(e)}")
    
    async def _handle_station_error(self, station: RadioStation):
        """Gère une erreur de station."""
        try:
            station.error_count += 1
            station.last_error_time = datetime.utcnow()
            station.status = "error"
            self.db_session.commit()
            
            # Tente de reconnecter si possible
            if station.error_count < self.retry_attempts:
                await asyncio.sleep(self.retry_delay * station.error_count)
                # La reconnexion sera tentée au prochain cycle
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement d'erreur pour {station.name}: {str(e)}")
    
    async def add_station(self, station: RadioStation):
        """Ajoute une nouvelle station au monitoring."""
        try:
            if station.id not in self.monitoring_tasks and station.is_active:
                task = asyncio.create_task(
                    self.monitor_station(
                        station,
                        self.stream_handler,
                        self.feature_extractor,
                        self.track_manager
                    )
                )
                self.monitoring_tasks[station.id] = task
                self.logger.info(f"Station {station.name} ajoutée au monitoring")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout de la station {station.name}: {str(e)}")
    
    async def remove_station(self, station_id: int):
        """Retire une station du monitoring."""
        try:
            if station_id in self.monitoring_tasks:
                task = self.monitoring_tasks[station_id]
                if not task.done():
                    task.cancel()
                await task
                del self.monitoring_tasks[station_id]
                self.logger.info(f"Station {station_id} retirée du monitoring")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du retrait de la station {station_id}: {str(e)}") 