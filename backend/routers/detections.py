from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status, Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
from backend.models.database import get_db
from ..models.models import TrackDetection, Track, RadioStation, StationStatus, Artist
from ..schemas.base import DetectionCreate, DetectionResponse, TrackResponse
from ..core.security import get_current_user
from ..utils.streams.websocket import broadcast_track_detection
from ..detection.audio_processor.core import AudioProcessor
from ..core.config import get_settings
import logging

router = APIRouter(
    prefix="/api/detections",
    tags=["detections"],
    responses={
        404: {"description": "Detection not found"},
        500: {"description": "Internal server error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"}
    }
)

class TrackInfo(BaseModel):
    """Model for track information."""
    title: str = Field(..., description="Title of the track")
    artist: str = Field(..., description="Artist name")
    isrc: Optional[str] = Field(None, description="International Standard Recording Code")
    label: Optional[str] = Field(None, description="Record label")
    fingerprint: Optional[str] = Field(None, description="Audio fingerprint")

    @validator('title', 'artist')
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()

class DetectionFilter(BaseModel):
    """Model for detection filtering parameters."""
    station_id: Optional[int] = Field(None, description="Filter by station ID")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence threshold")

    @validator('end_date')
    def validate_dates(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError("end_date must be after start_date")
        return v

@router.get(
    "/",
    response_model=List[DetectionResponse],
    summary="Get All Detections",
    description="Retrieve a list of all music detections with optional filtering.",
    responses={
        200: {
            "description": "List of detections",
            "content": {
                "application/json": {
                    "example": [{
                        "id": 1,
                        "track_id": 1,
                        "station_id": 1,
                        "detected_at": "2024-03-01T12:00:00",
                        "confidence": 0.95,
                        "play_duration": 180
                    }]
                }
            }
        }
    }
)
async def get_detections(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    filters: DetectionFilter = Depends(),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[DetectionResponse]:
    """
    Retrieve a list of music detections with optional filtering.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (pagination)
    - **filters**: Optional filtering parameters
    """
    try:
        query = db.query(TrackDetection).options(
            joinedload(TrackDetection.track),
            joinedload(TrackDetection.station)
        )
        
        if filters.station_id:
            query = query.filter(TrackDetection.station_id == filters.station_id)
        if filters.start_date:
            query = query.filter(TrackDetection.detected_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(TrackDetection.detected_at <= filters.end_date)
        if filters.confidence_threshold:
            query = query.filter(TrackDetection.confidence >= filters.confidence_threshold)
        
        detections = query.order_by(TrackDetection.detected_at.desc()).offset(skip).limit(limit).all()
        
        if not detections:
            return []
            
        return [
            DetectionResponse(
                id=detection.id,
                track=TrackResponse.from_orm(detection.track),
                station=detection.station,
                detected_at=detection.detected_at,
                confidence=detection.confidence,
                play_duration=detection.play_duration
            )
            for detection in detections
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving detections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving detections"
        )

@router.get(
    "/{detection_id}",
    response_model=DetectionResponse,
    summary="Get Detection by ID",
    description="Retrieve details of a specific music detection.",
    responses={
        404: {"description": "Detection not found"},
        200: {
            "description": "Detection details",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "track_id": 1,
                        "station_id": 1,
                        "detected_at": "2024-03-01T12:00:00",
                        "confidence": 0.95,
                        "play_duration": 180
                    }
                }
            }
        }
    }
)
async def get_detection(
    detection_id: int = Path(..., description="The ID of the detection to retrieve"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DetectionResponse:
    """
    Retrieve details of a specific music detection by its ID.
    
    - **detection_id**: The unique identifier of the detection
    """
    try:
        detection = db.query(TrackDetection).options(
            joinedload(TrackDetection.track),
            joinedload(TrackDetection.station)
        ).filter(TrackDetection.id == detection_id).first()
        
        if not detection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection with ID {detection_id} not found"
            )
            
        return DetectionResponse(
            id=detection.id,
            track=TrackResponse.from_orm(detection.track),
            station=detection.station,
            detected_at=detection.detected_at,
            confidence=detection.confidence,
            play_duration=detection.play_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving detection {detection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving detection"
        )

@router.post("/", response_model=DetectionResponse)
async def create_detection(
    detection: DetectionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Crée une nouvelle détection."""
    # Vérifie si la station existe
    station = db.query(RadioStation).filter(RadioStation.id == detection.station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Vérifie si la piste existe
    track = db.query(Track).filter(Track.id == detection.track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    db_detection = TrackDetection(**detection.dict())
    try:
        db.add(db_detection)
        db.commit()
        db.refresh(db_detection)
        
        # Diffuse la détection via WebSocket
        background_tasks.add_task(
            broadcast_track_detection,
            {
                "detection_id": db_detection.id,
                "track": {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist,
                    "duration": track.duration
                },
                "station": {
                    "id": station.id,
                    "name": station.name
                },
                "confidence": db_detection.confidence,
                "detection_time": db_detection.detection_time.isoformat()
            }
        )
        
        return db_detection
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{detection_id}")
async def delete_detection(
    detection_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Supprime une détection."""
    detection = db.query(TrackDetection).filter(TrackDetection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    try:
        db.delete(detection)
        db.commit()
        return {"message": "Detection deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/station/{station_id}", response_model=List[DetectionResponse])
async def get_station_detections(
    station_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Récupère les détections pour une station spécifique."""
    query = db.query(TrackDetection).filter(TrackDetection.station_id == station_id)
    
    if start_date:
        query = query.filter(TrackDetection.detection_time >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detection_time <= end_date)
    
    detections = query.order_by(TrackDetection.detection_time.desc()).offset(offset).limit(limit).all()
    if not detections:
        raise HTTPException(status_code=404, detail="No detections found for this station")
    return detections

@router.get("/track/{track_id}", response_model=List[DetectionResponse])
async def get_track_detections(
    track_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Récupère les détections pour une piste spécifique."""
    query = db.query(TrackDetection).filter(TrackDetection.track_id == track_id)
    
    if start_date:
        query = query.filter(TrackDetection.detection_time >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detection_time <= end_date)
    
    detections = query.order_by(TrackDetection.detection_time.desc()).offset(offset).limit(limit).all()
    if not detections:
        raise HTTPException(status_code=404, detail="No detections found for this track")
    return detections

@router.post("/process")
async def process_audio(
    station_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lance le traitement audio pour une station."""
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    try:
        processor = AudioProcessor(db)
        background_tasks.add_task(processor.process_stream, station.stream_url)
        return {"message": "Audio processing started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest", response_model=dict)
async def get_latest_detections(
    limit: int = Query(10, ge=1, le=100, description="Number of detections to return"),
    db: Session = Depends(get_db)
):
    """Get latest detections across all stations"""
    try:
        # Get latest detections with station and track info
        query = db.query(TrackDetection).options(
            joinedload(TrackDetection.station),
            joinedload(TrackDetection.track).joinedload(Track.artist)
        ).order_by(desc(TrackDetection.detected_at)).limit(limit)
        
        detections = query.all()
        
        detection_list = []
        for d in detections:
            try:
                track = d.track
                artist = track.artist if track else None
                
                # Format play_duration to keep only HH:MM:SS
                play_duration_str = "0:00:00"
                if d.play_duration:
                    total_seconds = int(d.play_duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    play_duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                
                detection_dict = {
                    "id": d.id,
                    "station_name": d.station.name if d.station else None,
                    "track_title": track.title if track else None,
                    "artist": artist.name if artist else None,
                    "detected_at": d.detected_at.isoformat(),
                    "confidence": round(d.confidence, 2),
                    "play_duration": play_duration_str,
                    "track": {
                        "id": track.id if track else None,
                        "title": track.title if track else None,
                        "artist": artist.name if artist else None,
                        "isrc": track.isrc if track else None,
                        "label": track.label if track else None,
                        "album": track.album if track else None
                    },
                    "station": {
                        "id": d.station.id if d.station else None,
                        "name": d.station.name if d.station else None,
                        "stream_url": d.station.stream_url if d.station else None
                    }
                }
                detection_list.append(detection_dict)
            except Exception as e:
                logger.error(f"Error processing detection {d.id}: {str(e)}")
                continue
        
        return {
            "total": len(detection_list),
            "detections": detection_list
        }
    except Exception as e:
        logger.error(f"Error getting latest detections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 