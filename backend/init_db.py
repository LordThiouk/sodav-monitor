"""Script to initialize the database."""

import os

from models.database import engine, test_engine
from models.models import Base


def init_db():
    """Initialize database tables."""
    # Set environment to development
    os.environ["ENV"] = "development"

    # Create all tables using the regular engine
    Base.metadata.create_all(bind=engine)

    # Also initialize test database
    Base.metadata.create_all(bind=test_engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
