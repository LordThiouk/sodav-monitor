from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import BackgroundTasks
import asyncio

from database import get_db
from models import RadioStation, StationStatus, Track, TrackDetection
from utils.radio_manager import RadioManager
import logging

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
        orm_mode = True

class StationStats(BaseModel):
    total_stations: int
    active_stations: int
    inactive_stations: int
    languages: Dict[str, int]

@router.get("/", response_model=Dict[str, List[StationResponse]])
def get_channels(db: Session = Depends(get_db)):
    """Get all radio channels"""
    try:
        manager = RadioManager(db)
        stations = manager.get_active_stations()
        
        # Convert stations to dict for proper serialization
        station_list = []
        for station in stations:
            station_dict = {
                "id": station.id,
                "name": station.name,
                "stream_url": station.stream_url,
                "country": station.country,
                "language": station.language,
                "status": station.status,
                "is_active": station.is_active,
                "last_checked": station.last_checked.isoformat() if station.last_checked else None,
                "last_detection_time": station.last_detection_time.isoformat() if station.last_detection_time else None
            }
            station_list.append(station_dict)
        
        return {
            "channels": station_list
        }
        
    except Exception as e:
        logger.error(f"Error getting channels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
def refresh_channels(db: Session = Depends(get_db)):
    """Refresh the list of radio channels"""
    try:
        manager = RadioManager(db)
        result = manager.update_senegal_stations()
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
        manager = RadioManager(db)
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
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{channel_id}/refresh")
def refresh_channel(channel_id: int, db: Session = Depends(get_db)):
    """Refresh a specific channel"""
    try:
        station = db.query(RadioStation).filter(RadioStation.id == channel_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Channel not found")
            
        manager = RadioManager(db)
        result = manager.update_station(station)
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
    background_tasks: BackgroundTasks,
    max_stations: int = Query(default=None, description="Nombre maximum de stations à traiter simultanément"),
    db: Session = Depends(get_db)
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
                    "successful_detections": 0,
                    "failed_detections": 0,
                    "results": []
                }
            }
        
        # Initialize audio processor with custom concurrency limit if specified
        manager = RadioManager(db)
        processor = manager.audio_processor
        if max_stations:
            processor.processing_semaphore = asyncio.Semaphore(max_stations)
        
        # Process all stations in parallel
        logger.info(f"Processing {len(stations)} active stations")
        
        # Lancer la détection en arrière-plan
        background_tasks.add_task(processor.process_all_stations, stations)
        
        return {
            "status": "success",
            "message": f"Started processing {len(stations)} stations in background",
            "details": {
                "total_stations": len(stations),
                "status": "processing",
                "background_task_id": id(background_tasks)
            }
        }
            
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
        # Verify station exists
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
            
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Calculate total play time with NULL handling
        total_play_time = db.query(func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0))).filter(
            TrackDetection.station_id == station_id
        ).scalar() or timedelta(seconds=0)
        
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
        
        # Get top tracks for this station with NULL handling
        top_tracks = db.query(
            Track,
            func.count(TrackDetection.id).label('plays'),
            func.coalesce(func.avg(TrackDetection.confidence), 0.0).label('avg_confidence'),
            func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0)).label('total_duration')
        ).join(
            TrackDetection,
            Track.id == TrackDetection.track_id
        ).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= last_24h
        ).group_by(
            Track.id
        ).order_by(
            desc('plays')
        ).limit(10).all()
        
        # Get top artists for this station with NULL handling
        top_artists = db.query(
            Track.artist,
            func.count(TrackDetection.id).label('plays'),
            func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0)).label('total_duration')
        ).join(
            TrackDetection,
            Track.id == TrackDetection.track_id
        ).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= last_24h
        ).group_by(
            Track.artist
        ).order_by(
            desc('plays')
        ).limit(10).all()
        
        # Get hourly detection counts with SQLite compatible datetime handling
        hourly_detections = db.query(
            func.strftime('%Y-%m-%d %H:00:00', TrackDetection.detected_at).label('hour'),
            func.count(TrackDetection.id).label('count'),
            func.coalesce(func.sum(TrackDetection.play_duration), timedelta(0)).label('duration')
        ).filter(
            TrackDetection.station_id == station_id,
            TrackDetection.detected_at >= last_24h,
            TrackDetection.detected_at.isnot(None)  # Exclude NULL dates
        ).group_by(
            'hour'
        ).order_by(
            'hour'
        ).all()

        # Calculate metrics with NULL handling
        total_detections = detections_24h + detections_7d + detections_30d
        uptime_percentage = (detections_24h / 96) * 100 if detections_24h > 0 else 0  # 96 = 24 hours * 4 (15-min intervals)
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
                    # Parse the SQLite datetime string and convert to ISO format
                    return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S').isoformat()
                except ValueError:
                    return dt
            else:
                return str(dt) if dt is not None else None
        
        return {
            "station": station_data,
            "metrics": {
                "total_play_time": str(total_play_time),
                "detection_count": total_detections,
                "unique_tracks": len(top_tracks),
                "average_track_duration": str(avg_duration),
                "uptime_percentage": round(uptime_percentage, 2)
            },
            "detections": {
                "last_24h": detections_24h,
                "last_7d": detections_7d,
                "last_30d": detections_30d
            },
            "top_tracks": [{
                "title": track.title,
                "artist": track.artist,
                "play_count": plays,
                "play_time": str(total_duration) if total_duration else "00:00:00"
            } for track, plays, avg_confidence, total_duration in top_tracks],
            "top_artists": [{
                "name": artist,
                "play_count": plays,
                "play_time": str(total_duration) if total_duration else "00:00:00"
            } for artist, plays, total_duration in top_artists],
            "hourly_detections": [{
                "hour": safe_datetime_to_iso(hour),
                "count": count,
                "duration": str(duration) if duration else "00:00:00"
            } for hour, count, duration in hourly_detections]
        }
        
    except Exception as e:
        logger.error(f"Error getting station stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{station_id}/detections", response_model=dict)
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
            detection_dict = {
                "id": detection.id,
                "station_id": detection.station_id,
                "track_id": detection.track_id,
                "confidence": detection.confidence,
                "detected_at": detection.detected_at.isoformat(),
                "play_duration": str(detection.play_duration) if detection.play_duration else "0:00:00",
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
        logger.error(f"Error getting channel detections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))