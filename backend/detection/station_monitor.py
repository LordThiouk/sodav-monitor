"""
Station monitoring module for SODAV Monitor (Legacy).

This module is kept for backward compatibility.
The actual implementation has been moved to detection/audio_processor/station_monitor.py.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime, timedelta

from backend.models.models import RadioStation, StationHealth, StationStatus
from backend.detection.audio_processor.station_monitor import StationMonitor as NewStationMonitor

# Configure logging
logger = logging.getLogger(__name__)

class StationMonitor(NewStationMonitor):
    """
    Legacy class for monitoring radio stations and their health.
    
    This class is kept for backward compatibility.
    The actual implementation has been moved to detection/audio_processor/station_monitor.py.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the StationMonitor with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        super().__init__(db_session)
        logger.warning("Using legacy StationMonitor. Please update your imports to use backend.detection.audio_processor.station_monitor.StationMonitor instead.") 