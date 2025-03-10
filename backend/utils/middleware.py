"""
Middleware pour le système SODAV Monitor.

Ce module contient des middlewares pour FastAPI, notamment pour
la collecte de métriques Prometheus.
"""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from .metrics import HTTP_REQUEST_COUNT, HTTP_REQUEST_LATENCY
import psutil
import asyncio
from .metrics import update_system_metrics

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour collecter des métriques Prometheus sur les requêtes HTTP.
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        """
        Initialise le middleware Prometheus.
        
        Args:
            app: L'application ASGI.
            exclude_paths: Liste des chemins à exclure de la collecte de métriques.
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Traite une requête HTTP et collecte des métriques.
        
        Args:
            request: La requête HTTP.
            call_next: La fonction à appeler pour continuer le traitement de la requête.
            
        Returns:
            La réponse HTTP.
        """
        # Exclure certains chemins
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Collecter les métriques
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            status_code = "500"
            raise e
        finally:
            duration = time.time() - start_time
            HTTP_REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status_code
            ).inc()
            HTTP_REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
        
        return response

class SystemMetricsCollector:
    """
    Collecteur de métriques système qui s'exécute en arrière-plan.
    """
    
    def __init__(self, interval: int = 15):
        """
        Initialise le collecteur de métriques système.
        
        Args:
            interval: Intervalle de collecte en secondes.
        """
        self.interval = interval
        self.is_running = False
        self.task = None
    
    async def collect_metrics(self):
        """
        Collecte périodiquement des métriques système.
        """
        while self.is_running:
            # Collecter les métriques système
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Mettre à jour les métriques
            update_system_metrics(
                memory_bytes=memory_info.used,
                cpu_percent=cpu_percent
            )
            
            # Attendre avant la prochaine collecte
            await asyncio.sleep(self.interval)
    
    def start(self):
        """
        Démarre la collecte de métriques système en arrière-plan.
        """
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.collect_metrics())
    
    def stop(self):
        """
        Arrête la collecte de métriques système.
        """
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel() 