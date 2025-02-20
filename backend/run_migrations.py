"""Script to run database migrations"""

from alembic import command
from alembic.config import Config
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending database migrations"""
    try:
        # Get the directory containing this script
        current_dir = Path(__file__).parent
        
        # Create Alembic config
        alembic_cfg = Config()
        alembic_cfg.set_main_option('script_location', str(current_dir / 'migrations'))
        alembic_cfg.set_main_option('sqlalchemy.url', 'postgresql://user:password@localhost/sodav')
        
        # Run the migration
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, 'head')
        logger.info("Database migrations completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running migrations: {str(e)}")
        raise

if __name__ == '__main__':
    run_migrations() 