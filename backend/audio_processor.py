import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .music_recognition import MusicRecognizer
from .models import Track, TrackDetection, RadioStation, StationTrackStats, Artist
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
from sqlalchemy.sql import text

# Configure logging
logger = setup_logging(__name__)

class AudioProcessor:
    def __init__(self, db_session: Session, music_recognizer: MusicRecognizer):
        self.db_session = db_session
        self.music_recognizer = music_recognizer
        self.logger = logging.getLogger(__name__)
        
        # Configuration des limites de ressources optimisées
        self.max_concurrent_stations = 10
        self.max_memory_usage = 1024 * 1024 * 250  # 250 MB maximum
        self.processing_timeout = 30  # 30 secondes par station
        self.chunk_duration = 20  # Augmenté à 20 secondes d'échantillonnage
        
        # Sémaphores pour le contrôle des ressources
        self.processing_semaphore = asyncio.Semaphore(self.max_concurrent_stations)
        self.memory_semaphore = asyncio.Semaphore(self.max_concurrent_stations)
        
        # État de traitement
        self.current_tracks = {}
        self.stats_updater = StatsUpdater(db_session)
        self.processing_stations = set()
        
        # Paramètres optimisés pour l'analyse audio
        self.chunk_size = 4096
        self.sample_rate = 22050
        self.min_duration = 8  # Augmenté à 8 secondes
        self.max_duration = 20  # Augmenté à 20 secondes
        self.min_confidence = 45.0  # Réduit à 45%
        
        # Paramètres de compression audio
        self.target_bitrate = "128k"  # Augmenté à 128k
        self.target_channels = 1  # Mono
        self.target_sample_width = 2  # 16 bits
        
        logger.info("AudioProcessor initialized with optimized settings: " + 
                   f"chunk_size={self.chunk_size}, " +
                   f"sample_rate={self.sample_rate}, " +
                   f"duration={self.min_duration}-{self.max_duration}s, " +
                   f"bitrate={self.target_bitrate}")

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
        """Process a single station safely with resource monitoring and automatic reconnection"""
        max_retries = 3
        retry_delay = 5  # seconds
        current_retry = 0
        
        while current_retry < max_retries:
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
                        
                        # Vérifier l'état de la connexion
                        stream_status = await self.check_stream_status(station.stream_url)
                        if not stream_status["ok"]:
                            logger.warning(f"Stream not available for {station.name}: {stream_status['message']}")
                            if current_retry < max_retries - 1:
                                current_retry += 1
                                logger.info(f"Retrying in {retry_delay} seconds... (attempt {current_retry + 1}/{max_retries})")
                                await asyncio.sleep(retry_delay)
                                continue
                            return {
                                "error": f"Stream not available: {stream_status['message']}",
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
                            if current_retry < max_retries - 1:
                                current_retry += 1
                                logger.info(f"Retrying in {retry_delay} seconds... (attempt {current_retry + 1}/{max_retries})")
                                await asyncio.sleep(retry_delay)
                                continue
                            self._end_current_track(station.id)  # End current track if timeout
                            return {
                                "error": "Processing timeout",
                                "station": station.name,
                                "station_id": station.id,
                                "is_music": False
                            }
                            
            except Exception as e:
                logger.error(f"Error processing station {station.name}: {str(e)}")
                if current_retry < max_retries - 1:
                    current_retry += 1
                    logger.info(f"Retrying in {retry_delay} seconds... (attempt {current_retry + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    continue
                self._end_current_track(station.id)  # End current track if error
                return {
                    "error": str(e),
                    "station": station.name,
                    "station_id": station.id,
                    "is_music": False
                }
        
        return {
            "error": "Max retries reached",
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
            # Get station info for logging
            station_name = "Unknown Station"
            if station_id:
                station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
                if station:
                    station_name = station.name
            
            logger.info(f"Starting stream analysis for {station_name}")
            
            # Download and process audio chunk
            async with aiohttp.ClientSession() as session:
                async with session.get(stream_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to connect to stream: {stream_url}")
                        return {
                            "error": "Stream connection failed",
                            "is_music": False,
                            "station_id": station_id
                        }
                    
                    # Read audio data
                    audio_data = await response.read()
                    if not audio_data:
                        logger.error("No audio data received")
                        return {
                            "error": "No audio data",
                            "is_music": False,
                            "station_id": station_id
                        }
                    
                    # Recognize music
                    recognition_result = await self.music_recognizer.recognize_music(audio_data)
                    
                    if not recognition_result:
                        logger.info(f"No music detected in stream: {station_name}")
                        return {
                            "is_music": False,
                            "confidence": 0,
                            "station_id": station_id
                        }
                    
                    # Calculate play duration
                    try:
                        audio = AudioSegment.from_file(io.BytesIO(audio_data))
                        play_duration = timedelta(milliseconds=len(audio))
                    except Exception as e:
                        logger.error(f"Error calculating play duration: {str(e)}")
                        play_duration = timedelta(seconds=30)  # Default duration
                    
                    # Create detection record
                    try:
                        # Get track from database
                        track = self.db_session.query(Track).join(Artist).filter(
                            Track.title == recognition_result['title'],
                            Artist.name == recognition_result['artist']
                        ).first()
                        
                        if track:
                            detection = TrackDetection(
                                track_id=track.id,
                                station_id=station_id,
                                detected_at=datetime.now(),
                                confidence=recognition_result['confidence'],
                                play_duration=play_duration
                            )
                            
                            self.db_session.add(detection)
                            
                            # Update station's last detection time and total play time
                            if station_id:
                                self.db_session.execute(text("""
                                    UPDATE radio_stations 
                                    SET last_detection_time = :now,
                                        total_play_time = COALESCE(total_play_time, interval '0') + :duration
                                    WHERE id = :station_id
                                """), {
                                    'now': datetime.now(),
                                    'duration': play_duration,
                                    'station_id': station_id
                                })
                            
                            self.db_session.commit()
                            
                            logger.info(f"Detection saved: {track.title} by {track.artist.name} on {station_name}")
                            
                            return {
                                "is_music": True,
                                "confidence": detection.confidence,
                                "station_id": station_id,
                                "track": {
                                    "id": track.id,
                                    "title": track.title,
                                    "artist": track.artist.name,
                                    "isrc": track.isrc,
                                    "label": track.label,
                                    "album": track.album
                                },
                                "duration_minutes": play_duration.total_seconds() / 60,
                                "detected_at": detection.detected_at.isoformat()
                            }
                    
                    except Exception as e:
                        logger.error(f"Error saving detection: {str(e)}")
                        self.db_session.rollback()
                        return {
                            "error": "Failed to save detection",
                            "is_music": True,
                            "station_id": station_id,
                            "recognition_result": recognition_result
                        }
            
        except Exception as e:
            logger.error(f"Error analyzing stream: {str(e)}")
            return {
                "error": str(e),
                "is_music": False,
                "station_id": station_id
            }

    def _end_current_track(self, station_id: int):
        """Terminer le suivi du morceau en cours et mettre à jour sa durée de lecture"""
        try:
            current_track_info = self.current_tracks.get(station_id)
            if not current_track_info:
                return
            
            # Calculer la durée réelle de lecture avec précision
            end_time = datetime.now()
            start_time = current_track_info['start_time']
            play_duration = end_time - start_time
            
            # Validation avancée de la durée
            duration_seconds = play_duration.total_seconds()
            
            # Vérifier si la durée est réaliste
            if duration_seconds < 10:  # Minimum 10 secondes pour éviter les faux positifs
                logger.warning(f"Play duration too short ({duration_seconds:.1f}s), skipping update")
                return
            elif duration_seconds > 900:  # Maximum 15 minutes
                logger.warning(f"Play duration too long ({duration_seconds:.1f}s), limiting to 15 minutes")
                play_duration = timedelta(minutes=15)
            
            # Mettre à jour la détection avec la durée réelle
            detection = self.db_session.query(TrackDetection).get(current_track_info['detection_id'])
            if detection:
                detection.play_duration = play_duration
                detection.end_time = end_time  # Ajouter le timestamp de fin
                
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
                    stats = self._update_station_track_stats(station_id, track.id, play_duration)
                    
                    # Enregistrer l'historique de lecture
                    self._log_play_history(station_id, track.id, start_time, end_time, duration_seconds)
                
                # Commit des changements
                self.db_session.commit()
                logger.info(
                    f"Updated play duration for track {track.title} on station {station_id}: "
                    f"{play_duration.total_seconds():.1f} seconds (from {start_time} to {end_time})"
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
        """Créer ou obtenir un morceau à partir du résultat de reconnaissance"""
        try:
            # Vérifier si le résultat est valide
            if not result or not isinstance(result, dict):
                self.logger.error("Invalid result format: result is None or not a dict")
                return None

            # Si un track_id est fourni, récupérer directement le morceau
            if result.get('track_id'):
                track = self.db_session.query(Track).get(result['track_id'])
                if track:
                    return track

            # Extraire les informations de base
            title = result.get('title', 'Unknown Track')
            artist_name = result.get('artist', 'Unknown Artist')
            isrc = result.get('isrc')
            confidence = result.get('confidence', 0)
            play_duration = result.get('play_duration')
            
            # Obtenir ou créer l'artiste
            artist = None
            if artist_name != "Unknown Artist":
                artist = self.db_session.query(Artist).filter(Artist.name == artist_name).first()
                if not artist:
                    artist = Artist(
                        name=artist_name,
                        created_at=datetime.utcnow(),
                        total_play_time=timedelta(0),
                        total_plays=0
                    )
                    self.db_session.add(artist)
                    self.db_session.flush()
            
            # Chercher la piste existante
            track = None
            if isrc:
                track = self.db_session.query(Track).filter(Track.isrc == isrc).first()
            
            if not track and artist:
                track = self.db_session.query(Track).filter(
                    Track.title == title,
                    Track.artist_id == artist.id
                ).first()
            elif not track:
                track = self.db_session.query(Track).filter(
                    Track.title == title,
                    Track.artist_id.is_(None)
                ).first()
            
            # Si la piste n'existe pas, la créer
            if not track:
                track = Track(
                    title=title,
                    artist_id=artist.id if artist else None,
                    isrc=isrc,
                    play_count=0,
                    total_play_time=timedelta(0),
                    created_at=datetime.utcnow(),
                    fingerprint=result.get('fingerprint')
                )
                self.db_session.add(track)
                self.db_session.flush()
            
            # Mettre à jour les statistiques si une durée est fournie
            if play_duration and isinstance(play_duration, timedelta):
                if not track.total_play_time:
                    track.total_play_time = timedelta(0)
                track.total_play_time += play_duration
                track.play_count += 1
                track.last_played = datetime.now()
                
                if artist:
                    if not artist.total_play_time:
                        artist.total_play_time = timedelta(0)
                    artist.total_play_time += play_duration
                    artist.total_plays += 1
            
            return track
            
        except Exception as e:
            self.logger.error(f"Error in _get_or_create_track: {str(e)}")
            self.db_session.rollback()
            return None

    async def _download_audio_chunk(self, url: str) -> bytes:
        """Download a chunk of audio from the stream with retries"""
        max_retries = 3
        retry_delay = 2  # seconds
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                logger.info(f"Starting audio download from {url} (attempt {current_retry + 1}/{max_retries})")
                timeout = aiohttp.ClientTimeout(total=30)  # Increased timeout
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': '*/*',
                        'Connection': 'keep-alive',
                        'Accept-Encoding': 'gzip, deflate',
                        'Cache-Control': 'no-cache'
                    }
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logger.error(f"HTTP {response.status} error downloading from {url}")
                            if current_retry < max_retries - 1:
                                current_retry += 1
                                await asyncio.sleep(retry_delay * (current_retry + 1))
                                continue
                            return None
                        
                        logger.info(f"Connected to stream {url}, starting to read data")
                        total_data = bytearray()
                        total_size = 0
                        max_size = 10 * 1024 * 1024  # 10MB limit
                        
                        while total_size < max_size:
                            try:
                                chunk = await asyncio.wait_for(
                                    response.content.read(8192 * 4),  # 32KB chunks
                                    timeout=5.0
                                )
                                
                                if not chunk:
                                    break
                                    
                                total_data.extend(chunk)
                                total_size += len(chunk)
                                
                            except asyncio.TimeoutError:
                                if total_size > 0:
                                    break
                                raise
                        
                        if total_size == 0:
                            logger.error(f"No data received from {url}")
                            if current_retry < max_retries - 1:
                                current_retry += 1
                                await asyncio.sleep(retry_delay * (current_retry + 1))
                                continue
                            return None
                        
                        logger.info(f"Successfully read {total_size} bytes from {url}")
                        return bytes(total_data)
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Error downloading from {url}: {str(e)}")
                if current_retry < max_retries - 1:
                    current_retry += 1
                    await asyncio.sleep(retry_delay * (current_retry + 1))
                    continue
                return None
                
            except Exception as e:
                logger.error(f"Error downloading from {url}: {str(e)}", exc_info=True)
                if current_retry < max_retries - 1:
                    current_retry += 1
                    await asyncio.sleep(retry_delay * (current_retry + 1))
                    continue
                return None
        
        logger.error(f"All retries failed for {url}")
        return None

    def _compress_audio(self, audio_data: bytes) -> bytes:
        """Compress audio data to reduce size while maintaining quality"""
        try:
            # Convertir les données en AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Convertir en mono si stéréo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Réduire le sample rate
            if audio.frame_rate > self.sample_rate:
                audio = audio.set_frame_rate(self.sample_rate)
            
            # Réduire la profondeur des échantillons à 16 bits
            if audio.sample_width > 2:
                audio = audio.set_sample_width(2)
            
            # Exporter avec compression
            output = io.BytesIO()
            audio.export(
                output,
                format="mp3",
                bitrate=self.target_bitrate,
                parameters=["-q:a", "5"]  # Qualité VBR moyenne (0-9, 5 est un bon compromis)
            )
            
            compressed_data = output.getvalue()
            compression_ratio = len(audio_data) / len(compressed_data)
            self.logger.info(f"Audio compressed with ratio {compression_ratio:.2f}x")
            
            return compressed_data
            
        except Exception as e:
            self.logger.error(f"Error compressing audio: {str(e)}")
            return audio_data  # Retourner les données non compressées en cas d'erreur

    async def _analyze_audio_features(self, audio_data: bytes) -> float:
        try:
            if not audio_data:
                self.logger.error("Empty audio data received")
                return 0.0

            # Convertir et optimiser l'audio
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Réduire la qualité pour l'analyse
            if audio.channels > 1:
                audio = audio.set_channels(1)
            if audio.frame_rate > self.sample_rate:
                audio = audio.set_frame_rate(self.sample_rate)
            
            # Convertir en numpy array avec optimisation mémoire
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / np.iinfo(samples.dtype).max
            
            # Utiliser des fenêtres plus grandes pour une meilleure résolution fréquentielle
            frame_length = 2048  # Augmenté pour une meilleure résolution
            hop_length = 512    # Maintenu pour la précision
            
            # Calculer les caractéristiques avec des paramètres optimisés
            rms = librosa.feature.rms(
                y=samples,
                frame_length=frame_length,
                hop_length=hop_length
            )[0]
            
            zcr = librosa.feature.zero_crossing_rate(
                samples,
                frame_length=frame_length,
                hop_length=hop_length
            )[0]
            
            spectral_centroid = librosa.feature.spectral_centroid(
                y=samples,
                sr=self.sample_rate,
                n_fft=frame_length,
                hop_length=hop_length
            )[0]
            
            # Ajouter le calcul du spectral rolloff pour mieux détecter la présence de musique
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=samples,
                sr=self.sample_rate,
                n_fft=frame_length,
                hop_length=hop_length
            )[0]
            
            # Calcul optimisé du score musical avec plus de paramètres
            music_score = (
                (min(np.mean(spectral_centroid) / 4000, 1.0) * 25) +  # Réduit à 25%
                (max(1 - np.std(rms) * 8, 0.0) * 25) +               # Réduit à 25%
                (max(1 - np.mean(zcr) * 80, 0.0) * 20) +            # Maintenu à 20%
                (min(np.mean(spectral_rolloff) / 8000, 1.0) * 30)   # Ajouté avec 30%
            )
            
            self.logger.info(
                f"Audio analysis results - RMS std: {np.std(rms):.3f}, "
                f"ZCR mean: {np.mean(zcr):.3f}, "
                f"Centroid mean: {np.mean(spectral_centroid):.3f}, "
                f"Rolloff mean: {np.mean(spectral_rolloff):.3f}, "
                f"Music score: {music_score:.1f}"
            )
            
            return music_score
            
        except Exception as e:
            self.logger.error(f"Error analyzing audio features: {str(e)}")
            return 0.0

    def _save_track_to_db(self, recognition_result: Dict[str, Any]) -> Track:
        """Save recognized track to database if it doesn't exist."""
        title = recognition_result.get('title', '')
        artist_name = recognition_result.get('artist', '')
        isrc = recognition_result.get('isrc', '')
        
        # Get actual play duration in minutes
        play_duration = recognition_result.get('play_duration')
        if isinstance(play_duration, timedelta):
            duration_minutes = play_duration.total_seconds() / 60
        else:
            duration_minutes = float(recognition_result.get('duration_minutes', 0))
            if not duration_minutes and play_duration:
                try:
                    duration_minutes = float(str(play_duration).split(':')[-1]) / 60
                except (ValueError, IndexError):
                    duration_minutes = 0
        
        logger.debug(f"Checking if track exists: {title} by {artist_name}")
        
        # Get or create artist
        artist = self.db_session.query(Artist).filter_by(name=artist_name).first()
        if not artist:
            artist = Artist(name=artist_name, created_at=datetime.now())
            self.db_session.add(artist)
            self.db_session.flush()
        
        # Check if track exists
        track = self.db_session.query(Track).filter_by(
            title=title,
            artist_id=artist.id
        ).first()
        
        if not track:
            logger.info(f"Creating new track record: {title} by {artist_name}")
            # Create new track
            track = Track(
                title=title,
                artist_id=artist.id,
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
        """Check stream status and get stream parameters with detailed diagnostics."""
        try:
            self.logger.info(f"Checking stream status for URL: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity;q=1, *;q=0',
                'Range': 'bytes=0-',
                'Connection': 'keep-alive',
                'Icy-MetaData': '1'
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    # First try HEAD request
                    try:
                        async with session.head(url, headers=headers, timeout=5) as response:
                            if response.status == 200:
                                self.logger.info(f"HEAD request successful for {url}")
                    except Exception as e:
                        self.logger.warning(f"HEAD request failed for {url}: {str(e)}, trying GET...")
                    
                    # Main connection check with GET
                    async with session.get(url, headers=headers, timeout=10) as response:
                        self.logger.info(f"Initial response status: {response.status}")
                        self.logger.info(f"Response headers: {response.headers}")
                        
                        if response.status != 200:
                            return {
                                "ok": False,
                                "message": f"Stream returned status code {response.status}",
                                "diagnostics": {
                                    "status_code": response.status,
                                    "headers": dict(response.headers),
                                    "url": url
                                }
                            }
                        
                        # Read initial chunk with timeout
                        try:
                            chunk = await asyncio.wait_for(
                                response.content.read(8192),
                                timeout=5
                            )
                            if not chunk:
                                return {
                                    "ok": False,
                                    "message": "Stream is empty",
                                    "diagnostics": {
                                        "status_code": response.status,
                                        "headers": dict(response.headers),
                                        "url": url
                                    }
                                }
                        except asyncio.TimeoutError:
                            return {
                                "ok": False,
                                "message": "Timeout reading stream data",
                                "diagnostics": {
                                    "status_code": response.status,
                                    "headers": dict(response.headers),
                                    "url": url
                                }
                            }
                        
                        # Analyze content type and stream metadata
                        content_type = response.headers.get('Content-Type', '').lower()
                        icy_metaint = response.headers.get('icy-metaint')
                        icy_name = response.headers.get('icy-name')
                        icy_br = response.headers.get('icy-br')
                        
                        self.logger.info(f"Content-Type: {content_type}")
                        self.logger.info(f"ICY Metadata: metaint={icy_metaint}, name={icy_name}, bitrate={icy_br}")
                        
                        # Validate content type
                        valid_types = ['audio', 'stream', 'mpegurl', 'octet-stream']
                        if not any(t in content_type for t in valid_types):
                            return {
                                "ok": False,
                                "message": f"Invalid content type: {content_type}",
                                "diagnostics": {
                                    "content_type": content_type,
                                    "valid_types": valid_types,
                                    "headers": dict(response.headers),
                                    "url": url
                                }
                            }
                        
                        # Analyze audio chunk
                        try:
                            audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk))
                            if len(audio_segment) == 0:
                                return {
                                    "ok": False,
                                    "message": "Invalid audio data",
                                    "diagnostics": {
                                        "chunk_size": len(chunk),
                                        "content_type": content_type,
                                        "url": url
                                    }
                                }
                        except Exception as e:
                            self.logger.warning(f"Audio analysis failed: {str(e)}")
                            # Continue anyway as some streams might need more data for proper analysis
                        
                        return {
                            "ok": True,
                            "message": "Stream is active and valid",
                            "content_type": content_type,
                            "icy_name": icy_name,
                            "bitrate": icy_br,
                            "metadata_interval": icy_metaint,
                            "diagnostics": {
                                "status_code": response.status,
                                "headers": dict(response.headers),
                                "content_type": content_type,
                                "chunk_size": len(chunk),
                                "url": url
                            }
                        }
                        
                except aiohttp.ClientError as e:
                    self.logger.error(f"HTTP error: {str(e)}")
                    return {
                        "ok": False,
                        "message": f"HTTP error: {str(e)}",
                        "diagnostics": {
                            "error_type": "client_error",
                            "error": str(e),
                            "url": url
                        }
                    }
                except asyncio.TimeoutError:
                    self.logger.error("Connection timeout")
                    return {
                        "ok": False,
                        "message": "Connection timeout",
                        "diagnostics": {
                            "error_type": "timeout",
                            "url": url
                        }
                    }
                        
        except Exception as e:
            self.logger.error(f"Error checking stream status: {str(e)}")
            return {
                "ok": False,
                "message": f"Error connecting to stream: {str(e)}",
                "diagnostics": {
                    "error_type": "general_error",
                    "error": str(e),
                    "url": url
                }
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

    def _log_play_history(self, station_id: int, track_id: int, start_time: datetime, end_time: datetime, duration_seconds: float):
        """Enregistrer l'historique détaillé de lecture"""
        try:
            logger.info(
                "Play history",
                extra={
                    'station_id': station_id,
                    'track_id': track_id,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration_seconds,
                    'type': 'play_history'
                }
            )
        except Exception as e:
            logger.error(f"Error logging play history: {str(e)}")

    async def monitor_stations(self, stations: List[RadioStation]) -> None:
        """Continuously monitor stations and handle reconnections.
        
        This method runs in the background and:
        1. Checks each station's status periodically
        2. Attempts to reconnect to failed stations
        3. Updates station status in the database
        4. Broadcasts status changes via WebSocket
        """
        while True:
            try:
                for station in stations:
                    try:
                        # Vérifier le statut du flux
                        status = await self.check_stream_status(station.stream_url)
                        
                        # Mettre à jour le statut dans la base de données
                        station.is_active = status["ok"]
                        station.last_checked = datetime.now()
                        station.status = status["message"]
                        self.db_session.commit()
                        
                        # Si la station était active et ne l'est plus
                        if not status["ok"] and station.id in self.current_tracks:
                            self._end_current_track(station.id)
                            logger.warning(
                                f"Station {station.name} disconnected: {status['message']}",
                                extra={"diagnostics": status.get("diagnostics", {})}
                            )
                        
                        # Broadcaster la mise à jour
                        await broadcast_station_update({
                            "id": station.id,
                            "name": station.name,
                            "status": status["message"],
                            "is_active": status["ok"],
                            "last_checked": datetime.now().isoformat(),
                            "diagnostics": status.get("diagnostics", {}),
                            "stream_url": station.stream_url
                        })
                        
                    except Exception as e:
                        logger.error(f"Error monitoring station {station.name}: {str(e)}")
                        continue
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(30)  # Vérifier toutes les 30 secondes
                
            except Exception as e:
                logger.error(f"Error in station monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Attendre plus longtemps en cas d'erreur
                continue

    async def monitor_station_health(self, station_id: int, station_url: str):
        """
        Monitor a station's health and handle reconnections
        """
        MAX_CONSECUTIVE_FAILURES = 5
        HEALTH_CHECK_INTERVAL = 30  # seconds
        consecutive_failures = 0
        
        while True:
            try:
                # Check if station is still marked as active in DB
                async with self.pool.acquire() as conn:
                    station = await conn.fetchrow(
                        "SELECT is_active FROM radio_stations WHERE id = $1",
                        station_id
                    )
                    if not station or not station['is_active']:
                        logger.info(f"Station {station_id} is no longer active, stopping health monitor")
                        return

                # Try to download a chunk to verify connection
                chunk = await self._download_audio_chunk(station_url)
                
                if chunk:
                    # Connection successful
                    if consecutive_failures > 0:
                        logger.info(f"Station {station_id} reconnected successfully after {consecutive_failures} failures")
                        consecutive_failures = 0
                        
                    # Update last_checked timestamp
                    async with self.pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE radio_stations 
                            SET last_checked = NOW(),
                                status = 'online'
                            WHERE id = $1
                            """,
                            station_id
                        )
                else:
                    consecutive_failures += 1
                    logger.warning(f"Station {station_id} health check failed ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
                    
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        logger.error(f"Station {station_id} has failed {MAX_CONSECUTIVE_FAILURES} consecutive health checks")
                        
                        # Update station status
                        async with self.pool.acquire() as conn:
                            await conn.execute(
                                """
                                UPDATE radio_stations 
                                SET status = 'offline',
                                    last_checked = NOW()
                                WHERE id = $1
                                """,
                                station_id
                            )
                            
                        # Try to reconnect
                        logger.info(f"Attempting to reconnect to station {station_id}")
                        if await self._reconnect_station(station_id, station_url):
                            consecutive_failures = 0
                        
            except Exception as e:
                logger.error(f"Error monitoring station {station_id}: {str(e)}", exc_info=True)
                
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            
    async def _reconnect_station(self, station_id: int, station_url: str) -> bool:
        """
        Attempt to reconnect to a station
        Returns True if reconnection was successful
        """
        MAX_RECONNECT_ATTEMPTS = 3
        RECONNECT_DELAY = 5  # seconds
        
        for attempt in range(MAX_RECONNECT_ATTEMPTS):
            try:
                logger.info(f"Reconnection attempt {attempt + 1}/{MAX_RECONNECT_ATTEMPTS} for station {station_id}")
                
                # Try to establish connection
                chunk = await self._download_audio_chunk(station_url)
                if chunk:
                    logger.info(f"Successfully reconnected to station {station_id}")
                    
                    # Update station status
                    async with self.pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE radio_stations 
                            SET status = 'online',
                                last_checked = NOW()
                            WHERE id = $1
                            """,
                            station_id
                        )
                    return True
                    
            except Exception as e:
                logger.error(f"Error during reconnection attempt for station {station_id}: {str(e)}")
                
            await asyncio.sleep(RECONNECT_DELAY)
            
        logger.error(f"All reconnection attempts failed for station {station_id}")
        return False

    async def start_monitoring(self):
        """
        Start monitoring all active stations
        """
        try:
            # Get all active stations
            async with self.pool.acquire() as conn:
                stations = await conn.fetch(
                    "SELECT id, stream_url FROM radio_stations WHERE is_active = true"
                )
            
            # Start monitoring tasks for each station
            monitoring_tasks = []
            for station in stations:
                task = asyncio.create_task(
                    self.monitor_station_health(station['id'], station['stream_url'])
                )
                monitoring_tasks.append(task)
                
            logger.info(f"Started monitoring {len(monitoring_tasks)} active stations")
            
            # Wait for all monitoring tasks
            await asyncio.gather(*monitoring_tasks)
            
        except Exception as e:
            logger.error(f"Error starting station monitoring: {str(e)}", exc_info=True)

    def _process_recognition_result(self, recognition_result: Dict, station_id: int) -> Optional[Dict]:
        """Process recognition result and save to database"""
        try:
            # Extract basic info
            title = recognition_result.get('title', 'Unknown Track')
            artist = recognition_result.get('artist', 'Unknown Artist')
            play_duration = recognition_result.get('play_duration')
            
            # Calculate duration in minutes
            duration_minutes = float(recognition_result.get('duration_minutes', 0))
            if not duration_minutes and play_duration:
                try:
                    duration_minutes = float(str(play_duration).split(':')[-1]) / 60
                except (ValueError, IndexError):
                    duration_minutes = 0
            
            logger.debug(f"Processing recognition result for {title} by {artist}")
            
            # Get or create track
            track = self._get_or_create_track(recognition_result)
            if not track:
                logger.error("Failed to get or create track")
                return None
            
            # Create detection record
            detection = {
                'track_id': track.id,
                'station_id': station_id,
                'detected_at': datetime.now(),
                'confidence': recognition_result.get('confidence', 0),
                'duration_minutes': duration_minutes
            }
            
            # Update statistics
            self._update_station_track_stats(station_id, track.id, duration_minutes)
            
            return detection
            
        except Exception as e:
            logger.error(f"Error processing recognition result: {str(e)}", exc_info=True)
            return None

    def _detect_rhythm_strength(self, samples: np.ndarray, sample_rate: int) -> float:
        """
        Detect rhythm strength in audio using onset detection and tempo estimation
        Returns value between 0-100
        """
        try:
            # Paramètres optimisés pour la détection du rythme
            hop_length = 512
            frame_length = 2048
            
            # Calculer l'enveloppe d'onset avec plusieurs features
            onset_env = librosa.onset.onset_strength(
                y=samples,
                sr=sample_rate,
                hop_length=hop_length,
                aggregate=np.median,  # Utiliser la médiane pour plus de robustesse
                fmax=8000,  # Limiter la fréquence maximale
                n_mels=128  # Augmenter le nombre de bandes mel
            )
            
            # Détecter le tempo et la force du beat
            tempo, beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sample_rate,
                hop_length=hop_length,
                start_bpm=100,  # BPM de départ typique pour la musique
                tightness=100  # Augmenter la précision
            )
            
            # Calculer la périodicité du signal
            ac = librosa.autocorrelate(onset_env, max_size=2 * sample_rate // hop_length)
            ac = ac[1:]  # Ignorer le lag zéro
            
            # Trouver les pics dans l'autocorrélation
            peaks = librosa.util.peak_pick(
                ac,
                pre_max=30,  # Augmenter la fenêtre de recherche
                post_max=30,
                pre_avg=30,
                post_avg=30,
                delta=0.5,  # Réduire le seuil pour détecter plus de pics
                wait=20
            )
            
            if len(peaks) == 0:
                return 0
            
            # Calculer la force du rythme basée sur plusieurs facteurs
            
            # 1. Force des pics d'autocorrélation
            peak_values = ac[peaks]
            ac_strength = np.mean(peak_values) * 50  # Normaliser à 50%
            
            # 2. Régularité du tempo
            if len(beat_frames) > 1:
                beat_intervals = np.diff(beat_frames)
                tempo_regularity = 1 - np.std(beat_intervals) / np.mean(beat_intervals)
                tempo_regularity = max(0, min(tempo_regularity * 30, 30))  # Normaliser à 30%
            else:
                tempo_regularity = 0
            
            # 3. Force des onsets
            onset_strength = np.mean(onset_env) * 20  # Normaliser à 20%
            
            # Combiner les scores
            rhythm_strength = ac_strength + tempo_regularity + onset_strength
            
            # Ajuster le score final
            if tempo >= 60 and tempo <= 200:  # Plage typique de BPM pour la musique
                rhythm_strength *= 1.2  # Bonus pour tempo musical
            
            self.logger.debug(
                f"Rhythm analysis - Tempo: {tempo:.1f} BPM, "
                f"AC strength: {ac_strength:.1f}, "
                f"Tempo regularity: {tempo_regularity:.1f}, "
                f"Onset strength: {onset_strength:.1f}, "
                f"Final strength: {rhythm_strength:.1f}"
            )
            
            return min(100, max(0, rhythm_strength))
            
        except Exception as e:
            self.logger.error(f"Error detecting rhythm: {str(e)}")
            return 0
