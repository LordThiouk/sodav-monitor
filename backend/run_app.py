#!/usr/bin/env python3
"""
Script to run the FastAPI backend application with proper path setup.
This script ensures that the backend directory is in the Python path
and handles import errors gracefully.
"""

import importlib
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Set up the environment for running the backend."""
    # Get the current directory (should be the backend directory)
    current_dir = Path(__file__).parent.absolute()
    project_root = current_dir.parent

    # Add the project root to the Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        logger.info(f"Added {project_root} to Python path")

    # Check critical modules
    critical_modules = ["fastapi", "uvicorn", "sqlalchemy", "redis"]

    for module in critical_modules:
        try:
            importlib.import_module(module)
        except ImportError as e:
            logger.error(f"Critical module {module} is missing: {e}")
            logger.error(f"Please install it with: pip install {module}")
            return False

    # Check local modules
    local_modules = [
        "backend.models.models",
        "backend.models.database",
        "backend.core.events",
        "backend.main",
    ]

    for module in local_modules:
        try:
            importlib.import_module(module)
        except ImportError as e:
            logger.error(f"Error importing {module}: {e}")
            logger.error(f"Local module {module} is missing or has import errors.")
            return False

    return True


def run_backend():
    """Run the backend server using uvicorn."""
    try:
        # Check for required API keys
        acoustid_key = os.environ.get("ACOUSTID_API_KEY")
        audd_key = os.environ.get("AUDD_API_KEY")

        if not acoustid_key:
            logger.warning("ACOUSTID_API_KEY is not set. MusicBrainz recognition will be disabled.")
        if not audd_key:
            logger.warning("AUDD_API_KEY is not set. AudD recognition will be disabled.")

        # Import uvicorn here to ensure it's available
        import uvicorn

        # Run the server
        logger.info("Starting the backend server...")
        uvicorn.run(
            "backend.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug",
            access_log=True,
            workers=1,  # Ensure single worker for WebSocket support
        )
    except Exception as e:
        logger.error(f"Failed to start the backend server: {e}")
        return False

    return True


if __name__ == "__main__":
    if not setup_environment():
        logger.error("Failed to set up the environment. Exiting.")
        sys.exit(1)

    if not run_backend():
        logger.error("Failed to run the backend. Exiting.")
        sys.exit(1)
