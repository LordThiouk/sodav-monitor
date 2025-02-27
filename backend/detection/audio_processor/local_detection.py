"""
Local music detection functionality for SODAV Monitor.
Handles local database searches and fingerprint operations.
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.models import Track, TrackDetection, Artist
from utils.logging_config import setup_logging
from .fingerprint import AudioFingerprinter

logger = setup_logging(__name__)

class LocalDetector:
    def __init__(self, db_session: Session):
        """Initialize local detector.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.fingerprinter = AudioFingerprinter()
        self.initialized = False
        self.initialize()
        
    def initialize(self):
        """Initialize local detector"""
        self.initialized = True
        logger.info("LocalDetector initialized successfully")
        
    def calculate_audio_hash(self, audio_data: bytes) -> str:
        """Calculate hash for audio data.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Audio hash string
        """
        try:
            # Convert audio to numpy array
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate hash using fingerprinter
            return self.fingerprinter.calculate_hash(samples)
            
        except Exception as e:
            logger.error(f"Error calculating audio hash: {str(e)}")
            raise
            
    def save_fingerprint(self, audio_data: bytes, track_id: int) -> Optional[TrackDetection]:
        """Save audio fingerprint for a track.
        
        Args:
            audio_data: Raw audio bytes
            track_id: ID of the track
            
        Returns:
            Created TrackDetection object or None if error
        """
        try:
            # Calculate audio hash
            audio_hash = self.calculate_audio_hash(audio_data)
            
            # Create detection entry
            detection = TrackDetection(
                track_id=track_id,
                audio_hash=audio_hash,
                confidence=1.0,
                verified=True,
                verification_date=datetime.now()
            )
            
            self.db_session.add(detection)
            self.db_session.commit()
            
            return detection
            
        except Exception as e:
            logger.error(f"Error saving fingerprint: {str(e)}")
            return None
            
    def search_local(self, audio_data: bytes, min_confidence: float = 0.8) -> Optional[Dict[str, Any]]:
        """Search for matching tracks in local database.
        
        Args:
            audio_data: Raw audio bytes
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dictionary with match details or None if no match
        """
        try:
            # Calculate audio hash
            audio_hash = self.calculate_audio_hash(audio_data)
            
            # Search for matches
            matches = (
                self.db_session.query(TrackDetection)
                .join(Track)
                .join(Artist)
                .filter(TrackDetection.audio_hash == audio_hash)
                .filter(TrackDetection.confidence >= min_confidence)
                .all()
            )
            
            if not matches:
                return None
                
            # Get best match
            best_match = max(matches, key=lambda x: x.confidence)
            
            return {
                'track_id': best_match.track_id,
                'title': best_match.track.title,
                'artist': best_match.track.artist.name,
                'confidence': best_match.confidence
            }
            
        except Exception as e:
            logger.error(f"Error searching local database: {str(e)}")
            return None 