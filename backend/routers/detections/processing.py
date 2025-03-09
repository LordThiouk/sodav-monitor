"""Audio processing functionality for SODAV Monitor.

This module handles audio processing and music detection operations.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
import json
import tempfile
import os
import asyncio

from backend.models.database import get_db
from backend.models.models import TrackDetection, Track, Artist, RadioStation
from backend.utils.auth import get_current_user
from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.detect_music import MusicDetector

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["detections"],
    dependencies=[Depends(get_current_user)]  # Require authentication for all endpoints
)

@router.post("/process")
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    station_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Process an audio file to detect music."""
    # Verify station if provided
    if station_id:
        station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
    
    # Save uploaded file to temporary location
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    try:
        # Write file content
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Process audio in background
        background_tasks.add_task(process_audio_file, temp_file.name, station_id, db)
        
        return {
            "message": "Audio processing started",
            "file_name": file.filename,
            "station_id": station_id,
            "status": "success"
        }
    except Exception as e:
        # Clean up temp file in case of error
        os.unlink(temp_file.name)
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

async def process_audio_file(file_path: str, station_id: Optional[int], db: Session):
    """Process an audio file in the background."""
    try:
        # Initialize audio processor
        processor = AudioProcessor()
        
        # Process audio file
        result = await processor.process_file(file_path)
        
        # Check if music was detected
        if result["type"] == "music":
            # Initialize music detector
            detector = MusicDetector(db)
            
            # Detect music
            detection_result = await detector.detect_music(
                fingerprint=result["fingerprint"],
                audio_data=result["audio_data"],
                station_id=station_id
            )
            
            logger.info(f"Music detection result: {detection_result}")
        else:
            logger.info(f"No music detected in file: {file_path}")
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
    finally:
        # Clean up temp file
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error deleting temp file: {str(e)}")

@router.post("/detect-music")
async def detect_music_on_station(
    background_tasks: BackgroundTasks,
    station_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Detect music on a specific radio station."""
    # Verify station exists
    station = db.query(RadioStation).filter(RadioStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Check if station is active
    if station.status != "active":
        raise HTTPException(status_code=400, detail="Station is not active")
    
    # Initialize music detector
    detector = MusicDetector(db)
    
    # Detect music in background
    background_tasks.add_task(detector.detect_music_from_station, station_id)
    
    return {
        "message": f"Music detection started for station: {station.name}",
        "station_id": station_id,
        "status": "success",
        "details": {
            "station_id": station_id,
            "station_name": station.name
        }
    }

@router.post("/detect-music-all")
async def detect_music_on_all_stations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Detect music on all active radio stations."""
    # Get all active stations
    active_stations = db.query(RadioStation).filter(RadioStation.status == "active").all()
    
    if not active_stations:
        return {
            "message": "No active stations found",
            "stations_count": 0
        }
    
    # Initialize music detector
    detector = MusicDetector(db)
    
    # Start detection for each active station
    station_ids = []
    for station in active_stations:
        background_tasks.add_task(detector.detect_music_from_station, station.id)
        station_ids.append(station.id)
    
    return {
        "message": f"Music detection started for {len(active_stations)} active stations",
        "stations_count": len(active_stations),
        "station_ids": station_ids
    } 