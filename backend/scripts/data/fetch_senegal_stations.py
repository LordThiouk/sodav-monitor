#!/usr/bin/env python3
"""
Script to fetch Senegalese radio stations and add them to the database.
"""

import os
import sys
import logging
import requests
from datetime import datetime

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from sqlalchemy.orm import Session
from models.models import RadioStation
from models.database import get_db, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Radio Browser API endpoint
API_URL = "https://de1.api.radio-browser.info/json/stations/bycountry/senegal"

def fetch_senegal_stations():
    """Fetch Senegalese radio stations from the Radio Browser API."""
    try:
        # Initialize the database
        init_db()
        
        # Get a database session
        db_session = next(get_db())
        
        # Fetch stations from the API
        logger.info("Fetching Senegalese radio stations...")
        headers = {
            'User-Agent': 'SODAV-Monitor/1.0',
            'Content-Type': 'application/json'
        }
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        
        stations = response.json()
        logger.info(f"Found {len(stations)} Senegalese radio stations.")
        
        # Add stations to the database
        added_count = 0
        for station in stations:
            # Check if station already exists
            existing_station = db_session.query(RadioStation).filter(
                RadioStation.name == station.get('name')
            ).first()
            
            if existing_station:
                logger.debug(f"Station '{station.get('name')}' already exists.")
                continue
            
            # Create new station
            new_station = RadioStation(
                name=station.get('name', ''),
                url=station.get('url', ''),
                homepage=station.get('homepage', ''),
                favicon=station.get('favicon', ''),
                country='Senegal',
                language=station.get('language', ''),
                tags=station.get('tags', ''),
                created_at=datetime.utcnow()
            )
            
            db_session.add(new_station)
            added_count += 1
        
        # Commit changes
        db_session.commit()
        logger.info(f"Added {added_count} new radio stations to the database.")
        
    except requests.RequestException as e:
        logger.error(f"Error fetching stations: {e}")
        raise
    except Exception as e:
        logger.error(f"Error adding stations to database: {e}")
        raise

if __name__ == "__main__":
    fetch_senegal_stations() 