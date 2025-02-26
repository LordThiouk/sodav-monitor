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
from ...utils.logging_config import setup_logging
from .audio_analysis import AudioAnalyzer
from sqlalchemy.orm import Session

logger = setup_logging(__name__)

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
        
    async def recognize_with_musicbrainz(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Recognize music using MusicBrainz.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
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
            
        except Exception as e:
            logger.error(f"Error recognizing with MusicBrainz: {str(e)}")
            return None
            
    async def recognize_with_audd(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Recognize music using Audd API.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Dictionary with recognition results or None if error/no match
        """
        if not self.audd_api_key:
            logger.error("No Audd API key provided")
            return None
            
        try:
            data = {
                'api_token': self.audd_api_key,
                'return': 'apple_music,spotify'
            }
            files = {'file': ('audio.wav', audio_data)}
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://api.audd.io/', data=data, files=files) as response:
                    if response.status != 200:
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
                        'source': 'audd',
                        'external_ids': {
                            'apple_music': result['result'].get('apple_music', {}).get('id'),
                            'spotify': result['result'].get('spotify', {}).get('id')
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Error recognizing with Audd: {str(e)}")
            return None 