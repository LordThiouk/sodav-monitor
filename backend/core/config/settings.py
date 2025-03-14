"""Module de configuration principale de l'application."""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Import from compatibility layer
from backend.core.compat import PYDANTIC_V2, BaseSettings, create_settings_config, get_config_class

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings."""

    # Serveur
    PORT: int = 8000
    API_PORT: int = 8000
    DEBUG: bool = True
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
    REDIS_PASSWORD: Optional[str] = None
    REDIS_POOL_SIZE: int = 10
    REDIS_POOL_TIMEOUT: int = 30

    # API
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "your-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_SECRET_KEY: str = "sodav_jwt_secret_2024"
    ALGORITHM: str = "HS256"

    # Services externes
    ACOUSTID_API_KEY: str = None
    AUDD_API_KEY: str = None
    MUSICBRAINZ_APP_NAME: str = "SODAV Monitor"
    MUSICBRAINZ_VERSION: str = "1.0"
    MUSICBRAINZ_CONTACT: str = "contact@sodav.sn"

    # Détection
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.8
    MIN_PLAY_DURATION: int = 30
    FINGERPRINT_WINDOW: int = 4096
    FINGERPRINT_OVERLAP: float = 0.5
    MIN_CONFIDENCE: float = 0.5
    MIN_RHYTHM_STRENGTH: int = 30
    MIN_BASS_ENERGY: int = 20
    MIN_MID_ENERGY: int = 15

    # Audio
    CHUNK_SIZE: int = 4096
    SAMPLE_RATE: int = 44100
    CHANNELS: int = 2
    MIN_AUDIO_LENGTH: int = 10
    MAX_AUDIO_LENGTH: int = 30
    BUFFER_SIZE: int = 16384

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
    LOG_FILE: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Detection Settings
    DETECTION_INTERVAL: int = 10  # seconds
    CONFIDENCE_THRESHOLD: float = 50.0
    MAX_FAILURES: int = 3
    RESPONSE_TIMEOUT: int = 10  # seconds
    MIN_CONFIDENCE_THRESHOLD: float = 0.8
    ACOUSTID_CONFIDENCE_THRESHOLD: float = 0.7
    AUDD_CONFIDENCE_THRESHOLD: float = 0.6
    LOCAL_CONFIDENCE_THRESHOLD: float = 0.8

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # Number of requests
    RATE_LIMIT_PERIOD: int = 60  # Period in seconds

    # Caching
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # Cache TTL in seconds
    CACHE_PREFIX: str = "sodav:"

    # Report Generation Settings
    REPORT_FORMATS: list = ["pdf", "xlsx", "csv"]
    REPORT_RETENTION_DAYS: int = 30
    MAX_REPORT_SIZE: int = 100 * 1024 * 1024  # 100MB

    # WebSocket Settings
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_CLOSE_TIMEOUT: int = 10  # seconds

    # Feature Flags
    ENABLE_WEBSOCKETS: bool = True
    ENABLE_ANALYTICS: bool = True
    ENABLE_REPORTS: bool = True

    # Database Settings
    SQLALCHEMY_DATABASE_URL: str = "postgresql://user:pass@localhost/sodav"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # Use appropriate configuration method based on Pydantic version
    if PYDANTIC_V2:
        model_config = create_settings_config(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="allow",  # Allow extra fields
        )
    else:
        # For Pydantic 1.x
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = True
            extra = "allow"  # Allow extra fields


@lru_cache()
def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
