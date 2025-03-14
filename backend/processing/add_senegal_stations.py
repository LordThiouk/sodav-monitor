import asyncio
import logging

from database import SessionLocal
from radio_manager import RadioManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Fetch and save Senegalese radio stations."""
    try:
        # Create database session
        db = SessionLocal()

        # Initialize radio manager
        radio_manager = RadioManager(db_session=db)

        # Update station list for Senegal
        logger.info("Fetching Senegalese radio stations...")
        await radio_manager.update_station_list(country="Senegal")

        # Commit changes
        db.commit()
        logger.info("Successfully updated Senegalese radio stations")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    asyncio.run(main())
