"""Script to initialize the database."""

import os
from models.models import Base
from models.database import test_engine

def init_db():
    """Initialize database tables."""
    # Set environment to test
    os.environ["ENV"] = "test"
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

if __name__ == "__main__":
    init_db()
    print("Test database initialized successfully") 