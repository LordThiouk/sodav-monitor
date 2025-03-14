"""Artist analytics functionality for SODAV Monitor.

This module handles the artist analytics endpoints.
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
    "/artists",
    response_model=List[Dict],
    summary="Get Artist Analytics",
    description="Returns detailed analytics data for all artists",
)
async def get_artist_analytics(
    stats_manager: StatsManager = Depends(get_stats_manager), current_user=Depends(get_current_user)
):
    """
    Get detailed artist analytics including:
    - Detection counts
    - Total play time
    - Unique tracks, albums, labels, and stations
    """
    try:
        return await stats_manager.get_all_artist_stats()
    except Exception as e:
        logger.error(f"Error in artist analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving artist analytics: {str(e)}")


@router.get("/artists/stats")
async def get_artist_stats(
    artist_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get statistics for a specific artist or all artists."""
    try:
        from sqlalchemy.orm import joinedload

        from backend.models.models import Artist, ArtistStats, Track, TrackDetection

        if artist_id:
            # Get stats for a specific artist
            artist = db.query(Artist).filter(Artist.id == artist_id).first()
            if not artist:
                raise HTTPException(status_code=404, detail="Artist not found")

            # Get artist stats
            stats = db.query(ArtistStats).filter(ArtistStats.artist_id == artist_id).first()

            # Get artist tracks
            tracks = db.query(Track).filter(Track.artist_id == artist_id).all()

            # Get recent detections
            recent_detections = (
                db.query(TrackDetection)
                .join(Track, TrackDetection.track_id == Track.id)
                .filter(Track.artist_id == artist_id)
                .order_by(TrackDetection.detected_at.desc())
                .limit(10)
                .options(joinedload(TrackDetection.track), joinedload(TrackDetection.station))
                .all()
            )

            # Format response
            return {
                "artist": {
                    "id": artist.id,
                    "name": artist.name,
                    "country": artist.country,
                    "label": artist.label,
                },
                "stats": {
                    "total_plays": stats.total_plays if stats else 0,
                    "total_play_time": str(stats.total_play_time)
                    if stats and stats.total_play_time
                    else "0:00:00",
                    "last_detected": stats.last_detected.isoformat()
                    if stats and stats.last_detected
                    else None,
                    "average_confidence": stats.average_confidence if stats else 0,
                },
                "tracks": [
                    {"id": track.id, "title": track.title, "isrc": track.isrc, "label": track.label}
                    for track in tracks
                ],
                "recent_detections": [
                    {
                        "id": detection.id,
                        "track": {"id": detection.track.id, "title": detection.track.title},
                        "station": {"id": detection.station.id, "name": detection.station.name},
                        "detected_at": detection.detected_at.isoformat(),
                        "confidence": detection.confidence,
                        "play_duration": str(detection.play_duration)
                        if detection.play_duration
                        else None,
                    }
                    for detection in recent_detections
                ],
            }
        else:
            # Get stats for all artists
            artists = db.query(Artist).options(joinedload(Artist.stats)).all()

            return [
                {
                    "id": artist.id,
                    "name": artist.name,
                    "country": artist.country,
                    "label": artist.label,
                    "stats": {
                        "total_plays": artist.stats.total_plays if artist.stats else 0,
                        "total_play_time": str(artist.stats.total_play_time)
                        if artist.stats and artist.stats.total_play_time
                        else "0:00:00",
                        "last_detected": artist.stats.last_detected.isoformat()
                        if artist.stats and artist.stats.last_detected
                        else None,
                    },
                }
                for artist in artists
            ]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting artist stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
