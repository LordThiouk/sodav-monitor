"""Search functionality for detections in SODAV Monitor.

This module handles search operations for music detections.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from backend.models.database import get_db
from backend.models.models import TrackDetection, Track, Artist, RadioStation
from backend.utils.auth import get_current_user
from backend.schemas.base import DetectionResponse

# Configure logging
import logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["detections"],
    dependencies=[Depends(get_current_user)]  # Require authentication for all endpoints
)

@router.get("/search/", response_model=List[DetectionResponse])
async def search_detections(
    query: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search for detections by track title, artist name, or station name."""
    search_query = f"%{query}%"
    
    detections = db.query(TrackDetection).join(
        Track, TrackDetection.track_id == Track.id
    ).join(
        Artist, Track.artist_id == Artist.id
    ).join(
        RadioStation, TrackDetection.station_id == RadioStation.id
    ).filter(
        or_(
            Track.title.ilike(search_query),
            Artist.name.ilike(search_query),
            RadioStation.name.ilike(search_query)
        )
    ).order_by(
        TrackDetection.detected_at.desc()
    ).offset(skip).limit(limit).all()
    
    # Transformer les détections en dictionnaires avec l'artiste comme chaîne
    result = []
    for detection in detections:
        # Ensure we're using the exact confidence value from the database
        confidence_value = float(detection.confidence)
        
        detection_dict = {
            "id": detection.id,
            "track": {
                "id": detection.track.id,
                "title": detection.track.title,
                "artist": detection.track.artist.name if detection.track.artist else "",
                "isrc": detection.track.isrc,
                "label": detection.track.label,
                "fingerprint": detection.track.fingerprint,
                "created_at": detection.track.created_at,
                "updated_at": detection.track.updated_at
            },
            "station": {
                "id": detection.station.id,
                "name": detection.station.name,
                "stream_url": detection.station.stream_url,
                "region": detection.station.region,
                "language": detection.station.language,
                "type": detection.station.type,
                "status": detection.station.status,
                "is_active": detection.station.is_active,
                "last_checked": detection.station.last_check,
                "created_at": detection.station.created_at,
                "updated_at": detection.station.updated_at
            },
            "detected_at": detection.detected_at,
            "confidence": confidence_value,
            "play_duration": detection.play_duration
        }
        result.append(detection_dict)
    
    return result

@router.get("/station/{station_id}", response_model=List[DetectionResponse])
async def get_station_detections(
    station_id: int,
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get detections for a specific station."""
    # Verify station exists
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Build query
    query = db.query(TrackDetection).filter(TrackDetection.station_id == station_id)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(TrackDetection.detected_at >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detected_at <= end_date)
    
    # Apply pagination
    detections = query.order_by(TrackDetection.detected_at.desc()).offset(skip).limit(limit).all()
    
    # Transformer les détections en dictionnaires avec l'artiste comme chaîne
    result = []
    for detection in detections:
        # Ensure we're using the exact confidence value from the database
        confidence_value = float(detection.confidence)
        
        detection_dict = {
            "id": detection.id,
            "track": {
                "id": detection.track.id,
                "title": detection.track.title,
                "artist": detection.track.artist.name if detection.track.artist else "",
                "isrc": detection.track.isrc,
                "label": detection.track.label,
                "fingerprint": detection.track.fingerprint,
                "created_at": detection.track.created_at,
                "updated_at": detection.track.updated_at
            },
            "station": {
                "id": detection.station.id,
                "name": detection.station.name,
                "stream_url": detection.station.stream_url,
                "region": detection.station.region,
                "language": detection.station.language,
                "type": detection.station.type,
                "status": detection.station.status,
                "is_active": detection.station.is_active,
                "last_checked": detection.station.last_check,
                "created_at": detection.station.created_at,
                "updated_at": detection.station.updated_at
            },
            "detected_at": detection.detected_at,
            "confidence": confidence_value,
            "play_duration": detection.play_duration
        }
        result.append(detection_dict)
    
    return result

@router.get("/track/{track_id}", response_model=List[DetectionResponse])
async def get_track_detections(
    track_id: int,
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get detections for a specific track."""
    # Verify track exists
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # Build query
    query = db.query(TrackDetection).filter(TrackDetection.track_id == track_id)
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(TrackDetection.detected_at >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detected_at <= end_date)
    
    # Apply pagination
    detections = query.order_by(TrackDetection.detected_at.desc()).offset(skip).limit(limit).all()
    
    # Transformer les détections en dictionnaires avec l'artiste comme chaîne
    result = []
    for detection in detections:
        # Ensure we're using the exact confidence value from the database
        confidence_value = float(detection.confidence)
        
        detection_dict = {
            "id": detection.id,
            "track": {
                "id": detection.track.id,
                "title": detection.track.title,
                "artist": detection.track.artist.name if detection.track.artist else "",
                "isrc": detection.track.isrc,
                "label": detection.track.label,
                "fingerprint": detection.track.fingerprint,
                "created_at": detection.track.created_at,
                "updated_at": detection.track.updated_at
            },
            "station": {
                "id": detection.station.id,
                "name": detection.station.name,
                "stream_url": detection.station.stream_url,
                "region": detection.station.region,
                "language": detection.station.language,
                "type": detection.station.type,
                "status": detection.station.status,
                "is_active": detection.station.is_active,
                "last_checked": detection.station.last_check,
                "created_at": detection.station.created_at,
                "updated_at": detection.station.updated_at
            },
            "detected_at": detection.detected_at,
            "confidence": confidence_value,
            "play_duration": detection.play_duration
        }
        result.append(detection_dict)
    
    return result

@router.get("/latest/", response_model=List[DetectionResponse])
async def get_latest_detections(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the latest detections across all stations."""
    detections = db.query(TrackDetection).order_by(TrackDetection.detected_at.desc()).limit(limit).all()
    
    # Transformer les détections en dictionnaires avec l'artiste comme chaîne
    result = []
    for detection in detections:
        # Ensure we're using the exact confidence value from the database
        confidence_value = float(detection.confidence)
        
        detection_dict = {
            "id": detection.id,
            "track": {
                "id": detection.track.id,
                "title": detection.track.title,
                "artist": detection.track.artist.name if detection.track.artist else "",
                "isrc": detection.track.isrc,
                "label": detection.track.label,
                "fingerprint": detection.track.fingerprint,
                "created_at": detection.track.created_at,
                "updated_at": detection.track.updated_at
            },
            "station": {
                "id": detection.station.id,
                "name": detection.station.name,
                "stream_url": detection.station.stream_url,
                "region": detection.station.region,
                "language": detection.station.language,
                "type": detection.station.type,
                "status": detection.station.status,
                "is_active": detection.station.is_active,
                "last_checked": detection.station.last_check,
                "created_at": detection.station.created_at,
                "updated_at": detection.station.updated_at
            },
            "detected_at": detection.detected_at,
            "confidence": confidence_value,
            "play_duration": detection.play_duration
        }
        result.append(detection_dict)
    
    return result 