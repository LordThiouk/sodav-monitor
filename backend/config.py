"""Configuration principale du backend SODAV Monitor."""

import os
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
from functools import lru_cache

class Settings(BaseSettings):
    """Configuration globale de l'application."""
    
    # Configuration de base
    PROJECT_NAME: str = "SODAV Monitor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Configuration de la base de données
    DATABASE_URL: str = "postgresql://sodav:sodav123@localhost:5432/sodav_dev"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Configuration Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Configuration de sécurité
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Configuration des APIs externes
    ACOUSTID_API_KEY: Optional[str] = None  # Clé API pour AcoustID/Chromaprint
    AUDD_API_KEY: Optional[str] = None      # Clé API pour Audd.io
    MUSICBRAINZ_APP_NAME: str = "SODAV Monitor"
    MUSICBRAINZ_VERSION: str = "1.0"
    MUSICBRAINZ_CONTACT: str = "contact@sodav.sn"

    # Configuration de détection audio
    DETECTION_INTERVAL: int = 15  # secondes
    MIN_CONFIDENCE_THRESHOLD: float = 0.8
    FINGERPRINT_ALGORITHM: str = "chromaprint"
    
    # Seuils de détection par service
    ACOUSTID_CONFIDENCE_THRESHOLD: float = 0.7
    AUDD_CONFIDENCE_THRESHOLD: float = 0.6
    LOCAL_CONFIDENCE_THRESHOLD: float = 0.8

    # Configuration des logs
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DIR: str = "logs"
    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT: int = 5

    # Configuration des rapports
    REPORT_DIR: str = "reports"
    DEFAULT_REPORT_FORMAT: str = "pdf"
    MAX_REPORT_DAYS: int = 90

    # Configuration des stations radio
    STATIONS_CHECK_INTERVAL: int = 300  # 5 minutes
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 5  # secondes

    # Configuration du monitoring
    ENABLE_PROMETHEUS: bool = True
    PROMETHEUS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 60  # secondes

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment

    def validate_api_keys(self) -> None:
        """Valide la présence des clés API requises."""
        if not self.ACOUSTID_API_KEY:
            raise ValueError("ACOUSTID_API_KEY est requis pour l'identification via AcoustID/Chromaprint")
        if not self.AUDD_API_KEY:
            raise ValueError("AUDD_API_KEY est requis pour l'identification via Audd.io")

@lru_cache()
def get_settings() -> Settings:
    """Retourne une instance mise en cache des paramètres."""
    settings = Settings()
    settings.validate_api_keys()  # Vérifie les clés API au démarrage
    return settings

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

PATHS = {
    "BASE_DIR": BASE_DIR,
    "BACKEND_DIR": BACKEND_DIR,
    "DATA_DIR": os.path.join(BACKEND_DIR, "data"),
    "LOG_DIR": os.path.join(BACKEND_DIR, "logs"),
    "REPORT_DIR": os.path.join(BACKEND_DIR, "reports"),
    "MIGRATION_DIR": os.path.join(BACKEND_DIR, "models", "migrations"),
}

# Création des dossiers nécessaires
for path in PATHS.values():
    os.makedirs(path, exist_ok=True)

# Configuration des logs par défaut
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

# Configuration des stations radio sénégalaises par défaut
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

# Configuration des formats de rapport supportés
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

# Configuration des algorithmes de détection
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