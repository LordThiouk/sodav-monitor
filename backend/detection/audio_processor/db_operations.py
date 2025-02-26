"""
Database operations for music recognition in SODAV Monitor.
Handles track management and database operations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from ...models.models import Track, Artist, TrackDetection, StationTrackStats
from ...utils.logging_config import setup_logging
from ...utils.validators import validate_track_info

logger = setup_logging(__name__)

class DatabaseHandler:
    def __init__(self, db_session: Session):
        """Initialize database handler with session"""
        self.db_session = db_session
        self.initialized = False
        
    async def initialize(self) -> None:
        """Initialize database handler"""
        if self.initialized:
            return
            
        try:
            # Verify database connection
            self.db_session.execute("SELECT 1")
            self.initialized = True
            logger.info("DatabaseHandler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseHandler: {str(e)}")
            raise
            
    @contextmanager
    def _db_transaction(self):
        """Context manager for database transactions"""
        try:
            yield
            self.db_session.commit()
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Database transaction error: {str(e)}")
            raise
            
    def get_or_create_unknown_track(self) -> Track:
        """Get or create an unknown track entry.
        
        Returns:
            Track object for unknown track
        """
        try:
            unknown_track = self.db_session.query(Track).filter(
                Track.title == "Unknown Track"
            ).first()
            
            if not unknown_track:
                unknown_track = Track(
                    title="Unknown Track",
                    artist_id=self.get_or_create_unknown_artist().id
                )
                self.db_session.add(unknown_track)
                self.db_session.commit()
                
            return unknown_track
            
        except Exception as e:
            logger.error(f"Error getting/creating unknown track: {str(e)}")
            raise

    def get_or_create_unknown_artist(self) -> Artist:
        """Get or create the unknown artist entry"""
        try:
            unknown_artist = (
                self.db_session.query(Artist)
                .filter(Artist.name == "Unknown Artist")
                .first()
            )
            
            if not unknown_artist:
                unknown_artist = Artist(name="Unknown Artist")
                self.db_session.add(unknown_artist)
                self.db_session.commit()
                
            return unknown_artist
            
        except Exception as e:
            logger.error(f"Error getting/creating unknown artist: {str(e)}")
            raise
            
    def save_track_to_db(self, track_info: Dict[str, Any]) -> Optional[Track]:
        """Save track information to database.
        
        Args:
            track_info: Dictionary containing track information
            
        Returns:
            Saved Track object or None if error
        """
        try:
            # Validate track info
            if not track_info.get('title') or not track_info.get('artist'):
                raise ValueError("Missing required track information")
            
            # Get or create artist
            artist = self.db_session.query(Artist).filter(
                Artist.name == track_info['artist']
            ).first()
            
            if not artist:
                artist = Artist(name=track_info['artist'])
                self.db_session.add(artist)
                self.db_session.commit()
            
            # Check for existing track
            track = self.db_session.query(Track).filter(
                Track.title == track_info['title'],
                Track.artist_id == artist.id
            ).first()
            
            if not track:
                track = Track(
                    title=track_info['title'],
                    artist_id=artist.id,
                    duration=track_info.get('duration', 0),
                    release_date=track_info.get('release_date')
                )
                self.db_session.add(track)
                self.db_session.commit()
            
            return track
            
        except Exception as e:
            logger.error(f"Error saving track to database: {str(e)}")
            return None

    def verify_detections(self, detections: List[TrackDetection]) -> None:
        """Verify and update track detections.
        
        Args:
            detections: List of track detections to verify
        """
        try:
            for detection in detections:
                # Update verification status
                detection.verified = True
                detection.verification_date = datetime.now()
                self.db_session.add(detection)
            
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error verifying detections: {str(e)}")
            raise 