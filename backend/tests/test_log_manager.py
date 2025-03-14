"""
Test the LogManager functionality.
"""

import pytest
import logging
import os
from pathlib import Path

# Try different import paths to find the working one
try:
    from backend.logs.log_manager import LogManager
    print("Successfully imported LogManager from backend.logs.log_manager")
except ImportError:
    try:
        from backend.logs.backend.logs.log_manager import LogManager
        print("Successfully imported LogManager from backend.logs.backend.logs.log_manager")
    except ImportError:
        from backend.logs import LogManager
        print("Successfully imported LogManager from backend.logs")


def test_log_manager_initialization():
    """Test that the LogManager can be initialized."""
    log_manager = LogManager()
    assert log_manager is not None
    assert isinstance(log_manager, LogManager)


def test_get_logger():
    """Test that the LogManager can create a logger."""
    log_manager = LogManager()
    logger = log_manager.get_logger("test")
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "sodav_monitor.test"


def test_singleton_pattern():
    """Test that the LogManager follows the singleton pattern."""
    log_manager1 = LogManager()
    log_manager2 = LogManager()
    assert log_manager1 is log_manager2 