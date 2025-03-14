#!/usr/bin/env python
"""
Script to detect music on all active radio stations at once.
"""
import json
import os
import sys
import time
from datetime import datetime

import requests

# Add the backend directory to the path so we can import from it
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Import using relative path
from backend.logs import LogManager
from backend.models.database import init_db

# Initialize logging with specific logger name
log_manager = LogManager()
logger = log_manager.get_logger("scripts.detection.music_all_stations")

# API endpoints
API_URL = os.environ.get("API_URL", "http://localhost:8000/api")
DETECT_ALL_URL = f"{API_URL}/detect-music-all"


async def detect_music_all_stations():
    """Detect music on all active radio stations."""
    try:
        logger.info("Starting music detection on all active stations...")

        # Make the request without authentication
        response = requests.post(DETECT_ALL_URL)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            stations_count = result.get("stations_count", 0)

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


if __name__ == "__main__":
    import asyncio

    asyncio.run(detect_music_all_stations())
