"""Utility module for checking radio stream availability."""

import aiohttp
import asyncio
from typing import Dict, Optional, Tuple
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
                "available": bool,
                "accessible": bool,
                "valid_format": bool
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
                        "available": response.status == 200,
                        "accessible": True,
                        "valid_format": is_audio
                    }
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout checking stream: {stream_url}")
            return {
                "available": False,
                "accessible": False,
                "valid_format": False
            }
        except aiohttp.ClientError as e:
            logger.error(f"Error checking stream {stream_url}: {str(e)}")
            return {
                "available": False,
                "accessible": False,
                "valid_format": False
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

# Helper function for simpler access
async def check_stream_status(stream_url: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Check if a radio stream is available and accessible.
    
    Args:
        stream_url: The URL of the radio stream to check
        timeout: Timeout for the request in seconds
        
    Returns:
        Tuple of (status: bool, message: str)
    """
    checker = StreamChecker(timeout=timeout)
    try:
        result = await checker.check_stream_availability(stream_url)
        if result["available"] and result["accessible"]:
            return True, "Stream is available and accessible"
        elif not result["available"]:
            return False, "Stream is not available"
        elif not result["accessible"]:
            return False, "Stream is not accessible"
        elif not result.get("valid_format", True):
            return False, "Stream format is not valid"
        else:
            return False, "Unknown stream status issue"
    except Exception as e:
        logger.error(f"Error checking stream status for {stream_url}: {str(e)}")
        return False, f"Error checking stream: {str(e)}" 