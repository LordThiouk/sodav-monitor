"""Configuration settings for the application"""
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

class Config:
    # AcoustID API configuration
    ACOUSTID_API_KEY: Optional[str] = os.getenv('ACOUSTID_API_KEY')
    
    # AudD API configuration
    AUDD_API_KEY: Optional[str] = os.getenv('AUDD_API_KEY')
    
    # MusicBrainz configuration
    MUSICBRAINZ_APP_NAME = os.getenv('MUSICBRAINZ_APP_NAME', 'SodavMonitor')
    
    # Network settings
    REQUEST_TIMEOUT = 10  # seconds
    CHUNK_SIZE = 8192  # bytes
    MAX_RETRIES = 3
    
    # Audio settings
    MIN_AUDIO_LENGTH = 10  # seconds
    MAX_AUDIO_LENGTH = 30  # seconds
    SAMPLE_RATE = 44100  # Hz
    CHANNELS = 2
    
    # Music detection settings
    MIN_CONFIDENCE = 50  # minimum confidence score to consider as music
    MIN_RHYTHM_STRENGTH = 30  # minimum rhythm strength to consider as music
    MIN_BASS_ENERGY = 20  # minimum bass energy percentage
    MIN_MID_ENERGY = 15  # minimum mid frequencies energy percentage
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables"""
        # Load API keys
        if not cls.ACOUSTID_API_KEY:
            print("Warning: ACOUSTID_API_KEY not set in environment")
        if not cls.AUDD_API_KEY:
            print("Warning: AUDD_API_KEY not set in environment")
        
        # Load optional settings from environment
        cls.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', cls.REQUEST_TIMEOUT))
        cls.CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', cls.CHUNK_SIZE))
        cls.MAX_RETRIES = int(os.getenv('MAX_RETRIES', cls.MAX_RETRIES))
        cls.MIN_AUDIO_LENGTH = int(os.getenv('MIN_AUDIO_LENGTH', cls.MIN_AUDIO_LENGTH))
        cls.MAX_AUDIO_LENGTH = int(os.getenv('MAX_AUDIO_LENGTH', cls.MAX_AUDIO_LENGTH))
        cls.SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', cls.SAMPLE_RATE))
        cls.CHANNELS = int(os.getenv('CHANNELS', cls.CHANNELS))
        cls.MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', cls.MIN_CONFIDENCE))
        cls.MIN_RHYTHM_STRENGTH = float(os.getenv('MIN_RHYTHM_STRENGTH', cls.MIN_RHYTHM_STRENGTH))
        cls.MIN_BASS_ENERGY = float(os.getenv('MIN_BASS_ENERGY', cls.MIN_BASS_ENERGY))
        cls.MIN_MID_ENERGY = float(os.getenv('MIN_MID_ENERGY', cls.MIN_MID_ENERGY))

# Load configuration on import
Config.load_from_env()
