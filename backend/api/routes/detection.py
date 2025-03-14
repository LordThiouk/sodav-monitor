from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.detection.detect_music import MusicDetector
from backend.models.database import get_db
from backend.utils.logging_config import log_with_category, setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    prefix="/detection",
    tags=["detection"],
    responses={404: {"description": "Not found"}},
)


@router.post("/detect-music-all", response_model=Dict[str, Any])
async def detect_music_all_stations(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Detect music playing on all active radio stations.

    This endpoint triggers music detection on all active radio stations.
    The detection process runs in the background.

    Returns:
        Dictionary with status information
    """
    try:
        # Get all active stations
        from backend.models.models import RadioStation, StationStatus

        stations = db.query(RadioStation).filter(RadioStation.status == StationStatus.ACTIVE).all()

        if not stations:
            return {"status": "success", "message": "No active stations found", "stations_count": 0}

        # Detect music on each station in the background
        for station in stations:
            background_tasks.add_task(detect_station_music, station.id)

        return {
            "status": "success",
            "message": f"Music detection started for {len(stations)} stations",
            "stations_count": len(stations),
        }

    except Exception as e:
        log_with_category(
            logger, "DETECTION", "error", f"Error detecting music on all stations: {str(e)}"
        )
        return {"status": "error", "message": f"Error detecting music on all stations: {str(e)}"}


async def detect_station_music(station_id: int):
    """Detect music playing on a radio station."""
    # Create a new database session
    from backend.models.database import SessionLocal

    db = SessionLocal()

    try:
        # Get the station from the database
        from backend.models.models import RadioStation

        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            log_with_category(logger, "DETECTION", "error", f"Station {station_id} not found")
            return

        # Use the music detector
        detector = MusicDetector(db)
        result = await detector.detect_music_from_station(station_id)
        log_with_category(
            logger, "DETECTION", "info", f"Music detection for station {station.name}: {result}"
        )

    except Exception as e:
        log_with_category(
            logger,
            "DETECTION",
            "error",
            f"Error detecting music for station {station_id}: {str(e)}",
        )
    finally:
        db.close()
