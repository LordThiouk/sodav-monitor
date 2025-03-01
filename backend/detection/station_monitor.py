"""Station monitoring module."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models.models import RadioStation, StationHealth, StationStatus
from backend.utils.streams.stream_checker import StreamChecker

logger = logging.getLogger(__name__)

class StationMonitor:
    """Monitor radio stations and track their health."""
    
    def __init__(self, db: Session):
        """Initialize the station monitor."""
        self.db = db
        self.stream_checker = StreamChecker()
        self.monitoring_tasks = {}
        
    async def start_monitoring(self, station_id: int) -> bool:
        """Start monitoring a station."""
        station = self.db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            return False
            
        try:
            # Check stream health
            health = await self.check_stream_health(station.stream_url)
            if not health['is_available'] or not health['is_audio_stream']:
                await self.update_station_health(station, health)
                return False
                
            # Update station status
            station.is_active = True
            station.last_checked = datetime.now()
            station.status = StationStatus.active
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring for station {station_id}: {str(e)}")
            self.db.rollback()
            return False
        
    async def stop_monitoring(self, station_id: int) -> bool:
        """Stop monitoring a station."""
        try:
            station = self.db.query(RadioStation).filter(RadioStation.id == station_id).first()
            if not station:
                return False
                
            station.is_active = False
            station.status = StationStatus.inactive
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error stopping monitoring for station {station_id}: {str(e)}")
            self.db.rollback()
            return False
        
    async def check_stream_health(self, url: str) -> Dict[str, Any]:
        """Check the health of a stream."""
        try:
            return await self.stream_checker.check_stream_availability(url)
        except Exception as e:
            logger.error(f"Error checking stream health: {str(e)}")
            return {
                'is_available': False,
                'is_audio_stream': False,
                'error': str(e)
            }
            
    async def update_station_health(self, station: RadioStation, health_data: Dict[str, Any]):
        """Update station health status."""
        try:
            station.last_checked = datetime.now()
            
            if not health_data['is_available']:
                station.status = StationStatus.inactive
            elif not health_data.get('is_audio_stream'):
                station.status = StationStatus.inactive
            elif health_data.get('latency', 0) > 1000:  # High latency
                station.status = StationStatus.inactive
            else:
                station.status = StationStatus.active
                
            # Record health check
            health_record = StationHealth(
                station_id=station.id,
                status=station.status.value,
                timestamp=station.last_checked,
                response_time=health_data.get('latency'),
                content_type=health_data.get('content_type'),
                error_message=health_data.get('error')
            )
            self.db.add(health_record)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating station health: {str(e)}")
            self.db.rollback()
        
    async def monitor_all_stations(self) -> list:
        """Monitor all active stations."""
        stations = self.db.query(RadioStation).filter(RadioStation.is_active == True).all()
        results = []
        
        for station in stations:
            success = await self.start_monitoring(station.id)
            results.append({
                'station_id': station.id,
                'name': station.name,
                'success': success
            })
            
        return results
        
    async def handle_station_recovery(self, station_id: int):
        """Handle recovery of a failed station."""
        station = self.db.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            return
            
        try:
            health = await self.check_stream_health(station.stream_url)
            if health['is_available'] and health['is_audio_stream']:
                station.status = StationStatus.active
                station.failure_count = 0
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error handling station recovery: {str(e)}")
            self.db.rollback()
            
    async def cleanup_old_health_records(self, days: int = 7) -> int:
        """Clean up old health records."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted = self.db.query(StationHealth).filter(
                StationHealth.timestamp < cutoff_date
            ).delete()
            self.db.commit()
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up old health records: {str(e)}")
            self.db.rollback()
            return 0 