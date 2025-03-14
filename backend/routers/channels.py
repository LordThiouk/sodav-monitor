"""Channel management functionality for SODAV Monitor.

This module handles operations related to radio channels/stations.
"""

# Configure logging
import logging
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.detection.detect_music import MusicDetector
from backend.models.database import get_db
from backend.models.models import RadioStation
from backend.utils.auth import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/channels",
    tags=["channels"],
    dependencies=[Depends(get_current_user)],  # Require authentication for all endpoints
)


@router.post("/{station_id}/detect-music")
async def detect_music_on_station(
    station_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Detect music on a specific radio station."""
    # Verify station exists
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Check if station is active
    if station.status != "active":
        raise HTTPException(status_code=400, detail="Station is not active")

    # Initialize music detector
    detector = MusicDetector(db)

    # Detect music in background
    background_tasks.add_task(detector.detect_music_from_station, station_id)

    return {
        "status": "success",
        "message": f"Successfully processed station {station.name}",
        "details": {"station_id": station_id, "station_name": station.name},
    }
