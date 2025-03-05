"""Configuration module for SODAV Monitor."""

from .main import (
    get_settings,
    Settings,
    PATHS,
    LOGGING_CONFIG,
    DEFAULT_STATIONS,
    REPORT_FORMATS,
    DETECTION_ALGORITHMS
)

__all__ = [
    'get_settings',
    'Settings',
    'PATHS',
    'LOGGING_CONFIG',
    'DEFAULT_STATIONS',
    'REPORT_FORMATS',
    'DETECTION_ALGORITHMS'
] 