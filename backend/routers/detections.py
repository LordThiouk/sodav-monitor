from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from ..database import get_db
from ..models import TrackDetection, Track, RadioStation, StationStatus
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

@router.get("", response_model=dict)
async def get_detections(
    station_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    label: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get detections for a specific radio station with pagination and filtering
    """
    try:
        # Verify station exists and is active
        station = db.query(RadioStation).filter(
            RadioStation.id == station_id,
            RadioStation.is_active == True,
            RadioStation.status == StationStatus.active
        ).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found or inactive")

        # Calculate offset
        offset = (page - 1) * limit

        # Base query
        query = db.query(TrackDetection).join(
            Track, TrackDetection.track_id == Track.id
        ).filter(
            TrackDetection.station_id == station_id
        )

        # Apply search filter if provided
        if search:
            search = f"%{search.lower()}%"
            query = query.filter(
                (Track.title.ilike(search)) |
                (Track.artist.ilike(search)) |
                (Track.isrc.ilike(search))
            )

        # Apply label filter if provided
        if label and label != "All Labels":
            query = query.filter(Track.label == label)

        # Get total count for pagination
        total_count = query.count()

        # Get detections with pagination
        detections = query.order_by(
            desc(TrackDetection.detected_at)
        ).offset(offset).limit(limit).all()

        # Get unique labels for filtering
        labels = db.query(Track.label).distinct().filter(
            Track.label.isnot(None)
        ).all()
        unique_labels = [label[0] for label in labels if label[0]]

        # Format response
        detection_list = []
        for detection in detections:
            track = detection.track
            
            # Format play_duration to keep only HH:MM:SS
            play_duration_str = "0:00:00"
            if detection.play_duration:
                total_seconds = int(detection.play_duration.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                play_duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            
            detection_dict = {
                "id": detection.id,
                "station_id": detection.station_id,
                "track_id": detection.track_id,
                "confidence": round(detection.confidence, 2),
                "detected_at": detection.detected_at.isoformat(),
                "play_duration": play_duration_str,
                "track": {
                    "title": track.title,
                    "artist": track.artist,
                    "isrc": track.isrc or "",
                    "label": track.label or "",
                    "fingerprint": track.fingerprint or ""
                }
            }
            detection_list.append(detection_dict)

        # Get station info for response
        station_info = {
            "id": station.id,
            "name": station.name,
            "country": station.country,
            "language": station.language,
            "status": station.status.value if station.status else "inactive",
            "total_detections": total_count,
            "average_confidence": 0.0,  # Calculate this if needed
            "total_play_duration": str(station.total_play_time) if station.total_play_time else "0:00:00"
        }

        return {
            "detections": detection_list,
            "total": total_count,
            "page": page,
            "pages": (total_count + limit - 1) // limit,
            "has_next": offset + limit < total_count,
            "has_prev": page > 1,
            "labels": unique_labels,
            "station": station_info
        }

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

@router.get("/{detection_id}", response_model=DetectionResponse)
async def get_detection(detection_id: int, db: Session = Depends(get_db)):
    """
    Get a specific detection by ID
    """
    try:
        detection = db.query(TrackDetection).filter(
            TrackDetection.id == detection_id
        ).first()

        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        # Format play_duration to keep only HH:MM:SS
        play_duration_str = "0:00:00"
        if detection.play_duration:
            total_seconds = int(detection.play_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            play_duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"

        # Format the response to match the expected schema
        response = {
            "id": detection.id,
            "station_id": detection.station_id,
            "track_id": detection.track_id,
            "confidence": round(detection.confidence, 2),
            "detected_at": detection.detected_at,
            "play_duration": play_duration_str,
            "track": {
                "title": detection.track.title,
                "artist": detection.track.artist,
                "isrc": detection.track.isrc or "",
                "label": detection.track.label or "",
                "fingerprint": detection.track.fingerprint or ""
            }
        }

        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 