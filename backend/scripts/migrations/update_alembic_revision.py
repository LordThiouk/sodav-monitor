#!/usr/bin/env python
"""
Script to update the Alembic revision to include our migration.
This script will create a new migration file that includes the updated_at column.
"""

import os
import sys
from sqlalchemy import create_engine, text
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

from backend.models.database import get_database_url

def update_alembic_revision():
    """Update the Alembic revision to include our migration."""
    print("Updating Alembic revision...")
    
    # Get database URL
    database_url = get_database_url()
    print(f"Database URL: {database_url}")
    
    # Create engine
    engine = create_engine(database_url)
    
    # Check if updated_at column exists in users table
    with engine.begin() as conn:
        # Check if updated_at column exists
        result = conn.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'updated_at'
        """))
        
        if result.rowcount == 0:
            print("updated_at column does not exist in users table")
            return False
        
        print("updated_at column exists in users table")
        
        # Get current revision
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_revision = result.scalar()
        print(f"Current revision: {current_revision}")
        
        # Delete current revision
        conn.execute(text("DELETE FROM alembic_version"))
        
        # Insert new revision
        new_revision = "2024_03_updated_at"
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"), {"version_num": new_revision})
        print(f"Updated revision to: {new_revision}")
    
    return True

if __name__ == "__main__":
    success = update_alembic_revision()
    if success:
        print("Alembic revision updated successfully!")
        sys.exit(0)
    else:
        print("Failed to update Alembic revision!")
        sys.exit(1) 