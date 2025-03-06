#!/usr/bin/env python3
"""
Script to test music detection on all radio stations in the database.
"""

import os
import sys
import logging
import requests
import time
import json
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

# API endpoint for music detection
API_URL = "http://localhost:8000/detect-music"

def test_music_detection():
    """Test music detection on all radio stations in the database."""
    try:
        # Initialize the database
        init_db()
        
        # Get a database session
        db_session = next(get_db())
        
        # Get all radio stations
        stations = db_session.query(RadioStation).all()
        logger.info(f"Found {len(stations)} radio stations in the database.")
        
        if not stations:
            logger.warning("No radio stations found in the database. Please run fetch_senegal_stations.py first.")
            return
        
        # Test music detection on each station
        results = []
        for station in stations:
            logger.info(f"Testing music detection on: {station.name}")
            
            try:
                # Prepare request data
                data = {
                    "station_id": station.id,
                    "url": station.stream_url
                }
                
                # Call the music detection API
                response = requests.post(API_URL, json=data)
                response.raise_for_status()
                
                # Process response
                result = response.json()
                result["station_name"] = station.name
                results.append(result)
                
                logger.info(f"Result for {station.name}: {result}")
                
                # Add a small delay to avoid overwhelming the server
                time.sleep(1)
                
            except requests.RequestException as e:
                logger.error(f"Error testing station {station.name}: {e}")
                results.append({
                    "station_name": station.name,
                    "error": str(e),
                    "success": False
                })
        
        # Save results to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"detection_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        
        # Print summary
        success_count = sum(1 for r in results if r.get("success", False))
        logger.info(f"Summary: {success_count}/{len(results)} stations successfully processed.")
        
    except Exception as e:
        logger.error(f"Error during music detection test: {e}")
        raise

if __name__ == "__main__":
    test_music_detection() 