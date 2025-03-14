"""
Router pour exposer les métriques Prometheus.

Ce module expose un endpoint pour les métriques Prometheus,
permettant à Prometheus de collecter les métriques du système SODAV Monitor.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.models import Artist, RadioStation, Track
from ..utils.metrics import update_active_stations, update_database_counts

# Configure logging
logger = logging.getLogger(__name__)

# Créer un routeur sans dépendance d'authentification
router = APIRouter(
    prefix="/metrics", tags=["metrics"], dependencies=[]  # Aucune dépendance d'authentification
)


@router.get(
    "",
    response_class=PlainTextResponse,
    description="Expose les métriques Prometheus",
    dependencies=[],  # Aucune dépendance d'authentification
)
async def metrics(request: Request, db: Session = Depends(get_db)):
    """
    Expose les métriques Prometheus.

    Cette route est appelée par Prometheus pour collecter les métriques
    du système SODAV Monitor.

    Args:
        request: Requête HTTP
        db: Session de base de données.

    Returns:
        Les métriques au format Prometheus.
    """
    try:
        # Mettre à jour les métriques de base de données
        track_count = db.query(Track).count()
        artist_count = db.query(Artist).count()
        active_stations_count = (
            db.query(RadioStation).filter(RadioStation.is_active == True).count()
        )

        update_database_counts(track_count, artist_count)
        update_active_stations(active_stations_count)
    except (ProgrammingError, OperationalError) as e:
        # Si les tables n'existent pas encore, on ignore l'erreur
        logger.warning(f"Erreur lors de la récupération des métriques de base de données: {str(e)}")
        # Initialiser avec des valeurs par défaut
        update_database_counts(0, 0)
        update_active_stations(0)

    # Générer les métriques
    return PlainTextResponse(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
