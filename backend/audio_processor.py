import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .music_recognition import MusicRecognizer
from .models import Track, TrackDetection, RadioStation, StationTrackStats
from sqlalchemy.orm import Session
import io
import aiohttp
import numpy as np
import asyncio
import av
from pydub import AudioSegment
from .utils.logging_config import setup_logging
from .utils.stats_updater import StatsUpdater
import tempfile
import os
import librosa
import soundfile as sf

# Configure logging
logger = setup_logging(__name__)

class AudioProcessor:
    def __init__(self, db_session: Session, music_recognizer: MusicRecognizer):
        self.db_session = db_session
        self.music_recognizer = music_recognizer
        self.logger = logging.getLogger(__name__)
        
        # Configuration des limites de ressources
        self.max_concurrent_stations = 10  # Nombre maximum de stations en parallèle
        self.max_memory_usage = 1024 * 1024 * 500  # 500 MB maximum
        self.processing_timeout = 60  # 60 secondes par station
        self.chunk_duration = 30  # Durée d'échantillonnage en secondes
        
        # Sémaphores pour le contrôle des ressources
        self.processing_semaphore = asyncio.Semaphore(self.max_concurrent_stations)
        self.memory_semaphore = asyncio.Semaphore(self.max_concurrent_stations)
        
        # État de traitement
        self.current_tracks = {}  # {station_id: {'track': track, 'start_time': datetime, 'detection_id': int}}
        self.stats_updater = StatsUpdater(db_session)
        self.processing_stations = set()
        
        logger.info(f"Initializing AudioProcessor with max {self.max_concurrent_stations} concurrent stations")

        # Initialize new attributes
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "8192"))
        self.sample_rate = int(os.getenv("SAMPLE_RATE", "44100"))
        self.min_duration = int(os.getenv("MIN_AUDIO_LENGTH", "10"))
        self.max_duration = int(os.getenv("MAX_AUDIO_LENGTH", "30"))
        self.min_confidence = float(os.getenv("MIN_CONFIDENCE", "50"))
        
        logger.info("AudioProcessor initialized with settings: " + 
                   f"chunk_size={self.chunk_size}, " +
                   f"sample_rate={self.sample_rate}, " +
                   f"duration={self.min_duration}-{self.max_duration}s")

    async def process_all_stations(self, stations: List[RadioStation]) -> Dict[str, Any]:
        """Process all stations in parallel with resource management"""
        try:
            total_stations = len(stations)
            logger.info(f"Starting parallel processing of {total_stations} stations")
            
            # Initialize results tracking
            results = []
            successful_detections = 0
            failed_detections = 0
            
            # Create tasks for all stations
            tasks = []
            for station in stations:
                if station.id not in self.processing_stations:
                    self.processing_stations.add(station.id)
                    task = asyncio.create_task(self._process_station_safe(station, asyncio.Queue()))
                    tasks.append(task)
            
            # Process stations as they complete
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    results.append(result)
                    
                    if result.get("is_music") and not result.get("error"):
                        successful_detections += 1
                    else:
                        failed_detections += 1
                    
                    # Release the station
                    station_id = result.get("station_id")
                    if station_id in self.processing_stations:
                        self.processing_stations.remove(station_id)
                    
                    # Log progress
                    completed = len(results)
                    logger.info(
                        f"Progress: {completed}/{total_stations} stations processed "
                        f"({successful_detections} successful, {failed_detections} failed)"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing task: {str(e)}")
                    failed_detections += 1
            
            logger.info(
                f"Completed parallel processing of {total_stations} stations: "
                f"{successful_detections} successful, {failed_detections} failed"
            )
            
            return {
                "status": "success",
                "total_stations": total_stations,
                "successful_detections": successful_detections,
                "failed_detections": failed_detections,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in parallel processing: {str(e)}")
            # Clean up processing stations
            self.processing_stations.clear()
            return {
                "status": "error",
                "message": str(e),
                "total_stations": len(stations),
                "successful_detections": 0,
                "failed_detections": len(stations)
            }

    async def _process_station_safe(self, station: RadioStation, results_queue: asyncio.Queue) -> Dict[str, Any]:
        """Process a single station safely with resource monitoring"""
        try:
            async with self.processing_semaphore:
                async with self.memory_semaphore:
                    if not self._check_memory_usage():
                        return {
                            "error": "Insufficient memory available",
                            "station": station.name,
                            "station_id": station.id,
                            "is_music": False
                        }
                    
                    # Check if a track is currently playing
                    current_track = self.current_tracks.get(station.id)
                    try:
                        if current_track:
                            # Check if the same track continues
                            result = await asyncio.wait_for(
                                self.analyze_stream(station.stream_url, station.id, current_track),
                                timeout=self.processing_timeout
                            )
                        else:
                            # New detection
                            result = await asyncio.wait_for(
                                self.analyze_stream(station.stream_url, station.id),
                                timeout=self.processing_timeout
                            )
                        
                        result["station_id"] = station.id
                        return result
                        
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout processing station {station.name}")
                        self._end_current_track(station.id)  # End current track if timeout
                        return {
                            "error": "Processing timeout",
                            "station": station.name,
                            "station_id": station.id,
                            "is_music": False
                        }
                        
        except Exception as e:
            logger.error(f"Error processing station {station.name}: {str(e)}")
            self._end_current_track(station.id)  # End current track if error
            return {
                "error": str(e),
                "station": station.name,
                "station_id": station.id,
                "is_music": False
            }

    def _check_memory_usage(self) -> bool:
        """Vérifier l'utilisation de la mémoire"""
        try:
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss
            return memory_usage < self.max_memory_usage
        except ImportError:
            logger.warning("psutil not installed, skipping memory check")
            return True
        except Exception as e:
            logger.error(f"Error checking memory usage: {str(e)}")
            return True

    async def analyze_stream(self, stream_url: str, station_id: int = None, current_track_info: dict = None) -> Dict[str, Any]:
        """Analyze audio stream and detect music"""
        try:
            station_name = "Unknown Station"
            if station_id:
                station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
                if station:
                    station_name = station.name
            
            logger.info("Starting stream analysis", extra={
                'station': {
                    'id': station_id,
                    'name': station_name,
                    'url': stream_url
                },
                'step': 'start'
            })
            
            # Télécharger et analyser l'échantillon audio
            audio_data = await self._download_audio_chunk(stream_url)
            if not audio_data:
                if current_track_info:
                    self._end_current_track(station_id)
                return {
                    "error": "Failed to download audio",
                    "station": station_name
                }
            
            # Reconnaître la musique
            result = await self.music_recognizer.recognize(audio_data, station_name)
            
            if result.get("is_music"):
                # Si un morceau est en cours
                if current_track_info:
                    current_track = current_track_info['track']
                    # Vérifier si c'est le même morceau
                    if (result.get("track", {}).get("title") == current_track.title and 
                        result.get("track", {}).get("artist") == current_track.artist):
                        # Continuer le suivi du morceau en cours
                        return result
                    else:
                        # Terminer le morceau en cours et commencer le nouveau
                        self._end_current_track(station_id)
                
                # Créer ou obtenir le morceau
                track = self._get_or_create_track(result)
                if track:
                    # Créer une nouvelle détection
                    detection = TrackDetection(
                        station_id=station_id,
                        track_id=track.id,
                        confidence=result.get("confidence", 0),
                        detected_at=datetime.now()
                    )
                    self.db_session.add(detection)
                    self.db_session.flush()  # Pour obtenir l'ID de la détection
                    
                    # Enregistrer le nouveau morceau en cours
                    self.current_tracks[station_id] = {
                        'track': track,
                        'start_time': datetime.now(),
                        'detection_id': detection.id
                    }
            else:
                # Si pas de musique détectée, terminer le morceau en cours
                if current_track_info:
                    self._end_current_track(station_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in stream analysis: {str(e)}")
            if current_track_info:
                self._end_current_track(station_id)
            return {
                "error": str(e),
                "station": station_name
            }

    def _end_current_track(self, station_id: int):
        """Terminer le suivi du morceau en cours et mettre à jour sa durée de lecture"""
        try:
            current_track_info = self.current_tracks.get(station_id)
            if not current_track_info:
                return
            
            # Calculer la durée réelle de lecture
            end_time = datetime.now()
            start_time = current_track_info['start_time']
            play_duration = end_time - start_time
            
            # Vérifier si la durée est réaliste (entre 30 secondes et 15 minutes)
            duration_seconds = play_duration.total_seconds()
            if duration_seconds < 30:
                logger.warning(f"Play duration too short ({duration_seconds:.1f}s), skipping update")
                return
            elif duration_seconds > 900:  # 15 minutes
                logger.warning(f"Play duration too long ({duration_seconds:.1f}s), limiting to 15 minutes")
                play_duration = timedelta(minutes=15)
            
            # Mettre à jour la détection avec la durée réelle
            detection = self.db_session.query(TrackDetection).get(current_track_info['detection_id'])
            if detection:
                detection.play_duration = play_duration
                
                # Mettre à jour les statistiques de la station
                station = self.db_session.query(RadioStation).get(station_id)
                if station:
                    if not station.total_play_time:
                        station.total_play_time = timedelta(0)
                    station.total_play_time += play_duration
                    station.last_detection_time = end_time
                
                # Mettre à jour les statistiques du morceau
                track = current_track_info['track']
                if track:
                    if not track.total_play_time:
                        track.total_play_time = timedelta(0)
                    track.total_play_time += play_duration
                    track.play_count += 1
                    track.last_played = end_time
                
                # Mettre à jour les statistiques station-morceau
                self._update_station_track_stats(station_id, track.id, play_duration)
                
                # Commit des changements
                self.db_session.commit()
                logger.info(
                    f"Updated play duration for track {track.title} on station {station_id}: "
                    f"{play_duration.total_seconds():.1f} seconds"
                )
            
            # Supprimer le morceau en cours
            del self.current_tracks[station_id]
            
        except Exception as e:
            logger.error(f"Error ending current track: {str(e)}")
            self.db_session.rollback()

    def _update_station_track_stats(self, station_id: int, track_id: int, duration: timedelta):
        """Mettre à jour les statistiques de lecture station-morceau"""
        try:
            # Obtenir ou créer les stats station-morceau
            stats = self.db_session.query(StationTrackStats).filter(
                StationTrackStats.station_id == station_id,
                StationTrackStats.track_id == track_id
            ).first()
            
            if not stats:
                stats = StationTrackStats(
                    station_id=station_id,
                    track_id=track_id,
                    play_count=1,
                    total_play_time=duration,
                    last_played=datetime.now()
                )
                self.db_session.add(stats)
            else:
                stats.play_count += 1
                if not stats.total_play_time:
                    stats.total_play_time = timedelta(0)
                stats.total_play_time += duration
                stats.last_played = datetime.now()
            
            logger.info(
                f"Updated station-track stats: station={station_id}, track={track_id}, "
                f"duration={duration.total_seconds():.1f}s, total={stats.total_play_time}"
            )
            
        except Exception as e:
            logger.error(f"Error updating station track stats: {str(e)}")
            self.db_session.rollback()

    def _get_or_create_track(self, result):
        try:
            # Extract track info
            track_info = result['track']
            
            # Get ISRC from various sources
            isrc = track_info.get('isrc')
            if not isrc and 'external_metadata' in track_info:
                # Try to get ISRC from MusicBrainz metadata
                musicbrainz_data = track_info['external_metadata'].get('musicbrainz', {})
                if isinstance(musicbrainz_data, dict):
                    isrc = musicbrainz_data.get('isrc')
                
                # Try to get ISRC from Spotify metadata if still not found
                if not isrc:
                    spotify_data = track_info['external_metadata'].get('spotify', {})
                    if spotify_data:
                        isrc = spotify_data.get('external_ids', {}).get('isrc')
                
                # Try to get ISRC from Deezer metadata if still not found
                if not isrc:
                    deezer_data = track_info['external_metadata'].get('deezer', {})
                    if deezer_data:
                        isrc = deezer_data.get('isrc')
            
            # Get label from various sources
            label = track_info.get('label')
            if not label and 'external_metadata' in track_info:
                # Try to get label from Spotify metadata
                spotify_data = track_info['external_metadata'].get('spotify', {})
                if spotify_data and 'album' in spotify_data:
                    label = spotify_data['album'].get('label')
                
                # Try to get label from Deezer metadata if still not found
                if not label:
                    deezer_data = track_info['external_metadata'].get('deezer', {})
                    if deezer_data:
                        label = deezer_data.get('record_type')
            
            # Try to get label from MusicBrainz metadata if still not found
            if not label:
                musicbrainz_data = track_info['external_metadata'].get('musicbrainz', {})
                if isinstance(musicbrainz_data, dict):
                    label = musicbrainz_data.get('label')
            
            # Try to find existing track by ISRC first if available
            track = None
            if isrc:
                track = self.db_session.query(Track).filter(Track.isrc == isrc).first()
                if track:
                    self.logger.info(f"Found existing track by ISRC: {track.title} (ISRC: {isrc})")
                    # Update label if not set
                    if not track.label and label:
                        track.label = label
                        self.db_session.commit()
                        self.logger.info(f"Updated label for track {track.title}: {label}")
            
            # If no track found by ISRC, try by title and artist
            if not track:
                track = self.db_session.query(Track).filter(
                    Track.title == track_info.get('title'),
                    Track.artist == track_info.get('artist')
                ).first()
                if track:
                    # Update ISRC and label if not set
                    updated = False
                    if isrc and not track.isrc:
                        track.isrc = isrc
                        updated = True
                        self.logger.info(f"Updated ISRC for track {track.title}: {isrc}")
                    if label and not track.label:
                        track.label = label
                        updated = True
                        self.logger.info(f"Updated label for track {track.title}: {label}")
                    if updated:
                        self.db_session.commit()
            
            # If still no track found, create new one
            if not track:
                track = Track(
                    title=track_info.get('title'),
                    artist=track_info.get('artist'),
                    isrc=isrc,
                    label=label,
                    album=track_info.get('album'),
                    external_ids=track_info.get('external_metadata', {}),
                    play_count=0,
                    total_play_time=timedelta(0)
                )
                self.db_session.add(track)
                self.db_session.commit()
                self.logger.info(f"Created new track: {track.title} by {track.artist} (ISRC: {isrc or 'Unknown'}, Label: {label or 'Unknown'})")
            
            return track
            
        except Exception as e:
            self.logger.error(f"Error in get_or_create_track: {str(e)}")
            self.db_session.rollback()
            return None

    async def _download_audio_chunk(self, url: str) -> bytes:
        """Download a chunk of audio from the stream"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to connect to stream: {url}, status: {response.status}")
                        return None
                    
                    # Download 15 seconds of audio (assuming 44.1kHz, 16-bit stereo)
                    target_size = 44100 * 2 * 2 * 15  # 15 seconds
                    
                    # Ensure target_size is a multiple of 2 (for 16-bit audio)
                    target_size = (target_size // 2) * 2
                    
                    chunks = []
                    total_size = 0
                    chunk_size = 1024 * 2  # 2KB chunks (multiple of 2)
                    
                    while total_size < target_size:
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        total_size += len(chunk)
                    
                    # Combine chunks and ensure final size is a multiple of 2
                    audio_data = b''.join(chunks)
                    if len(audio_data) % 2 != 0:
                        audio_data = audio_data[:-1]
                    
                    self.logger.info(f"Downloaded {len(audio_data)} bytes of audio data")
                    return audio_data
                    
        except Exception as e:
            self.logger.error(f"Error downloading stream: {str(e)}")
            return None

    async def _analyze_audio_features(self, audio_data: bytes) -> float:
        try:
            # Ensure audio_data is not empty
            if not audio_data:
                self.logger.error("Empty audio data received")
                return 0.0

            # Convert audio bytes to numpy array, ensuring proper alignment
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Ensure we have enough samples for analysis (at least 1024)
            if len(audio_array) < 1024:
                self.logger.error("Insufficient audio data for analysis")
                return 0.0
            
            # Pad array to ensure it's a multiple of 1024
            remainder = len(audio_array) % 1024
            if remainder != 0:
                padding = 1024 - remainder
                audio_array = np.pad(audio_array, (0, padding), mode='constant')
            
            # Normalize samples
            normalized = audio_array.astype(np.float32) / 32768.0
            
            # Calculate basic audio features
            rms = np.sqrt(np.mean(normalized**2))
            zero_crossings = np.sum(np.abs(np.diff(np.signbit(normalized))))
            spectral_centroid = np.mean(np.abs(np.fft.rfft(normalized)))
            
            # Calculate music likelihood score (0-100)
            # Higher centroid, consistent energy, lower ZCR, higher rolloff = more likely to be music
            music_score = (
                (min(spectral_centroid / 4000, 1.0) * 30) +  # Increased weight for spectral centroid
                (max(1 - rms * 8, 0.0) * 30) +  # Increased weight for energy consistency
                (max(1 - zero_crossings / len(normalized) * 80, 0.0) * 20) +  # Reduced weight for ZCR
                (min(spectral_centroid / 10000, 1.0) * 20)  # Reduced weight for rolloff
            )
            
            self.logger.info(f"Audio analysis results - RMS: {rms:.3f}, Zero crossings: {zero_crossings}, Spectral centroid: {spectral_centroid:.3f}, Music score: {music_score:.3f}")
            return music_score
            
        except Exception as e:
            self.logger.error(f"Error analyzing audio features: {str(e)}")
            return 0.0

    def _save_track_to_db(self, recognition_result: Dict[str, Any]) -> Track:
        """Save recognized track to database if it doesn't exist."""
        title = recognition_result.get('title', '')
        artist = recognition_result.get('artist', '')
        isrc = recognition_result.get('isrc', '')
        
        # Get actual play duration in minutes
        play_duration = recognition_result.get('play_duration')
        if isinstance(play_duration, timedelta):
            duration_minutes = play_duration.total_seconds() / 60
        else:
            duration_minutes = float(recognition_result.get('duration_minutes', 0)) or (
                float(str(play_duration).split(':')[-1]) / 60 if play_duration else 0
            )
        
        logger.debug(f"Checking if track exists: {title} by {artist}")
        
        # Check if track exists
        track = self.db_session.query(Track).filter_by(
            title=title,
            artist=artist
        ).first()
        
        if not track:
            logger.info(f"Creating new track record: {title} by {artist}")
            # Create new track
            track = Track(
                title=title,
                artist=artist,
                isrc=isrc,
                label=recognition_result.get('label', ''),
                album=recognition_result.get('album', ''),
                external_ids=recognition_result.get('external_metadata', {}),
                play_count=1,
                total_play_time=timedelta(minutes=duration_minutes),
                last_played=datetime.now()
            )
            self.db_session.add(track)
            self.db_session.commit()
            logger.debug(f"New track saved with ID: {track.id} (play duration: {duration_minutes:.2f} minutes)")
        else:
            # Update last played time and total play time
            track.last_played = datetime.now()
            track.play_count += 1
            play_time_delta = timedelta(minutes=duration_minutes)
            if track.total_play_time:
                track.total_play_time += play_time_delta
            else:
                track.total_play_time = play_time_delta
            if isrc and not track.isrc:
                track.isrc = isrc
            self.db_session.commit()
            logger.debug(f"Updated track {track.id}: play count = {track.play_count}, added play time = {duration_minutes:.2f} minutes")
        
        return track

    async def check_stream_status(self, url: str) -> dict:
        """Check stream status and get stream parameters."""
        try:
            self.logger.info(f"Checking stream status for URL: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity;q=1, *;q=0',
                'Range': 'bytes=0-',
                'Connection': 'keep-alive',
                'Icy-MetaData': '1',
                'Referer': 'https://www.zeno.fm/',
                'Origin': 'https://www.zeno.fm',
                'Sec-Fetch-Dest': 'audio',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site'
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=headers, timeout=10) as response:
                        self.logger.info(f"Initial response status: {response.status}")
                        self.logger.info(f"Response headers: {response.headers}")
                        
                        if response.status != 200:
                            return {
                                "ok": False,
                                "message": f"Stream returned status code {response.status}"
                            }
                        
                        # Read initial chunk to analyze stream
                        chunk = await response.content.read(8192)
                        if not chunk:
                            return {
                                "ok": False,
                                "message": "Stream is empty"
                            }
                        
                        # Get content type and ICY metadata
                        content_type = response.headers.get('Content-Type', '')
                        icy_metaint = response.headers.get('icy-metaint')
                        icy_name = response.headers.get('icy-name')
                        icy_br = response.headers.get('icy-br')
                        
                        self.logger.info(f"Content-Type: {content_type}")
                        self.logger.info(f"ICY Metadata: metaint={icy_metaint}, name={icy_name}, bitrate={icy_br}")
                        
                        if not any(t in content_type.lower() for t in ['audio', 'stream', 'mpegurl', 'octet-stream']):
                            return {
                                "ok": False,
                                "message": f"Invalid content type: {content_type}"
                            }
                        
                        return {
                            "ok": True,
                            "message": "Stream is active",
                            "content_type": content_type,
                            "icy_name": icy_name,
                            "bitrate": icy_br,
                            "metadata_interval": icy_metaint
                        }
                        
                except aiohttp.ClientError as e:
                    self.logger.error(f"HTTP error: {str(e)}")
                    return {
                        "ok": False,
                        "message": f"HTTP error: {str(e)}"
                    }
                except asyncio.TimeoutError:
                    self.logger.error("Connection timeout")
                    return {
                        "ok": False,
                        "message": "Connection timeout"
                    }
                        
        except Exception as e:
            self.logger.error(f"Error checking stream status: {str(e)}")
            return {
                "ok": False,
                "message": f"Error connecting to stream: {str(e)}"
            }

    def _get_track_duration(self, result: dict, audio_data: bytes) -> float:
        """Calculate track duration in minutes from various sources"""
        try:
            # Try to get duration from recognition result first
            if result.get('track', {}).get('duration_minutes'):
                return float(result['track']['duration_minutes'])
            
            # Try to get duration from external metadata
            external_meta = result.get('track', {}).get('external_metadata', {})
            if external_meta:
                # Try Spotify duration (in ms)
                if 'spotify' in external_meta and external_meta['spotify'].get('duration_ms'):
                    return float(external_meta['spotify']['duration_ms']) / (1000 * 60)
                
                # Try Deezer duration (in seconds)
                if 'deezer' in external_meta and external_meta['deezer'].get('duration'):
                    return float(external_meta['deezer']['duration']) / 60
            
            # Calculate from audio data as last resort
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            return len(audio) / (1000 * 60)  # Convert milliseconds to minutes
            
        except Exception as e:
            self.logger.error(f"Error calculating track duration: {str(e)}")
            return 3.0  # Default to 3 minutes if all else fails

    def _get_sample_duration(self, audio_data: bytes) -> float:
        """Calculate the actual duration of the audio sample in seconds"""
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            return len(audio) / 1000.0  # Convert milliseconds to seconds
        except Exception as e:
            self.logger.error(f"Error calculating sample duration: {str(e)}")
            return 15.0  # Default to 15 seconds if calculation fails

    async def process_stream(self, stream_url: str) -> Optional[Dict]:
        """Process an audio stream for music detection
        
        Args:
            stream_url (str): URL of the audio stream to process
            
        Returns:
            Optional[Dict]: Detection results if successful, None otherwise
        """
        try:
            async with self.processing_semaphore:
                logger.info(f"Processing stream: {stream_url}")
                
                # Create temporary file for audio data
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    try:
                        # Download audio chunk
                        async with aiohttp.ClientSession() as session:
                            async with session.get(stream_url) as response:
                                if response.status != 200:
                                    raise ValueError(f"Failed to access stream: {response.status}")
                                
                                # Read audio data
                                audio_data = await response.read()
                                temp_file.write(audio_data)
                                temp_file.flush()
                        
                        # Load and process audio
                        audio = AudioSegment.from_mp3(temp_file.name)
                        duration = len(audio) / 1000  # Convert to seconds
                        
                        if duration < self.min_duration:
                            raise ValueError(f"Audio duration too short: {duration}s")
                            
                        # Trim to max duration if needed
                        if duration > self.max_duration:
                            audio = audio[:self.max_duration * 1000]
                        
                        # Convert to numpy array for processing
                        samples = np.array(audio.get_array_of_samples())
                        
                        # Detect music features
                        features = self._extract_features(samples)
                        
                        # Format results
                        return {
                            "status": "success",
                            "tracks": [{
                                "title": "Music Detected",  # Placeholder - implement actual recognition
                                "artist": "Unknown Artist",
                                "confidence": features["confidence"],
                                "detected_at": datetime.now().isoformat(),
                                "duration": str(timedelta(seconds=int(duration)))
                            }] if features["is_music"] else []
                        }
                        
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(temp_file.name)
                        except Exception as e:
                            logger.warning(f"Error cleaning up temp file: {str(e)}")
                            
        except Exception as e:
            logger.error(f"Error processing stream {stream_url}: {str(e)}")
            return None

    def _extract_features(self, samples: np.ndarray) -> Dict:
        """Extract audio features to detect music
        
        Args:
            samples (np.ndarray): Audio samples
            
        Returns:
            Dict: Extracted features including confidence
        """
        try:
            # Convert to mono if stereo
            if len(samples.shape) > 1:
                samples = np.mean(samples, axis=1)
            
            # Normalize samples
            samples = samples.astype(float) / np.iinfo(samples.dtype).max
            
            # Extract features
            tempo, _ = librosa.beat.beat_track(y=samples, sr=self.sample_rate)
            spectral_centroid = librosa.feature.spectral_centroid(y=samples, sr=self.sample_rate)
            rms = librosa.feature.rms(y=samples)
            
            # Calculate confidence based on features
            tempo_confidence = min(100, max(0, (tempo - 60) / 120 * 100))
            spectral_confidence = min(100, np.mean(spectral_centroid) * 100)
            rms_confidence = min(100, np.mean(rms) * 1000)
            
            # Overall confidence
            confidence = np.mean([tempo_confidence, spectral_confidence, rms_confidence])
            
            return {
                "is_music": confidence >= self.min_confidence,
                "confidence": float(confidence),
                "tempo": float(tempo),
                "spectral_centroid": float(np.mean(spectral_centroid)),
                "rms": float(np.mean(rms))
            }
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return {
                "is_music": False,
                "confidence": 0.0,
                "error": str(e)
            }
