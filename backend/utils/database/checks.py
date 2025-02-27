"""Database checking and validation functionality."""

import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta

from backend.models.models import Track, TrackDetection, RadioStation
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)

class DatabaseChecker:
    """Handles database validation and health checks."""
    
    def __init__(self, db: Session):
        """Initialize the database checker.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        
    def check_all_tables(self) -> Dict[str, bool]:
        """Check all database tables for consistency.
        
        Returns:
            Dictionary with table names and their status
        """
        results = {}
        
        # Check tracks
        results["tracks"] = self.check_tracks()
        
        # Check detections
        results["detections"] = self.check_detections()
        
        # Check stations
        results["stations"] = self.check_stations()
        
        # Check relationships
        results["relationships"] = self.check_relationships()
        
        return results
        
    def check_tracks(self) -> bool:
        """Check tracks table for consistency.
        
        Returns:
            True if all checks pass
        """
        try:
            # Check for tracks without fingerprints
            invalid_tracks = self.db.query(Track).filter(
                (Track.fingerprint == None) | 
                (Track.fingerprint_raw == None)
            ).all()
            
            if invalid_tracks:
                logger.warning(f"Found {len(invalid_tracks)} tracks without fingerprints")
                return False
                
            # Check for duplicate fingerprints
            duplicate_query = text("""
                SELECT fingerprint, COUNT(*) 
                FROM tracks 
                GROUP BY fingerprint 
                HAVING COUNT(*) > 1
            """)
            duplicates = self.db.execute(duplicate_query).fetchall()
            
            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicate fingerprints")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking tracks: {str(e)}")
            return False
            
    def check_detections(self) -> bool:
        """Check detections table for consistency.
        
        Returns:
            True if all checks pass
        """
        try:
            # Check for detections without tracks
            invalid_detections = self.db.query(TrackDetection).filter(
                TrackDetection.track_id == None
            ).all()
            
            if invalid_detections:
                logger.warning(f"Found {len(invalid_detections)} detections without tracks")
                return False
                
            # Check for invalid durations
            invalid_durations = self.db.query(TrackDetection).filter(
                (TrackDetection.play_duration <= 0) |
                (TrackDetection.play_duration > 3600)  # Max 1 hour
            ).all()
            
            if invalid_durations:
                logger.warning(f"Found {len(invalid_durations)} detections with invalid durations")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking detections: {str(e)}")
            return False
            
    def check_stations(self) -> bool:
        """Check stations table for consistency.
        
        Returns:
            True if all checks pass
        """
        try:
            # Check for stations without URLs
            invalid_stations = self.db.query(RadioStation).filter(
                (RadioStation.stream_url == None) |
                (RadioStation.stream_url == "")
            ).all()
            
            if invalid_stations:
                logger.warning(f"Found {len(invalid_stations)} stations without URLs")
                return False
                
            # Check for duplicate URLs
            duplicate_query = text("""
                SELECT stream_url, COUNT(*) 
                FROM radio_stations 
                GROUP BY stream_url 
                HAVING COUNT(*) > 1
            """)
            duplicates = self.db.execute(duplicate_query).fetchall()
            
            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicate station URLs")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking stations: {str(e)}")
            return False
            
    def check_relationships(self) -> bool:
        """Check database relationships for consistency.
        
        Returns:
            True if all checks pass
        """
        try:
            # Check for orphaned detections
            orphaned_detections = self.db.query(TrackDetection).filter(
                ~TrackDetection.track_id.in_(
                    self.db.query(Track.id)
                )
            ).all()
            
            if orphaned_detections:
                logger.warning(f"Found {len(orphaned_detections)} orphaned detections")
                return False
                
            # Check for detections with invalid stations
            invalid_station_detections = self.db.query(TrackDetection).filter(
                ~TrackDetection.station_id.in_(
                    self.db.query(RadioStation.id)
                )
            ).all()
            
            if invalid_station_detections:
                logger.warning(f"Found {len(invalid_station_detections)} detections with invalid stations")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking relationships: {str(e)}")
            return False
            
    def get_table_stats(self) -> Dict[str, int]:
        """Get statistics for all tables.
        
        Returns:
            Dictionary with table names and row counts
        """
        try:
            stats = {}
            
            # Get track count
            stats["tracks"] = self.db.query(Track).count()
            
            # Get detection count
            stats["detections"] = self.db.query(TrackDetection).count()
            
            # Get station count
            stats["stations"] = self.db.query(RadioStation).count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting table stats: {str(e)}")
            return {} 