#!/usr/bin/env python

"""
Script to check if the updated_at column exists in the database tables.
"""

import os
import sys
from sqlalchemy import create_engine, text
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

from backend.models.database import get_database_url

def check_migration():
    """Check if the updated_at column exists in the database tables."""
    print("Checking migration...")
    
    # Get database URL
    database_url = get_database_url()
    print(f"Database URL: {database_url}")
    
    # Create engine
    engine = create_engine(database_url)
    
    # Check if updated_at column exists in users table
    with engine.connect() as conn:
        # Check users table
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'updated_at'"))
        if result.rowcount > 0:
            print("✅ updated_at column exists in users table")
        else:
            print("❌ updated_at column does not exist in users table")
        
        # Check other tables
        tables = ['reports', 'radio_stations', 'artists', 'tracks']
        for table in tables:
            result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'updated_at'"))
            if result.rowcount > 0:
                print(f"✅ updated_at column exists in {table} table")
            else:
                print(f"❌ updated_at column does not exist in {table} table")

if __name__ == "__main__":
    check_migration() 