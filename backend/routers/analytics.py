"""
Legacy analytics router module for SODAV Monitor.

This module is deprecated and will be removed in a future version.
Please use the new modular analytics routers in the analytics/ directory.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import and_, desc, distinct, func
from sqlalchemy.orm import Session

from backend.models.database import get_db

from ..analytics.stats_manager import StatsManager
from ..core.config import get_settings
from ..models.models import (
    AnalyticsData,
    Artist,
    ArtistStats,
    DetectionHourly,
    RadioStation,
    StationStats,
    StationStatus,
    StationTrackStats,
    Track,
    TrackDetection,
    TrackStats,
)
from ..schemas.base import AnalyticsResponse, ChartData, SystemHealth
from ..utils.auth import get_current_user

router = APIRouter(tags=["analytics"], responses={404: {"description": "Not found"}})

logger = logging.getLogger(__name__)


async def get_stats_manager(db: Session = Depends(get_db)) -> StatsManager:
    """Get a StatsManager instance for dependency injection."""
    stats_manager = StatsManager(db)
    try:
        yield stats_manager
    finally:
        await stats_manager.close()


class ChartDataPoint(BaseModel):
    """Data point for analytics charts with hour and count."""

    hour: str
    count: int


class TopTrack(BaseModel):
    """Track information with ranking and play statistics."""

    rank: int
    title: str
    artist: str
    plays: int
    duration: str


class TopArtist(BaseModel):
    """Artist information with ranking and play count."""

    rank: int
    name: str
    plays: int


class TopLabel(BaseModel):
    """Label information with ranking and play count."""

    rank: int
    name: str
    plays: int


class TopChannel(BaseModel):
    """Channel information with ranking and play statistics."""

    rank: int
    name: str
    country: str
    language: str
    plays: int


class SystemHealth(BaseModel):
    """System health status information."""

    status: str
    uptime: float
    lastError: Optional[str] = None


class AnalyticsResponse(BaseModel):
    """Complete analytics response with all statistics."""

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
    try:
        daily_report = await stats_manager.generate_daily_report()

        return {
            "totalChannels": daily_report["total_stations"],
            "activeStations": daily_report["active_stations"],
            "totalPlays": daily_report["total_detections"],
            "totalPlayTime": daily_report["total_play_time"],
            "playsData": [
                ChartDataPoint(hour=hour.isoformat(), count=count).dict()
                for hour, count in daily_report["hourly_detections"]
            ],
            "topTracks": [
                TopTrack(
                    rank=idx + 1,
                    title=track["title"],
                    artist=track["artist"],
                    plays=track["plays"],
                    duration=track["duration"],
                ).dict()
                for idx, track in enumerate(daily_report["top_tracks"])
            ],
            "topArtists": [
                TopArtist(rank=idx + 1, name=artist["name"], plays=artist["plays"]).dict()
                for idx, artist in enumerate(daily_report["top_artists"])
            ],
            "topLabels": [
                TopLabel(rank=idx + 1, name=label["name"], plays=label["plays"]).dict()
                for idx, label in enumerate(daily_report["top_labels"])
            ],
            "topChannels": [
                TopChannel(
                    rank=idx + 1,
                    name=channel["name"],
                    country=channel["country"],
                    language=channel["language"],
                    plays=channel["plays"],
                ).dict()
                for idx, channel in enumerate(daily_report["top_channels"])
            ],
            "systemHealth": SystemHealth(
                status="healthy" if daily_report["active_stations"] > 0 else "warning",
                uptime=100.0
                * (
                    daily_report["active_stations"] / daily_report["total_stations"]
                    if daily_report["total_stations"] > 0
                    else 0
                ),
                lastError=None,
            ).dict(),
        }
    except Exception as e:
        logger.error(f"Error in analytics overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics data: {str(e)}")


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


@router.get(
    "/tracks",
    response_model=List[Dict],
    summary="Get Track Analytics",
    description="Returns detailed analytics data for all tracks",
)
async def get_track_analytics(
    stats_manager: StatsManager = Depends(get_stats_manager), current_user=Depends(get_current_user)
):
    """
    Get detailed track analytics including:
    - Play counts
    - Average confidence
    - Last detection time
    """
    try:
        return await stats_manager.get_all_track_stats()
    except Exception as e:
        logger.error(f"Error in track analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving track analytics: {str(e)}")


@router.get(
    "/dashboard",
    response_model=Dict,
    summary="Get Dashboard Analytics",
    description="Returns analytics data for the dashboard",
)
async def get_dashboard_stats(
    period: Optional[int] = 24,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Get analytics data for the dashboard.

    Args:
        period: Time period in hours to get stats for (default: 24)
        stats_manager: StatsManager instance for data access
        current_user: Current authenticated user

    Returns:
        Dict containing dashboard analytics data

    Raises:
        HTTPException: If period is invalid or error occurs
    """
    try:
        if period <= 0:
            raise HTTPException(status_code=400, detail="Period must be positive")

        return await stats_manager.get_dashboard_stats(period)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in dashboard analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving dashboard analytics: {str(e)}"
        )


