"""
External music recognition services integration for SODAV Monitor.
Handles MusicBrainz and Audd API integration.
"""

import logging
import os
from typing import Dict, Any, Optional
import requests
import musicbrainzngs
import aiohttp
import tempfile
from utils.logging_config import setup_logging
from .audio_analysis import AudioAnalyzer
from sqlalchemy.orm import Session
import asyncio

logger = setup_logging(__name__)

class ExternalServiceError(Exception):
    """Exception raised for errors in external service calls."""
    pass

class MusicBrainzService:
    """Service for interacting with the MusicBrainz API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.musicbrainz.org/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def detect_track(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Detect a track using MusicBrainz API.
        
        Args:
            audio_data: Raw audio data bytes
            
        Returns:
            Dict containing track information or None if no match found
            
        Raises:
            ExternalServiceError: If API request fails
        """
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(
                    f"{self.base_url}/lookup",
                    data=audio_data,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        raise ExternalServiceError(f"MusicBrainz API error: {response.status}")
                    
                    data = await response.json()
                    if not data.get("results"):
                        return None
                    
                    result = data["results"][0]
                    return {
                        "title": result["title"],
                        "artist": result["artist"],
                        "confidence": result["score"]
                    }
                    
        except asyncio.TimeoutError:
            raise ExternalServiceError("MusicBrainz request timed out")
        except aiohttp.ClientError as e:
            raise ExternalServiceError(f"MusicBrainz request failed: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Unexpected error in MusicBrainz request: {str(e)}")
    
    async def detect_track_with_retry(
        self, 
        audio_data: bytes, 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a track with automatic retry on failure.
        
        Args:
            audio_data: Raw audio data bytes
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict containing track information or None if no match found
        """
        for attempt in range(max_retries):
            try:
                return await self.detect_track(audio_data)
            except ExternalServiceError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"MusicBrainz detection failed (attempt {attempt + 1}): {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))
        return None

class AuddService:
    """Service for interacting with the Audd API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.audd.io"):
        self.api_key = api_key
        self.base_url = base_url
        
    async def detect_track(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Detect a track using Audd API.
        
        Args:
            audio_data: Raw audio data bytes
            
        Returns:
            Dict containing track information or None if no match found
            
        Raises:
            ExternalServiceError: If API request fails
        """
        try:
            data = aiohttp.FormData()
            data.add_field("api_token", self.api_key)
            data.add_field("file", audio_data)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    data=data,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        raise ExternalServiceError(f"Audd API error: {response.status}")
                    
                    result = await response.json()
                    if result.get("status") == "error":
                        raise ExternalServiceError(f"Audd API error: {result.get('error')}")
                    
                    if not result.get("result"):
                        return None
                    
                    track = result["result"]
                    return {
                        "title": track["title"],
                        "artist": track["artist"],
                        "confidence": track["score"]
                    }
                    
        except asyncio.TimeoutError:
            raise ExternalServiceError("Audd request timed out")
        except aiohttp.ClientError as e:
            raise ExternalServiceError(f"Audd request failed: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Unexpected error in Audd request: {str(e)}")
    
    async def detect_track_with_retry(
        self, 
        audio_data: bytes, 
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a track with automatic retry on failure.
        
        Args:
            audio_data: Raw audio data bytes
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict containing track information or None if no match found
        """
        for attempt in range(max_retries):
            try:
                return await self.detect_track(audio_data)
            except ExternalServiceError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Audd detection failed (attempt {attempt + 1}): {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))
        return None

class ExternalServiceHandler:
    def __init__(self, db_session: Session, audd_api_key: Optional[str] = None):
        """Initialize external services handler.
        
        Args:
            db_session: Database session
            audd_api_key: Optional API key for Audd service
        """
        self.db_session = db_session
        self.audd_api_key = audd_api_key or os.getenv('AUDD_API_KEY')
        self.audio_analyzer = AudioAnalyzer()
        self.initialized = False
        self.initialize()
        
    def initialize(self):
        """Initialize external services"""
        if not self.audd_api_key:
            logger.warning("Audd API key not provided")
            
        # Initialize MusicBrainz
        musicbrainzngs.set_useragent(
            "SODAV Monitor",
            "1.0",
            "https://sodav.sn"
        )
        
        self.initialized = True
        logger.info("ExternalServiceHandler initialized successfully")
        
    async def recognize_with_musicbrainz(self, audio_data: bytes, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Recognize music using MusicBrainz.
        
        Args:
            audio_data: Raw audio bytes
            max_retries: Maximum number of retries for rate limit errors
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
        retries = 0
        while retries <= max_retries:
            try:
                # Extract audio features
                features = self.audio_analyzer.extract_features(audio_data)
                
                # Search MusicBrainz
                result = musicbrainzngs.search_recordings(
                    query=f"duration:{int(features['duration'])}",
                    limit=5
                )
                
                if not result['recordings']:
                    return None
                    
                recording = result['recordings'][0]
                return {
                    'title': recording['title'],
                    'artist': recording['artist-credit'][0]['name'],
                    'duration': recording['duration'] / 1000.0,
                    'confidence': 0.7,
                    'source': 'musicbrainz'
                }
                
            except musicbrainzngs.WebServiceError as e:
                if 'Rate limit exceeded' in str(e) and retries < max_retries:
                    retries += 1
                    await asyncio.sleep(1)  # Wait before retrying
                    continue
                logger.error(f"Error recognizing with MusicBrainz: {str(e)}, caused by: {e.__cause__}")
                return None
            except Exception as e:
                logger.error(f"Error recognizing with MusicBrainz: {str(e)}")
                return None
            
    async def recognize_with_audd(self, audio_data: bytes, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Recognize music using Audd API.
        
        Args:
            audio_data: Raw audio bytes
            max_retries: Maximum number of retries for network errors
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
        if not self.audd_api_key:
            logger.error("No Audd API key provided")
            return None
            
        retries = 0
        while retries <= max_retries:
            try:
                data = {
                    'api_token': self.audd_api_key,
                    'return': 'apple_music,spotify'
                }
                files = {'file': ('audio.wav', audio_data)}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post('https://api.audd.io/', data=data, files=files) as response:
                        if response.status != 200:
                            if retries < max_retries:
                                retries += 1
                                await asyncio.sleep(1)  # Wait before retrying
                                continue
                            logger.error(f"Audd API error: {response.status}")
                            return None
                            
                        result = await response.json()
                        
                        if not result.get('result'):
                            return None
                            
                        return {
                            'title': result['result']['title'],
                            'artist': result['result']['artist'],
                            'album': result['result'].get('album'),
                            'release_date': result['result'].get('release_date'),
                            'confidence': 0.9,
                            'source': 'audd'
                        }
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if retries < max_retries:
                    retries += 1
                    await asyncio.sleep(1)  # Wait before retrying
                    continue
                logger.error(f"Error recognizing with Audd: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Error recognizing with Audd: {str(e)}")
                return None 