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
from .models import Track, Artist
import acoustid
import hashlib
from functools import lru_cache
from .utils.logging_config import setup_logging
import soundfile as sf
import asyncio
import aiohttp
import tempfile
from sqlalchemy import func, desc
from .models import TrackDetection, RadioStation, StationTrackStats
from .audio_fingerprint import generate_fingerprint, compare_fingerprints, get_audio_features
from sqlalchemy.sql import text
from .utils.validators import validate_track_info
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

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

    def _save_fingerprint(self, audio_data: bytes, track: Track) -> None:
        """Save fingerprint to database"""
        try:
            fingerprint_result = generate_fingerprint(audio_data)
            if fingerprint_result:
                duration, fingerprint = fingerprint_result
                track.fingerprint = fingerprint
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

    async def _search_local_database(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Search for matching tracks in local database using audio fingerprinting"""
        try:
            # Generate fingerprint for the audio
            fingerprint_result = generate_fingerprint(audio_data)
            if not fingerprint_result:
                logger.warning("Could not generate fingerprint")
                return None
                
            duration, fingerprint = fingerprint_result
            
            # Get audio features for additional comparison
            features = get_audio_features(audio_data)
            
            # Search for matching tracks
            tracks = self.db_session.query(Track).filter(
                Track.fingerprint.isnot(None)
            ).all()
            
            best_match = None
            best_confidence = 0
            
            for track in tracks:
                if not track.fingerprint:
                    continue
                    
                # Compare fingerprints
                confidence = compare_fingerprints(fingerprint, track.fingerprint)
                
                # Adjust confidence based on duration difference if available
                if track.total_play_time and features.get("duration"):
                    track_duration = track.total_play_time.total_seconds()
                    duration_diff = abs(track_duration - features["duration"])
                    duration_penalty = min(20, (duration_diff / track_duration) * 100)
                    confidence = max(0, confidence - duration_penalty)
                
                if confidence > best_confidence:
                    best_match = track
                    best_confidence = confidence
            
            if best_match and best_confidence > 80:  # 80% confidence threshold
                logger.info(f"Found matching track in database: {best_match.title} (confidence: {best_confidence:.2f}%)")
                return {
                    "track": best_match,
                    "confidence": best_confidence
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching local database: {str(e)}", exc_info=True)
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

    def _calculate_play_duration(self, audio_data: bytes) -> float:
        """Calculate the duration of the audio in seconds"""
        try:
            # First try using AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            duration = len(audio) / 1000.0  # Convert milliseconds to seconds
            
            # Validate duration
            if duration <= 0 or duration > 3600:  # Max 1 hour
                raise ValueError(f"Invalid duration: {duration} seconds")
                
            # Convert to mono if stereo
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # Normalize samples
            samples = samples / np.max(np.abs(samples))
            
            # Use librosa with the same sample rate and mono audio
            librosa_duration = librosa.get_duration(y=samples, sr=audio.frame_rate)
            
            # If durations are significantly different, log warning
            if abs(duration - librosa_duration) > 1.0:  # More than 1 second difference
                logger.warning(
                    f"Duration mismatch: AudioSegment={duration:.2f}s, "
                    f"Librosa={librosa_duration:.2f}s"
                )
                # Use AudioSegment duration as it's more reliable
                duration = duration
            
            logger.info(f"Calculated audio duration: {duration:.2f} seconds")
            return duration
            
        except Exception as e:
            logger.error(f"Error calculating play duration: {str(e)}", exc_info=True)
            return 15.0  # Default to 15 seconds if calculation fails

    def _recognize_with_audd(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Recognize music using AudD service"""
        try:
            if not self.audd_api_key:
                logger.error("AudD API key not configured")
                return None

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
                if isinstance(spotify_data, list) and spotify_data:
                    spotify_data = spotify_data[0]
                
                deezer_data = song.get('deezer', {})
                if isinstance(deezer_data, list) and deezer_data:
                    deezer_data = deezer_data[0]
                
                musicbrainz_data = song.get('musicbrainz', [])
                if musicbrainz_data and isinstance(musicbrainz_data, list):
                    musicbrainz_data = musicbrainz_data[0]
                
                # Calculate duration
                duration = self._calculate_play_duration(audio_data)
                duration_minutes = duration / 60.0
                
                # Ensure all required fields are present
                track_data = {
                    "title": song.get('title', 'Unknown Title'),
                    "artist": song.get('artist', 'Unknown Artist'),
                    "album": song.get('album', 'Unknown Album'),
                    "release_date": song.get('release_date'),
                    "label": song.get('label'),
                    "isrc": None,  # Will be set below
                    "duration_minutes": duration_minutes,
                    "external_metadata": {
                        "spotify": spotify_data if isinstance(spotify_data, dict) else {},
                        "deezer": deezer_data if isinstance(deezer_data, dict) else {},
                        "musicbrainz": musicbrainz_data if isinstance(musicbrainz_data, dict) else {}
                    }
                }

                # Try to get ISRC from different sources
                if isinstance(musicbrainz_data, dict):
                    track_data["isrc"] = musicbrainz_data.get('isrc')
                if not track_data["isrc"] and isinstance(spotify_data, dict):
                    track_data["isrc"] = spotify_data.get('isrc')
                if not track_data["isrc"] and isinstance(deezer_data, dict):
                    track_data["isrc"] = deezer_data.get('isrc')

                # Try to get label if not already set
                if not track_data["label"]:
                    if isinstance(spotify_data, dict) and spotify_data.get('album', {}).get('label'):
                        track_data["label"] = spotify_data['album']['label']
                    elif isinstance(deezer_data, dict) and deezer_data.get('label'):
                        track_data["label"] = deezer_data['label']

                logger.info(f"AudD recognition successful: {track_data['title']} by {track_data['artist']}")
                return track_data
            
            logger.warning("No result found in AudD response")
            return None
                
        except Exception as e:
            logger.error(f"Error with AudD recognition: {str(e)}")
            return None

    async def recognize_music(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Recognize music from audio data"""
        try:
            # First check if it's likely to be music
            features = self._analyze_audio_features(audio_data)
            if features['music_likelihood'] < 50:
                logger.info(f"Audio unlikely to be music (score: {features['music_likelihood']})")
                return None

            # Try local database first
            local_result = await self._search_local_database(audio_data)
            if local_result:
                logger.info("Found match in local database")
                return {
                    'title': local_result['track'].title,
                    'artist': local_result['track'].artist.name,
                    'confidence': local_result['confidence'],
                    'isrc': local_result['track'].isrc,
                    'label': local_result['track'].label,
                    'album': local_result['track'].album,
                    'source': 'local_db'
                }

            # If no local match and AudD API key available, try AudD
            if self.audd_api_key:
                logger.info("Attempting AudD recognition")
                async with aiohttp.ClientSession() as session:
                    data = aiohttp.FormData()
                    data.add_field('api_token', self.audd_api_key)
                    data.add_field('file', audio_data)
                    data.add_field('return', 'apple_music,spotify,musicbrainz')

                    async with session.post('https://api.audd.io/', data=data) as response:
                        if response.status == 200:
                            audd_result = await response.json()
                            
                            if audd_result.get('status') == 'success' and audd_result.get('result'):
                                result = audd_result['result']
                                logger.info(f"AudD recognition successful: {result.get('title')} by {result.get('artist')}")

                                # Generate fingerprint
                                fingerprint_result = generate_fingerprint(audio_data)
                                fingerprint = fingerprint_result[1] if fingerprint_result else None

                                # Save track to database
                                track = await self._save_track_to_db(result, fingerprint)
                                
                                if track:
                                    return {
                                        'title': track.title,
                                        'artist': track.artist.name,
                                        'confidence': 100.0,  # AudD matches are considered highly confident
                                        'isrc': track.isrc,
                                        'label': track.label,
                                        'album': track.album,
                                        'source': 'audd'
                                    }

            logger.info("No music detected")
            return None

        except Exception as e:
            logger.error(f"Error in music recognition: {str(e)}")
            return None

    def _get_or_create_unknown_track(self) -> Track:
        """Create or get the default unknown track"""
        try:
            unknown_track = self.db_session.query(Track).filter(
                Track.title == "Unknown Track",
                Track.artist_id == None
            ).first()
            
            if not unknown_track:
                unknown_track = Track(
                    title="Unknown Track",
                    artist_id=None,
                    isrc=None,
                    label=None,
                    album=None
                )
                self.db_session.add(unknown_track)
                self.db_session.commit()
            
            return unknown_track
            
        except Exception as e:
            logger.error(f"Error creating unknown track: {str(e)}")
            self.db_session.rollback()
            raise

    @contextmanager
    def _db_transaction(self):
        """Gestionnaire de contexte pour les transactions"""
        try:
            yield
            self.db_session.commit()
        except SQLAlchemyError as e:
            self.logger.error(f"Erreur de transaction: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Erreur inattendue: {str(e)}")
            self.db_session.rollback()
            raise

    async def _save_track_to_db(self, track_info: Dict[str, Any], fingerprint: Optional[str] = None) -> Optional[Track]:
        """Sauvegarde une piste dans la base de données avec gestion améliorée des transactions"""
        if not validate_track_info(track_info):
            return None

        try:
            with self._db_transaction():
                # Vérification par ISRC
                if track_info.get('isrc'):
                    existing_track = self.db_session.query(Track).filter(
                        Track.isrc == track_info['isrc']
                    ).first()
                    if existing_track:
                        self.logger.info(f"Piste trouvée avec ISRC: {track_info['isrc']}")
                        return existing_track

                # Recherche ou création de l'artiste
                artist_name = track_info['artist']
                artist = self.db_session.query(Artist).filter(
                    Artist.name == artist_name
                ).first()

                if not artist:
                    artist = Artist(
                        name=artist_name,
                        country=track_info.get('country'),
                        label=track_info.get('label'),
                        type=track_info.get('artist_type', 'unknown')
                    )
                    self.db_session.add(artist)
                    self.db_session.flush()

                # Recherche de piste existante par titre et artiste
                existing_track = self.db_session.query(Track).filter(
                    Track.title == track_info['title'],
                    Track.artist_id == artist.id
                ).first()

                if existing_track:
                    self.logger.info(f"Piste existante trouvée: {track_info['title']} par {artist_name}")
                    return existing_track

                # Création de la nouvelle piste
                new_track = Track(
                    title=track_info['title'],
                    artist_id=artist.id,
                    isrc=track_info.get('isrc'),
                    label=track_info.get('label'),
                    album=track_info.get('album'),
                    fingerprint=fingerprint,
                    release_date=track_info.get('release_date'),
                    external_ids=track_info.get('external_ids', {})
                )
                self.db_session.add(new_track)
                self.db_session.flush()

                self.logger.info(f"Nouvelle piste créée: {new_track.title} par {artist.name}")
                return new_track

        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la piste: {str(e)}")
            return None

    async def verify_detections(self, start_time: datetime = None, end_time: datetime = None):
        """Verify and recover missing detections"""
        try:
            if not start_time:
                start_time = datetime.now() - timedelta(hours=24)
            if not end_time:
                end_time = datetime.now()

            logger.info(f"Verifying detections from {start_time} to {end_time}")

            # Check for tracks without detections
            missing_detections = self.db_session.execute(text("""
                WITH detection_gaps AS (
                    SELECT 
                        t.id as track_id,
                        t.title,
                        a.name as artist_name,
                        td.detected_at,
                        LEAD(td.detected_at) OVER (
                            PARTITION BY t.id 
                            ORDER BY td.detected_at
                        ) - td.detected_at as gap
                    FROM tracks t
                    JOIN artists a ON t.artist_id = a.id
                    LEFT JOIN track_detections td ON t.id = td.track_id
                    WHERE td.detected_at BETWEEN :start_time AND :end_time
                )
                SELECT 
                    track_id,
                    title,
                    artist_name,
                    detected_at,
                    gap
                FROM detection_gaps
                WHERE gap > interval '1 hour'
                ORDER BY gap DESC;
            """), {
                'start_time': start_time,
                'end_time': end_time
            })

            results = missing_detections.fetchall()
            
            if results:
                logger.warning(f"Found {len(results)} tracks with potential missing detections", extra={
                    'missing_detections': [
                        {
                            'track_id': r.track_id,
                            'title': r.title,
                            'artist': r.artist_name,
                            'last_detection': r.detected_at.isoformat() if r.detected_at else None,
                            'gap': str(r.gap) if r.gap else None
                        }
                        for r in results
                    ]
                })
            else:
                logger.info("No missing detections found")

            # Check for orphaned detections (no track or station)
            orphaned = self.db_session.execute(text("""
                SELECT td.id, td.detected_at, td.track_id, td.station_id
                FROM track_detections td
                LEFT JOIN tracks t ON td.track_id = t.id
                LEFT JOIN radio_stations rs ON td.station_id = rs.id
                WHERE (t.id IS NULL OR rs.id IS NULL)
                AND td.detected_at BETWEEN :start_time AND :end_time;
            """), {
                'start_time': start_time,
                'end_time': end_time
            })

            orphaned_results = orphaned.fetchall()
            
            if orphaned_results:
                logger.warning(f"Found {len(orphaned_results)} orphaned detections", extra={
                    'orphaned_detections': [
                        {
                            'detection_id': r.id,
                            'detected_at': r.detected_at.isoformat(),
                            'track_id': r.track_id,
                            'station_id': r.station_id
                        }
                        for r in orphaned_results
                    ]
                })
                
                # Clean up orphaned detections
                self.db_session.execute(text("""
                    DELETE FROM track_detections
                    WHERE id IN (
                        SELECT td.id
                        FROM track_detections td
                        LEFT JOIN tracks t ON td.track_id = t.id
                        LEFT JOIN radio_stations rs ON td.station_id = rs.id
                        WHERE (t.id IS NULL OR rs.id IS NULL)
                        AND td.detected_at BETWEEN :start_time AND :end_time
                    );
                """), {
                    'start_time': start_time,
                    'end_time': end_time
                })
                
                self.db_session.commit()
                logger.info("Cleaned up orphaned detections")
            else:
                logger.info("No orphaned detections found")

        except Exception as e:
            logger.error(f"Error verifying detections: {str(e)}", exc_info=True)
            self.db_session.rollback()
            raise
