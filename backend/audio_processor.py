import requests
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from music_recognition import MusicRecognizer
from models import Track, TrackDetection
from sqlalchemy.orm import Session
import io
import aiohttp
import numpy as np
import asyncio
import av

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, db_session: Session, music_recognizer: MusicRecognizer):
        self.db_session = db_session
        self.music_recognizer = music_recognizer
        self.current_track = None
        self.track_start_time = None
        self.logger = logging.getLogger(__name__)
        logger.info("Initializing AudioProcessor")

    async def analyze_stream(self, stream_url: str, station_id: int):
        try:
            # Download a 15-second sample of the stream
            target_size = 320 * 1024  # 320KB for better quality samples
            audio_data = await self._download_stream_sample(stream_url, target_size)
            
            if not audio_data:
                self.logger.error(f"Failed to download audio from stream: {stream_url}")
                return None

            # Analyze audio features to determine if it's likely music
            music_likelihood = await self._analyze_audio_features(audio_data)
            if music_likelihood < 0.5:  # Less than 50% likely to be music
                self.logger.info(f"Audio sample unlikely to be music (likelihood: {music_likelihood})")
                return None

            # Recognize the music
            result = await self.music_recognizer.recognize(audio_data)
            
            if result and 'track' in result:
                # Create or update track record
                track = self._get_or_create_track(result)
                
                # Get actual duration from recognition result or default to 15 seconds
                duration_minutes = result.get('duration_minutes', 0.25)  # 0.25 minutes = 15 seconds
                play_duration = timedelta(minutes=duration_minutes)
                
                # Create detection record with station_id
                detection = TrackDetection(
                    station_id=station_id,
                    track_id=track.id,
                    confidence=result.get('confidence', 0),
                    detected_at=datetime.now(),
                    play_duration=play_duration  # Use actual duration
                )
                
                self.db_session.add(detection)
                await self.db_session.commit()
                
                return {
                    'id': detection.id,
                    'track': {
                        'id': track.id,
                        'title': track.title,
                        'artist': track.artist,
                        'isrc': track.isrc
                    },
                    'confidence': detection.confidence,
                    'detected_at': detection.detected_at.isoformat(),
                    'play_duration': str(play_duration),
                    'station_id': station_id
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing stream: {str(e)}")
            return None

    def _get_or_create_track(self, result):
        # Extract track info
        track_info = result['track']
        isrc = track_info.get('isrc')
        
        # Try to find existing track by ISRC first if available
        track = None
        if isrc:
            track = self.db_session.query(Track).filter_by(isrc=isrc).first()
        
        # If no track found by ISRC, try by title and artist
        if not track:
            track = self.db_session.query(Track).filter_by(
                title=track_info.get('title'),
                artist=track_info.get('artist')
            ).first()
            
            # If track exists but has no ISRC, update it
            if track and isrc and not track.isrc:
                track.isrc = isrc
                self.logger.info(f"Updated ISRC for track {track.id}: {isrc}")
        
        if not track:
            # Create new track if not found
            duration_minutes = track_info.get('duration_minutes', 0.25)  # 0.25 minutes = 15 seconds
            track = Track(
                title=track_info.get('title'),
                artist=track_info.get('artist'),
                isrc=isrc,
                album=track_info.get('album'),
                label=track_info.get('label'),
                release_date=track_info.get('release_date'),
                external_ids=track_info.get('external_metadata', {}),
                play_count=1,
                total_play_time=timedelta(minutes=duration_minutes),  # Use actual duration
                last_played=datetime.now()
            )
            self.db_session.add(track)
            self.db_session.flush()
            self.logger.info(f"Created new track with ISRC: {isrc}")
        
        return track

    async def _download_stream_sample(self, url: str, target_size: int) -> bytes:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to connect to stream: {url}, status: {response.status}")
                        return None
                    
                    chunks = []
                    total_size = 0
                    
                    while total_size < target_size:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        total_size += len(chunk)
                    
                    return b''.join(chunks)
        except Exception as e:
            self.logger.error(f"Error downloading stream: {str(e)}")
            return None

    async def _analyze_audio_features(self, audio_data: bytes) -> float:
        try:
            # Convert audio bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize samples
            normalized = audio_array.astype(np.float32) / 32768.0
            
            # Calculate basic audio features
            rms = np.sqrt(np.mean(normalized**2))
            zero_crossings = np.sum(np.abs(np.diff(np.signbit(normalized))))
            spectral_centroid = np.mean(np.abs(np.fft.rfft(normalized)))
            
            # Simple heuristic for music likelihood
            # High RMS (volume), moderate zero crossings, and high spectral centroid
            # typically indicate music rather than speech
            music_likelihood = (
                min(rms * 2, 1.0) * 0.4 +
                min(zero_crossings / len(normalized) * 100, 1.0) * 0.3 +
                min(spectral_centroid / 1000, 1.0) * 0.3
            )
            
            return music_likelihood
        except Exception as e:
            self.logger.error(f"Error analyzing audio features: {str(e)}")
            return 0.0

    def _save_track_to_db(self, recognition_result: Dict[str, Any]) -> Track:
        """Save recognized track to database if it doesn't exist."""
        title = recognition_result.get('title', '')
        artist = recognition_result.get('artist', '')
        isrc = recognition_result.get('isrc', '')
        duration_minutes = recognition_result.get('duration_minutes', 0.25)  # 0.25 minutes = 15 seconds
        
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
                external_ids=recognition_result.get('external_metadata', {}),
                play_count=1,
                total_play_time=timedelta(minutes=duration_minutes),  # Use actual duration
                last_played=datetime.now()
            )
            self.db_session.add(track)
            self.db_session.commit()
            logger.debug(f"New track saved with ID: {track.id}")
        else:
            # Update last played time and total play time
            track.last_played = datetime.now()
            track.play_count += 1
            if track.total_play_time:
                track.total_play_time += timedelta(minutes=duration_minutes)
            else:
                track.total_play_time = timedelta(minutes=duration_minutes)
            if isrc and not track.isrc:
                track.isrc = isrc
            self.db_session.commit()
            logger.debug(f"Updated track {track.id}: play count = {track.play_count}, total play time = {track.total_play_time}")
        
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
