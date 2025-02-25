from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from ..database import get_db
from ..models import TrackDetection, Track, RadioStation, StationStatus
from ..schemas.base import DetectionCreate, DetectionResponse, TrackResponse
from ..core.security import get_current_user
from ..utils.websocket import broadcast_track_detection
from ..detection.audio_processor.core import AudioProcessor
import logging

router = APIRouter(prefix="/api/detections", tags=["detections"])

class TrackInfo(BaseModel):
    title: str
    artist: str
    isrc: Optional[str]
    label: Optional[str]
    fingerprint: Optional[str]

class DetectionResponse(BaseModel):
    id: int
    station_id: int
    track_id: int
    confidence: float
    detected_at: datetime
    play_duration: str
    track: TrackInfo

    class Config:
        orm_mode = True

@router.get("/", response_model=List[DetectionResponse])
async def get_detections(
    skip: int = 0,
    limit: int = 100,
    station_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Récupère la liste des détections."""
    query = db.query(TrackDetection)
    
    if station_id:
        query = query.filter(TrackDetection.station_id == station_id)
    if start_date:
        query = query.filter(TrackDetection.detection_time >= start_date)
    if end_date:
        query = query.filter(TrackDetection.detection_time <= end_date)
    
    detections = query.order_by(TrackDetection.detection_time.desc()).offset(skip).limit(limit).all()
    return detections

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

@router.get("/{detection_id}", response_model=DetectionResponse)
async def get_detection(
    detection_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Récupère les détails d'une détection."""
    detection = db.query(TrackDetection).filter(TrackDetection.id == detection_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    return detection

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