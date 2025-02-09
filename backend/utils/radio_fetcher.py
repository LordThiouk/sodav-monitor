import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
from models import StationStatus

logger = logging.getLogger(__name__)

class RadioFetcher:
    def __init__(self):
        self.base_url = "https://de1.api.radio-browser.info/json"
        
    def _make_request(self, endpoint: str) -> Optional[List[Dict]]:
        """Make a request to the Radio Browser API"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching radio stations: {str(e)}")
            return None

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
