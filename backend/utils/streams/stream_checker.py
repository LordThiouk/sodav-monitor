"""Utility module for checking radio stream availability and health."""

import aiohttp
import asyncio
from typing import Dict, Optional, List, Tuple
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class StreamChecker:
    """Class for checking radio stream availability, metadata and health metrics."""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the stream checker.
        
        Args:
            timeout: Default timeout for requests in seconds
            max_retries: Maximum number of retries for failed checks
            session: Optional aiohttp ClientSession to use for requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._health_history: Dict[str, List[Dict]] = {}
        self._session = session

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get a session for making requests.
        
        Returns:
            An aiohttp ClientSession instance
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def check_stream_availability(self, stream_url: str, timeout: Optional[int] = None) -> Dict[str, bool]:
        """
        Check if a radio stream is available and accessible.
        
        Args:
            stream_url: The URL of the radio stream to check
            timeout: Optional timeout override in seconds
            
        Returns:
            Dict containing status information:
            {
                'is_available': bool,
                'is_audio_stream': bool,
                'status_code': int,
                'latency': float
            }
        """
        timeout = timeout or self.timeout
        start_time = time.time()
        
        try:
            session = await self._get_session()
            async with session.head(stream_url, timeout=timeout) as response:
                latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                headers = response.headers
                content_type = headers.get('Content-Type', '').lower()
                
                is_audio = any(audio_type in content_type for audio_type in [
                    'audio/',
                    'application/ogg',
                    'application/x-mpegurl',
                    'application/vnd.apple.mpegurl'
                ])
                
                result = {
                    'is_available': response.status == 200,
                    'is_audio_stream': is_audio,
                    'status_code': response.status,
                    'latency': latency
                }
                
                # Update health history
                self._update_health_history(stream_url, result)
                
                return result
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout checking stream: {stream_url}")
            result = {
                'is_available': False,
                'is_audio_stream': False,
                'status_code': 408,
                'latency': self.timeout * 1000,
                'error': 'timeout'
            }
            self._update_health_history(stream_url, result)
            return result
            
        except aiohttp.ClientError as e:
            logger.error(f"Error checking stream {stream_url}: {str(e)}")
            result = {
                'is_available': False,
                'is_audio_stream': False,
                'status_code': 503,
                'latency': -1,
                'error': 'connection_error'
            }
            self._update_health_history(stream_url, result)
            return result

    async def get_stream_metadata(self, stream_url: str, timeout: Optional[int] = None) -> Optional[Dict[str, str]]:
        """
        Attempt to get metadata from a radio stream.
        
        Args:
            stream_url: The URL of the radio stream
            timeout: Optional timeout override in seconds
            
        Returns:
            Dict containing metadata if available, None otherwise
        """
        timeout = timeout or self.timeout
        
        try:
            session = await self._get_session()
            async with session.get(stream_url, timeout=timeout) as response:
                headers = response.headers
                icy_name = headers.get('icy-name')
                icy_genre = headers.get('icy-genre')
                icy_br = headers.get('icy-br')
                icy_description = headers.get('icy-description')
                icy_url = headers.get('icy-url')
                
                if any([icy_name, icy_genre, icy_br, icy_description, icy_url]):
                    return {
                        'name': icy_name,
                        'genre': icy_genre,
                        'bitrate': icy_br,
                        'description': icy_description,
                        'url': icy_url
                    }
                return None
                
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"Error getting metadata from {stream_url}: {str(e)}")
            return None

    def _update_health_history(self, stream_url: str, result: Dict) -> None:
        """Update the health history for a stream.
        
        Args:
            stream_url: The URL of the stream
            result: The result dict from check_stream_availability
        """
        if stream_url not in self._health_history:
            self._health_history[stream_url] = []
            
        history = self._health_history[stream_url]
        history.append({
            'timestamp': datetime.now(),
            'is_available': result['is_available'],
            'latency': result['latency']
        })
        
        # Keep only the last 100 entries
        if len(history) > 100:
            history.pop(0)

    def get_health_metrics(self, stream_url: str) -> Dict:
        """Get health metrics for a stream.
        
        Args:
            stream_url: The URL of the stream
            
        Returns:
            Dict containing health metrics
        """
        if stream_url not in self._health_history:
            return {
                'uptime_percentage': 0,
                'average_latency': 0,
                'checks_count': 0,
                'last_check': None
            }
            
        history = self._health_history[stream_url]
        if not history:
            return {
                'uptime_percentage': 0,
                'average_latency': 0,
                'checks_count': 0,
                'last_check': None
            }
            
        uptime_count = sum(1 for entry in history if entry['is_available'])
        total_latency = sum(entry['latency'] for entry in history if entry['latency'] >= 0)
        valid_latency_count = sum(1 for entry in history if entry['latency'] >= 0)
        
        return {
            'uptime_percentage': (uptime_count / len(history)) * 100,
            'average_latency': total_latency / valid_latency_count if valid_latency_count > 0 else 0,
            'checks_count': len(history),
            'last_check': history[-1]['timestamp']
        }

    async def monitor_stream_health(self, stream_url: str, interval: int = 60) -> None:
        """
        Continuously monitor a stream's health.
        
        Args:
            stream_url: The URL of the stream to monitor
            interval: Time between checks in seconds
        """
        while True:
            await self.check_stream_availability(stream_url)
            await asyncio.sleep(interval)

    async def close(self) -> None:
        """Close the session if it exists."""
        if self._session is not None:
            await self._session.close()
            self._session = None 