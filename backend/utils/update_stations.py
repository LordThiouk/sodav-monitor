import sys
import os
import logging

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from radio_manager import RadioManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_stations():
    """Update radio stations in the database"""
    try:
        # Create database session
        session = SessionLocal()
        
        # Create radio manager
        manager = RadioManager(session)
        
        # Update Senegalese stations
        manager.update_senegal_stations()
        
    except Exception as e:
        logger.error(f"Error in update script: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    update_stations()
