from database import SessionLocal
from models import RadioStation
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_stations():
    """Keep only Senegalese radio stations in the database."""
    try:
        # Create database session
        db = SessionLocal()
        
        # Delete all non-Senegalese stations
        deleted_count = db.query(RadioStation).filter(
            RadioStation.country != 'Senegal'
        ).delete()
        
        # Commit changes
        db.commit()
        logger.info(f"Successfully deleted {deleted_count} non-Senegalese radio stations")
        
        # Count remaining Senegalese stations
        senegal_count = db.query(RadioStation).filter(
            RadioStation.country == 'Senegal'
        ).count()
        logger.info(f"Remaining Senegalese stations: {senegal_count}")
        
    except Exception as e:
        logger.error(f"Error cleaning stations: {str(e)}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    clean_stations()
