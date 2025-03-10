"""
Module de métriques pour le système SODAV Monitor.

Ce module utilise prometheus-client pour exposer des métriques importantes
du système SODAV Monitor, permettant une surveillance en temps réel des
performances et de l'état du système.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
import time
from typing import Callable, Any
import functools

# Métriques globales
HTTP_REQUEST_COUNT = Counter(
    'sodav_http_requests_total',
    'Nombre total de requêtes HTTP',
    ['method', 'endpoint', 'status']
)

HTTP_REQUEST_LATENCY = Histogram(
    'sodav_http_request_duration_seconds',
    'Latence des requêtes HTTP en secondes',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
)

ACTIVE_STATIONS = Gauge(
    'sodav_active_stations',
    'Nombre de stations radio actives'
)

DETECTION_COUNT = Counter(
    'sodav_detections_total',
    'Nombre total de détections musicales',
    ['detection_method', 'status']
)

DETECTION_LATENCY = Histogram(
    'sodav_detection_duration_seconds',
    'Temps de détection en secondes',
    ['detection_method'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0, float('inf'))
)

DETECTION_CONFIDENCE = Summary(
    'sodav_detection_confidence',
    'Niveau de confiance des détections',
    ['detection_method']
)

DB_QUERY_LATENCY = Histogram(
    'sodav_db_query_duration_seconds',
    'Temps d\'exécution des requêtes de base de données en secondes',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf'))
)

EXTERNAL_API_REQUEST_COUNT = Counter(
    'sodav_external_api_requests_total',
    'Nombre total de requêtes aux API externes',
    ['api', 'endpoint', 'status']
)

EXTERNAL_API_LATENCY = Histogram(
    'sodav_external_api_duration_seconds',
    'Temps de réponse des API externes en secondes',
    ['api', 'endpoint'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0, float('inf'))
)

MEMORY_USAGE = Gauge(
    'sodav_memory_usage_bytes',
    'Utilisation de la mémoire en octets'
)

CPU_USAGE = Gauge(
    'sodav_cpu_usage_percent',
    'Utilisation du CPU en pourcentage'
)

TRACK_COUNT = Gauge(
    'sodav_track_count',
    'Nombre total de pistes dans la base de données'
)

ARTIST_COUNT = Gauge(
    'sodav_artist_count',
    'Nombre total d\'artistes dans la base de données'
)

REPORT_GENERATION_COUNT = Counter(
    'sodav_report_generation_total',
    'Nombre total de rapports générés',
    ['report_type', 'format', 'status']
)

REPORT_GENERATION_LATENCY = Histogram(
    'sodav_report_generation_duration_seconds',
    'Temps de génération des rapports en secondes',
    ['report_type', 'format'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, float('inf'))
)

# Décorateurs pour mesurer automatiquement les métriques

def track_http_request(endpoint: str):
    """
    Décorateur pour suivre les métriques des requêtes HTTP.
    
    Args:
        endpoint: Le nom de l'endpoint.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            method = kwargs.get('request', args[0] if args else None)
            if hasattr(method, 'method'):
                method = method.method
            else:
                method = 'UNKNOWN'
            
            start_time = time.time()
            status = '200'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = '500'
                raise e
            finally:
                duration = time.time() - start_time
                HTTP_REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
                HTTP_REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        
        return wrapper
    return decorator

def track_detection(detection_method: str):
    """
    Décorateur pour suivre les métriques de détection musicale.
    
    Args:
        detection_method: La méthode de détection utilisée.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                
                # Enregistrer le niveau de confiance si disponible
                if result and isinstance(result, dict) and 'confidence' in result:
                    DETECTION_CONFIDENCE.labels(detection_method=detection_method).observe(result['confidence'])
                
                return result
            except Exception as e:
                status = 'failure'
                raise e
            finally:
                duration = time.time() - start_time
                DETECTION_COUNT.labels(detection_method=detection_method, status=status).inc()
                DETECTION_LATENCY.labels(detection_method=detection_method).observe(duration)
        
        return wrapper
    return decorator

def track_db_query(operation: str, table: str):
    """
    Décorateur pour suivre les métriques des requêtes de base de données.
    
    Args:
        operation: Le type d'opération (SELECT, INSERT, UPDATE, DELETE).
        table: La table concernée.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_LATENCY.labels(operation=operation, table=table).observe(duration)
        
        return wrapper
    return decorator

def track_external_api(api: str, endpoint: str):
    """
    Décorateur pour suivre les métriques des appels aux API externes.
    
    Args:
        api: Le nom de l'API externe.
        endpoint: L'endpoint appelé.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failure'
                raise e
            finally:
                duration = time.time() - start_time
                EXTERNAL_API_REQUEST_COUNT.labels(api=api, endpoint=endpoint, status=status).inc()
                EXTERNAL_API_LATENCY.labels(api=api, endpoint=endpoint).observe(duration)
        
        return wrapper
    return decorator

def track_report_generation(report_type: str, format: str):
    """
    Décorateur pour suivre les métriques de génération de rapports.
    
    Args:
        report_type: Le type de rapport.
        format: Le format du rapport.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failure'
                raise e
            finally:
                duration = time.time() - start_time
                REPORT_GENERATION_COUNT.labels(report_type=report_type, format=format, status=status).inc()
                REPORT_GENERATION_LATENCY.labels(report_type=report_type, format=format).observe(duration)
        
        return wrapper
    return decorator

# Fonctions utilitaires pour mettre à jour les métriques

def update_system_metrics(memory_bytes: float, cpu_percent: float):
    """
    Met à jour les métriques système.
    
    Args:
        memory_bytes: Utilisation de la mémoire en octets.
        cpu_percent: Utilisation du CPU en pourcentage.
    """
    MEMORY_USAGE.set(memory_bytes)
    CPU_USAGE.set(cpu_percent)

def update_database_counts(track_count: int, artist_count: int):
    """
    Met à jour les compteurs de la base de données.
    
    Args:
        track_count: Nombre total de pistes.
        artist_count: Nombre total d'artistes.
    """
    TRACK_COUNT.set(track_count)
    ARTIST_COUNT.set(artist_count)

def update_active_stations(count: int):
    """
    Met à jour le nombre de stations actives.
    
    Args:
        count: Nombre de stations actives.
    """
    ACTIVE_STATIONS.set(count) 