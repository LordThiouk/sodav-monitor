"""Radio station management utilities.

This module provides functionality for managing radio stations, including
status updates, monitoring, and configuration.
"""

from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.models import RadioStation, StationStatus
from backend.utils.logging_config import setup_logging

logger = setup_logging(__name__)


class RadioManager:
    """Radio station manager for handling station operations.

    This class provides methods for managing radio stations, including
    status updates, monitoring configuration, and station information.
    """

    def __init__(self, db: Session):
        """Initialize the radio manager.

        Args:
            db: Database session to use for operations
        """
        self.db = db

    def get_all_stations(self) -> List[RadioStation]:
        """Get all radio stations.

        Returns:
            List[RadioStation]: List of all radio stations
        """
        return self.db.query(RadioStation).all()

    def get_active_stations(self) -> List[RadioStation]:
        """Get all active radio stations.

        Returns:
            List[RadioStation]: List of active radio stations
        """
        return self.db.query(RadioStation).filter(RadioStation.status == StationStatus.ACTIVE).all()

    def get_station_by_id(self, station_id: int) -> Optional[RadioStation]:
        """Get a radio station by its ID.

        Args:
            station_id: ID of the station to retrieve

        Returns:
            Optional[RadioStation]: The radio station if found, None otherwise
        """
        return self.db.query(RadioStation).filter(RadioStation.id == station_id).first()

    def update_station_status(
        self, station_id: int, status: StationStatus
    ) -> Optional[RadioStation]:
        """Update a station's status.

        Args:
            station_id: ID of the station to update
            status: New status to set

        Returns:
            Optional[RadioStation]: Updated station if found, None otherwise
        """
        station = self.get_station_by_id(station_id)
        if station:
            station.status = status
            self.db.commit()
        return station

    def get_station_stats(self, station_id: int) -> Dict:
        """Get statistics for a specific station.

        Args:
            station_id: ID of the station to get stats for

        Returns:
            Dict: Station statistics
        """
        station = self.get_station_by_id(station_id)
        if station is None:
            return {}

        # Get detection count
        detection_count = (
            self.db.query(func.count()).filter(RadioStation.id == station_id).scalar() or 0
        )

        # Get monitoring status
        is_monitored = station.status == StationStatus.ACTIVE

        return {
            "id": station.id,
            "name": station.name,
            "stream_url": station.stream_url,
            "status": station.status.value,
            "detection_count": detection_count,
            "is_monitored": is_monitored,
            "last_checked": station.last_checked.isoformat() if station.last_checked else None,
        }

    def get_monitoring_status(self, station_id: int) -> bool:
        """Get the monitoring status of a station.

        Args:
            station_id: ID of the station to check

        Returns:
            bool: True if the station is being monitored, False otherwise
        """
        station = self.get_station_by_id(station_id)
        return station.status == StationStatus.ACTIVE if station else False

    def set_monitoring_status(self, station_id: int, enabled: bool) -> bool:
        """Set the monitoring status of a station.

        Args:
            station_id: ID of the station to update
            enabled: Whether to enable or disable monitoring

        Returns:
            bool: True if the update was successful, False otherwise
        """
        station = self.get_station_by_id(station_id)
        if station is not None:
            station.status = StationStatus.ACTIVE if enabled else StationStatus.INACTIVE
            self.db.commit()
            return True
        return False
