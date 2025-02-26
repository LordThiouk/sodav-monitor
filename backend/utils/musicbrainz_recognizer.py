import musicbrainzngs
import logging
from typing import Dict, Any, Optional
import io
from pydub import AudioSegment
import os
from datetime import datetime
from backend.config import Settings
import librosa
import numpy as np
from backend.detection.audio_processor.local_detection import LocalDetector
from backend.detection.audio_processor.external_services import ExternalServiceHandler
from sqlalchemy.orm import Session
import asyncio
import acoustid

# Configure logging
logger = logging.getLogger(__name__)

class MusicBrainzRecognizer:
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize MusicBrainz recognizer"""
        self.settings = Settings()
        
        # Validate required API keys
        if not self.settings.ACOUSTID_API_KEY:
            raise ValueError("ACOUSTID_API_KEY est requis pour l'identification via AcoustID/Chromaprint")
        if not self.settings.AUDD_API_KEY:
            raise ValueError("AUDD_API_KEY est requis pour l'identification via Audd.io")
        
        # Set up MusicBrainz
        musicbrainzngs.set_useragent(
            self.settings.MUSICBRAINZ_APP_NAME,
            self.settings.MUSICBRAINZ_VERSION,
            self.settings.MUSICBRAINZ_CONTACT
        )
        
        # Set up AcoustID
        self.acoustid_api_key = self.settings.ACOUSTID_API_KEY
        
        # Initialize detectors
        self.local_detector = LocalDetector(db_session) if db_session else None
        self.external_handler = ExternalServiceHandler(
            db_session=db_session,
            audd_api_key=self.settings.AUDD_API_KEY
        ) if db_session else None
    
    def _analyze_audio_features(self, audio_data: bytes) -> Dict[str, float]:
        """
        Analyze audio features to determine if the content is music
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
            
            # Calculate features
            sr = audio.frame_rate
            
            # Spectral centroid
            centroid = librosa.feature.spectral_centroid(y=samples, sr=sr)
            centroid_mean = float(np.mean(centroid))
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(samples)
            zcr_mean = float(np.mean(zcr))
            
            # RMS energy
            rms = librosa.feature.rms(y=samples)
            rms_mean = float(np.mean(rms))
            
            # Calculate music likelihood based on features
            # Higher centroid and zcr typically indicate music
            music_likelihood = float(
                min(100, max(0, 
                    centroid_mean * 0.4 +  # Weight spectral centroid
                    zcr_mean * 30 +        # Weight zero crossing rate
                    rms_mean * 100         # Weight RMS energy
                ))
            )
            
            return {
                "centroid_mean": centroid_mean,
                "zcr_mean": zcr_mean,
                "rms_mean": rms_mean,
                "music_likelihood": music_likelihood
            }
            
        except Exception as e:
            logger.error(f"Error analyzing audio features: {str(e)}")
            return {"error": str(e)}
    
    async def recognize_from_audio_data(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Analyze audio and attempt recognition using multiple services in order:
        1. Local detection
        2. MusicBrainz/AcoustID
        3. Audd
        """
        try:
            logger.info("Starting music recognition process")
            
            # First analyze audio features
            features = self._analyze_audio_features(audio_data)
            
            if "error" in features:
                return {"error": f"Failed to analyze audio: {features['error']}"}
            
            music_likelihood = features.get("music_likelihood", 0)
            logger.info(f"Music likelihood score: {music_likelihood}")
            
            if music_likelihood < self.settings.MIN_CONFIDENCE_THRESHOLD * 100:
                return {"error": "Audio does not appear to be music"}
            
            # Try local detection first
            if self.local_detector:
                try:
                    logger.info("Attempting local detection")
                    local_result = self.local_detector.search_local(audio_data)
                    if local_result and not "error" in local_result:
                        if local_result.get("confidence", 0) >= self.settings.LOCAL_CONFIDENCE_THRESHOLD:
                            logger.info("Local detection successful")
                            return local_result
                        else:
                            logger.info("Local detection confidence too low")
                except Exception as e:
                    logger.error(f"Local detection failed: {str(e)}")
            
            # If local detection fails or is not available, try external services
            if self.external_handler:
                # Try MusicBrainz/AcoustID
                try:
                    logger.info("Attempting MusicBrainz/AcoustID recognition")
                    mb_result = await self.external_handler.recognize_with_musicbrainz(audio_data)
                    if mb_result and not "error" in mb_result:
                        if mb_result.get("confidence", 0) >= self.settings.ACOUSTID_CONFIDENCE_THRESHOLD:
                            logger.info("MusicBrainz/AcoustID recognition successful")
                            return mb_result
                        else:
                            logger.info("MusicBrainz/AcoustID confidence too low")
                except Exception as e:
                    logger.error(f"MusicBrainz/AcoustID detection failed: {str(e)}")
                
                # If MusicBrainz/AcoustID fails or confidence is too low, try Audd
                try:
                    logger.info("Attempting Audd recognition")
                    audd_result = await self.external_handler.recognize_with_audd(audio_data)
                    if audd_result and not "error" in audd_result:
                        if audd_result.get("confidence", 0) >= self.settings.AUDD_CONFIDENCE_THRESHOLD:
                            logger.info("Audd recognition successful")
                            return audd_result
                        else:
                            logger.info("Audd confidence too low")
                except Exception as e:
                    logger.error(f"Audd detection failed: {str(e)}")
            
            return {"error": "All detection methods failed or returned low confidence results"}
            
        except Exception as e:
            logger.error(f"Error in music recognition: {str(e)}")
            return {"error": str(e)}
