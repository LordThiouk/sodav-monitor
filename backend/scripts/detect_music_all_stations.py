#!/usr/bin/env python
"""
Script to detect music on all active radio stations at once.
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

from models.database import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API endpoints
BASE_URL = "http://localhost:8000/api"
LOGIN_URL = f"{BASE_URL}/auth/login"
DETECT_ALL_URL = f"{BASE_URL}/detect-music-all"

# Admin credentials (should be stored securely in a real application)
ADMIN_EMAIL = "admin@sodav.sn"
ADMIN_PASSWORD = "admin123"

def get_auth_token():
    """Get authentication token by logging in."""
    try:
        login_data = {
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = requests.post(LOGIN_URL, data=login_data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data.get("access_token")
    
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return None

def detect_music_all_stations():
    """Detect music on all active radio stations at once."""
    try:
        # Initialize the database
        init_db()
        
        # Get authentication token
        token = get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return {"status": "error", "message": "Authentication failed"}
        
        # Set up headers with authentication token
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        logger.info("Starting music detection on all active stations...")
        
        # Call the music detection API for all stations
        response = requests.post(DETECT_ALL_URL, headers=headers)
        response.raise_for_status()
        
        # Process response
        result = response.json()
        
        # Save results to a file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detection_results_all_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(result, f, indent=4)
        
        logger.info(f"Music detection initiated for {result.get('stations_count', 0)} active stations")
        logger.info(f"Results saved to {filename}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    detect_music_all_stations() 