"""
Router pour exposer les métriques Prometheus.

Ce module expose un endpoint pour les métriques Prometheus,
permettant à Prometheus de collecter les métriques du système SODAV Monitor.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from ..models.database import get_db
from sqlalchemy.orm import Session
from ..models.models import Track, Artist, RadioStation
from ..utils.metrics import update_database_counts, update_active_stations

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
)

@router.get(
    "",
    response_class=PlainTextResponse,
    description="Expose les métriques Prometheus"
)
async def metrics(db: Session = Depends(get_db)):
    """
    Expose les métriques Prometheus.
    
    Cette route est appelée par Prometheus pour collecter les métriques
    du système SODAV Monitor.
    
    Args:
        db: Session de base de données.
        
    Returns:
        Les métriques au format Prometheus.
    """
    # Mettre à jour les métriques de base de données
    track_count = db.query(Track).count()
    artist_count = db.query(Artist).count()
    active_stations_count = db.query(RadioStation).filter(RadioStation.is_active == True).count()
    
    update_database_counts(track_count, artist_count)
    update_active_stations(active_stations_count)
    
    # Générer les métriques
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    ) 