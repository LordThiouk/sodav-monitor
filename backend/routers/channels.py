from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from models import RadioStation, StationStatus
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
    status: StationStatus
    is_active: bool
    last_checked: Optional[datetime]
    last_detection_time: Optional[datetime]

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
async def detect_music_all_channels(db: Session = Depends(get_db)):
    """Detect music on all active radio channels"""
    try:
        manager = RadioManager(db)
        result = await manager.detect_music_all_stations()
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Successfully detected music on {result['successful_detections']} out of {result['total_stations']} stations",
                "details": result
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error detecting music: {str(e)}")
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