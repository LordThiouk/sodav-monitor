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
import librosa
import io
import soundfile as sf

from backend.models.models import RadioStation, Track, Artist, TrackDetection
from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.stream_handler import StreamHandler
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.external.musicbrainz_recognizer import MusicBrainzRecognizer
from backend.utils.logging_config import setup_logging, log_with_category

# Configure logging
logger = setup_logging(__name__)

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
        
        log_with_category(logger, "DETECTION", "info", "MusicDetector initialized")
    
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
                log_with_category(logger, "DETECTION", "error", f"Station with ID {station_id} not found")
                return {
                    "status": "error",
                    "message": f"Station with ID {station_id} not found"
                }
            
            if not station.is_active:
                log_with_category(logger, "DETECTION", "warning", f"Station {station.name} is not active")
                return {
                    "status": "error",
                    "message": f"Station {station.name} is not active"
                }
            
            if not station.stream_url:
                log_with_category(logger, "DETECTION", "error", f"Station {station.name} has no stream URL")
                return {
                    "status": "error",
                    "message": f"Station {station.name} has no stream URL"
                }
            
            # Get audio data from stream
            log_with_category(logger, "DETECTION", "info", f"Getting audio data from {station.name} ({station.stream_url})")
            audio_bytes = await self.stream_handler.get_audio_data(station.stream_url)
            
            if audio_bytes is None or len(audio_bytes) == 0:
                log_with_category(logger, "DETECTION", "error", f"[DETECTION] Failed to get audio data from {station.name}")
                return {
                    "status": "error",
                    "message": f"Failed to get audio data from {station.name}"
                }
            
            log_with_category(logger, "DETECTION", "info", f"[DETECTION] Successfully retrieved {len(audio_bytes)} bytes of audio data from {station.name}")
            
            # Process the audio file
            result = await self.process_audio_file(audio_bytes, station_id)
            log_with_category(logger, "DETECTION", "info", f"[DETECTION] Processing result for {station.name}: {result}")
            return result
            
        except Exception as e:
            log_with_category(logger, "DETECTION", "error", f"[DETECTION] Error detecting music from station {station_id}: {str(e)}")
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
                log_with_category(logger, "DETECTION", "warning", "No active stations found")
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
            log_with_category(logger, "DETECTION", "info", f"Processing {len(stations)} stations concurrently")
            tasks = [self.detect_music_from_station(station.id) for station in stations]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    log_with_category(logger, "DETECTION", "error", f"Error processing station {stations[i].name}: {result}")
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
            log_with_category(logger, "DETECTION", "error", f"Error detecting music from all stations: {e}")
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
            import librosa
            import soundfile as sf
            
            # Get station name if station_id is provided
            station_name = None
            station = None
            if station_id:
                station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
                if station:
                    station_name = station.name
            
            # Try to load the audio data using soundfile first
            try:
                with io.BytesIO(audio_data) as audio_file:
                    # Try to determine the file format
                    audio_array, sample_rate = sf.read(audio_file)
                    
                    # Convert to mono if stereo
                    if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
                        audio_array = np.mean(audio_array, axis=1)
            except Exception as sf_error:
                log_with_category(logger, "DETECTION", "warning", f"SoundFile failed to load audio: {sf_error}. Trying librosa...")
                try:
                    # Try librosa as a fallback
                    audio_array, sample_rate = librosa.load(io.BytesIO(audio_data), sr=None)
                except Exception as librosa_error:
                    log_with_category(logger, "DETECTION", "error", f"Both SoundFile and librosa failed to load audio: {librosa_error}")
                    return {
                        "status": "error",
                        "message": f"Failed to load audio data: {librosa_error}"
                    }
            
            # Process audio data
            if station_name:
                log_with_category(logger, "DETECTION", "info", f"Processing audio data from {station_name}")
            else:
                log_with_category(logger, "DETECTION", "info", "Processing audio file")
                
            result = await self.audio_processor.process_stream(audio_array)
            log_with_category(logger, "DETECTION", "info", f"Audio processing result: {result}")
            
            # Prepare response with station info if available
            response = {
                "status": "success",
                "details": {
                    "type": result.get("type", "unknown"),
                    "confidence": result.get("confidence", 0.0)
                }
            }
            
            if station_id:
                response["details"]["station_id"] = station_id
            
            if station_name:
                response["details"]["station_name"] = station_name
            
            # Add type-specific details
            if result.get("type") == "speech":
                if station_name:
                    log_with_category(logger, "DETECTION", "info", f"Speech detected on {station_name}")
                    response["message"] = f"Speech detected on {station_name}"
                else:
                    log_with_category(logger, "DETECTION", "info", "Speech detected in audio file")
                    response["message"] = "Speech detected in audio file"
            
            elif result.get("type") == "music":
                log_with_category(logger, "DETECTION", "info", f"Result structure: {result}")
                track_title = result.get("track", {}).get("title", "Unknown")
                track_artist = result.get("track", {}).get("artist", "Unknown")
                
                if station_name:
                    log_with_category(logger, "DETECTION", "info", f"Music detected on {station_name}: {track_title} by {track_artist}")
                    response["message"] = f"Music detected on {station_name}"
                else:
                    log_with_category(logger, "DETECTION", "info", f"Music detected in audio file: {track_title} by {track_artist}")
                    response["message"] = "Music detected in audio file"
                
                response["details"]["source"] = result.get("source")
                response["details"]["track"] = result.get("track", {})
                
                # Enregistrer la détection dans la base de données
                if station_id:
                    try:
                        log_with_category(logger, "DETECTION", "info", f"Attempting to record detection in database for station_id={station_id}")
                        log_with_category(logger, "DETECTION", "info", f"Result structure: {result}")
                        log_with_category(logger, "DETECTION", "info", f"Recording detection regardless of track information")
                        
                        # Vérifier si la piste existe déjà
                        track_info = result.get("track", {})
                        track_title = track_info.get("title", "Unknown Track")
                        track_artist = track_info.get("artist", "Unknown Artist")
                        
                        # Rechercher l'artiste
                        artist = self.db_session.query(Artist).filter(Artist.name == track_artist).first()
                        if not artist:
                            # Créer un nouvel artiste
                            artist = Artist(name=track_artist)
                            self.db_session.add(artist)
                            self.db_session.flush()
                            log_with_category(logger, "DETECTION", "info", f"Created new artist: {track_artist}")
                        
                        # Rechercher la piste
                        track = self.db_session.query(Track).filter(
                            Track.title == track_title,
                            Track.artist_id == artist.id
                        ).first()
                        
                        if not track:
                            # Créer une nouvelle piste
                            log_with_category(logger, "DETECTION", "info", f"Creating new track: {track_title} by {track_artist}")
                            track = Track(
                                title=track_title,
                                artist_id=artist.id,
                                album=track_info.get("album", "Unknown Album"),
                                duration=track_info.get("duration", 0),
                                fingerprint=track_info.get("fingerprint", ""),
                                external_id=track_info.get("id", ""),
                                source=result.get("source", "unknown")
                            )
                            self.db_session.add(track)
                            self.db_session.flush()
                            log_with_category(logger, "DETECTION", "info", f"Created new track: {track_title} by {track_artist}")
                        
                        # Créer une nouvelle détection
                        log_with_category(logger, "DETECTION", "info", f"Creating new detection for track_id={track.id}, station_id={station_id}")
                        detection = TrackDetection(
                            track_id=track.id,
                            station_id=station_id,
                            detected_at=datetime.now(),
                            confidence=result.get("confidence", 0.0),
                            play_duration=timedelta(seconds=float(result.get("play_duration", 0.0)))
                        )
                        self.db_session.add(detection)
                        log_with_category(logger, "DETECTION", "info", f"Added detection to session, committing...")
                        self.db_session.commit()
                        log_with_category(logger, "DETECTION", "info", f"Recorded detection: {track_title} by {track_artist} on station {station_name}")
                        
                        # Ajouter l'ID de détection à la réponse
                        response["details"]["detection_id"] = detection.id
                        
                    except Exception as e:
                        log_with_category(logger, "DETECTION", "error", f"Error recording detection: {str(e)}")
                        import traceback
                        log_with_category(logger, "DETECTION", "error", f"Traceback: {traceback.format_exc()}")
                        self.db_session.rollback()
            
            else:
                if station_name:
                    log_with_category(logger, "DETECTION", "warning", f"Unknown content detected on {station_name}")
                    response["message"] = f"Unknown content detected on {station_name}"
                else:
                    log_with_category(logger, "DETECTION", "warning", "Unknown content detected in audio file")
                    response["message"] = "Unknown content detected in audio file"
            
            return response
            
        except Exception as e:
            log_with_category(logger, "DETECTION", "error", f"Error processing audio file: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing audio file: {str(e)}"
            }
    
    async def process_audio_data(self, station_id: int, audio_data: bytes, station_name: str = None) -> Dict[str, Any]:
        """
        Process audio data from a station.
        
        Args:
            station_id: ID of the station
            audio_data: Raw audio data as bytes
            station_name: Name of the station (optional)
            
        Returns:
            Dictionary with detection results
        """
        try:
            # Get station name if not provided
            if not station_name:
                station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
                if station:
                    station_name = station.name
                else:
                    station_name = f"Station {station_id}"
            
            log_with_category(logger, "DETECTION", "info", f"Processing audio data from {station_name}")
            
            # Create station data
            station_data = {
                "raw_audio": audio_data,
                "station_id": station_id,
                "station_name": station_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Process station data
            result = await self.track_manager.process_station_data(station_data)
            
            # Log result
            if result.get("success"):
                detection = result.get("detection", {})
                log_with_category(logger, "DETECTION", "info", f"Track detected from {station_name}: {detection.get('title', 'Unknown')} by {detection.get('artist', 'Unknown')}")
            else:
                log_with_category(logger, "DETECTION", "info", f"No track detected from {station_name}: {result.get('error', 'Unknown error')}")
            
            return result
        
        except Exception as e:
            log_with_category(logger, "DETECTION", "error", f"Error processing audio data: {str(e)}")
            import traceback
            log_with_category(logger, "DETECTION", "error", f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)} 