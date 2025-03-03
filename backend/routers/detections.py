from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status, Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
from backend.models.database import get_db
from ..models.models import TrackDetection, Track, RadioStation, StationStatus, Artist
from ..schemas.base import DetectionCreate, DetectionResponse, TrackResponse, StationResponse
from ..core.security import get_current_user
from ..utils.streams.websocket import broadcast_track_detection
from ..detection.audio_processor.core import AudioProcessor
from ..core.config import get_settings
import logging
from sqlalchemy import or_, func
import numpy as np

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

logger = logging.getLogger(__name__)

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
            joinedload(TrackDetection.track).joinedload(Track.artist),
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
                track=TrackResponse(
                    id=detection.track.id,
                    title=detection.track.title,
                    artist=detection.track.artist.name,
                    isrc=detection.track.isrc or "",
                    label=detection.track.label or "",
                    fingerprint=detection.track.fingerprint or "",
                    created_at=detection.track.created_at or datetime.utcnow(),
                    updated_at=detection.track.updated_at or datetime.utcnow()
                ),
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

@router.get("/search/", response_model=List[DetectionResponse])
async def search_detections(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Search for detections by track title, artist name, or ISRC."""
    try:
        logger.info(f"Searching detections with query: {query}")
        search_query = f"%{query.lower()}%"
        
        detections = db.query(TrackDetection).options(
            joinedload(TrackDetection.track).joinedload(Track.artist),
            joinedload(TrackDetection.station)
        ).join(Track).join(Artist).filter(
            or_(
                func.lower(Track.title).like(search_query),
                func.lower(Artist.name).like(search_query),
                func.lower(Track.isrc).like(search_query) if Track.isrc else False
            )
        ).order_by(
            desc(TrackDetection.detected_at)
        ).offset(skip).limit(limit).all()
        
        if not detections:
            return []
            
        return [
            DetectionResponse(
                id=d.id,
                track=TrackResponse(
                    id=d.track.id,
                    title=d.track.title,
                    artist=d.track.artist.name,
                    isrc=d.track.isrc or "",
                    label=d.track.label or "",
                    fingerprint=d.track.fingerprint or "",
                    created_at=d.track.created_at or datetime.utcnow(),
                    updated_at=d.track.updated_at or datetime.utcnow()
                ),
                station=StationResponse(
                    id=d.station.id,
                    name=d.station.name,
                    stream_url=d.station.stream_url or "http://test.stream/audio",
                    region=d.station.region or "",
                    language=d.station.language or "",
                    type=d.station.type or "radio",
                    status="active",
                    is_active=True,
                    last_checked=d.station.last_check or datetime.utcnow(),
                    created_at=d.station.created_at or datetime.utcnow(),
                    updated_at=d.station.updated_at or datetime.utcnow()
                ),
                detected_at=d.detected_at or datetime.utcnow(),
                confidence=d.confidence or 0.0,
                play_duration=d.play_duration or timedelta(seconds=0)
            )
            for d in detections
            if d.track and d.station and d.track.artist
        ]
        
    except Exception as e:
        logger.error(f"Error searching detections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching detections: {str(e)}"
        )

@router.get("/{detection_id}", response_model=DetectionResponse)
async def get_detection(
    detection_id: int = Path(..., description="The ID of the detection to retrieve"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific detection by ID."""
    try:
        detection = db.query(TrackDetection).options(
            joinedload(TrackDetection.track).joinedload(Track.artist),
            joinedload(TrackDetection.station)
        ).filter(TrackDetection.id == detection_id).first()
        
        if not detection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection with ID {detection_id} not found"
            )
            
        return DetectionResponse(
            id=detection.id,
            track=TrackResponse(
                id=detection.track.id,
                title=detection.track.title,
                artist=detection.track.artist.name,
                isrc=detection.track.isrc or "",
                label=detection.track.label or "",
                fingerprint=detection.track.fingerprint or "",
                created_at=detection.track.created_at or datetime.utcnow(),
                updated_at=detection.track.updated_at or datetime.utcnow()
            ),
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
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new detection."""
    try:
        # Verify track and station exist
        track = db.query(Track).options(joinedload(Track.artist)).filter(Track.id == detection.track_id).first()
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Track with ID {detection.track_id} not found"
            )
        
        station = db.query(RadioStation).filter(RadioStation.id == detection.station_id).first()
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station with ID {detection.station_id} not found"
            )
        
        # Convert play_duration to timedelta if it's an integer
        play_duration = detection.play_duration
        if isinstance(play_duration, int):
            play_duration = timedelta(seconds=play_duration)
        
        # Create detection
        new_detection = TrackDetection(
            track_id=detection.track_id,
            station_id=detection.station_id,
            detected_at=detection.detected_at or datetime.utcnow(),
            confidence=detection.confidence,
            play_duration=play_duration,
            fingerprint=detection.fingerprint,
            audio_hash=detection.audio_hash
        )
        db.add(new_detection)
        db.commit()
        db.refresh(new_detection)
        
        return DetectionResponse(
            id=new_detection.id,
            track=TrackResponse(
                id=track.id,
                title=track.title,
                artist=track.artist.name,
                isrc=track.isrc or "",
                label=track.label or "",
                fingerprint=track.fingerprint or "",
                created_at=track.created_at or datetime.utcnow(),
                updated_at=track.updated_at or datetime.utcnow()
            ),
            station=station,
            detected_at=new_detection.detected_at,
            confidence=new_detection.confidence,
            play_duration=new_detection.play_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating detection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating detection: {str(e)}"
        )

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
    """Get detections for a specific station."""
    query = db.query(TrackDetection).options(
        joinedload(TrackDetection.track).joinedload(Track.artist),
        joinedload(TrackDetection.station)
    ).filter(TrackDetection.station_id == station_id)

    if start_date:
        query = query.filter(TrackDetection.detected_at >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detected_at <= end_date)

    detections = query.order_by(TrackDetection.detected_at.desc()).offset(offset).limit(limit).all()

    return [
        DetectionResponse(
            id=detection.id,
            track=TrackResponse(
                id=detection.track.id,
                title=detection.track.title,
                artist=detection.track.artist.name,
                isrc=detection.track.isrc or "",
                label=detection.track.label or "",
                fingerprint=detection.track.fingerprint or "",
                created_at=detection.track.created_at or datetime.utcnow(),
                updated_at=detection.track.updated_at or datetime.utcnow()
            ),
            station=detection.station,
            detected_at=detection.detected_at,
            confidence=detection.confidence,
            play_duration=detection.play_duration
        )
        for detection in detections
    ]

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
    """Get detections for a specific track."""
    query = db.query(TrackDetection).options(
        joinedload(TrackDetection.track).joinedload(Track.artist),
        joinedload(TrackDetection.station)
    ).filter(TrackDetection.track_id == track_id)

    if start_date:
        query = query.filter(TrackDetection.detected_at >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detected_at <= end_date)

    detections = query.order_by(TrackDetection.detected_at.desc()).offset(offset).limit(limit).all()

    return [
        DetectionResponse(
            id=detection.id,
            track=TrackResponse(
                id=detection.track.id,
                title=detection.track.title,
                artist=detection.track.artist.name,
                isrc=detection.track.isrc or "",
                label=detection.track.label or "",
                fingerprint=detection.track.fingerprint or "",
                created_at=detection.track.created_at or datetime.utcnow(),
                updated_at=detection.track.updated_at or datetime.utcnow()
            ),
            station=detection.station,
            detected_at=detection.detected_at,
            confidence=detection.confidence,
            play_duration=detection.play_duration
        )
        for detection in detections
    ]

@router.get("/latest/", response_model=List[DetectionResponse])
async def get_latest_detections(
    limit: int = Query(10, ge=1, le=100, description="Number of detections to return"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the latest detections."""
    detections = db.query(TrackDetection).options(
        joinedload(TrackDetection.track).joinedload(Track.artist),
        joinedload(TrackDetection.station)
    ).order_by(TrackDetection.detected_at.desc()).limit(limit).all()

    return [
        DetectionResponse(
            id=detection.id,
            track=TrackResponse(
                id=detection.track.id,
                title=detection.track.title,
                artist=detection.track.artist.name,
                isrc=detection.track.isrc or "",
                label=detection.track.label or "",
                fingerprint=detection.track.fingerprint or "",
                created_at=detection.track.created_at or datetime.utcnow(),
                updated_at=detection.track.updated_at or datetime.utcnow()
            ),
            station=detection.station,
            detected_at=detection.detected_at,
            confidence=detection.confidence,
            play_duration=detection.play_duration
        )
        for detection in detections
    ]

@router.post("/process")
async def process_audio(
    station_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Process audio from a station."""
    try:
        # Get the station
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station with ID {station_id} not found"
            )

        # Initialize audio processor with db session
        processor = AudioProcessor(db_session=db)
        
        # Create a mock audio data for testing
        audio_data = np.zeros((44100, 2), dtype=np.float32)  # 1 second of stereo audio
        
        # Process audio in background
        background_tasks.add_task(processor.process_stream, audio_data)
        
        return {
            "status": "success",
            "message": f"Started processing audio from station {station.name}"
        }
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audio: {str(e)}"
        )