"""
MusicBrainz recognizer module for SODAV Monitor.

This module provides functionality for recognizing music using MusicBrainz and AudD APIs.
"""

import logging
import os
import tempfile
from typing import Dict, Any, Optional, List, Union
import musicbrainzngs
import acoustid
import requests
import numpy as np
import librosa
from sqlalchemy.orm import Session
import asyncio
import json

from backend.config import Settings
from backend.detection.audio_processor.local_detection import LocalDetector
from backend.detection.audio_processor.external_services import ExternalServiceHandler

# Configure logging
logger = logging.getLogger(__name__)

class MusicBrainzRecognizer:
    """
    Class for recognizing music using MusicBrainz and AudD APIs.
    
    This class provides methods for recognizing music from audio data using
    local database, MusicBrainz/AcoustID, and AudD APIs.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the MusicBrainzRecognizer with API keys and services.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.settings = Settings()
        
        # Validate required API keys
        if not self.settings.ACOUSTID_API_KEY:
            raise ValueError("ACOUSTID_API_KEY is required for MusicBrainz recognition")
        
        if not self.settings.AUDD_API_KEY:
            raise ValueError("AUDD_API_KEY is required for AudD recognition")
        
        # Initialize MusicBrainz
        musicbrainzngs.set_useragent(
            self.settings.MUSICBRAINZ_APP_NAME,
            self.settings.MUSICBRAINZ_VERSION,
            self.settings.MUSICBRAINZ_CONTACT
        )
        
        # Initialize services
        self.local_detector = LocalDetector(db_session)
        self.external_handler = ExternalServiceHandler(db_session)
        
        # Configure confidence thresholds
        self.min_confidence = 0.6
        self.music_threshold = 0.7
    
    def analyze_audio_features(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Analyze audio data to extract features and determine if it's music.
        
        Args:
            audio_data: Raw audio data as bytes
            
        Returns:
            Dictionary of audio features and analysis results
        """
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Load audio with librosa
                y, sr = librosa.load(temp_path, sr=None)
                
                # Extract features
                spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
                rms = librosa.feature.rms(y=y)[0]
                zero_crossing_rate = librosa.feature.zero_crossing_rate(y=y)[0]
                
                # Calculate statistics
                sc_mean = np.mean(spectral_centroid)
                sc_std = np.std(spectral_centroid)
                rms_mean = np.mean(rms)
                zcr_mean = np.mean(zero_crossing_rate)
                
                # Determine if it's music based on features
                # Higher spectral centroid and RMS with lower ZCR typically indicates music
                is_music_score = (
                    (sc_mean > 1000) * 0.4 +
                    (rms_mean > 0.05) * 0.4 +
                    (zcr_mean < 0.1) * 0.2
                )
                
                is_music = is_music_score > self.music_threshold
                
                return {
                    'is_music': is_music,
                    'confidence': is_music_score,
                    'spectral_centroid_mean': float(sc_mean),
                    'spectral_centroid_std': float(sc_std),
                    'rms_mean': float(rms_mean),
                    'zero_crossing_rate_mean': float(zcr_mean)
                }
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Error analyzing audio features: {e}")
            return {
                'is_music': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def recognize_from_audio_data(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Analyze audio and attempt recognition using multiple services in order:
        1. Local detection
        2. MusicBrainz/AcoustID
        3. AudD
        
        Args:
            audio_data: Raw audio data as bytes
            
        Returns:
            Dictionary with recognition results
        """
        try:
            # First, analyze audio to determine if it's music
            features = self.analyze_audio_features(audio_data)
            
            if not features.get('is_music', False):
                logger.info("Audio is not music, skipping recognition")
                return {
                    'type': 'speech',
                    'confidence': features.get('confidence', 0.0)
                }
            
            # Try local detection first
            local_result = await self.local_detector.detect(audio_data)
            
            if local_result and local_result.get('confidence', 0) >= self.min_confidence:
                logger.info(f"Local detection successful: {local_result.get('title')} by {local_result.get('artist')}")
                return {
                    'type': 'music',
                    'source': 'local',
                    'confidence': local_result.get('confidence', 0.0),
                    'title': local_result.get('title'),
                    'artist': local_result.get('artist'),
                    'isrc': local_result.get('isrc'),
                    'label': local_result.get('label')
                }
            
            # Try MusicBrainz/AcoustID
            mb_result = await self.external_handler.detect_with_musicbrainz(audio_data)
            
            if mb_result and mb_result.get('confidence', 0) >= self.min_confidence:
                logger.info(f"MusicBrainz detection successful: {mb_result.get('title')} by {mb_result.get('artist')}")
                return {
                    'type': 'music',
                    'source': 'musicbrainz',
                    'confidence': mb_result.get('confidence', 0.0),
                    'title': mb_result.get('title'),
                    'artist': mb_result.get('artist'),
                    'isrc': mb_result.get('isrc'),
                    'label': mb_result.get('label')
                }
            
            # Try AudD as last resort
            audd_result = await self.external_handler.detect_with_audd(audio_data)
            
            if audd_result and audd_result.get('confidence', 0) >= self.min_confidence:
                logger.info(f"AudD detection successful: {audd_result.get('title')} by {audd_result.get('artist')}")
                return {
                    'type': 'music',
                    'source': 'audd',
                    'confidence': audd_result.get('confidence', 0.0),
                    'title': audd_result.get('title'),
                    'artist': audd_result.get('artist'),
                    'isrc': audd_result.get('isrc'),
                    'label': audd_result.get('label')
                }
            
            # If all services failed or returned low confidence
            logger.info("All recognition services failed or returned low confidence")
            return {
                'type': 'unknown',
                'confidence': 0.0
            }
            
        except Exception as e:
            logger.error(f"Error in music recognition: {e}")
            return {
                'type': 'error',
                'error': str(e),
                'confidence': 0.0
            } 