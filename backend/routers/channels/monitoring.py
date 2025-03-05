"""Station monitoring functionality for SODAV Monitor.

This module handles operations related to monitoring radio stations.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import asyncio

from backend.models.database import get_db
from backend.models.models import RadioStation, StationStatus, TrackDetection, Track, Artist
from backend.utils.auth import get_current_user
from backend.utils.streams.stream_checker import check_stream_status
from backend.schemas.base import DetectionsResponse

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["channels"],
    dependencies=[Depends(get_current_user)]  # Require authentication for all endpoints
)

@router.post("/{station_id}/check")
async def check_station(
    station_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Check the status of a specific radio station."""
    # Get the station from the database
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Check the station status in the background
    background_tasks.add_task(check_station_status, station_id)
    
    return {"message": f"Station check initiated for {station.name}"}

@router.post("/refresh")
async def refresh_all_stations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Refresh the status of all radio stations."""
    # Get all active stations
    stations = db.query(RadioStation).filter(
        RadioStation.status.in_([StationStatus.ACTIVE, StationStatus.ERROR])
    ).all()
    
    # Check each station in the background
    for station in stations:
        background_tasks.add_task(check_station_status, station.id)
    
    return {"message": f"Refresh initiated for {len(stations)} stations"}

@router.post("/{station_id}/detect-music")
async def detect_music(
    station_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Detect music playing on a specific radio station."""
    # Get the station from the database
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        logger.error(f"Station {station_id} not found")
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Check if the station is active
    if station.status != StationStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Station is not active")
    
    # Detect music in the background
    background_tasks.add_task(detect_station_music, station_id)
    
    return {"message": f"Music detection initiated for {station.name}"}

@router.get("/{station_id}/detections", response_model=DetectionsResponse)
async def get_station_detections(
    station_id: int,
    skip: int = 0,
    limit: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get music detections for a specific radio station."""
    # Get the station from the database
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Build the query
    query = db.query(TrackDetection).filter(TrackDetection.station_id == station_id)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(TrackDetection.detected_at >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detected_at <= end_date)
    
    # Get the total count
    total_count = query.count()
    
    # Apply pagination
    detections = query.order_by(TrackDetection.detected_at.desc()).offset(skip).limit(limit).all()
    
    # Get the track and artist details for each detection
    detection_details = []
    for detection in detections:
        track = db.query(Track).filter(Track.id == detection.track_id).first()
        artist = db.query(Artist).filter(Artist.id == track.artist_id).first() if track else None
        
        detection_details.append({
            "id": detection.id,
            "detected_at": detection.detected_at,
            "play_duration": detection.play_duration.total_seconds() if detection.play_duration else None,
            "confidence": detection.confidence,
            "track": {
                "id": track.id,
                "title": track.title,
                "isrc": track.isrc
            } if track else None,
            "artist": {
                "id": artist.id,
                "name": artist.name
            } if artist else None
        })
    
    return {
        "total": total_count,
        "items": detection_details,
        "station": {
            "id": station.id,
            "name": station.name
        }
    }

@router.get("/stats", response_model=Dict[str, Any])
async def get_monitoring_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get monitoring statistics for all stations."""
    # Get counts by status
    status_counts = {
        "active": db.query(RadioStation).filter(RadioStation.status == StationStatus.ACTIVE).count(),
        "inactive": db.query(RadioStation).filter(RadioStation.status == StationStatus.INACTIVE).count(),
        "error": db.query(RadioStation).filter(RadioStation.status == StationStatus.ERROR).count(),
        "maintenance": db.query(RadioStation).filter(RadioStation.status == StationStatus.MAINTENANCE).count()
    }
    
    # Get detection counts for the last 24 hours
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    detection_count = db.query(TrackDetection).filter(
        TrackDetection.detected_at >= yesterday
    ).count()
    
    # Get stations with the most detections
    top_stations = db.query(
        RadioStation.id,
        RadioStation.name,
        func.count(TrackDetection.id).label('detection_count')
    ).join(
        TrackDetection, TrackDetection.station_id == RadioStation.id
    ).filter(
        TrackDetection.detected_at >= yesterday
    ).group_by(
        RadioStation.id
    ).order_by(
        func.count(TrackDetection.id).desc()
    ).limit(5).all()
    
    return {
        "status_counts": status_counts,
        "detection_count_24h": detection_count,
        "top_stations": [
            {
                "id": station.id,
                "name": station.name,
                "detection_count": station.detection_count
            }
            for station in top_stations
        ]
    }

# Helper functions

async def check_station_status(station_id: int):
    """Check the status of a radio station."""
    # Create a new database session
    from backend.models.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get the station from the database
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            logger.error(f"Station {station_id} not found")
            return
        
        # Update the last check timestamp
        station.last_check = datetime.utcnow()
        db.commit()
        
        # Check the stream status
        status, message = await check_stream_status(station.stream_url)
        
        # Update the station status
        old_status = station.status
        if status:
            station.status = StationStatus.ACTIVE
            station.last_successful_check = datetime.utcnow()
            station.error_count = 0
        else:
            station.error_count += 1
            if station.error_count >= 3:
                station.status = StationStatus.ERROR
        
        # Create a status history entry if the status changed
        if old_status != station.status:
            from backend.models.models import StationStatusHistory
            status_history = StationStatusHistory(
                station_id=station_id,
                old_status=old_status,
                new_status=station.status,
                message=message,
                created_by=None  # System-generated
            )
            db.add(status_history)
        
        db.commit()
        logger.info(f"Station {station.name} status updated: {station.status}")
        
    except Exception as e:
        logger.error(f"Error checking station {station_id}: {str(e)}")
    finally:
        db.close()

async def detect_station_music(station_id: int):
    """Detect music playing on a radio station."""
    # Create a new database session
    from backend.models.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Get the station from the database
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            logger.error(f"Station {station_id} not found")
            return
        
        # Get the radio manager from the app state
        from fastapi import FastAPI
        from starlette.applications import Starlette
        
        # Get the app instance
        app = None
        for app_instance in Starlette._applications:
            if isinstance(app_instance, FastAPI):
                app = app_instance
                break
        
        if app and hasattr(app.state, 'radio_manager'):
            radio_manager = app.state.radio_manager
            # Call the radio manager's detect_music method
            result = await radio_manager.detect_music(station_id)
            logger.info(f"Music detection for station {station.name}: {result}")
        else:
            # Fallback to the original implementation
            from backend.detection.detect_music import MusicDetector
            detector = MusicDetector(db)
            result = await detector.detect_music_from_station(station_id)
            logger.info(f"Music detection for station {station.name}: {result}")
        
    except Exception as e:
        logger.error(f"Error detecting music for station {station_id}: {str(e)}")
    finally:
        db.close()