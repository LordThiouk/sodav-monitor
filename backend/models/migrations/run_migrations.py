"""Script to run database migrations."""

import os
import sys
from alembic import command
from alembic.config import Config

def run_migrations():
    """Run database migrations."""
    try:
        # Get the directory containing this script
        migrations_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create Alembic configuration
        alembic_cfg = Config(os.path.join(migrations_dir, "alembic.ini"))
        alembic_cfg.set_main_option("script_location", migrations_dir)
        
        # Run the migration to our latest merge revision
        command.upgrade(alembic_cfg, "20240321_006")
        print("✅ Migrations completed successfully")
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations() 