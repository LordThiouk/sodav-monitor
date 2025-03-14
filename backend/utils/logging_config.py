"""Logging configuration for the SODAV Monitor system.

This module provides logging configuration and setup functions to ensure
consistent logging across the application.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.core.config import get_settings

# Define logging categories for different parts of the application
LOG_CATEGORIES = {
    "DETECTION": "Detection",
    "API": "API",
    "DATABASE": "Database",
    "STREAM": "Stream",
    "WEBSOCKET": "WebSocket",
    "REPORT": "Report",
    "ANALYTICS": "Analytics",
    "SECURITY": "Security",
    "SYSTEM": "System",
}


def setup_logging(
    name: str, log_level: Optional[str] = None, log_file: Optional[str] = None
) -> logging.Logger:
    """Set up a logger with the specified configuration.

    Args:
        name: Name of the logger
        log_level: Optional logging level (defaults to settings)
        log_file: Optional log file path (defaults to settings)

    Returns:
        logging.Logger: Configured logger instance
    """
    settings = get_settings()
    logger = logging.getLogger(name)

    # Set log level
    level = log_level or settings.LOG_LEVEL
    logger.setLevel(level)

    # Create formatters and handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file or settings.LOG_FILE:
        file_path = Path(log_file or settings.LOG_FILE)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            file_path, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_with_category(logger: logging.Logger, category: str) -> Callable:
    """Create a decorator that adds category information to log messages.

    Args:
        logger: The logger instance to use
        category: The category to add to log messages

    Returns:
        Callable: A decorator function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.debug(f"[{category}] Calling {func.__name__}")
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"[{category}] Error in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator
