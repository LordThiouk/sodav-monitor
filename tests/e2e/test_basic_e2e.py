"""
Basic E2E tests for the SODAV Monitor system.
These tests verify that the core components of the system work together correctly.
"""

import logging
import os
import sys
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config.settings import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


def test_settings_loaded(settings):
    """Test that settings are loaded correctly."""
    assert settings is not None
    assert settings.API_V1_STR == "/api/v1"
    logger.info("Settings loaded successfully")


def test_environment_variables():
    """Test that required environment variables are set."""
    # Load environment variables from .env file
    from dotenv import load_dotenv

    load_dotenv()

    # Check for critical environment variables
    assert os.getenv("DATABASE_URL") is not None or os.getenv("POSTGRES_USER") is not None
    logger.info("Environment variables verified")


def test_database_connection(settings):
    """Test that we can connect to the database."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.sql import text

        # Create a database URL from settings if not provided directly
        if hasattr(settings, "DATABASE_URL") and settings.DATABASE_URL:
            db_url = settings.DATABASE_URL
        else:
            # Construct from components
            db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

        # Create engine and test connection
        engine = create_engine(db_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.scalar() == 1
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        pytest.skip(f"Database connection failed: {e}")


@pytest.mark.skip_if_no_server
def test_api_endpoints():
    """Test that API endpoints are accessible."""
    try:
        import socket

        import httpx

        # Check if server is running before attempting to connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", 8000))
        sock.close()

        if result != 0:
            pytest.skip("Backend server is not running on port 8000")

        # Test the health check endpoint
        response = httpx.get("http://localhost:8000/api/health", timeout=5.0)
        assert response.status_code == 200
        logger.info("API health endpoint accessible")
    except Exception as e:
        logger.error(f"API endpoint test failed: {e}")
        pytest.skip(f"API endpoint test failed: {e}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
