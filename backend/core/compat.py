"""
Compatibility layer for Pydantic versions.

This module provides compatibility between different versions of Pydantic,
allowing the codebase to work with both Pydantic 1.x and 2.x.
"""

import sys
from typing import Any, Dict, Optional

# Check Pydantic version
try:
    import pydantic
    from pydantic import __version__ as pydantic_version

    PYDANTIC_V2 = pydantic_version.startswith("2.")
except ImportError:
    PYDANTIC_V2 = False

# Import appropriate BaseSettings
if PYDANTIC_V2:
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict
    except ImportError:
        from pydantic import BaseSettings

        SettingsConfigDict = None
else:
    from pydantic import BaseSettings

    SettingsConfigDict = None


def create_settings_config(**kwargs) -> Dict[str, Any]:
    """
    Create a settings configuration that works with both Pydantic 1.x and 2.x.

    In Pydantic 1.x, this returns a dict that will be ignored (Config class is used instead).
    In Pydantic 2.x, this returns a SettingsConfigDict.

    Args:
        **kwargs: Configuration parameters

    Returns:
        Configuration object or dict
    """
    if PYDANTIC_V2 and SettingsConfigDict is not None:
        return SettingsConfigDict(**kwargs)
    return kwargs  # Will be ignored in Pydantic 1.x (Config class is used instead)


def get_config_class(**kwargs) -> Optional[type]:
    """
    Get a Config class for Pydantic 1.x.

    Args:
        **kwargs: Configuration parameters

    Returns:
        Config class for Pydantic 1.x, None for Pydantic 2.x
    """
    if not PYDANTIC_V2:
        # Create a Config class for Pydantic 1.x
        class Config:
            pass

        # Set attributes from kwargs
        for key, value in kwargs.items():
            setattr(Config, key, value)

        return Config
    return None
