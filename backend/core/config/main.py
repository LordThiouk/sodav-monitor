"""Main configuration module for SODAV Monitor backend."""

import os
from pydantic import validator, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Global application configuration."""
    
    # Base configuration
    PROJECT_NAME: str = "SODAV Monitor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database configuration
    DATABASE_URL: str = "postgresql://sodav:sodav123@localhost:5432/sodav_dev"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Redis configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Security configuration
    SECRET_KEY: str = "your-secret-key-here"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # External API configuration
    ACOUSTID_API_KEY: Optional[str] = None  # API key for AcoustID/Chromaprint
    AUDD_API_KEY: Optional[str] = None      # API key for Audd.io
    MUSICBRAINZ_APP_NAME: str = "SODAV Monitor"
    MUSICBRAINZ_VERSION: str = "1.0"
    MUSICBRAINZ_CONTACT: str = "contact@sodav.sn"

    # Audio detection configuration
    DETECTION_INTERVAL: int = 15  # seconds
    MIN_CONFIDENCE_THRESHOLD: float = 0.8
    FINGERPRINT_ALGORITHM: str = "chromaprint"
    
    # Detection thresholds by service
    ACOUSTID_CONFIDENCE_THRESHOLD: float = 0.7
    AUDD_CONFIDENCE_THRESHOLD: float = 0.6
    LOCAL_CONFIDENCE_THRESHOLD: float = 0.8

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DIR: str = "logs"
    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT: int = 5

    # Report configuration
    REPORT_DIR: str = "reports"
    DEFAULT_REPORT_FORMAT: str = "pdf"
    MAX_REPORT_DAYS: int = 90

    # Radio station configuration
    STATIONS_CHECK_INTERVAL: int = 300  # 5 minutes
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 5  # seconds

    # Monitoring configuration
    ENABLE_PROMETHEUS: bool = True
    PROMETHEUS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 60  # seconds

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"  # Allow extra fields from environment
    )

    def validate_api_keys(self) -> None:
        """Validate that required API keys are set."""
        if not self.ACOUSTID_API_KEY:
            logger.warning("ACOUSTID_API_KEY not set. MusicBrainz detection will be disabled.")
        if not self.AUDD_API_KEY:
            logger.warning("AUDD_API_KEY not set. Audd detection will be disabled.")

@lru_cache()
def get_settings() -> Settings:
    """Return cached settings."""
    settings = Settings()
    settings.validate_api_keys()
    return settings

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

PATHS = {
    "BASE_DIR": BASE_DIR,
    "BACKEND_DIR": BACKEND_DIR,
    "DATA_DIR": os.path.join(BACKEND_DIR, "data"),
    "LOG_DIR": os.path.join(BACKEND_DIR, "logs"),
    "REPORT_DIR": os.path.join(BACKEND_DIR, "reports"),
    "MIGRATION_DIR": os.path.join(BACKEND_DIR, "models", "migrations"),
}

# Create necessary directories
for path in PATHS.values():
    os.makedirs(path, exist_ok=True)

# Default logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": os.path.join(PATHS["LOG_DIR"], "sodav_monitor.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "sodav_monitor": {
            "handlers": ["console", "file"],
            "level": "INFO"
        }
    }
}

# Default Senegalese radio stations configuration
DEFAULT_STATIONS = [
    {
        "name": "RTS Radio",
        "stream_url": "http://rts.sn/radio/stream",
        "location": "Dakar",
        "is_active": True
    },
    {
        "name": "RFM Sénégal",
        "stream_url": "http://rfm.sn/live",
        "location": "Dakar",
        "is_active": True
    }
]

# Supported report formats configuration
REPORT_FORMATS = {
    "pdf": {
        "mime_type": "application/pdf",
        "extension": ".pdf"
    },
    "xlsx": {
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "extension": ".xlsx"
    },
    "csv": {
        "mime_type": "text/csv",
        "extension": ".csv"
    }
}

# Detection algorithms configuration
DETECTION_ALGORITHMS = {
    "chromaprint": {
        "threshold": 0.8,
        "sample_rate": 44100,
        "duration": 15
    },
    "acoustid": {
        "threshold": 0.7,
        "sample_rate": 44100,
        "duration": 30
    },
    "audd": {
        "threshold": 0.6,
        "sample_rate": 44100,
        "duration": 20
    }
}

settings = get_settings() 