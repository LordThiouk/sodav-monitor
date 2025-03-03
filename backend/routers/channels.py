from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from fastapi import BackgroundTasks
import asyncio
import json
import redis

from backend.models.database import get_db
from ..models import RadioStation, StationStatus, Track, TrackDetection, Artist
from ..utils.radio.manager import RadioManager
from ..utils.streams.websocket import broadcast_station_update
from ..utils.streams.stream_checker import StreamChecker
import logging
from ..schemas.base import StationCreate, StationUpdate, StationResponse, StationStatusResponse
from ..core.security import get_current_user
from ..core.config import get_settings
from backend.core.config.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/channels",
    tags=["channels"],
    responses={
        404: {"description": "Station not found"},
        500: {"description": "Internal server error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"}
    }
)

# Initialize StreamChecker
stream_checker = StreamChecker()

class StationResponse(BaseModel):
    """Response model for radio station data."""
    id: int = Field(..., description="Unique identifier for the station")
    name: str = Field(..., description="Name of the radio station")
    stream_url: str = Field(..., description="URL of the radio stream")
    country: Optional[str] = Field(None, description="Country code of the station")
    language: Optional[str] = Field(None, description="Language code(s) of the station")
    is_active: bool = Field(..., description="Whether the station is currently active")
    last_checked: datetime = Field(..., description="Last time the station was checked")
    status: str = Field(..., description="Current status of the station")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Radio Senegal",
                "stream_url": "http://stream.example.com/radio",
                "country": "SN",
                "language": "fr",
                "is_active": True,
                "last_checked": "2024-03-01T12:00:00",
                "status": "active"
            }
        }

class StationStats(BaseModel):
    total_stations: int
    active_stations: int
    inactive_stations: int
    languages: Dict[str, int]

class TrackInfo(BaseModel):
    """Model for track information."""
    title: str = Field(..., description="Title of the track")
    artist: str = Field(..., description="Artist name")
    isrc: Optional[str] = Field(None, description="International Standard Recording Code")
    label: Optional[str] = Field(None, description="Record label")
    fingerprint: Optional[str] = Field(None, description="Audio fingerprint")

class DetectionResponse(BaseModel):
    """Model for detection response."""
    id: int = Field(..., description="Detection ID")
    station_id: int = Field(..., description="Station ID")
    track_id: int = Field(..., description="Track ID")
    confidence: float = Field(..., description="Detection confidence")
    detected_at: datetime = Field(..., description="Detection timestamp")
    play_duration: str = Field(..., description="Play duration")
    track: TrackInfo = Field(..., description="Track information")

class StationInfo(BaseModel):
    """Model for station information."""
    id: int = Field(..., description="Station ID")
    name: str = Field(..., description="Station name")
    country: Optional[str] = Field(None, description="Station country")
    language: Optional[str] = Field(None, description="Station language")
    status: str = Field(..., description="Station status")
    total_detections: int = Field(..., description="Total number of detections")
    average_confidence: float = Field(..., description="Average detection confidence")
    total_play_duration: str = Field(..., description="Total play duration")

class DetectionsResponse(BaseModel):
    """Model for detections list response."""
    detections: List[DetectionResponse] = Field(..., description="List of detections")
    total: int = Field(..., description="Total number of detections")
    page: int = Field(..., description="Current page number")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    labels: List[str] = Field(..., description="List of unique labels")
    station: StationInfo = Field(..., description="Station information")

class StationStatsResponse(BaseModel):
    """Response model for station statistics."""
    total_stations: int = Field(..., description="Total number of stations")
    active_stations: int = Field(..., description="Number of active stations")
    inactive_stations: int = Field(..., description="Number of inactive stations")
    languages: Dict[str, int] = Field(default_factory=dict, description="Count of stations by language")

