"""Database checking and validation functionality.

This module provides functionality for checking and validating the database state,
including table consistency, relationships, and data integrity.
"""

from typing import Dict

from sqlalchemy.orm import Session

from backend.models.models import RadioStation, Track, TrackDetection
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)


class DatabaseChecker:
    """Database validation and health check manager.

    This class provides methods for checking database consistency, validating
    relationships between tables, and ensuring data integrity across the system.
    """

    def __init__(self, db: Session):
        """Initialize the database checker.

        Args:
            db: SQLAlchemy database session to use for checks
        """
        self.db = db

    def check_all_tables(self) -> Dict[str, bool]:
        """Check all database tables for consistency.

        Performs comprehensive checks on all tables including tracks,
        detections, stations, and their relationships.

        Returns:
            Dict[str, bool]: Dictionary mapping table names to their validation status
        """
        results = {}

        results["tracks"] = self.check_tracks()
        results["detections"] = self.check_detections()
        results["stations"] = self.check_stations()
        results["relationships"] = self.check_relationships()

        return results

    def check_tracks(self) -> bool:
        """Check tracks table for consistency.

        Validates track records for required fields and data integrity.

        Returns:
            bool: True if all checks pass, False otherwise
        """
        try:
            # Check for tracks with missing required fields
            invalid_tracks = (
                self.db.query(Track)
                .filter((Track.title is None) | (Track.artist_id is None) | (Track.isrc is None))
                .all()
            )

            if invalid_tracks:
                logger.warning(f"Found {len(invalid_tracks)} tracks with missing required fields")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking tracks: {str(e)}")
            return False

    def check_detections(self) -> bool:
        """Check detections table for consistency.

        Validates detection records for required fields, timestamps,
        and relationships with tracks and stations.

        Returns:
            bool: True if all checks pass, False otherwise
        """
        try:
            # Check for detections with missing required fields
            invalid_detections = (
                self.db.query(TrackDetection)
                .filter(
                    (TrackDetection.track_id is None)
                    | (TrackDetection.station_id is None)
                    | (TrackDetection.detected_at is None)
                )
                .all()
            )

            if invalid_detections:
                logger.warning(
                    f"Found {len(invalid_detections)} detections with missing required fields"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking detections: {str(e)}")
            return False

    def check_stations(self) -> bool:
        """Check stations table for consistency.

        Validates station records for required fields, stream URLs,
        and monitoring status.

        Returns:
            bool: True if all checks pass, False otherwise
        """
        try:
            # Check for stations with missing required fields
            invalid_stations = (
                self.db.query(RadioStation)
                .filter(
                    (RadioStation.name is None)
                    | (RadioStation.stream_url is None)
                    | (RadioStation.status is None)
                )
                .all()
            )

            if invalid_stations:
                logger.warning(
                    f"Found {len(invalid_stations)} stations with missing required fields"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking stations: {str(e)}")
            return False

    def check_relationships(self) -> bool:
        """Check relationships between tables.

        Validates foreign key relationships between tracks, detections,
        and stations tables.

        Returns:
            bool: True if all relationships are valid, False otherwise
        """
        try:
            # Check for detections with invalid track references
            orphaned_detections = (
                self.db.query(TrackDetection)
                .filter(TrackDetection.track_id.isnot(None))
                .join(Track, TrackDetection.track_id == Track.id, isouter=True)
                .filter(Track.id is None)
                .all()
            )

            if orphaned_detections:
                logger.warning(
                    f"Found {len(orphaned_detections)} detections with invalid track references"
                )
                return False

            # Check for detections with invalid station references
            invalid_station_refs = (
                self.db.query(TrackDetection)
                .filter(TrackDetection.station_id.isnot(None))
                .join(RadioStation, TrackDetection.station_id == RadioStation.id, isouter=True)
                .filter(RadioStation.id is None)
                .all()
            )

            if invalid_station_refs:
                logger.warning(
                    f"Found {len(invalid_station_refs)} detections with invalid station references"
                )
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
