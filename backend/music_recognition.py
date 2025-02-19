import requests
import logging
from typing import Dict, Any, Optional, Tuple
import io
from pydub import AudioSegment
import os
from dotenv import load_dotenv
import numpy as np
import librosa
from datetime import datetime, timedelta
import musicbrainzngs
from sqlalchemy.orm import Session
from models import Track
import acoustid
import hashlib
from functools import lru_cache
from utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Load environment variables
load_dotenv()

class MusicRecognizer:
    def __init__(self, db_session: Session, audd_api_key: Optional[str] = None):
        """Initialize music recognizer with API key"""
        self.db_session = db_session
        self.audd_api_key = audd_api_key or os.getenv('AUDD_API_KEY')
        self.initialized = False
        logger.info("Initializing MusicRecognizer")
        
        # Initialize MusicBrainz
        musicbrainzngs.set_useragent(
            "SODAV Monitor",
            "1.0",
            "https://sodav.sn"
        )
        
        if not self.audd_api_key:
            logger.warning("AudD API key not found")

    async def initialize(self) -> None:
        """Initialize the music recognizer service"""
        try:
            if self.initialized:
                logger.info("MusicRecognizer already initialized")
                return

            logger.info("Starting MusicRecognizer initialization...")
            
            # Test AudD API connection
            if self.audd_api_key:
                logger.info("Testing AudD API connection...")
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://api.audd.io/test/?api_token={self.audd_api_key}') as response:
                            if response.status == 200:
                                logger.info("✅ AudD API connection successful")
                            else:
                                logger.warning(f"⚠️ AudD API test failed with status code: {response.status}")
                except Exception as e:
                    logger.error(f"❌ AudD API connection error: {str(e)}")
                    # Don't raise here, we can still function with local database
            else:
                logger.warning("⚠️ No AudD API key provided, will use local database only")
            
            # Test MusicBrainz connection
            logger.info("Testing MusicBrainz connection...")
            try:
                # Test with a known artist ID (Michael Jackson)
                test_artist_id = 'f27ec8db-af05-4f36-916e-3d57f91ecf5e'
                artist_info = musicbrainzngs.get_artist_by_id(test_artist_id)
                if artist_info and artist_info.get('artist', {}).get('name'):
                    logger.info("✅ MusicBrainz connection successful")
                else:
                    logger.warning("⚠️ MusicBrainz response format unexpected")
            except Exception as e:
                logger.error(f"❌ MusicBrainz test failed: {str(e)}")
                # Don't raise here, we can still function with AudD
            
            # Test database connection
            logger.info("Testing database connection...")
            try:
                # Try to query the Track table
                self.db_session.query(Track).limit(1).all()
                logger.info("✅ Database connection successful")
            except Exception as e:
                logger.error(f"❌ Database connection error: {str(e)}")
                raise  # Database is critical, so we raise this error
            
            self.initialized = True
            logger.info("✅ MusicRecognizer initialization completed successfully")
            
        except Exception as e:
            error_msg = f"❌ Error during MusicRecognizer initialization: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    @staticmethod
    def _calculate_audio_hash(audio_data: bytes) -> str:
        """Calculate a hash of the audio data for caching"""
        return hashlib.md5(audio_data).hexdigest()

    @lru_cache(maxsize=1000)
    def _get_fingerprint(self, audio_hash: str) -> Tuple[float, str]:
        """Get fingerprint from cache or generate it"""
        # Check if we have this fingerprint in the database
        track = self.db_session.query(Track).filter(
            Track.fingerprint == audio_hash
        ).first()
        
        if track and track.fingerprint_raw:
            logger.info(f"Found cached fingerprint for track: {track.title}")
            return track.fingerprint_raw
        
        return None

    def _save_fingerprint(self, audio_hash: str, fingerprint_raw: bytes, track: Track) -> None:
        """Save fingerprint to database"""
        try:
            track.fingerprint = audio_hash
            track.fingerprint_raw = list(fingerprint_raw)  # Convert to list for storage
            self.db_session.commit()
            logger.info(f"Saved fingerprint for track: {track.title}")
        except Exception as e:
            logger.error(f"Error saving fingerprint: {str(e)}")
            self.db_session.rollback()

    def _analyze_audio_features(self, audio_data: bytes) -> Dict[str, float]:
        """
        Analyze audio features to determine if the content is music or speech
        Returns dict with features and likelihood scores
        """
        try:
            # Convert audio bytes to numpy array
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            # Convert to mono if stereo
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # Normalize samples
            samples = samples / np.max(np.abs(samples))
            
            # Get sample rate
            sample_rate = audio.frame_rate
            
            # Calculate features
            # Spectral Centroid - higher for music, lower for speech
            cent = librosa.feature.spectral_centroid(y=samples, sr=sample_rate)[0]
            
            # RMS Energy - music typically has more consistent energy
            rms = librosa.feature.rms(y=samples)[0]
            
            # Zero Crossing Rate - typically higher for speech
            zcr = librosa.feature.zero_crossing_rate(samples)[0]
            
            # Spectral Rolloff - typically higher for music
            rolloff = librosa.feature.spectral_rolloff(y=samples, sr=sample_rate)[0]
            
            # Calculate averages
            features = {
                'spectral_centroid_mean': float(np.mean(cent)),
                'rms_energy_std': float(np.std(rms)),  # Variation in energy
                'zero_crossing_rate_mean': float(np.mean(zcr)),
                'spectral_rolloff_mean': float(np.mean(rolloff)),
            }
            
            # Calculate music likelihood score (0-100)
            # Higher centroid, consistent energy, lower ZCR, higher rolloff = more likely to be music
            music_score = (
                (min(features['spectral_centroid_mean'] / 5000, 1.0) * 25) +  # 25% weight
                (max(1 - features['rms_energy_std'] * 10, 0.0) * 25) +  # 25% weight
                (max(1 - features['zero_crossing_rate_mean'] * 100, 0.0) * 25) +  # 25% weight
                (min(features['spectral_rolloff_mean'] / 12000, 1.0) * 25)  # 25% weight
            )
            
            features['music_likelihood'] = min(100, max(0, music_score))
            return features
            
        except Exception as e:
            logger.error(f"Error analyzing audio features: {str(e)}", exc_info=True)
            return {'music_likelihood': 50}  # Default to uncertain if analysis fails

    def _search_local_database(self, audio_data: bytes) -> Optional[Track]:
        """Search for matching track in local database using acoustic fingerprinting"""
        try:
            # Calculate audio hash
            audio_hash = self._calculate_audio_hash(audio_data)
            
            # Check cache first
            cached_fingerprint = self._get_fingerprint(audio_hash)
            if cached_fingerprint:
                # Search for track by fingerprint
                track = self.db_session.query(Track).filter(
                    Track.fingerprint_raw == cached_fingerprint
                ).first()
                
                if track:
                    logger.info(f"Found matching track in cache: {track.title}")
                    return track
            
            # If not in cache, generate new fingerprint
            # Convert audio to WAV for fingerprinting
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            wav_data = io.BytesIO()
            audio.export(wav_data, format="wav")
            wav_data.seek(0)
            
            # Save temporary WAV file
            temp_wav = "temp_audio.wav"
            with open(temp_wav, "wb") as f:
                f.write(wav_data.getvalue())
            
            try:
                # Generate fingerprint using acoustid
                duration, fingerprint = acoustid.fingerprint_file(temp_wav)
                
                # Search for tracks in our database with similar fingerprints
                matches = acoustid.lookup(os.getenv('ACOUSTID_API_KEY'), fingerprint, duration)
                
                if not matches:
                    return None
                    
                # Get the best match
                best_match = matches[0]
                recording_id = best_match.get('recordings', [{}])[0].get('id')
                
                if not recording_id:
                    return None
                    
                # Try to find track in our database by MusicBrainz ID
                track = self.db_session.query(Track).filter(
                    Track.external_ids['musicbrainz_id'].astext == recording_id
                ).first()
                
                if track:
                    # Save fingerprint for future use
                    self._save_fingerprint(audio_hash, fingerprint, track)
                    logger.info(f"Found matching track in database: {track.title}")
                    return track
                    
                return None
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
                
        except Exception as e:
            logger.error(f"Error searching local database: {str(e)}")
            return None

    def _recognize_with_musicbrainz(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Try to recognize music using MusicBrainz"""
        try:
            # TODO: Implement actual MusicBrainz acoustic fingerprinting
            # For now, return None to indicate no match found
            return None
        except Exception as e:
            logger.error(f"Error with MusicBrainz recognition: {str(e)}")
            return None

    def _recognize_with_audd(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Recognize music using AudD service"""
        try:
            data = {
                'api_token': self.audd_api_key,
                'return': 'spotify,deezer,musicbrainz'
            }
            
            files = {
                'file': ('audio.mp3', audio_data, 'audio/mpeg')
            }
            
            response = requests.post('https://api.audd.io/', data=data, files=files)
            
            if response.status_code != 200:
                logger.error(f"AudD API error: {response.status_code}")
                return None
            
            result = response.json()
            
            if result.get('status') == 'success' and result.get('result'):
                song = result['result']
                
                # Extract metadata
                spotify_data = song.get('spotify', {})
                if isinstance(spotify_data, list) and len(spotify_data) > 0:
                    spotify_data = spotify_data[0]
                
                deezer_data = song.get('deezer', {})
                if isinstance(deezer_data, list) and len(deezer_data) > 0:
                    deezer_data = deezer_data[0]
                
                musicbrainz_data = song.get('musicbrainz', {})
                if isinstance(musicbrainz_data, list) and len(musicbrainz_data) > 0:
                    musicbrainz_data = musicbrainz_data[0]
                
                return {
                    "title": song.get('title'),
                    "artist": song.get('artist'),
                    "album": song.get('album'),
                    "isrc": musicbrainz_data.get('isrc') if isinstance(musicbrainz_data, dict) else None,
                    "confidence": 100,
                    "detected_at": datetime.now().isoformat(),
                    "external_metadata": {
                        "spotify": spotify_data,
                        "deezer": deezer_data,
                        "musicbrainz": musicbrainz_data
                    }
                }
            
            return None
                
        except Exception as e:
            logger.error(f"Error with AudD recognition: {str(e)}")
            return None

    def _calculate_play_duration(self, audio_data: bytes) -> float:
        """Calculate the duration of the audio in seconds"""
        try:
            # First try using AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            duration = len(audio) / 1000.0  # Convert milliseconds to seconds
            
            # Validate duration
            if duration <= 0 or duration > 3600:  # Max 1 hour
                raise ValueError(f"Invalid duration: {duration} seconds")
                
            # Use librosa as backup validation
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            sample_rate = audio.frame_rate
            librosa_duration = librosa.get_duration(y=samples, sr=sample_rate)
            
            # If durations are significantly different, log warning
            if abs(duration - librosa_duration) > 1.0:  # More than 1 second difference
                logger.warning(
                    f"Duration mismatch: AudioSegment={duration:.2f}s, "
                    f"Librosa={librosa_duration:.2f}s"
                )
                # Use the shorter duration to be conservative
                duration = min(duration, librosa_duration)
            
            logger.info(f"Calculated audio duration: {duration:.2f} seconds")
            return duration
            
        except Exception as e:
            logger.error(f"Error calculating play duration: {str(e)}", exc_info=True)
            return 15.0  # Default to 15 seconds if calculation fails

    async def recognize(self, audio_data: bytes, station_name: str = None) -> dict:
        """
        Main recognition function implementing the cascade detection strategy:
        1. Check if it's music
        2. Search local database
        3. Try MusicBrainz
        4. Try AudD
        """
        try:
            logger.info("Starting music detection", extra={
                'station': {'name': station_name},
                'step': 'start',
                'audio_size': len(audio_data)
            })
            
            # First, analyze if it's music
            features = self._analyze_audio_features(audio_data)
            
            # Calculate duration early
            duration_seconds = self._calculate_play_duration(audio_data)
            duration_minutes = duration_seconds / 60.0
            
            logger.info("Audio analysis completed", extra={
                'station': {'name': station_name},
                'step': 'analysis',
                'detection_data': {
                    'music_likelihood': features['music_likelihood'],
                    'spectral_centroid': features.get('spectral_centroid_mean', 0),
                    'rms_energy': features.get('rms_energy_std', 0),
                    'zero_crossing_rate': features.get('zero_crossing_rate_mean', 0),
                    'spectral_rolloff': features.get('spectral_rolloff_mean', 0),
                    'duration_seconds': duration_seconds
                }
            })
            
            if features['music_likelihood'] < 30:
                logger.info("No music detected", extra={
                    'station': {'name': station_name},
                    'step': 'analysis',
                    'detection_data': {
                        'music_likelihood': features['music_likelihood'],
                        'content_type': 'speech'
                    }
                })
                return {
                    "is_music": False,
                    "confidence": features['music_likelihood'],
                    "station": station_name,
                    "content_type": "speech",
                    "duration_minutes": duration_minutes
                }

            logger.info("Music detected", extra={
                'station': {'name': station_name},
                'step': 'analysis',
                'detection_data': {
                    'music_likelihood': features['music_likelihood'],
                    'content_type': 'music',
                    'duration_seconds': duration_seconds
                }
            })
            
            # Try local database first
            logger.info("Searching local database", extra={
                'station': {'name': station_name},
                'step': 'local_search'
            })
            
            local_match = self._search_local_database(audio_data)
            if local_match:
                logger.info("Match found in local database", extra={
                    'station': {'name': station_name},
                    'step': 'local_search',
                    'detection_data': {
                        'title': local_match.title,
                        'artist': local_match.artist,
                        'label': local_match.label,
                        'isrc': local_match.isrc,
                        'duration': str(timedelta(seconds=duration_seconds))
                    }
                })
                return {
                    "is_music": True,
                    "station": station_name,
                    "track": {
                        "title": local_match.title,
                        "artist": local_match.artist,
                        "isrc": local_match.isrc,
                        "label": local_match.label
                    },
                    "confidence": 100.0,
                    "source": "local_db",
                    "duration_minutes": duration_minutes
                }

            # Try MusicBrainz
            logger.info("Searching MusicBrainz", extra={
                'station': {'name': station_name},
                'step': 'musicbrainz_search'
            })
            
            mb_result = self._recognize_with_musicbrainz(audio_data)
            if mb_result:
                mb_result['duration_minutes'] = duration_minutes
                logger.info("Match found in MusicBrainz", extra={
                    'station': {'name': station_name},
                    'step': 'musicbrainz_search',
                    'detection_data': {
                        'title': mb_result.get('title'),
                        'artist': mb_result.get('artist'),
                        'isrc': mb_result.get('isrc'),
                        'label': mb_result.get('label'),
                        'duration': str(timedelta(seconds=duration_seconds))
                    }
                })
                return {
                    "is_music": True,
                    "station": station_name,
                    "track": mb_result,
                    "confidence": 90.0,
                    "source": "musicbrainz",
                    "duration_minutes": duration_minutes
                }

            # Finally, try AudD
            logger.info("Searching AudD", extra={
                'station': {'name': station_name},
                'step': 'audd_search'
            })
            
            audd_result = self._recognize_with_audd(audio_data)
            if audd_result:
                audd_result['duration_minutes'] = duration_minutes
                logger.info("Match found in AudD", extra={
                    'station': {'name': station_name},
                    'step': 'audd_search',
                    'detection_data': {
                        'title': audd_result.get('title'),
                        'artist': audd_result.get('artist'),
                        'album': audd_result.get('album'),
                        'isrc': audd_result.get('isrc'),
                        'label': audd_result.get('label'),
                        'duration': str(timedelta(seconds=duration_seconds))
                    }
                })
                
                return {
                    "is_music": True,
                    "station": station_name,
                    "track": audd_result,
                    "confidence": 85.0,
                    "source": "audd",
                    "duration_minutes": duration_minutes
                }
            
            return {
                "is_music": True,
                "confidence": features['music_likelihood'],
                "station": station_name,
                "content_type": "music",
                "duration_minutes": duration_minutes,
                "error": "No matching track found"
            }
                
        except Exception as e:
            logger.error(f"Error in music recognition: {str(e)}")
            return {
                "is_music": False,
                "confidence": 0,
                "station": station_name,
                "error": str(e),
                "duration_minutes": 0.25  # Default 15 seconds on error
            }
        finally:
            logger.info(f"=== Fin de la détection pour la station: {station_name} ===\n")
