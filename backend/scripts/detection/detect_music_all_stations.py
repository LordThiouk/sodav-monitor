#!/usr/bin/env python
"""
Script to detect music on all active radio stations at once.
"""
import os
import sys
import requests
import time
import json
from datetime import datetime

# Add the backend directory to the path so we can import from it
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from backend.models.database import init_db
from backend.logs.log_manager import LogManager

# Initialize logging with specific logger name
log_manager = LogManager()
logger = log_manager.get_logger("scripts.detection.music_all_stations")

# API endpoints
API_URL = os.environ.get("API_URL", "http://localhost:8000/api")
AUTH_URL = f"{API_URL}/auth/login"
DETECT_ALL_URL = f"{API_URL}/detect-music-all"

# Admin credentials from environment variables
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

async def detect_music_all_stations():
    """Detect music on all active radio stations."""
    try:
        # Get auth token
        token = get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return None
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info("Starting music detection on all active stations...")
        
        # Make the request
        response = requests.post(DETECT_ALL_URL, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            stations_count = result.get('stations_count', 0)
            
            if stations_count > 0:
                logger.info(f"Music detection initiated for {stations_count} active stations")
                
                # Save the results to a file with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"detection_results_all_{timestamp}.json"
                
                with open(filename, "w") as f:
                    json.dump(result, f, indent=4)
                    
                logger.info(f"Results saved to {filename}")
                logger.debug(f"Detailed results: {json.dumps(result, indent=4)}")
                
                return result
            else:
                logger.warning("No active stations found for music detection")
                return None
        else:
            logger.error(f"Failed to detect music: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error detecting music on all stations: {str(e)}")
        return None

def get_auth_token():
    """Get authentication token by logging in."""
    try:
        # Check if credentials are provided
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            logger.error("Admin credentials not provided. Please set ADMIN_EMAIL and ADMIN_PASSWORD environment variables.")
            return None
            
        login_data = {
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = requests.post(AUTH_URL, data=login_data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data.get("access_token")
    
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return None

if __name__ == "__main__":
    # Check if environment variables are set
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        logger.error("Admin credentials not provided. Please set ADMIN_EMAIL and ADMIN_PASSWORD environment variables.")
        sys.exit(1)
        
    import asyncio
    asyncio.run(detect_music_all_stations()) 