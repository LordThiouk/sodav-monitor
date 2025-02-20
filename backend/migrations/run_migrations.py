import logging
from alembic import command
from alembic.config import Config
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending database migrations."""
    try:
        # Get the directory containing this script
        migrations_dir = Path(__file__).parent.absolute()
        
        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option('script_location', str(migrations_dir))
        
        # Run the migration
        logger.info("Starting database migration...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        raise

if __name__ == "__main__":
    run_migrations() 