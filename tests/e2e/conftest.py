"""
Pytest configuration for E2E tests.

This module provides fixtures and configuration for E2E tests.
"""

import logging
import os
import sys
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def settings():
    """Get application settings."""
    from backend.core.config.settings import get_settings

    return get_settings()


@pytest.fixture(scope="session")
def db_engine(settings):
    """Create a database engine."""
    try:
        from sqlalchemy import create_engine

        # Create a database URL from settings if not provided directly
        if hasattr(settings, "DATABASE_URL") and settings.DATABASE_URL:
            db_url = settings.DATABASE_URL
        else:
            # Construct from components
            db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

        # Create engine
        engine = create_engine(db_url)
        yield engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        pytest.skip(f"Database engine creation failed: {e}")


@pytest.fixture(scope="session")
def db_session(db_engine):
    """Create a database session."""
    try:
        from sqlalchemy.orm import sessionmaker

        Session = sessionmaker(bind=db_engine)
        session = Session()
        yield session
        session.close()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        pytest.skip(f"Database session creation failed: {e}")


@pytest.fixture(scope="session")
def api_client():
    """Create an HTTP client for API testing."""
    import httpx

    with httpx.Client(base_url="http://localhost:8000", timeout=5.0) as client:
        yield client
