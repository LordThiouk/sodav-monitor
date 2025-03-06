"""
Music detection module for SODAV Monitor.

This module provides the main entry point for music detection.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import numpy as np

from backend.models.models import RadioStation, Track, Artist, TrackDetection
from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.external.musicbrainz_recognizer import MusicBrainzRecognizer

# Configure logging
logger = logging.getLogger(__name__)

class MusicDetector:
    """
    Main class for music detection.
    
    This class provides methods for detecting music from radio stations.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the MusicDetector with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.audio_processor = AudioProcessor(db_session)
        self.stream_handler = StreamHandler()
        self.track_manager = TrackManager(db_session)
        self.musicbrainz_recognizer = MusicBrainzRecognizer(db_session)
        
        # Configure detection parameters
        self.sample_duration = 10  # seconds
        self.min_confidence = 0.6
        self.max_concurrent_stations = 5
    
    async def detect_music_from_station(self, station_id: int) -> Dict[str, Any]:
        """
        Detect music from a radio station.
        
        Args:
            station_id: ID of the radio station
            
        Returns:
            Dictionary with detection results
        """
        try:
            # Get station from database
            station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            
            if not station:
                logger.error(f"Station with ID {station_id} not found")
                return {
                    "status": "error",
                    "message": f"Station with ID {station_id} not found"
                }
            
            if not station.is_active:
                logger.warning(f"Station {station.name} is not active")
                return {
                    "status": "error",
                    "message": f"Station {station.name} is not active"
                }
            
            # Get audio data from stream
            logger.info(f"Getting audio data from {station.name} ({station.stream_url})")
            audio_data = await self.stream_handler.get_audio_data(station.stream_url)
            
            if audio_data is None or len(audio_data) == 0:
                logger.error(f"Failed to get audio data from {station.name}")
                return {
                    "status": "error",
                    "message": f"Failed to get audio data from {station.name}"
                }
            
            # Process audio data
            logger.info(f"Processing audio data from {station.name}")
            result = await self.audio_processor.process_stream(audio_data)
            
            if result.get("type") == "speech":
                logger.info(f"Speech detected on {station.name}")
                return {
                    "status": "success",
                    "message": f"Speech detected on {station.name}",
                    "details": {
                        "station_id": station_id,
                        "station_name": station.name,
                        "type": "speech",
                        "confidence": result.get("confidence", 0.0)
                    }
                }
            
            if result.get("type") == "music":
                logger.info(f"Music detected on {station.name}: {result.get('track', {}).get('title')} by {result.get('track', {}).get('artist')}")
                return {
                    "status": "success",
                    "message": f"Music detected on {station.name}",
                    "details": {
                        "station_id": station_id,
                        "station_name": station.name,
                        "type": "music",
                        "source": result.get("source"),
                        "confidence": result.get("confidence", 0.0),
                        "track": result.get("track", {})
                    }
                }
            
            logger.warning(f"Unknown content detected on {station.name}")
            return {
                "status": "success",
                "message": f"Unknown content detected on {station.name}",
                "details": {
                    "station_id": station_id,
                    "station_name": station.name,
                    "type": "unknown",
                    "confidence": result.get("confidence", 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error detecting music from station {station_id}: {e}")
            return {
                "status": "error",
                "message": f"Error detecting music from station {station_id}: {str(e)}"
            }
    
    async def detect_music_from_all_stations(self, max_stations: Optional[int] = None) -> Dict[str, Any]:
        """
        Detect music from all active stations.
        
        Args:
            max_stations: Maximum number of stations to process
            
        Returns:
            Dictionary with detection results
        """
        try:
            # Get active stations from database
            stations = self.db_session.query(RadioStation).filter(
                RadioStation.is_active == True
            ).all()
            
            if not stations:
                logger.warning("No active stations found")
                return {
                    "status": "success",
                    "message": "No active stations found",
                    "details": {
                        "total_stations": 0,
                        "processed_stations": 0,
                        "results": []
                    }
                }
            
            # Limit number of stations if specified
            if max_stations is not None and max_stations > 0:
                stations = stations[:max_stations]
            
            # Process stations concurrently
            logger.info(f"Processing {len(stations)} stations concurrently")
            tasks = [self.detect_music_from_station(station.id) for station in stations]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing station {stations[i].name}: {result}")
                    processed_results.append({
                        "station_id": stations[i].id,
                        "station_name": stations[i].name,
                        "status": "error",
                        "message": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return {
                "status": "success",
                "message": f"Processed {len(stations)} stations",
                "details": {
                    "total_stations": len(stations),
                    "processed_stations": len(processed_results),
                    "results": processed_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error detecting music from all stations: {e}")
            return {
                "status": "error",
                "message": f"Error detecting music from all stations: {str(e)}"
            }
    
    async def process_audio_file(self, audio_data: bytes, station_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Process audio data from a file.
        
        Args:
            audio_data: Raw audio data as bytes
            station_id: Optional station ID
            
        Returns:
            Dictionary with detection results
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            
            # Process audio data
            logger.info("Processing audio file")
            result = await self.audio_processor.process_stream(audio_array)
            
            if result.get("type") == "speech":
                logger.info("Speech detected in audio file")
                return {
                    "status": "success",
                    "message": "Speech detected in audio file",
                    "details": {
                        "type": "speech",
                        "confidence": result.get("confidence", 0.0)
                    }
                }
            
            if result.get("type") == "music":
                logger.info(f"Music detected in audio file: {result.get('track', {}).get('title')} by {result.get('track', {}).get('artist')}")
                return {
                    "status": "success",
                    "message": "Music detected in audio file",
                    "details": {
                        "type": "music",
                        "source": result.get("source"),
                        "confidence": result.get("confidence", 0.0),
                        "track": result.get("track", {})
                    }
                }
            
            logger.warning("Unknown content detected in audio file")
            return {
                "status": "success",
                "message": "Unknown content detected in audio file",
                "details": {
                    "type": "unknown",
                    "confidence": result.get("confidence", 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            return {
                "status": "error",
                "message": f"Error processing audio file: {str(e)}"
            } 