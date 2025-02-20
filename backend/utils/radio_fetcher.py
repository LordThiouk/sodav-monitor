import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
from ..models import StationStatus
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class RadioFetcher:
    def __init__(self):
        self.base_url = "https://de1.api.radio-browser.info/json"
        self.timeout = 10
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def _make_request(self, endpoint: str) -> Optional[List[Dict]]:
        """Make a request to the Radio Browser API"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching radio stations: {str(e)}")
            return None

    async def check_stream_status(self, stream_url: str) -> bool:
        """Check if a stream URL is currently active.
        
        Args:
            stream_url (str): The URL of the stream to check
            
        Returns:
            bool: True if the stream is active, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    stream_url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True
                ) as response:
                    return response.status == 200
                    
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Stream check failed for {stream_url}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking stream {stream_url}: {str(e)}")
            return False

    def get_senegal_stations(self) -> List[Dict]:
        """Get all radio stations from Senegal"""
        try:
            # Search by country code and country name for better coverage
            stations_by_code = self._make_request("stations/bycountrycodeexact/SN") or []
            stations_by_name = self._make_request("stations/bycountry/Senegal") or []
            
            # Combine and deduplicate stations
            all_stations = stations_by_code + stations_by_name
            unique_stations = {station['url']: station for station in all_stations}.values()
            
            # Format stations
            formatted_stations = []
            for station in unique_stations:
                if not station['url']:  # Skip stations without URL
                    continue
                    
                formatted_station = {
                    'name': station['name'],
                    'stream_url': station['url'],
                    'country': 'Senegal',
                    'language': station.get('language', 'Unknown'),
                    'status': StationStatus.active if station.get('lastcheckok', 0) == 1 else StationStatus.inactive,
                    'is_active': True,
                    'last_check_time': datetime.utcnow(),
                    'last_detection_time': None
                }
                formatted_stations.append(formatted_station)
            
            logger.info(f"Found {len(formatted_stations)} Senegalese radio stations")
            return formatted_stations
            
        except Exception as e:
            logger.error(f"Error processing radio stations: {str(e)}")
            return []
