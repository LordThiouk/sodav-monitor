import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import aiohttp
from .models import RadioStation, StationStatus, Track, TrackDetection
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from .utils.logging_config import setup_logging
from .audio_processor import AudioProcessor

class RadioManager:
    def __init__(self, db_session: Session, audio_processor: AudioProcessor = None):
        """Initialize RadioManager with database session and audio processor.
        
        Args:
            db_session (Session): SQLAlchemy database session
            audio_processor (AudioProcessor, optional): Instance of AudioProcessor for music detection
        """
        self.db_session = db_session
        self.api_base_url = "https://de1.api.radio-browser.info/json"
        self.logger = logging.getLogger(__name__)
        self.audio_processor = audio_processor
        
        if not audio_processor:
            self.logger.warning("No AudioProcessor provided, some features will be limited")
        else:
            self.logger.info("RadioManager initialized successfully with AudioProcessor")

    async def update_station_list(self, country: str = None, language: str = None) -> None:
        """Update the radio station list from RadioBrowser API."""
        try:
            params = {}
            if country:
                params['country'] = country
            if language:
                params['language'] = language

            async with aiohttp.ClientSession() as session:
                # Get stations from API
                async with session.get(f"{self.api_base_url}/stations", params=params) as response:
                    if response.status == 200:
                        stations = await response.json()
                        await self._process_stations(stations)
                    else:
                        self.logger.error(f"Failed to fetch stations: {response.status}")

        except Exception as e:
            self.logger.error(f"Error updating station list: {str(e)}")

    async def _process_stations(self, stations: List[Dict[Any, Any]]) -> None:
        """Process and update stations in database."""
        for station_data in stations:
            try:
                # Check if station exists
                station = self.db_session.query(RadioStation).filter_by(
                    name=station_data['name']
                ).first()

                if station:
                    # Update existing station
                    station.stream_url = station_data['url_resolved']
                    station.country = station_data['country']
                    station.language = station_data['language']
                    station.last_checked = datetime.now()
                    station.last_checked = datetime.utcnow()
                else:
                    # Create new station
                    station = RadioStation(
                        name=station_data['name'],
                        stream_url=station_data['url_resolved'],
                        country=station_data['country'],
                        language=station_data['language'],
                        is_active=1,
                        last_checked=datetime.now()
                    )
                    self.db_session.add(station)

            except Exception as e:
                self.logger.error(f"Error processing station {station_data.get('name', 'unknown')}: {str(e)}")
                continue

        try:
            self.db_session.commit()
        except Exception as e:
            self.logger.error(f"Error committing stations to database: {str(e)}")
            self.db_session.rollback()

    async def check_station_availability(self, station: RadioStation) -> bool:
        """Check if a station's stream is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(station.stream_url, timeout=10) as response:
                    return response.status == 200
        except Exception:
            return False

    async def get_active_stations(self) -> List[RadioStation]:
        """Get list of active radio stations."""
        return self.db_session.query(RadioStation).filter_by(is_active=True).all()

    async def update_station_status(self, station: RadioStation, is_active: bool) -> None:
        """Update station's active status."""
        station.is_active = is_active
        station.last_checked = datetime.utcnow()
        self.db_session.commit()

    async def detect_music(self, station_id: int = None) -> Dict:
        """Detect music from a station or all active stations."""
        try:
            if station_id:
                station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
                if not station:
                    raise ValueError("Station not found")
                stations = [station]
            else:
                stations = await self.get_active_stations()

            results = []
            for station in stations:
                try:
                    if not self.audio_processor:
                        raise ValueError("AudioProcessor not initialized")
                        
                    result = await self.audio_processor.analyze_stream(station.stream_url, station.id)
                    if result:
                        results.append({
                            "station_id": station.id,
                            "station_name": station.name,
                            "detection": result
                        })
                except Exception as e:
                    self.logger.error(f"Error detecting music for station {station.name}: {str(e)}")
                    continue

            return {
                "status": "success",
                "message": f"Analyzed {len(stations)} stations",
                "detections": results
            }

        except Exception as e:
            self.logger.error(f"Error in detect_music: {str(e)}")
            raise
