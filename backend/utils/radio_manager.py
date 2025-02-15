import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import RadioStation, StationStatus, Track, TrackDetection, TrackStats, ArtistStats, StationTrackStats
from .radio_fetcher import RadioFetcher
from .websocket import broadcast_track_detection  # Import broadcast_track_detection function

logger = logging.getLogger(__name__)

class RadioManager:
    def __init__(self, db: Session):
        self.db = db
        self.fetcher = RadioFetcher()
    
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
        from utils.musicbrainz_recognizer import MusicBrainzRecognizer
        import requests
        from datetime import datetime
        import json
        
        recognizer = MusicBrainzRecognizer()
        total_stations = 0
        successful_detections = 0
        failed_stations = []
        
        try:
            # Get all active stations
            stations = self.db.query(RadioStation).filter(
                RadioStation.is_active == True,
                RadioStation.status == StationStatus.active
            ).all()
            
            total_stations = len(stations)
            logger.info(f"Starting music detection on {total_stations} stations using MusicBrainz")
            
            for station in stations:
                try:
                    # Download audio stream
                    response = requests.get(station.stream_url, stream=True, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"Failed to access stream for station {station.name}: {response.status_code}")
                        failed_stations.append({"id": station.id, "name": station.name, "error": "Stream access failed"})
                        continue
                    
                    # Get first 30 seconds of audio
                    audio_data = b''
                    for chunk in response.iter_content(chunk_size=8192):
                        audio_data += chunk
                        if len(audio_data) >= 30 * 8192:  # ~30 seconds of audio
                            break
                    
                    # Recognize music using MusicBrainz
                    result = recognizer.recognize_from_audio_data(audio_data)
                    
                    if "error" not in result:
                        # Create or update track
                        track = self.db.query(Track).filter(
                            Track.title == result["title"],
                            Track.artist == result["artist"]
                        ).first()
                        
                        if not track:
                            # Create new track
                            track = Track(
                                title=result["title"],
                                artist=result["artist"],
                                album=result.get("album"),
                                release_date=self._parse_release_date(result.get("release_date")),
                                isrc=result.get("isrc"),  # Save ISRC code
                                label=result.get("label"),  # Save label
                                external_ids=result.get("external_metadata", {}),
                                last_played=datetime.now()
                            )
                            self.db.add(track)
                            self.db.flush()  # Get track ID
                        else:
                            # Update existing track
                            track.last_played = datetime.now()
                            track.play_count += 1
                            if track.total_play_time:
                                track.total_play_time += timedelta(minutes=result.get("duration_minutes", 0.5))  # Use actual duration or default to 30 seconds
                            else:
                                track.total_play_time = timedelta(minutes=result.get("duration_minutes", 0.5))
                        
                        # Save the detection
                        detection = TrackDetection(
                            station_id=station.id,
                            track_id=track.id,
                            confidence=result["confidence"],
                            detected_at=datetime.now(),
                            play_duration=timedelta(minutes=result["duration_minutes"])
                        )
                        self.db.add(detection)
                        await self.db.commit()
                        
                        # Broadcast the detection
                        from main import broadcast_track_detection
                        await broadcast_track_detection({
                            "title": track.title,
                            "artist": track.artist,
                            "album": track.album,
                            "isrc": track.isrc,
                            "label": track.label,
                            "confidence": detection.confidence,
                            "play_duration": str(detection.play_duration),
                            "station_id": station.id,
                            "station_name": station.name,
                            "detected_at": detection.detected_at.isoformat()
                        })
                        
                        # Update track stats
                        track_stats = self.db.query(TrackStats).filter(
                            TrackStats.track_id == track.id
                        ).first()
                        
                        if not track_stats:
                            track_stats = TrackStats(
                                track_id=track.id,
                                detection_count=1,
                                average_confidence=result["confidence"],
                                last_detected=datetime.now()
                            )
                            self.db.add(track_stats)
                        else:
                            track_stats.detection_count += 1
                            track_stats.average_confidence = (
                                (track_stats.average_confidence * (track_stats.detection_count - 1) +
                                result["confidence"]) / track_stats.detection_count
                            )
                            track_stats.last_detected = datetime.now()
                        
                        # Update artist stats
                        artist_stats = self.db.query(ArtistStats).filter(
                            ArtistStats.artist_name == track.artist
                        ).first()
                        
                        if not artist_stats:
                            artist_stats = ArtistStats(
                                artist_name=track.artist,
                                detection_count=1,
                                last_detected=datetime.now()
                            )
                            self.db.add(artist_stats)
                        else:
                            artist_stats.detection_count += 1
                            artist_stats.last_detected = datetime.now()
                        
                        # Update station track stats
                        station_track_stats = self.db.query(StationTrackStats).filter(
                            StationTrackStats.station_id == station.id,
                            StationTrackStats.track_id == track.id
                        ).first()
                        
                        if not station_track_stats:
                            station_track_stats = StationTrackStats(
                                station_id=station.id,
                                track_id=track.id,
                                play_count=1,
                                total_play_time=timedelta(minutes=result["duration_minutes"]),
                                last_played=datetime.now(),
                                average_confidence=result["confidence"]
                            )
                            self.db.add(station_track_stats)
                        else:
                            station_track_stats.play_count += 1
                            station_track_stats.total_play_time += timedelta(minutes=result["duration_minutes"])
                            station_track_stats.last_played = datetime.now()
                            station_track_stats.average_confidence = (
                                (station_track_stats.average_confidence * (station_track_stats.play_count - 1) +
                                result["confidence"]) / station_track_stats.play_count
                            )
                        
                        self.db.commit()
                        successful_detections += 1
                        logger.info(f"Successfully detected music on station {station.name}: {track.title} by {track.artist}")
                    else:
                        logger.warning(f"No music detected on station {station.name}: {result.get('error', 'Unknown error')}")
                        failed_stations.append({
                            "id": station.id,
                            "name": station.name,
                            "error": result.get("error", "Unknown error")
                        })
                
                except Exception as e:
                    logger.error(f"Error processing station {station.name}: {str(e)}")
                    failed_stations.append({
                        "id": station.id,
                        "name": station.name,
                        "error": str(e)
                    })
            
            return {
                "status": "success",
                "total_stations": total_stations,
                "successful_detections": successful_detections,
                "failed_stations": failed_stations,
                "message": f"Successfully detected music on {successful_detections} out of {total_stations} stations"
            }
            
        except Exception as e:
            logger.error(f"Error in music detection: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
