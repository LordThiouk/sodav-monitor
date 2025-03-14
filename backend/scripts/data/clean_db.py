"""Script to clean the database by dropping all tables and recreating them."""

import logging
import os
import sys

# Add the parent directory to the path so we can import from backend
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from models.database import engine, init_db
from models.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_db():
    """Clean database by dropping all tables and recreating them."""
    try:
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")

        logger.info("Recreating tables...")
        init_db()
        logger.info("Database cleaned and reinitialized successfully")
    except Exception as e:
        logger.error(f"Error cleaning database: {str(e)}")
        raise


if __name__ == "__main__":
    clean_db()
    print("Database cleaned successfully")
