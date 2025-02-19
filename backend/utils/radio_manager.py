import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import RadioStation, StationStatus, Track, TrackDetection, TrackStats, ArtistStats, StationTrackStats
from .radio_fetcher import RadioFetcher
from .websocket import broadcast_track_detection  # Import broadcast_track_detection function
from .analytics_manager import AnalyticsManager
from audio_processor import AudioProcessor

logger = logging.getLogger(__name__)

class RadioManager:
    def __init__(self, db: Session, audio_processor: AudioProcessor = None):
        """Initialize RadioManager with database session and audio processor.
        
        Args:
            db (Session): SQLAlchemy database session
            audio_processor (AudioProcessor, optional): Instance of AudioProcessor for music detection
        """
        self.db = db
        self.fetcher = RadioFetcher()
        self.analytics_manager = AnalyticsManager(db)
        
        # Initialize audio processor if not provided
        if audio_processor is None:
            try:
                from audio_processor import AudioProcessor
                self.audio_processor = AudioProcessor()
                logger.info("AudioProcessor initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize AudioProcessor: {str(e)}")
                self.audio_processor = None
        else:
            self.audio_processor = audio_processor
            logger.info("Using provided AudioProcessor instance")
    
    def update_senegal_stations(self) -> Dict:
        """Update Senegalese radio stations in the database"""
        try:
            # Fetch stations from API
            stations = self.fetcher.get_senegal_stations()
            logger.info(f"Processing {len(stations)} stations...")

            new_count = 0
            updated_count = 0

            for station_data in stations:
                # Check if station exists
                existing_station = self.db.query(RadioStation).filter(
                    RadioStation.stream_url == station_data['stream_url']
                ).first()

                if existing_station:
                    # Update existing station
                    for key, value in station_data.items():
                        setattr(existing_station, key, value)
                    existing_station.is_active = True
                    existing_station.status = StationStatus.active
                    updated_count += 1
                else:
                    # Create new station
                    new_station = RadioStation(
                        name=station_data['name'],
                        stream_url=station_data['stream_url'],
                        country=station_data['country'],
                        language=station_data['language'],
                        is_active=True,
                        status=StationStatus.active,
                        last_checked=datetime.utcnow()
                    )
                    self.db.add(new_station)
                    new_count += 1

            self.db.commit()
            logger.info(f"Successfully added {new_count} new stations and updated {updated_count} existing stations")

            return {
                "status": "success",
                "message": f"Added {new_count} new stations and updated {updated_count} existing stations",
                "new_count": new_count,
                "updated_count": updated_count
            }

        except Exception as e:
            logger.error(f"Error updating stations: {str(e)}")
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_active_stations(self) -> List[RadioStation]:
        """Get all active radio stations"""
        return self.db.query(RadioStation).all()
    
    def get_station_by_url(self, url: str) -> Optional[RadioStation]:
        """Get a radio station by its stream URL"""
        return self.db.query(RadioStation).filter(
            RadioStation.stream_url == url
        ).first()
    
    def update_station_status(self, station_id: int, status: StationStatus) -> None:
        """Update a station's status"""
        station = self.db.query(RadioStation).get(station_id)
        if station:
            station.status = status
            station.last_checked = datetime.utcnow()
            self.db.commit()
            logger.info(f"Updated status of station {station.name} to {status.value}")
        else:
            logger.error(f"Station with id {station_id} not found")

    def _parse_release_date(self, date_str):
        """Parse release date in various formats"""
        if not date_str:
            return None
            
        try:
            # Try full date format first
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # Try year-month format
                return datetime.strptime(date_str, "%Y-%m")
            except ValueError:
                try:
                    # Try year only format
                    return datetime.strptime(f"{date_str}-01-01", "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Could not parse release date: {date_str}")
                    return None

    async def detect_music_all_stations(self) -> Dict:
        """Detect music on all active radio stations"""
        try:
            # Get all active stations
            stations = self.db.query(RadioStation).filter(
                RadioStation.is_active == True,
                RadioStation.status == StationStatus.active
            ).all()
            
            if not stations:
                logger.warning("No active stations found")
                return {"status": "error", "message": "No active stations found"}
            
            results = []
            for station in stations:
                try:
                    # Download and analyze audio sample
                    audio_data = await self._download_audio_sample(station.stream_url)
                    if not audio_data:
                        continue
                    
                    # Recognize music
                    result = await self.music_recognizer.recognize(audio_data, station.name)
                    
                    if not result or "error" in result:
                        logger.warning(f"No result for station {station.name}: {result.get('error') if result else 'No result'}")
                        continue
                    
                    if not result.get("is_music", False):
                        logger.info(f"No music detected on {station.name}")
                        continue
                    
                    # Get or create track
                    track_info = result.get("track", {})
                    if not track_info:
                        logger.warning(f"No track info in result for station {station.name}")
                        continue
                    
                    # Get duration from recognition result
                    duration_seconds = result.get("duration_seconds", 0)
                    if duration_seconds <= 0:
                        duration_seconds = result.get("duration_minutes", 0.5) * 60
                    
                    # Validate duration
                    if duration_seconds <= 0:
                        logger.warning(f"Invalid duration for station {station.name}, using default")
                        duration_seconds = 15
                    elif duration_seconds > 3600:  # Cap at 1 hour
                        logger.warning(f"Duration exceeds maximum for station {station.name}, capping at 1 hour")
                        duration_seconds = 3600
                        
                    duration_td = timedelta(seconds=duration_seconds)
                    current_time = datetime.now()
                    
                    logger.info(f"Processing detection for station {station.name}", extra={
                        'duration': str(duration_td),
                        'track': track_info.get("title"),
                        'artist': track_info.get("artist")
                    })
                    
                    # 1. Find or create track
                    track = self.db.query(Track).filter(
                        Track.title == track_info.get("title"),
                        Track.artist == track_info.get("artist")
                    ).first()
                    
                    if not track:
                        # Create new track
                        track = Track(
                            title=track_info.get("title"),
                            artist=track_info.get("artist"),
                            album=track_info.get("album"),
                            isrc=track_info.get("isrc"),
                            label=track_info.get("label"),
                            external_ids=track_info.get("external_metadata", {}),
                            play_count=1,
                            total_play_time=duration_td,
                            last_played=current_time,
                            created_at=current_time
                        )
                        self.db.add(track)
                        self.db.flush()  # Get track ID
                    else:
                        # Update existing track
                        track.last_played = current_time
                        track.play_count += 1
                        track.total_play_time = (track.total_play_time or timedelta(0)) + duration_td
                    
                    # 2. Create detection
                    detection = TrackDetection(
                        station_id=station.id,
                        track_id=track.id,
                        confidence=result.get("confidence", 0),
                        detected_at=current_time,
                        play_duration=duration_td
                    )
                    self.db.add(detection)
                    
                    # 3. Update track stats
                    track_stats = self.db.query(TrackStats).filter(
                        TrackStats.track_id == track.id
                    ).first()
                    
                    if not track_stats:
                        track_stats = TrackStats(
                            track_id=track.id,
                            detection_count=1,
                            average_confidence=result.get("confidence", 0),
                            last_detected=current_time,
                            total_play_time=duration_td
                        )
                        self.db.add(track_stats)
                    else:
                        track_stats.detection_count += 1
                        track_stats.last_detected = current_time
                        track_stats.total_play_time = (track_stats.total_play_time or timedelta(0)) + duration_td
                        # Update average confidence
                        track_stats.average_confidence = (
                            (track_stats.average_confidence * (track_stats.detection_count - 1) +
                            result.get("confidence", 0)) / track_stats.detection_count
                        )
                    
                    # 4. Update artist stats
                    artist_stats = self.db.query(ArtistStats).filter(
                        ArtistStats.artist_name == track.artist
                    ).first()
                    
                    if not artist_stats:
                        artist_stats = ArtistStats(
                            artist_name=track.artist,
                            detection_count=1,
                            last_detected=current_time,
                            total_play_time=duration_td
                        )
                        self.db.add(artist_stats)
                    else:
                        artist_stats.detection_count += 1
                        artist_stats.last_detected = current_time
                        artist_stats.total_play_time = (artist_stats.total_play_time or timedelta(0)) + duration_td
                    
                    # 5. Update station track stats
                    station_track_stats = self.db.query(StationTrackStats).filter(
                        StationTrackStats.station_id == station.id,
                        StationTrackStats.track_id == track.id
                    ).first()
                    
                    if not station_track_stats:
                        station_track_stats = StationTrackStats(
                            station_id=station.id,
                            track_id=track.id,
                            play_count=1,
                            total_play_time=duration_td,
                            last_played=current_time,
                            average_confidence=result.get("confidence", 0)
                        )
                        self.db.add(station_track_stats)
                    else:
                        station_track_stats.play_count += 1
                        station_track_stats.last_played = current_time
                        station_track_stats.total_play_time = (station_track_stats.total_play_time or timedelta(0)) + duration_td
                        # Update average confidence
                        station_track_stats.average_confidence = (
                            (station_track_stats.average_confidence * (station_track_stats.play_count - 1) +
                            result.get("confidence", 0)) / station_track_stats.play_count
                        )
                    
                    # 6. Update station stats
                    station.last_detection_time = current_time
                    station.total_play_time = (station.total_play_time or timedelta(0)) + duration_td
                    
                    # Commit all changes
                    await self.db.commit()
                    
                    # Prepare detection data for broadcast
                    detection_data = {
                        "id": detection.id,
                        "title": track.title,
                        "artist": track.artist,
                        "album": track.album,
                        "isrc": track.isrc,
                        "label": track.label,
                        "confidence": detection.confidence,
                        "play_duration": str(detection.play_duration),
                        "station_id": station.id,
                        "station_name": station.name,
                        "detected_at": detection.detected_at.isoformat(),
                        "track_id": track.id,
                        "total_play_time": str(track.total_play_time),
                        "play_count": track.play_count,
                        "stats": {
                            "track": {
                                "detection_count": track_stats.detection_count,
                                "average_confidence": track_stats.average_confidence,
                                "total_play_time": str(track_stats.total_play_time)
                            },
                            "artist": {
                                "detection_count": artist_stats.detection_count,
                                "total_play_time": str(artist_stats.total_play_time)
                            },
                            "station": {
                                "play_count": station_track_stats.play_count,
                                "total_play_time": str(station_track_stats.total_play_time),
                                "average_confidence": station_track_stats.average_confidence
                            }
                        }
                    }
                    
                    # Broadcast detection
                    await broadcast_track_detection(detection_data)
                    
                    results.append({
                        "station": station.name,
                        "status": "success",
                        "detection": detection_data
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing station {station.name}: {str(e)}")
                    await self.db.rollback()  # Rollback on error
                    results.append({
                        "station": station.name,
                        "status": "error",
                        "error": str(e)
                    })
            
            return {
                "status": "success",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in detect_music_all_stations: {str(e)}")
            await self.db.rollback()  # Rollback on error
            return {
                "status": "error",
                "error": str(e)
            }

    async def detect_music(self, station_id: int) -> Dict:
        """Detect music on a specific radio station
        
        Args:
            station_id (int): ID of the station to process
            
        Returns:
            Dict: Detection results including status and any found tracks
        """
        try:
            if not self.audio_processor:
                raise ValueError("AudioProcessor is required for music detection")
            
            # Get station from database
            station = self.db.query(RadioStation).filter(RadioStation.id == station_id).first()
            if not station:
                raise ValueError(f"Station with ID {station_id} not found")
            
            # Check if station is active
            if not station.is_active or station.status != StationStatus.active:
                raise ValueError(f"Station {station.name} is not active")
            
            # Process audio stream
            logger.info(f"Starting music detection for station: {station.name}")
            detection_result = await self.audio_processor.process_stream(station.stream_url)
            
            if not detection_result:
                logger.warning(f"No music detected for station: {station.name}")
                return {
                    "status": "success",
                    "message": "No music detected",
                    "detections": []
                }
            
            # Update station status
            station.last_detection_time = datetime.now()
            self.db.commit()
            
            # Format detections
            detections = []
            for track in detection_result.get("tracks", []):
                detection = {
                    "title": track.get("title", "Unknown"),
                    "artist": track.get("artist", "Unknown"),
                    "confidence": track.get("confidence", 0.0),
                    "detected_at": track.get("detected_at", datetime.now().isoformat()),
                    "play_duration": str(track.get("duration", "0:00:00"))
                }
                detections.append(detection)
                
                # Broadcast detection via WebSocket
                await broadcast_track_detection({
                    "station_id": station.id,
                    "station_name": station.name,
                    "track": detection
                })
            
            return {
                "status": "success",
                "message": f"Processed {len(detections)} detections",
                "detections": detections
            }
            
        except ValueError as e:
            logger.warning(f"Validation error for station {station_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error detecting music for station {station_id}: {str(e)}")
            raise

    def check_station_status(self, station: RadioStation) -> bool:
        """Check if a station is currently active by attempting to connect to its stream.
        
        Args:
            station (RadioStation): The station to check
            
        Returns:
            bool: True if the station is active, False otherwise
        """
        try:
            # Try to connect to the stream
            is_active = self.fetcher.check_stream_status(station.stream_url)
            
            # Update last checked time
            station.last_checked = datetime.now()
            self.db.commit()
            
            return is_active
            
        except Exception as e:
            logger.warning(f"Error checking station {station.name}: {str(e)}")
            return False

    async def process_detection(self, detection_data: Dict) -> None:
        """Process a new detection and update all analytics"""
        try:
            # Validate detection data
            required_fields = ['station_id', 'track_id', 'confidence', 'play_duration']
            if not all(field in detection_data for field in required_fields):
                raise ValueError(f"Missing required fields: {required_fields}")
            
            # Update all analytics in a single transaction
            await self.analytics_manager.update_all_analytics(detection_data)
            
            # Broadcast detection via WebSocket
            await broadcast_track_detection(detection_data)
            
            logger.info(
                "Detection processed successfully",
                extra={
                    'station_id': detection_data['station_id'],
                    'track_id': detection_data['track_id']
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing detection: {str(e)}", exc_info=True)
            raise
