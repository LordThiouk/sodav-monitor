"""Module de configuration de l'application."""

from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Paramètres de configuration de l'application."""
    
    # Serveur
    PORT: int = 3000
    API_PORT: int = 8000
    DEBUG: bool = False
    NODE_ENV: str = "production"
    HOST: str = "0.0.0.0"
    ENV: str = "development"
    
    # Base de données
    DATABASE_URL: str = "sqlite:///./sodav.db"
    TEST_DATABASE_URL: str = "sqlite:///./test.db"
    DATABASE_PUBLIC_URL: str = "postgresql://postgres:postgres@localhost:5432/sodav"
    DEV_DATABASE_URL: str = "postgresql://sodav:sodav123@localhost:5432/sodav_dev"
    POSTGRES_USER: str = "sodav"
    POSTGRES_PASSWORD: str = "sodav123"
    POSTGRES_DB: str = "sodav_dev"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    
    # API
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_SECRET_KEY: str = "sodav_jwt_secret_2024"
    ALGORITHM: str = "HS256"
    
    # Services externes
    ACOUSTID_API_KEY: str = "7HKKBoukZR"
    AUDD_API_KEY: str = "a718282167d84385a8c9d1ea9f45747a"
    MUSICBRAINZ_APP_NAME: str = "sodav-monitor"
    
    # Détection
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.8
    MIN_PLAY_DURATION: int = 30
    FINGERPRINT_WINDOW: int = 4096
    FINGERPRINT_OVERLAP: float = 0.5
    MIN_CONFIDENCE: int = 50
    MIN_RHYTHM_STRENGTH: int = 30
    MIN_BASS_ENERGY: int = 20
    MIN_MID_ENERGY: int = 15
    
    # Audio
    CHUNK_SIZE: int = 8192
    SAMPLE_RATE: int = 44100
    CHANNELS: int = 2
    MIN_AUDIO_LENGTH: int = 10
    MAX_AUDIO_LENGTH: int = 30
    
    # Monitoring
    STREAM_CHECK_INTERVAL: int = 60
    HEALTH_CHECK_INTERVAL: int = 300
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    STARTUP_GRACE_PERIOD: bool = True
    HEALTHCHECK_TIMEOUT: int = 60
    HEALTHCHECK_INTERVAL: int = 30
    HEALTHCHECK_RETRIES: int = 3
    HEALTHCHECK_START_PERIOD: int = 180
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    UVICORN_LOG_LEVEL: str = "info"
    NGINX_LOG_LEVEL: str = "warn"
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

@lru_cache()
def get_settings() -> Settings:
    """Obtenir les paramètres de configuration."""
    return Settings()

settings = get_settings() 