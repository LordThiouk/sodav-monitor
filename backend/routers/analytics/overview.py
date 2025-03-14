"""Overview analytics functionality for SODAV Monitor.

This module handles the overview analytics endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.analytics.stats_manager import StatsManager
from backend.models.database import get_db
from backend.models.models import AnalyticsData, RadioStation, Track, TrackDetection
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


class ChartDataPoint(BaseModel):
    hour: str
    count: int


class TopTrack(BaseModel):
    rank: int
    title: str
    artist: str
    plays: int
    duration: str


class TopArtist(BaseModel):
    rank: int
    name: str
    plays: int


class TopLabel(BaseModel):
    rank: int
    name: str
    plays: int


class TopChannel(BaseModel):
    rank: int
    name: str
    country: str
    language: str
    plays: int


class SystemHealth(BaseModel):
    status: str
    uptime: float
    lastError: Optional[str] = None


class AnalyticsResponse(BaseModel):
    totalChannels: int
    activeStations: int
    totalPlays: int
    totalPlayTime: str
    playsData: List[ChartDataPoint]
    topTracks: List[TopTrack]
    topArtists: List[TopArtist]
    topLabels: List[TopLabel]
    topChannels: List[TopChannel]
    systemHealth: SystemHealth


@router.get(
    "/overview",
    response_model=AnalyticsResponse,
    summary="Get Analytics Overview",
    description="Returns an overview of system analytics including detection stats, top artists, tracks, labels, and channels",
)
async def get_analytics_overview(
    stats_manager: StatsManager = Depends(get_stats_manager), current_user=Depends(get_current_user)
):
    """Get an overview of system analytics."""
    try:
        daily_report = await stats_manager.generate_daily_report()

        return {
            "totalChannels": daily_report["total_stations"],
            "activeStations": daily_report["active_stations"],
            "totalPlays": daily_report["total_detections"],
            "totalPlayTime": daily_report["total_play_time"],
            "playsData": [
                ChartDataPoint(hour=hour.isoformat(), count=count)
                for hour, count in daily_report["hourly_detections"]
            ],
            "topTracks": [
                TopTrack(
                    rank=i + 1,
                    title=track["title"],
                    artist=track["artist"],
                    plays=track["plays"],
                    duration=track["duration"],
                )
                for i, track in enumerate(daily_report["top_tracks"])
            ],
            "topArtists": [
                TopArtist(rank=i + 1, name=artist["name"], plays=artist["plays"])
                for i, artist in enumerate(daily_report["top_artists"])
            ],
            "topLabels": [
                TopLabel(rank=i + 1, name=label["name"], plays=label["plays"])
                for i, label in enumerate(daily_report["top_labels"])
            ],
            "topChannels": [
                TopChannel(
                    rank=i + 1,
                    name=channel["name"],
                    country=channel["country"],
                    language=channel["language"],
                    plays=channel["plays"],
                )
                for i, channel in enumerate(daily_report["top_channels"])
            ],
            "systemHealth": {
                "status": "healthy",
                "uptime": daily_report["uptime"],
                "lastError": daily_report.get("last_error"),
            },
        }
    except Exception as e:
        logger.error(f"Error in analytics overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics data: {str(e)}")


@router.get("/dashboard")
async def get_dashboard_stats(
    period: Optional[int] = 24,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Get dashboard statistics for a specified period (in hours)."""
    try:
        return await stats_manager.get_dashboard_stats(period)
    except Exception as e:
        logger.error(f"Error in dashboard stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving dashboard analytics: {str(e)}"
        )


@router.get("/trends")
async def get_trends(
    days: Optional[int] = 7,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Get trend analysis for a specified number of days."""
    try:
        return await stats_manager.get_trend_analysis(days=days)
    except Exception as e:
        logger.error(f"Error getting trend analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_analytics_by_timeframe(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get analytics data for a specific timeframe."""
    try:
        # Validate dates
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        # Get detections within timeframe
        detections = (
            db.query(TrackDetection)
            .filter(
                TrackDetection.detected_at >= start_date, TrackDetection.detected_at <= end_date
            )
            .all()
        )

        # Get unique tracks and artists
        unique_tracks = len(set(d.track_id for d in detections))
        unique_artists = len(set(d.track.artist_id for d in detections if d.track))

        # Calculate total play time
        total_play_time = sum(
            (d.play_duration.total_seconds() for d in detections if d.play_duration), start=0
        )

        return {
            "total_detections": len(detections),
            "unique_tracks": unique_tracks,
            "unique_artists": unique_artists,
            "total_play_time": str(timedelta(seconds=total_play_time)),
            "average_confidence": sum(d.confidence for d in detections) / len(detections)
            if detections
            else 0,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting analytics by timeframe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics data: {str(e)}")
