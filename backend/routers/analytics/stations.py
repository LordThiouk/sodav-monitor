"""Station analytics functionality for SODAV Monitor.

This module handles the station analytics endpoints.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.analytics.stats_manager import StatsManager
from backend.models.database import get_db
from backend.utils.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["analytics"], responses={404: {"description": "Not found"}})


async def get_stats_manager(db: Session = Depends(get_db)) -> StatsManager:
    """Dependency to get StatsManager instance."""
    stats_manager = StatsManager(db)
    try:
        yield stats_manager
    finally:
        await stats_manager.close()


@router.get(
    "/stations",
    response_model=List[Dict],
    summary="Get Station Analytics",
    description="Returns analytics data for all radio stations",
)
async def get_station_analytics(
    stats_manager: StatsManager = Depends(get_stats_manager), current_user=Depends(get_current_user)
):
    """
    Get analytics data for radio stations including:
    - Station status
    - Detection counts
    - Last check and detection times
    """
    try:
        return await stats_manager.get_all_station_stats()
    except Exception as e:
        logger.error(f"Error in station analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving station analytics: {str(e)}")


@router.get("/stations/stats")
async def get_station_stats(
    station_id: Optional[int] = None,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Get statistics for a specific station or all stations."""
    try:
        if station_id:
            # Get stats for a specific station
            station_stats = await stats_manager.get_station_stats(station_id)
            return station_stats
        else:
            # Get stats for all stations
            all_station_stats = await stats_manager.get_all_station_stats()
            return all_station_stats
    except Exception as e:
        logger.error(f"Error getting station stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stations/{station_id}/stats",
    response_model=Dict,
    summary="Get Station Statistics",
    description="Returns statistics for a specific radio station",
)
async def get_specific_station_stats(
    station_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get detailed statistics for a specific radio station."""
    try:
        from sqlalchemy.orm import joinedload

        from backend.models.models import RadioStation, StationStats, TrackDetection

        # Check if station exists
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Get station stats
        stats = db.query(StationStats).filter(StationStats.station_id == station_id).first()

        # Get recent detections
        recent_detections = (
            db.query(TrackDetection)
            .filter(TrackDetection.station_id == station_id)
            .order_by(TrackDetection.detected_at.desc())
            .limit(10)
            .options(joinedload(TrackDetection.track))
            .all()
        )

        # Format response
        return {
            "station": {
                "id": station.id,
                "name": station.name,
                "status": station.status,
                "is_active": station.is_active,
                "last_check": station.last_check.isoformat() if station.last_check else None,
                "last_detection_time": station.last_detection_time.isoformat()
                if station.last_detection_time
                else None,
            },
            "stats": {
                "detection_count": stats.detection_count if stats else 0,
                "average_confidence": stats.average_confidence if stats else 0,
                "last_detected": stats.last_detected.isoformat()
                if stats and stats.last_detected
                else None,
            },
            "recent_detections": [
                {
                    "id": detection.id,
                    "track": {
                        "id": detection.track.id,
                        "title": detection.track.title,
                        "artist": detection.track.artist.name
                        if detection.track.artist
                        else "Unknown",
                    },
                    "detected_at": detection.detected_at.isoformat(),
                    "confidence": detection.confidence,
                    "play_duration": str(detection.play_duration)
                    if detection.play_duration
                    else None,
                }
                for detection in recent_detections
            ],
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting station stats: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving station statistics: {str(e)}"
        )