@router.get(
    "/",
    response_model=List[StationResponse],
    summary="Get All Radio Stations",
    description="Retrieve a list of all radio stations with optional filtering.",
    responses={
        200: {
            "description": "List of radio stations",
            "content": {
                "application/json": {
                    "example": [{
                        "id": 1,
                        "name": "Radio Senegal",
                        "stream_url": "http://stream.example.com/radio",
                        "country": "SN",
                        "language": "fr",
                        "is_active": True,
                        "last_checked": "2024-03-01T12:00:00",
                        "status": "active"
                    }]
                }
            }
        }
    }
)
async def get_stations(
    country: Optional[str] = Query(None, description="Filter by country code"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    status: Optional[str] = Query(None, description="Filter by station status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[StationResponse]:
    """
    Retrieve a list of radio stations with optional filtering.
    
    - **country**: Optional country code filter
    - **language**: Optional language code filter
    - **status**: Optional status filter
    - **is_active**: Optional active status filter
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (pagination)
    """
    query = db.query(RadioStation)
    
    if country:
        query = query.filter(RadioStation.country == country)
    if language:
        query = query.filter(RadioStation.language == language)
    if status:
        query = query.filter(RadioStation.status == status)
    if is_active is not None:
        query = query.filter(RadioStation.is_active == is_active)
        
    stations = query.offset(skip).limit(limit).all()
    return stations

@router.post("/", response_model=StationResponse)
async def create_station(
    station: StationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Crée une nouvelle station radio."""
    db_station = RadioStation(**station.dict())
    try:
        db.add(db_station)
        db.commit()
        db.refresh(db_station)
        
        # Vérifie la disponibilité du flux en arrière-plan
        background_tasks.add_task(stream_checker.check_stream_availability, db_station.stream_url)
        
        return db_station
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{station_id}", response_model=StationResponse)
async def get_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Récupère les détails d'une station radio."""
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station

@router.put("/{station_id}", response_model=StationResponse)
async def update_station(
    station_id: int,
    station_update: StationUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Met à jour une station radio."""
    db_station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not db_station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    for field, value in station_update.dict(exclude_unset=True).items():
        setattr(db_station, field, value)
    
    try:
        db.commit()
        db.refresh(db_station)
        
        # Si l'URL du flux a changé, vérifie sa disponibilité
        if station_update.stream_url:
            background_tasks.add_task(stream_checker.check_stream_availability, db_station.stream_url)
        
        return db_station
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{station_id}")
async def delete_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Supprime une station radio."""
    db_station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not db_station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    try:
        db.delete(db_station)
        db.commit()
        return {"message": "Station deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{station_id}/status", response_model=StationStatusResponse)
async def get_station_status(
    station_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Récupère le statut d'une station radio."""
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    status = db.query(StationStatus).filter(
        StationStatus.station_id == station_id
    ).order_by(StationStatus.timestamp.desc()).first()
    
    if not status:
        return StationStatusResponse(
            station_id=station_id,
            status="unknown",
            last_check=datetime.utcnow(),
            error=None
        )
    
    return status

@router.post("/{station_id}/check")
async def check_station(
    station_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Vérifie la disponibilité d'une station radio."""
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    background_tasks.add_task(stream_checker.check_stream_availability, station.stream_url)
    return {"message": "Station check initiated"}

@router.post("/refresh")
async def refresh_channels(db: Session = Depends(get_db)):
    """Refresh the list of radio channels"""
    try:
        manager = RadioManager(db)
        result = manager.update_senegal_stations()
        
        # Broadcast updates for each modified station
        for station in db.query(RadioStation).all():
            await broadcast_station_update({
                "id": station.id,
                "name": station.name,
                "status": station.status.value if station.status else "inactive",
                "is_active": station.is_active,
                "last_checked": station.last_checked.isoformat() if station.last_checked else None,
                "last_detection_time": station.last_detection_time.isoformat() if station.last_detection_time else None,
                "stream_url": station.stream_url,
                "country": station.country,
                "language": station.language,
                "total_play_time": f"{int(station.total_play_time.total_seconds() // 3600):01d}:{int((station.total_play_time.total_seconds() % 3600) // 60):02d}:{int(station.total_play_time.total_seconds() % 60):02d}" if station.total_play_time else "0:00:00"
            })
        
        return {
            "status": "success",
            "message": "Channels refreshed successfully",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch-senegal")
def fetch_senegal_stations(db: Session = Depends(get_db)):
    """Fetch and save Senegalese radio stations"""
    try:
        # Initialize RadioManager without audio processor for station fetching only
        manager = RadioManager(db, audio_processor=None)
        result = manager.update_senegal_stations()
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Successfully fetched Senegalese stations",
                "count": result.get("new_count", 0) + result.get("updated_count", 0)
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error fetching Senegalese stations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{channel_id}/refresh")
async def refresh_channel(channel_id: int, db: Session = Depends(get_db)):
    """Refresh a specific channel"""
    try:
        station = db.query(RadioStation).filter(RadioStation.id == channel_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Channel not found")
            
        manager = RadioManager(db)
        result = manager.update_station(station)
        
        # Broadcast the station update
        await broadcast_station_update({
            "id": station.id,
            "name": station.name,
            "status": station.status.value if station.status else "inactive",
            "is_active": station.is_active,
            "last_checked": station.last_checked.isoformat() if station.last_checked else None,
            "last_detection_time": station.last_detection_time.isoformat() if station.last_detection_time else None,
            "stream_url": station.stream_url,
            "country": station.country,
            "language": station.language,
            "total_play_time": f"{int(station.total_play_time.total_seconds() // 3600):01d}:{int((station.total_play_time.total_seconds() % 3600) // 60):02d}:{int(station.total_play_time.total_seconds() % 60):02d}" if station.total_play_time else "0:00:00"
        })
        
        return {
            "status": "success",
            "message": f"Channel {channel_id} refreshed successfully",
            "details": result
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-music")
async def detect_music_all_channels(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    max_stations: int = Query(default=5, description="Maximum number of stations to process simultaneously")
):
    """Detect music on all active radio channels"""
    try:
        logger.info("Starting music detection for all active channels")
        
        # Get all active stations
        stations = db.query(RadioStation).filter(
            RadioStation.status == StationStatus.active,
            RadioStation.is_active == True
        ).all()
        
        if not stations:
            logger.warning("No active stations found")
            return {
                "status": "success",
                "message": "No active stations to process",
                "details": {
                    "total_stations": 0,
                    "processed_stations": 0,
                    "status": "completed"
                }
            }
        
        # Get RadioManager from app state
        manager = request.app.state.radio_manager
        if not manager:
            raise HTTPException(
                status_code=500,
                detail="RadioManager not initialized. Please check server configuration."
            )
        
        # Verify audio processor is available
        if not hasattr(manager, 'audio_processor') or not manager.audio_processor:
            raise HTTPException(
                status_code=500,
                detail="Audio processor not initialized. Please check server configuration."
            )
        
        async def process_stations():
            """Background task to process stations"""
            try:
                logger.info(f"Processing {len(stations)} active stations")
                results = []
                
                # Create a semaphore to limit concurrent processing
                sem = asyncio.Semaphore(max_stations)
                
                async def process_station(station):
                    async with sem:
                        try:
                            result = await manager.detect_music(station.id)
                            results.append({
                                "station_id": station.id,
                                "station_name": station.name,
                                "status": "success",
                                "detections": result.get("detections", [])
                            })
                        except Exception as e:
                            logger.error(f"Error processing station {station.name}: {str(e)}")
                            results.append({
                                "station_id": station.id,
                                "station_name": station.name,
                                "status": "error",
                                "error": str(e)
                            })
                
                # Create tasks for all stations
                tasks = [process_station(station) for station in stations]
                await asyncio.gather(*tasks)
                
                logger.info(f"Completed processing {len(stations)} stations")
                return results
                
            except Exception as e:
                logger.error(f"Error in background processing: {str(e)}")
                raise
        
        # Add the background task
        background_tasks.add_task(process_stations)
        
        return {
            "status": "success",
            "message": f"Started processing {len(stations)} stations in background",
            "details": {
                "total_stations": len(stations),
                "status": "processing",
                "max_concurrent": max_stations
            }
        }
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in music detection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, StationStatsResponse])
def get_channel_stats(db: Session = Depends(get_db)):
    """Get channel statistics"""
    try:
        stations = db.query(RadioStation).all()
        
        total_stations = len(stations)
        active_stations = len([s for s in stations if s.status == "active"])
        inactive_stations = total_stations - active_stations
        
        languages = {}
        for station in stations:
            if station.language:
                for lang in station.language.split(','):
                    lang = lang.strip()
                    languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "stats": StationStatsResponse(
                total_stations=total_stations,
                active_stations=active_stations,
                inactive_stations=inactive_stations,
                languages=languages
            )
        }
        
    except Exception as e:
        logger.error(f"Error getting channel stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{station_id}/stats", response_model=Dict)
def get_station_stats(station_id: int, db: Session = Depends(get_db)):
    """Get detailed statistics for a specific radio station"""
    try:
        logger.info(f"Getting stats for station {station_id}")
        
        # Verify station exists
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            logger.warning(f"Station {station_id} not found")
            raise HTTPException(status_code=404, detail="Station not found")
            
        logger.info(f"Found station: {station.name}")
            
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Calculate total play time with NULL handling
        total_play_time = db.query(func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0))).filter(
            TrackDetection.station_id == station_id
        ).scalar() or timedelta(seconds=0)
        
        logger.info(f"Total play time: {total_play_time}")
        
        # Get detection counts for different time periods
        detections_24h = db.query(func.count(TrackDetection.id)).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= last_24h
        ).scalar() or 0
        
        detections_7d = db.query(func.count(TrackDetection.id)).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= last_7d
        ).scalar() or 0
        
        detections_30d = db.query(func.count(TrackDetection.id)).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= last_30d
        ).scalar() or 0
        
        logger.info(f"Detection counts - 24h: {detections_24h}, 7d: {detections_7d}, 30d: {detections_30d}")
        
        # Get hourly detection counts
        try:
            hourly_detections = db.query(
                func.date_trunc('hour', TrackDetection.detected_at).label('hour'),
                func.count(TrackDetection.id).label('count'),
                func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0)).label('duration')
            ).filter(
                TrackDetection.station_id == station_id,
                TrackDetection.detected_at >= last_24h
            ).group_by(
                'hour'
            ).order_by(
                'hour'
            ).all()
            
            logger.info(f"Found {len(hourly_detections)} hourly detection records")
            
        except Exception as hourly_error:
            logger.error(f"Error getting hourly detections: {str(hourly_error)}")
            hourly_detections = []

        # Calculate metrics with NULL handling
        total_detections = db.query(func.count(TrackDetection.id)).filter(
            TrackDetection.station_id == station_id
        ).scalar() or 0
        
        # Calculate uptime percentage based on detections in last 24h
        total_24h_play_time = db.query(func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0))).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= last_24h
        ).scalar() or timedelta(0)

        # Calculate percentage (24h = 86400 seconds)
        play_time_seconds = total_24h_play_time.total_seconds()
        uptime_percentage = (play_time_seconds / 86400) * 100

        uptime_percentage = min(100, round(uptime_percentage, 2))  # Cap at 100% and round to 2 decimals
        
        avg_duration = total_play_time / total_detections if total_detections > 0 else timedelta(0)
        
        # Format response
        return {
            "station_id": station.id,
            "name": station.name,
            "status": station.status.value if station.status else "inactive",
            "total_detections": total_detections,
            "detections_24h": detections_24h,
            "detections_7d": detections_7d,
            "detections_30d": detections_30d,
            "total_play_time": str(total_play_time),
            "average_duration": str(avg_duration),
            "uptime_percentage": uptime_percentage,
            "hourly_detections": [
                {
                    "hour": detection.hour.isoformat(),
                    "count": detection.count,
                    "duration": str(detection.duration)
                }
                for detection in hourly_detections
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting station stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting station stats: {str(e)}"
        )

@router.get("/{station_id}/detections", response_model=DetectionsResponse)
async def get_channel_detections(
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
        logger.info(f"Getting detections for station {station_id}, page {page}, limit {limit}")
        
        # Verify station exists and is active
        station = db.query(RadioStation).filter(
            RadioStation.id == station_id
        ).first()
        
        if not station:
            logger.warning(f"Station {station_id} not found")
            raise HTTPException(status_code=404, detail="Station not found")
            
        logger.info(f"Found station: {station.name}")

        # Calculate offset
        offset = (page - 1) * limit
        logger.info(f"Calculated offset: {offset}")

        try:
            # Base query with eager loading
            query = db.query(TrackDetection).options(
                joinedload(TrackDetection.track).joinedload(Track.artist)
            ).filter(
                TrackDetection.station_id == station_id
            )
            
            # Apply search filter if provided
            if search:
                search = f"%{search.lower()}%"
                logger.info(f"Applying search filter: {search}")
                query = query.join(Track).join(Artist).filter(
                    or_(
                        func.lower(Track.title).like(search),
                        func.lower(Artist.name).like(search),
                        func.lower(Track.isrc).like(search) if Track.isrc else False
                    )
                )

            # Apply label filter if provided
            if label and label != "All Labels":
                logger.info(f"Applying label filter: {label}")
                query = query.join(Track).filter(Track.label == label)

            # Get total count for pagination
            total_count = query.count()
            logger.info(f"Total count: {total_count}")

            # Get detections with pagination
            detections = query.order_by(
                desc(TrackDetection.detected_at)
            ).offset(offset).limit(limit).all()
            logger.info(f"Retrieved {len(detections)} detections")

            # Get unique labels for filtering
            labels = db.query(Track.label).distinct().filter(
                Track.label.isnot(None)
            ).all()
            unique_labels = [label[0] for label in labels if label[0]]
            logger.info(f"Found {len(unique_labels)} unique labels")

            # Calculate average confidence
            avg_confidence = db.query(func.avg(TrackDetection.confidence)).filter(
                TrackDetection.station_id == station_id
            ).scalar() or 0.0

            # Format response
            detection_list = []
            for detection in detections:
                try:
                    if not detection.track:
                        logger.warning(f"Detection {detection.id} has no track")
                        continue
                        
                    track = detection.track
                    artist = track.artist if track else None
                    
                    if not artist:
                        logger.warning(f"Track {track.id} has no artist")
                        continue
                        
                    detection_dict = DetectionResponse(
                        id=detection.id,
                        station_id=detection.station_id,
                        track_id=detection.track_id,
                        confidence=detection.confidence,
                        detected_at=detection.detected_at,
                        play_duration=str(detection.play_duration) if detection.play_duration else "0:00:00",
                        track=TrackInfo(
                            title=track.title,
                            artist=artist.name,
                            isrc=track.isrc or "",
                            label=track.label or "",
                            fingerprint=track.fingerprint or ""
                        )
                    )
                    detection_list.append(detection_dict)
                except Exception as e:
                    logger.error(f"Error formatting detection {detection.id}: {str(e)}")
                    continue

            # Get station info for response
            station_info = StationInfo(
                id=station.id,
                name=station.name,
                country=station.country,
                language=station.language,
                status=station.status.value if station.status else "inactive",
                total_detections=total_count,
                average_confidence=round(avg_confidence, 2),
                total_play_duration=str(station.total_play_time) if station.total_play_time else "0:00:00"
            )

            response = DetectionsResponse(
                detections=detection_list,
                total=total_count,
                page=page,
                pages=(total_count + limit - 1) // limit,
                has_next=offset + limit < total_count,
                has_prev=page > 1,
                labels=unique_labels,
                station=station_info
            )
            
            logger.info("Successfully formatted response")
            return response

        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting channel detections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{channel_id}/detect-music")
async def detect_music_channel(
    channel_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Detect music on a specific radio channel"""
    try:
        logger.info(f"Starting music detection for channel {channel_id}")
        
        # Get the station
        station = db.query(RadioStation).filter(
            RadioStation.id == channel_id,
            RadioStation.status == "active",
            RadioStation.is_active == True
        ).first()
        
        if not station:
            logger.warning(f"Station {channel_id} not found or not active")
            raise HTTPException(status_code=404, detail="Station not found or not active")
        
        # Get RadioManager from app state
        manager = request.app.state.radio_manager
        if not manager:
            raise HTTPException(
                status_code=500,
                detail="RadioManager not initialized. Please check server configuration."
            )
        
        # Verify audio processor is available
        if not hasattr(manager, 'audio_processor') or not manager.audio_processor:
            raise HTTPException(
                status_code=500,
                detail="Audio processor not initialized. Please check server configuration."
            )
        
        # Process the station
        result = await manager.detect_music(station.id)
        
        # Check for error status
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))
        
        # Prepare response data
        response_data = {
            "status": "success",
            "message": f"Successfully processed station {station.name}",
            "details": {
                "station_id": station.id,
                "station_name": station.name,
                "detections": result.get("detections", [])
            }
        }
        
        # Publish detection update to Redis
        detection_data = {
            "type": "detection_update",
            "data": {
                "station_id": station.id,
                "confidence": result.get("detections", [{}])[0].get("detection", {}).get("confidence", 0.0) if result.get("detections") else 0.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        try:
            # Get Redis client from dependency injection
            redis_client.publish("sodav_monitor:websocket", json.dumps(detection_data))
        except Exception as e:
            logger.error(f"Error publishing to Redis: {str(e)}")
            # Don't fail the request if Redis publish fails
        
        return response_data
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in music detection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))