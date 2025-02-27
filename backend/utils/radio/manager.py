"""Radio station management functionality."""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.models.models import RadioStation, StationStatus
from backend.utils.logging_config import setup_logging
from backend.core.config import settings

logger = setup_logging(__name__)

class RadioManager:
    """Handles radio station management and monitoring."""
    
    def __init__(self, db: Session):
        """Initialize the radio manager.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.session = aiohttp.ClientSession()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.session.close()
        
    async def fetch_station_info(self, url: str) -> Optional[Dict[str, str]]:
        """Fetch metadata for a radio station.
        
        Args:
            url: Stream URL
            
        Returns:
            Dictionary with station metadata or None
        """
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    headers = response.headers
                    return {
                        "content_type": headers.get("Content-Type", ""),
                        "server": headers.get("Server", ""),
                        "bitrate": headers.get("icy-br", ""),
                        "name": headers.get("icy-name", ""),
                        "genre": headers.get("icy-genre", ""),
                        "url": headers.get("icy-url", "")
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error fetching station info for {url}: {str(e)}")
            return None
            
    async def check_stream_status(self, station: RadioStation) -> bool:
        """Check if a station's stream is accessible.
        
        Args:
            station: RadioStation instance
            
        Returns:
            True if stream is accessible
        """
        try:
            async with self.session.get(station.stream_url, timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error checking stream {station.stream_url}: {str(e)}")
            return False
            
    async def update_station_status(self, station: RadioStation) -> bool:
        """Update a station's status and metadata.
        
        Args:
            station: RadioStation instance
            
        Returns:
            True if update successful
        """
        try:
            # Check stream accessibility
            is_accessible = await self.check_stream_status(station)
            
            # Update status
            station.last_check = datetime.utcnow()
            station.is_active = is_accessible
            
            if is_accessible:
                # Fetch and update metadata
                info = await self.fetch_station_info(station.stream_url)
                if info:
                    station.name = info.get("name", station.name)
                    station.genre = info.get("genre", station.genre)
                    station.website = info.get("url", station.website)
                    station.bitrate = info.get("bitrate", station.bitrate)
                    
            # Create status record
            status = StationStatus(
                station_id=station.id,
                timestamp=datetime.utcnow(),
                is_active=is_accessible,
                response_time=0,  # TODO: Implement response time measurement
                error_message="" if is_accessible else "Stream not accessible"
            )
            self.db.add(status)
            
            # Commit changes
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating station {station.id}: {str(e)}")
            self.db.rollback()
            return False
            
    async def update_all_stations(self) -> Dict[int, bool]:
        """Update status for all stations.
        
        Returns:
            Dictionary mapping station IDs to update success
        """
        results = {}
        stations = self.db.query(RadioStation).all()
        
        for station in stations:
            results[station.id] = await self.update_station_status(station)
            
        return results
        
    def get_active_stations(self) -> List[RadioStation]:
        """Get list of currently active stations.
        
        Returns:
            List of active RadioStation instances
        """
        return self.db.query(RadioStation).filter(
            RadioStation.is_active == True
        ).all()
        
    def get_inactive_stations(self) -> List[RadioStation]:
        """Get list of currently inactive stations.
        
        Returns:
            List of inactive RadioStation instances
        """
        return self.db.query(RadioStation).filter(
            RadioStation.is_active == False
        ).all()
        
    def get_station_stats(self) -> Dict[str, int]:
        """Get statistics about stations.
        
        Returns:
            Dictionary with station statistics
        """
        try:
            stats = {}
            
            # Get total count
            stats["total"] = self.db.query(RadioStation).count()
            
            # Get active count
            stats["active"] = self.db.query(RadioStation).filter(
                RadioStation.is_active == True
            ).count()
            
            # Get inactive count
            stats["inactive"] = stats["total"] - stats["active"]
            
            # Get stations with recent errors
            stats["errors"] = self.db.query(RadioStation).filter(
                RadioStation.last_error != None,
                RadioStation.last_error > datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting station stats: {str(e)}")
            return {} 