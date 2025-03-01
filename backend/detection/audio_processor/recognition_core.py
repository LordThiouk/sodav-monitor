"""
Core music recognition functionality for SODAV Monitor.
Handles the main recognition flow and initialization.
"""

import logging
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import musicbrainzngs
from sqlalchemy.orm import Session
from utils.logging_config import setup_logging
from .local_detection import LocalDetector
from .external_services import ExternalServiceHandler
from .db_operations import DatabaseHandler
from .audio_analysis import AudioAnalyzer
from datetime import datetime

# Configure logging
logger = setup_logging(__name__)

# Load environment variables
load_dotenv()

class MusicRecognizer:
    def __init__(self, db_session: Session, audd_api_key: Optional[str] = None):
        """Initialize music recognizer with dependencies"""
        self.db_session = db_session
        self.audd_api_key = audd_api_key or os.getenv('AUDD_API_KEY')
        self.initialized = False
        logger.info("Initializing MusicRecognizer")
        
        # Initialize components
        self.local_detector = LocalDetector(db_session)
        self.external_handler = ExternalServiceHandler(audd_api_key)
        self.db_handler = DatabaseHandler(db_session)
        self.audio_analyzer = AudioAnalyzer()
        
        # Initialize MusicBrainz
        musicbrainzngs.set_useragent(
            "SODAV Monitor",
            "1.0",
            "https://sodav.sn"
        )
        
        # Confidence thresholds
        self.min_confidence = 0.5  # Minimum confidence for accepting a match
        
    async def initialize(self) -> None:
        """Initialize the recognizer and its components"""
        if self.initialized:
            return
            
        try:
            # Initialize local detector
            await self.local_detector.initialize()
            
            # Initialize external services
            await self.external_handler.initialize()
            
            # Initialize database handler
            await self.db_handler.initialize()
            
            self.initialized = True
            logger.info("MusicRecognizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MusicRecognizer: {str(e)}")
            raise
            
    async def recognize_music(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Main recognition flow. Tries local detection first, then external services.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Dictionary containing recognition results or None if no match found
        """
        if not self.initialized:
            await self.initialize()
            
        try:
            # First try local database
            result = await self.local_detector.search_local(audio_data)
            if result:
                confidence = float(result.get('confidence', 0.0))
                if confidence >= self.min_confidence:
                    logger.info("Track found in local database")
                    await self.db_handler.save_track_to_db(result)
                    return result
                else:
                    logger.info("Local match rejected due to low confidence")
                    return None  # Stop here if local match has low confidence
                    
            # Try MusicBrainz
            result = await self.external_handler.recognize_with_musicbrainz(audio_data)
            if result:
                confidence = float(result.get('confidence', 0.0))
                if confidence >= self.min_confidence:
                    logger.info("Track found with MusicBrainz")
                    await self.db_handler.save_track_to_db(result)
                    return result
                else:
                    logger.info("MusicBrainz match rejected due to low confidence")
                    
            # Finally try Audd
            result = await self.external_handler.recognize_with_audd(audio_data)
            if result:
                confidence = float(result.get('confidence', 0.0))
                if confidence >= self.min_confidence:
                    logger.info("Track found with Audd")
                    await self.db_handler.save_track_to_db(result)
                    return result
                else:
                    logger.info("Audd match rejected due to low confidence")
                    
            logger.info("No match found for audio")
            return None
            
        except Exception as e:
            logger.error(f"Error during music recognition: {str(e)}")
            return None
            
    async def verify_detections(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        """Verify recent detections for accuracy"""
        try:
            await self.db_handler.verify_detections(start_time, end_time)
        except Exception as e:
            logger.error(f"Error verifying detections: {str(e)}")
            raise 