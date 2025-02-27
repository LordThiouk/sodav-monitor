"""Configuration settings for detection."""

from functools import lru_cache
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Detection settings."""
    
    # Audio processing settings
    SAMPLE_RATE: int = 44100
    CHUNK_SIZE: int = 4096
    BUFFER_SIZE: int = 10  # Number of chunks to buffer
    
    # Feature extraction settings
    N_MELS: int = 128
    N_FFT: int = 2048
    HOP_LENGTH: int = 512
    
    # Detection settings
    CONFIDENCE_THRESHOLD: float = 0.5
    MIN_DURATION: float = 10.0  # Minimum duration in seconds
    MAX_DURATION: float = 900.0  # Maximum duration in seconds (15 minutes)
    
    # External service settings
    MUSICBRAINZ_API_KEY: str = ""
    AUDD_API_KEY: str = ""
    
    class Config:
        """Pydantic config."""
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 