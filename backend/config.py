"""Configuration principale du backend SODAV Monitor."""

import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import validator

# Import from compatibility layer instead of directly from pydantic_settings
from backend.core.compat import PYDANTIC_V2, BaseSettings, create_settings_config

logger = logging.getLogger(__name__)

# Déterminer quel fichier .env charger
env = os.environ.get("ENV", "development")
env_file = f".env.{env}"

# Vérifier si le fichier existe, sinon utiliser .env
if not os.path.exists(env_file) and os.path.exists(".env"):
    env_file = ".env"
    logger.info(f"Fichier {env_file} non trouvé, utilisation de .env")
else:
    logger.info(f"Utilisation du fichier de configuration: {env_file}")


class Settings(BaseSettings):
    """Configuration globale de l'application."""

    # Configuration de base
    PROJECT_NAME: str = "SODAV Monitor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENV: str = "development"  # development ou production

    # Configuration de la base de données
    DATABASE_URL: Optional[str] = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Configuration Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Configuration de sécurité
    SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Configuration des APIs externes
    ACOUSTID_API_KEY: Optional[str] = None  # Clé API pour AcoustID/Chromaprint
    AUDD_API_KEY: Optional[str] = None  # Clé API pour Audd.io
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

    # Use appropriate configuration method based on Pydantic version
    if PYDANTIC_V2:
        model_config = create_settings_config(
            env_file=env_file,
            case_sensitive=True,
            extra="allow",  # Allow extra fields from environment
        )
    else:
        # For Pydantic 1.x
        class Config:
            env_file = env_file
            case_sensitive = True
            extra = "allow"  # Allow extra fields from environment

    def validate_api_keys(self) -> None:
        """Validate that required API keys are set."""
        if not self.ACOUSTID_API_KEY:
            logger.warning("ACOUSTID_API_KEY not set. MusicBrainz detection will be disabled.")
        if not self.AUDD_API_KEY:
            logger.warning("AUDD_API_KEY not set. Audd detection will be disabled.")
        if not self.SECRET_KEY:
            logger.error(
                "SECRET_KEY not set. This is a security risk. Please set a strong SECRET_KEY in your .env file."
            )
        if not self.DATABASE_URL:
            logger.error(
                "DATABASE_URL not set. Database connection will fail. Please set DATABASE_URL in your .env file."
            )

        # Log l'environnement actuel
        logger.info(f"Application running in {self.ENV} environment")


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings."""
    settings = Settings()
    settings.validate_api_keys()
    return settings


# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.dirname(
    os.path.abspath(__file__)
)  # Chemin direct vers le dossier backend actuel

PATHS = {
    "BASE_DIR": BASE_DIR,
    "BACKEND_DIR": BACKEND_DIR,
    "DATA_DIR": os.path.join(BACKEND_DIR, "data"),
    "LOG_DIR": os.path.join(BACKEND_DIR, "logs"),
    "REPORT_DIR": os.path.join(BACKEND_DIR, "reports"),
    "MIGRATION_DIR": os.path.join(BACKEND_DIR, "models", "migrations"),
    "STATIC_DIR": os.path.join(BASE_DIR, "static"),  # Ajout du dossier static à la racine
}

# Création des dossiers nécessaires avec logging
logger.info("Création des dossiers nécessaires...")
for path_name, path in PATHS.items():
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Dossier créé : {path_name} ({path})")
        else:
            logger.debug(f"Dossier existant : {path_name} ({path})")
    except Exception as e:
        logger.error(f"Erreur lors de la création du dossier {path_name} ({path}): {str(e)}")

# Configuration des logs par défaut
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": os.path.join(PATHS["LOG_DIR"], "sodav_monitor.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {"sodav_monitor": {"handlers": ["console", "file"], "level": "INFO"}},
}

# Configuration des stations radio sénégalaises par défaut
DEFAULT_STATIONS = [
    {
        "name": "RTS Radio",
        "stream_url": "http://rts.sn/radio/stream",
        "location": "Dakar",
        "is_active": True,
    },
    {
        "name": "RFM Sénégal",
        "stream_url": "http://rfm.sn/live",
        "location": "Dakar",
        "is_active": True,
    },
]

# Configuration des formats de rapport supportés
REPORT_FORMATS = {
    "pdf": {"mime_type": "application/pdf", "extension": ".pdf"},
    "xlsx": {
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "extension": ".xlsx",
    },
    "csv": {"mime_type": "text/csv", "extension": ".csv"},
}

# Configuration des algorithmes de détection
DETECTION_ALGORITHMS = {
    "chromaprint": {"threshold": 0.8, "sample_rate": 44100, "duration": 15},
    "acoustid": {"threshold": 0.7, "sample_rate": 44100, "duration": 30},
    "audd": {"threshold": 0.6, "sample_rate": 44100, "duration": 20},
}

settings = get_settings()
