"""
Local detection module for SODAV Monitor.

This module provides functionality for detecting music using the local database.
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
import asyncio

from backend.models.models import Track, Artist
from backend.detection.audio_processor.fingerprint import AudioFingerprinter

# Configure logging
logger = logging.getLogger(__name__)

class LocalDetector:
    """
    Class for detecting music using the local database.
    
    This class provides methods for detecting music from audio data using
    fingerprints stored in the local database.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the LocalDetector with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.fingerprinter = AudioFingerprinter()
        self.min_confidence = 0.6
    
    async def detect(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Detect music from audio data using the local database.
        
        Args:
            audio_data: Raw audio data as bytes
            
        Returns:
            Dictionary with detection results or None if no match found
        """
        try:
            # Extract fingerprint from audio data
            fingerprint = self.fingerprinter.generate_fingerprint(audio_data)
            
            if not fingerprint:
                logger.warning("Failed to generate fingerprint from audio data")
                return None
            
            # Search for matching tracks in the database
            track = self.db_session.query(Track).filter(
                func.similarity(Track.fingerprint, fingerprint) > self.min_confidence
            ).order_by(
                func.similarity(Track.fingerprint, fingerprint).desc()
            ).first()
            
            if not track:
                logger.info("No matching track found in local database")
                return None
            
            # Calculate confidence based on fingerprint similarity
            confidence = self._calculate_confidence(fingerprint, track.fingerprint)
            
            # Get artist information
            artist = self.db_session.query(Artist).filter(Artist.id == track.artist_id).first()
            artist_name = artist.name if artist else "Unknown"
            
            logger.info(f"Local detection successful: {track.title} by {artist_name} (confidence: {confidence:.2f})")
            
            return {
                'track_id': track.id,
                'title': track.title,
                'artist': artist_name,
                'artist_id': track.artist_id,
                'isrc': track.isrc,
                'label': track.label,
                'confidence': confidence,
                'fingerprint': fingerprint
            }
            
        except Exception as e:
            logger.error(f"Error in local detection: {e}")
            return None
    
    def _calculate_confidence(self, fingerprint1: str, fingerprint2: str) -> float:
        """
        Calculate confidence score based on fingerprint similarity.
        
        Args:
            fingerprint1: First fingerprint
            fingerprint2: Second fingerprint
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Simple Jaccard similarity for string fingerprints
            set1 = set(fingerprint1)
            set2 = set(fingerprint2)
            
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            if union == 0:
                return 0.0
                
            return intersection / union
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.0
    
    async def search_by_metadata(self, title: str, artist: str) -> Optional[Dict[str, Any]]:
        """
        Search for a track by title and artist.
        
        Args:
            title: Track title
            artist: Artist name
            
        Returns:
            Dictionary with track information or None if no match found
        """
        try:
            # Search for artist first
            artist_obj = self.db_session.query(Artist).filter(
                func.lower(Artist.name) == func.lower(artist)
            ).first()
            
            if not artist_obj:
                logger.info(f"No artist found for name: {artist}")
                return None
            
            # Search for track by title and artist
            track = self.db_session.query(Track).filter(
                func.lower(Track.title) == func.lower(title),
                Track.artist_id == artist_obj.id
            ).first()
            
            if not track:
                logger.info(f"No track found for title: {title} by artist: {artist}")
                return None
            
            logger.info(f"Found track by metadata: {track.title} by {artist_obj.name}")
            
            return {
                'track_id': track.id,
                'title': track.title,
                'artist': artist_obj.name,
                'artist_id': track.artist_id,
                'isrc': track.isrc,
                'label': track.label,
                'confidence': 1.0,  # High confidence for exact metadata match
                'fingerprint': track.fingerprint
            }
            
        except Exception as e:
            logger.error(f"Error searching by metadata: {e}")
            return None 