"""Core detections functionality for SODAV Monitor.

This module handles basic CRUD operations for music detections.
"""

# Configure logging
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from backend.models.database import get_db
from backend.models.models import Artist, RadioStation, Track, TrackDetection
from backend.schemas.base import DetectionResponse
from backend.utils.auth import get_current_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["detections"],
    dependencies=[Depends(get_current_user)],  # Require authentication for all endpoints
)


@router.get("/", response_model=List[DetectionResponse])
async def get_detections(
    skip: int = 0,
    limit: int = 100,
    station_id: Optional[int] = None,
    track_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    confidence_threshold: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a list of detections with optional filtering."""
    query = db.query(TrackDetection)

    # Apply filters if provided
    if station_id:
        query = query.filter(TrackDetection.station_id == station_id)
    if track_id:
        query = query.filter(TrackDetection.track_id == track_id)
    if start_date:
        query = query.filter(TrackDetection.detected_at >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detected_at <= end_date)
    if confidence_threshold:
        query = query.filter(TrackDetection.confidence >= confidence_threshold)

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
                "updated_at": detection.track.updated_at,
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
                "updated_at": detection.station.updated_at,
            },
            "detected_at": detection.detected_at,
            "confidence": confidence_value,
            "play_duration": detection.play_duration,
        }
        result.append(detection_dict)

    return result


@router.get("/{detection_id}", response_model=DetectionResponse)
async def get_detection(
    detection_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Get a specific detection by ID."""
    detection = db.query(TrackDetection).filter(TrackDetection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    # Créer une copie du dictionnaire de détection pour la manipulation
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
            "updated_at": detection.track.updated_at,
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
            "updated_at": detection.station.updated_at,
        },
        "detected_at": detection.detected_at,
        "confidence": detection.confidence,
        "play_duration": detection.play_duration,
    }

    return detection_dict


@router.post("/", response_model=DetectionResponse)
async def create_detection(
    detection_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new detection."""
    # Extraire les données de détection du format attendu par les tests
    if "detection" in detection_data:
        detection_data = detection_data["detection"]

    # Validate required fields
    required_fields = ["track_id", "station_id", "confidence"]
    for field in required_fields:
        if field not in detection_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    # Create detection object
    detection = TrackDetection(
        track_id=detection_data["track_id"],
        station_id=detection_data["station_id"],
        confidence=detection_data["confidence"],
        detected_at=detection_data.get("detected_at", datetime.utcnow()),
        play_duration=timedelta(seconds=detection_data.get("play_duration", 0)),
        fingerprint=detection_data.get("fingerprint"),
        audio_hash=detection_data.get("audio_hash"),
    )

    # Add to database
    db.add(detection)
    db.commit()
    db.refresh(detection)

    # Transformer la détection en dictionnaire avec l'artiste comme chaîne
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
            "updated_at": detection.track.updated_at,
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
            "updated_at": detection.station.updated_at,
        },
        "detected_at": detection.detected_at,
        "confidence": detection.confidence,
        "play_duration": detection.play_duration,
    }

    return detection_dict


@router.delete("/{detection_id}")
async def delete_detection(
    detection_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """Delete a specific detection."""
    detection = db.query(TrackDetection).filter(TrackDetection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    db.delete(detection)
    db.commit()

    return {"message": "Detection deleted successfully"}