@router.get(
    "/export",
    response_model=List[Dict],
    summary="Export Analytics Data",
    description="Exports analytics data in the specified format",
)
async def export_analytics(
    format: str = "json",
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Export analytics data in the specified format.

    Args:
        format: Export format (json, csv, or xlsx)
        stats_manager: StatsManager instance for data access
        current_user: Current authenticated user

    Returns:
        List of dictionaries containing analytics data

    Raises:
        HTTPException: If format is invalid or error occurs
    """
    try:
        if format not in ["json", "csv", "xlsx"]:
            raise HTTPException(status_code=400, detail="Invalid export format")

        return await stats_manager.export_analytics(format)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error exporting analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting analytics data: {str(e)}")


@router.get("/trends")
async def get_trends(
    days: Optional[int] = 7,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Get trend analysis for a specified number of days.

    Args:
        days: Number of days to analyze trends for (default: 7)
        stats_manager: StatsManager instance for data access
        current_user: Current authenticated user

    Returns:
        Dict containing trend analysis data

    Raises:
        HTTPException: If error occurs during analysis
    """
    try:
        return await stats_manager.get_trend_analysis(days=days)
    except Exception as e:
        logger.error(f"Error getting trend analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stations")
async def get_station_stats(
    station_id: Optional[int] = None,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Get statistics for a specific station or all stations.

    Args:
        station_id: Optional ID of a specific station to get stats for
        stats_manager: StatsManager instance for data access
        current_user: Current authenticated user

    Returns:
        Dict containing station statistics

    Raises:
        HTTPException: If error occurs retrieving stats
    """
    try:
        if station_id:
            return await stats_manager.get_station_stats(station_id)
        else:
            return await stats_manager.get_all_station_stats()
    except Exception as e:
        logger.error(f"Error getting station stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artists")
async def get_artist_stats(
    artist_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get statistics for a specific artist or all artists.

    Args:
        artist_id: Optional ID of a specific artist to get stats for
        db: Database session
        current_user: Current authenticated user

    Returns:
        Dict containing artist statistics

    Raises:
        HTTPException: If artist not found or error occurs
    """
    try:
        stats_manager = StatsManager(db)
        daily_report = await stats_manager.generate_daily_report()

        if artist_id:
            artist_stats = next(
                (stat for stat in daily_report["top_artists"] if stat["id"] == artist_id), None
            )
            if not artist_stats:
                raise HTTPException(status_code=404, detail="Artist not found")
            return artist_stats

        return daily_report["top_artists"]
    except Exception as e:
        logger.error(f"Error getting artist stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict)
async def get_analytics_by_timeframe(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get analytics data for a specific timeframe.

    Args:
        start_date: Start date of the timeframe
        end_date: End date of the timeframe
        db: Database session
        current_user: Current authenticated user

    Returns:
        Dict containing analytics data for the timeframe

    Raises:
        HTTPException: If timeframe is invalid or error occurs
    """
    try:
        # Validate timeframe
        if end_date <= start_date:
            raise HTTPException(
                status_code=400, detail="Invalid timeframe: end_date must be after start_date"
            )

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
        unique_artists = len(set(d.track.artist_id for d in detections))

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

    except Exception as e:
        logger.error(f"Error getting analytics by timeframe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics data: {str(e)}")


@router.get(
    "/tracks/{track_id}/stats",
    response_model=Dict,
    summary="Get Track Statistics",
    description="Returns statistics for a specific track",
)
async def get_track_stats(
    track_id: int,
    stats_manager: StatsManager = Depends(get_stats_manager),
    current_user=Depends(get_current_user),
):
    """Get statistics for a specific track.

    Args:
        track_id: ID of the track to get stats for
        stats_manager: StatsManager instance for data access
        current_user: Current authenticated user

    Returns:
        Dict containing track statistics

    Raises:
        HTTPException: If track not found or error occurs
    """
    try:
        return await stats_manager.get_track_stats(track_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting track stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stations/{station_id}/stats",
    response_model=Dict,
    summary="Get Station Statistics",
    description="Returns statistics for a specific radio station",
)
async def get_station_stats(
    station_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get statistics for a specific radio station.

    Args:
        station_id: ID of the station to get stats for
        db: Database session
        current_user: Current authenticated user

    Returns:
        Dict containing station statistics

    Raises:
        HTTPException: If station not found or error occurs
    """
    try:
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")

        # Get detection stats for the last 24 hours
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)

        detections = (
            db.query(TrackDetection)
            .filter(TrackDetection.station_id == station_id, TrackDetection.detected_at >= last_24h)
            .all()
        )

        total_play_time = sum(
            (d.play_duration.total_seconds() for d in detections if d.play_duration), start=0
        )

        return {
            "id": station.id,
            "name": station.name,
            "status": station.status.value if station.status else "inactive",
            "total_detections": len(detections),
            "total_play_time": str(timedelta(seconds=total_play_time)),
            "average_confidence": sum(d.confidence for d in detections) / len(detections)
            if detections
            else 0,
            "last_checked": station.last_checked.isoformat() if station.last_checked else None,
        }
    except Exception as e:
        logger.error(f"Error getting station stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
