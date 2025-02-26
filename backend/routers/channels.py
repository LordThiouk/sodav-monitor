from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import BackgroundTasks
import asyncio

from backend.models.database import get_db
from ..models import RadioStation, StationStatus, Track, TrackDetection, Artist
from ..utils.radio_manager import RadioManager
from ..utils.websocket import broadcast_station_update
import logging
from ..schemas.base import StationCreate, StationUpdate, StationResponse, StationStatusResponse
from ..core.security import get_current_user
from ..utils.stream_checker import check_stream_availability
from ..core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channels"])

class StationResponse(BaseModel):
    id: int
    name: str
    stream_url: str
    country: Optional[str]
    language: Optional[str]
    is_active: bool
    last_checked: datetime
    status: str

    class Config:
        from_attributes = True

class StationStats(BaseModel):
    total_stations: int
    active_stations: int
    inactive_stations: int
    languages: Dict[str, int]

class TrackInfo(BaseModel):
    title: str
    artist: str
    isrc: Optional[str] = ""
    label: Optional[str] = ""
    fingerprint: Optional[str] = ""

    class Config:
        from_attributes = True

class DetectionResponse(BaseModel):
    id: int
    station_id: int
    track_id: int
    confidence: float
    detected_at: datetime
    play_duration: str
    track: TrackInfo

    class Config:
        from_attributes = True

class StationInfo(BaseModel):
    id: int
    name: str
    country: Optional[str]
    language: Optional[str]
    status: str
    total_detections: int
    average_confidence: float
    total_play_duration: str

    class Config:
        from_attributes = True

