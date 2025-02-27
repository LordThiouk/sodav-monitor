"""Utility module for checking radio stream availability."""

import aiohttp
import asyncio
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class StreamChecker:
    """Class for checking radio stream availability and metadata."""
    
    def __init__(self, timeout: int = 10):
        """Initialize the stream checker.
        
        Args:
            timeout: Default timeout for requests in seconds
        """
        self.timeout = timeout
    
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
                'is_audio_stream': bool
            }
        """
        timeout = timeout or self.timeout
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(stream_url, timeout=timeout) as response:
                    headers = response.headers
                    content_type = headers.get('Content-Type', '').lower()
                    
                    is_audio = any(audio_type in content_type for audio_type in [
                        'audio/',
                        'application/ogg',
                        'application/x-mpegurl',
                        'application/vnd.apple.mpegurl'
                    ])
                    
                    return {
                        'is_available': response.status == 200,
                        'is_audio_stream': is_audio
                    }
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout checking stream: {stream_url}")
            return {
                'is_available': False,
                'is_audio_stream': False
            }
        except aiohttp.ClientError as e:
            logger.error(f"Error checking stream {stream_url}: {str(e)}")
            return {
                'is_available': False,
                'is_audio_stream': False
            }

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
            async with aiohttp.ClientSession() as session:
                async with session.get(stream_url, timeout=timeout) as response:
                    headers = response.headers
                    icy_name = headers.get('icy-name')
                    icy_genre = headers.get('icy-genre')
                    icy_br = headers.get('icy-br')
                    
                    if any([icy_name, icy_genre, icy_br]):
                        return {
                            'name': icy_name,
                            'genre': icy_genre,
                            'bitrate': icy_br
                        }
                    return None
                    
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.error(f"Error getting stream metadata {stream_url}: {str(e)}")
            return None 