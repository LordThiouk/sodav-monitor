"""
Logging module for SODAV Monitor (nested version).

This module provides logging functionality for the SODAV Monitor application.
This is a nested version of the module to support CI environments.
"""

from .log_manager import LogManager

__all__ = ["LogManager"]
