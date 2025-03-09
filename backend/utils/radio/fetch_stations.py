"""Module for fetching radio stations from the Radio Browser API.

This module provides functions to fetch radio stations from the Radio Browser API,
specifically focusing on Senegalese radio stations.
"""

import logging
import aiohttp
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy import inspect

from backend.models.models import RadioStation

logger = logging.getLogger(__name__)

class RadioBrowserClient:
    """Client for interacting with the Radio Browser API."""
    
    BASE_URL = "https://de1.api.radio-browser.info/json"
    
    @classmethod
    async def fetch_stations_by_country(cls, country: str) -> List[Dict[str, Any]]:
        """Fetch radio stations by country from the Radio Browser API.
        
        Args:
            country: Country name to filter stations by
            
        Returns:
            List of station dictionaries
        """
        try:
            url = f"{cls.BASE_URL}/stations/bycountry/{country}"
            headers = {
                'User-Agent': 'SODAV-Monitor/1.0',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        stations = await response.json()
                        logger.info(f"Found {len(stations)} stations for country: {country}")
                        return stations
                    else:
                        logger.error(f"Error fetching stations for country {country}: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Exception fetching stations for country {country}: {str(e)}")
            return []

async def fetch_and_save_senegal_stations(db: Session) -> int:
    """Fetch Senegalese radio stations and save them to the database.
    
    Args:
        db: Database session
        
    Returns:
        Number of stations processed
    """
    try:
        # Check if radio_stations table exists
        inspector = inspect(db.bind)
        if not inspector.has_table("radio_stations"):
            logger.warning("radio_stations table does not exist yet. Will be created during next database initialization.")
            return 0
            
        # Fetch stations from Radio Browser API
        stations = await RadioBrowserClient.fetch_stations_by_country("Senegal")
        
        if not stations:
            logger.warning("No Senegalese stations found from Radio Browser API")
            return 0
        
        # Process each station
        stations_added = 0
        stations_updated = 0
        
        for station_data in stations:
            try:
                # Check if station already exists by stream URL
                existing_station = db.query(RadioStation).filter(
                    RadioStation.stream_url == station_data['url_resolved']
                ).first()
                
                if existing_station:
                    # Update existing station
                    existing_station.name = station_data['name']
                    existing_station.stream_url = station_data['url_resolved']
                    existing_station.country = 'Senegal'
                    existing_station.language = station_data.get('language', '')
                    existing_station.is_active = True
                    existing_station.status = 'active'
                    existing_station.last_check = datetime.utcnow()
                    existing_station.updated_at = datetime.utcnow()
                    stations_updated += 1
                    logger.info(f"Updated station: {station_data['name']}")
                else:
                    # Create new station
                    new_station = RadioStation(
                        name=station_data['name'],
                        stream_url=station_data['url_resolved'],
                        country='Senegal',
                        language=station_data.get('language', ''),
                        region=station_data.get('state', ''),
                        is_active=True,
                        status='active',
                        last_check=datetime.utcnow()
                    )
                    db.add(new_station)
                    stations_added += 1
                    logger.info(f"Added new station: {station_data['name']}")
            except Exception as station_error:
                logger.error(f"Error processing station {station_data.get('name', 'unknown')}: {str(station_error)}")
                continue
                
        # Commit changes
        db.commit()
        logger.info(f"Successfully processed {stations_added + stations_updated} Senegalese stations (Added: {stations_added}, Updated: {stations_updated})")
        return stations_added + stations_updated
        
    except (ProgrammingError, OperationalError) as db_error:
        logger.error(f"Database error processing Senegalese stations: {str(db_error)}")
        db.rollback()
        return 0
    except Exception as e:
        logger.error(f"Error processing Senegalese stations: {str(e)}")
        db.rollback()
        return 0 