"""Module de gestion des événements système."""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Base
from ..database import engine
from ..utils.logging_config import setup_logging
from ..redis_config import init_redis, close_redis
from ..utils.stats_updater import StatsUpdater
from ..utils.websocket import manager

logger = logging.getLogger(__name__)

class EventManager:
    """Gestionnaire des événements système."""
    
    def __init__(self):
        """Initialise le gestionnaire d'événements."""
        self.background_tasks: List[asyncio.Task] = []
        self.stats_updater: Optional[StatsUpdater] = None
        self.is_shutting_down = False
    
    async def startup(self):
        """Exécute les tâches de démarrage."""
        try:
            # Initialise la base de données
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized")
            
            # Configure les logs
            setup_logging()
            logger.info("Logging configured")
            
            # Initialise Redis
            await init_redis()
            logger.info("Redis initialized")
            
            # Démarre les tâches en arrière-plan
            self.stats_updater = StatsUpdater()
            task = asyncio.create_task(self.stats_updater.start())
            self.background_tasks.append(task)
            logger.info("Background tasks started")
            
        except Exception as e:
            logger.error(f"Error during startup: {e}")
            raise
    
    async def shutdown(self):
        """Exécute les tâches d'arrêt."""
        try:
            self.is_shutting_down = True
            logger.info("Starting shutdown sequence")
            
            # Annule les tâches en arrière-plan
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Attend la fin des tâches
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Ferme les connexions WebSocket
            for connection in manager.active_connections[:]:
                try:
                    await connection.close()
                except Exception as e:
                    logger.error(f"Error closing WebSocket connection: {e}")
            
            # Ferme la connexion Redis
            await close_redis()
            logger.info("Redis connection closed")
            
            logger.info("Shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie l'état du système."""
        try:
            return {
                "status": "healthy" if not self.is_shutting_down else "shutting_down",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {
                    "database": await self._check_database(),
                    "redis": await self._check_redis(),
                    "background_tasks": self._check_background_tasks()
                }
            }
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Vérifie l'état de la base de données."""
        try:
            # Vérifie si la base de données répond
            engine.connect()
            return {
                "status": "connected",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Vérifie l'état de Redis."""
        try:
            # Vérifie si Redis répond
            redis = await init_redis()
            await redis.ping()
            return {
                "status": "connected",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    def _check_background_tasks(self) -> Dict[str, Any]:
        """Vérifie l'état des tâches en arrière-plan."""
        active_tasks = len([task for task in self.background_tasks if not task.done()])
        completed_tasks = len([task for task in self.background_tasks if task.done()])
        
        return {
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "total_tasks": len(self.background_tasks),
            "last_check": datetime.utcnow().isoformat()
        }

# Instance globale du gestionnaire d'événements
event_manager = EventManager() 