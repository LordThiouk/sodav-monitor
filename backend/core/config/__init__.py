"""Configuration module for SODAV Monitor."""

# Define constants that were previously in main.py
import os
from pathlib import Path

from .settings import Settings, get_settings

# Define paths
BACKEND_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
PATHS = {
    "LOGS_DIR": os.path.join(BACKEND_DIR, "logs"),
    "DATA_DIR": os.path.join(BACKEND_DIR, "data"),
    "STATIC_DIR": os.path.join(PROJECT_ROOT, "static"),
    "REPORTS_DIR": os.path.join(BACKEND_DIR, "reports"),
    "TEMP_DIR": os.path.join(BACKEND_DIR, "temp"),
}

# Define logging config
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"default": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}},
}

# Define default stations
DEFAULT_STATIONS = []

# Define report formats
REPORT_FORMATS = ["pdf", "xlsx", "csv"]

# Define detection algorithms
DETECTION_ALGORITHMS = ["chromaprint", "acoustid", "audd"]

__all__ = [
    "get_settings",
    "Settings",
    "PATHS",
    "LOGGING_CONFIG",
    "DEFAULT_STATIONS",
    "REPORT_FORMATS",
    "DETECTION_ALGORITHMS",
]
