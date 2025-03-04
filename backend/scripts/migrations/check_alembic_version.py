#!/usr/bin/env python
"""
Script to check the Alembic version table.
"""

import os
import sys
from sqlalchemy import create_engine, text
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

from backend.models.database import get_database_url

def check_alembic_version():
    """Check the Alembic version table."""
    print("Checking Alembic version...")
    
    # Get database URL
    database_url = get_database_url()
    print(f"Database URL: {database_url}")
    
    # Create engine
    engine = create_engine(database_url)
    
    # Check alembic version
    try:
        with engine.connect() as conn:
            result = conn.execute(text('SELECT * FROM alembic_version'))
            versions = list(result)
            print("Alembic versions:", versions)
    except Exception as e:
        print("Error checking alembic_version:", e)

if __name__ == "__main__":
    check_alembic_version() 