class DetectionsResponse(BaseModel):
    detections: List[DetectionResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool
    labels: List[str]
    station: StationInfo

    class Config:
        from_attributes = True

@router.get("/", response_model=List[StationResponse])
async def get_all_stations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Récupère la liste des stations radio."""
    stations = db.query(RadioStation).offset(skip).limit(limit).all()
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
        background_tasks.add_task(check_stream_availability, db_station.stream_url)
        
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
            background_tasks.add_task(check_stream_availability, db_station.stream_url)
        
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
    
    background_tasks.add_task(check_stream_availability, station.stream_url)
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

@router.get("/stats", response_model=Dict[str, StationStats])
def get_channel_stats(db: Session = Depends(get_db)):
    """Get channel statistics"""
    try:
        stations = db.query(RadioStation).all()
        
        total_stations = len(stations)
        active_stations = len([s for s in stations if s.status == StationStatus.active])
        inactive_stations = total_stations - active_stations
        
        languages = {}
        for station in stations:
            if station.language:
                for lang in station.language.split(','):
                    lang = lang.strip()
                    languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "stats": StationStats(
                total_stations=total_stations,
                active_stations=active_stations,
                inactive_stations=inactive_stations,
                languages=languages
            )
        }
        
    except Exception as e:
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
        
        # Get top tracks for this station with NULL handling
        try:
            top_tracks = db.query(
                Track,
                func.count(TrackDetection.id).label('plays'),
                func.coalesce(func.avg(TrackDetection.confidence), 0.0).label('avg_confidence'),
                func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0)).label('total_duration')
            ).join(
                TrackDetection, Track.id == TrackDetection.track_id
            ).join(
                Artist, Track.artist_id == Artist.id
            ).filter(
                TrackDetection.station_id == station_id,
                TrackDetection.detected_at >= last_24h
            ).group_by(
                Track.id
            ).order_by(
                desc('plays')
            ).limit(10).all()
            
            logger.info(f"Found {len(top_tracks)} top tracks")
            
        except Exception as track_error:
            logger.error(f"Error getting top tracks: {str(track_error)}")
            top_tracks = []
        
        # Get top artists for this station with NULL handling
        try:
            top_artists = db.query(
                Artist,
                func.count(TrackDetection.id).label('plays'),
                func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0)).label('total_duration')
            ).join(
                Track, Track.artist_id == Artist.id
            ).join(
                TrackDetection, TrackDetection.track_id == Track.id
            ).filter(
                TrackDetection.station_id == station_id,
                TrackDetection.detected_at >= last_24h
            ).group_by(
                Artist.id
            ).order_by(
                desc('plays')
            ).limit(10).all()
            
            logger.info(f"Found {len(top_artists)} top artists")
            
        except Exception as artist_error:
            logger.error(f"Error getting top artists: {str(artist_error)}")
            top_artists = []
        
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
        
        # Ensure all datetime objects are converted to ISO format strings
        station_data = {
            "id": station.id,
            "name": station.name,
            "country": station.country or "Non spécifié",
            "language": station.language or "Non spécifié",
            "status": station.status.value if station.status else "inactive",
            "last_checked": station.last_checked.isoformat() if station.last_checked else None,
            "last_detection_time": station.last_detection_time.isoformat() if station.last_detection_time else None
        }
        
        # Helper function to safely convert datetime to ISO format
        def safe_datetime_to_iso(dt):
            if isinstance(dt, datetime):
                return dt.isoformat()
            elif isinstance(dt, str):
                try:
                    return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S').isoformat()
                except ValueError:
                    return dt
            else:
                return str(dt) if dt is not None else None
        
        response = {
            "station": station_data,
            "metrics": {
                "total_play_time": f"{int(total_play_time.total_seconds() // 3600):01d}:{int((total_play_time.total_seconds() % 3600) // 60):02d}:{int(total_play_time.total_seconds() % 60):02d}" if total_play_time else "0:00:00",
                "detection_count": total_detections,
                "unique_tracks": len(top_tracks),
                "average_track_duration": f"{int(avg_duration.total_seconds() // 3600):01d}:{int((avg_duration.total_seconds() % 3600) // 60):02d}:{int(avg_duration.total_seconds() % 60):02d}" if avg_duration else "0:00:00",
                "uptime_percentage": round(uptime_percentage, 2)
            },
            "detections": {
                "last_24h": detections_24h,
                "last_7d": detections_7d,
                "last_30d": detections_30d
            },
            "top_tracks": [{
                "title": track.title,
                "artist": track.artist.name if track.artist else "Unknown",
                "play_count": plays,
                "play_time": f"{int(total_duration.total_seconds() // 3600):01d}:{int((total_duration.total_seconds() % 3600) // 60):02d}:{int(total_duration.total_seconds() % 60):02d}" if total_duration else "0:00:00"
            } for track, plays, avg_confidence, total_duration in top_tracks],
            "top_artists": [{
                "name": artist.name,
                "label": artist.label or "Unknown",
                "country": artist.country or "Unknown",
                "play_count": plays,
                "play_time": f"{int(total_duration.total_seconds() // 3600):01d}:{int((total_duration.total_seconds() % 3600) // 60):02d}:{int(total_duration.total_seconds() % 60):02d}" if total_duration else "0:00:00"
            } for artist, plays, total_duration in top_artists],
            "hourly_detections": [{
                "hour": safe_datetime_to_iso(hour),
                "count": count,
                "duration": f"{int(duration.total_seconds() // 3600):01d}:{int((duration.total_seconds() % 3600) // 60):02d}:{int(duration.total_seconds() % 60):02d}" if duration else "0:00:00"
            } for hour, count, duration in hourly_detections]
        }
        
        logger.info("Successfully generated station stats response")
        return response
        
    except Exception as e:
        logger.error(f"Error getting station stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
                    (Track.title.ilike(search)) |
                    (Artist.name.ilike(search)) |
                    (Track.isrc.ilike(search))
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

            # Format response
            detection_list = []
            for detection in detections:
                try:
                    track = detection.track
                    artist = track.artist if track else None
                    detection_dict = DetectionResponse(
                        id=detection.id,
                        station_id=detection.station_id,
                        track_id=detection.track_id,
                        confidence=detection.confidence,
                        detected_at=detection.detected_at,
                        play_duration=f"{int(detection.play_duration.total_seconds() // 3600):01d}:{int((detection.play_duration.total_seconds() % 3600) // 60):02d}:{int(detection.play_duration.total_seconds() % 60):02d}" if detection.play_duration else "0:00:00",
                        track=TrackInfo(
                            title=track.title if track else "Unknown",
                            artist=artist.name if artist else "Unknown",
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
                average_confidence=0.0,  # Calculate this if needed
                total_play_duration=f"{int(station.total_play_time.total_seconds() // 3600):01d}:{int((station.total_play_time.total_seconds() % 3600) // 60):02d}:{int(station.total_play_time.total_seconds() % 60):02d}" if station.total_play_time else "0:00:00"
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