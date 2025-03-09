"""
Station monitoring module for SODAV Monitor.

This module provides functionality for monitoring radio stations,
checking their health, and updating their status.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.models.models import RadioStation, StationHealth, StationStatus
from backend.utils.streams.stream_checker import StreamChecker

# Configure logging
logger = logging.getLogger(__name__)

class StationMonitor:
    """
    Class for monitoring radio stations and their health.
    
    This class provides methods for starting and stopping monitoring,
    checking stream health, and updating station status.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the StationMonitor with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.stream_checker = StreamChecker()
        self.monitoring_tasks = {}
        self.health_check_interval = 300  # 5 minutes
        self.cleanup_interval = 86400  # 24 hours
        self.health_record_retention = 30  # days
    
    async def start_monitoring(self, station_id: int) -> bool:
        """
        Start monitoring a radio station.
        
        Args:
            station_id: ID of the radio station to monitor
            
        Returns:
            True if monitoring started successfully, False otherwise
        """
        try:
            station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            
            if not station:
                logger.error(f"Station with ID {station_id} not found")
                return False
            
            if not station.is_active:
                logger.info(f"Station {station.name} is not active, not starting monitoring")
                return False
            
            # Check initial health
            health_check = await self.check_stream_health(station.stream_url)
            
            # Update station health
            await self.update_station_health(station, health_check)
            
            # Start monitoring task if not already running
            if station_id not in self.monitoring_tasks or self.monitoring_tasks[station_id].done():
                self.monitoring_tasks[station_id] = asyncio.create_task(
                    self._monitor_station(station_id)
                )
                logger.info(f"Started monitoring station {station.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring for station {station_id}: {e}")
            return False
    
    async def stop_monitoring(self, station_id: int) -> bool:
        """
        Stop monitoring a radio station.
        
        Args:
            station_id: ID of the radio station to stop monitoring
            
        Returns:
            True if monitoring stopped successfully, False otherwise
        """
        try:
            if station_id in self.monitoring_tasks and not self.monitoring_tasks[station_id].done():
                self.monitoring_tasks[station_id].cancel()
                try:
                    await self.monitoring_tasks[station_id]
                except asyncio.CancelledError:
                    pass
                
                del self.monitoring_tasks[station_id]
                
                # Update station status
                station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
                if station:
                    station.status = StationStatus.inactive
                    self.db_session.commit()
                    logger.info(f"Stopped monitoring station {station.name}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error stopping monitoring for station {station_id}: {e}")
            return False
    
    async def check_stream_health(self, stream_url: str) -> Dict[str, Any]:
        """
        Check the health of a stream.
        
        Args:
            stream_url: URL of the stream to check
            
        Returns:
            Dictionary containing health check results
        """
        try:
            return await self.stream_checker.check_stream(stream_url)
        except Exception as e:
            logger.error(f"Error checking stream health for {stream_url}: {e}")
            return {
                'is_available': False,
                'is_audio_stream': False,
                'status_code': None,
                'content_type': None,
                'bitrate': None,
                'error': str(e)
            }
    
    async def update_station_health(self, station: RadioStation, health_check: Dict[str, Any]) -> None:
        """
        Update the health status of a station based on health check results.
        
        Args:
            station: RadioStation object
            health_check: Health check results
        """
        try:
            # Create health record
            health_record = StationHealth(
                station_id=station.id,
                timestamp=datetime.now(),
                is_available=health_check.get('is_available', False),
                is_audio_stream=health_check.get('is_audio_stream', False),
                status_code=health_check.get('status_code'),
                content_type=health_check.get('content_type'),
                bitrate=health_check.get('bitrate'),
                error=health_check.get('error')
            )
            
            self.db_session.add(health_record)
            
            # Update station status
            station.last_checked = datetime.now()
            
            if health_check.get('is_available', False) and health_check.get('is_audio_stream', False):
                # Stream is healthy
                if station.status != StationStatus.active:
                    station.status = StationStatus.active
                station.failure_count = 0
            else:
                # Stream is unhealthy
                station.failure_count += 1
                
                if station.failure_count >= 3:
                    station.status = StationStatus.error
                else:
                    station.status = StationStatus.degraded
            
            self.db_session.commit()
            
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Database error updating station health for {station.name}: {e}")
        except Exception as e:
            logger.error(f"Error updating station health for {station.name}: {e}")
    
    async def monitor_all_stations(self) -> None:
        """
        Start monitoring all active stations.
        """
        try:
            stations = self.db_session.query(RadioStation).filter(RadioStation.is_active == True).all()
            
            for station in stations:
                await self.start_monitoring(station.id)
                
            # Start cleanup task
            asyncio.create_task(self._cleanup_task())
            
        except Exception as e:
            logger.error(f"Error starting monitoring for all stations: {e}")
    
    async def handle_station_recovery(self, station_id: int) -> bool:
        """
        Handle recovery of a station that was previously in error state.
        
        Args:
            station_id: ID of the station to recover
            
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
            
            if not station:
                logger.error(f"Station with ID {station_id} not found")
                return False
            
            # Check current health
            health_check = await self.check_stream_health(station.stream_url)
            
            if health_check.get('is_available', False) and health_check.get('is_audio_stream', False):
                # Reset failure count and update status
                station.failure_count = 0
                station.status = StationStatus.active
                station.last_checked = datetime.now()
                
                # Create health record
                health_record = StationHealth(
                    station_id=station.id,
                    timestamp=datetime.now(),
                    is_available=True,
                    is_audio_stream=True,
                    status_code=health_check.get('status_code'),
                    content_type=health_check.get('content_type'),
                    bitrate=health_check.get('bitrate')
                )
                
                self.db_session.add(health_record)
                self.db_session.commit()
                
                # Restart monitoring if needed
                if station_id not in self.monitoring_tasks or self.monitoring_tasks[station_id].done():
                    await self.start_monitoring(station_id)
                
                logger.info(f"Successfully recovered station {station.name}")
                return True
            
            logger.info(f"Recovery attempt for station {station.name} failed, stream still unhealthy")
            return False
            
        except Exception as e:
            logger.error(f"Error handling recovery for station {station_id}: {e}")
            return False
    
    async def cleanup_old_health_records(self) -> None:
        """
        Clean up old health records to prevent database bloat.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.health_record_retention)
            
            # Delete old records
            self.db_session.query(StationHealth).filter(
                StationHealth.timestamp < cutoff_date
            ).delete()
            
            self.db_session.commit()
            logger.info(f"Cleaned up health records older than {cutoff_date}")
            
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Database error cleaning up old health records: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up old health records: {e}")
    
    async def _monitor_station(self, station_id: int) -> None:
        """
        Internal method to continuously monitor a station.
        
        Args:
            station_id: ID of the station to monitor
        """
        try:
            while True:
                station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
                
                if not station or not station.is_active:
                    logger.info(f"Station {station_id} is no longer active, stopping monitoring")
                    break
                
                # Check health
                health_check = await self.check_stream_health(station.stream_url)
                
                # Update station health
                await self.update_station_health(station, health_check)
                
                # Wait for next check
                await asyncio.sleep(self.health_check_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Monitoring task for station {station_id} cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring task for station {station_id}: {e}")
    
    async def _cleanup_task(self) -> None:
        """
        Internal method to periodically clean up old health records.
        """
        try:
            while True:
                await self.cleanup_old_health_records()
                await asyncio.sleep(self.cleanup_interval)
                
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}") 