import sys
import os
import logging
from tabulate import tabulate

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import RadioStation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    """Check the contents of the database"""
    try:
        # Create database session
        session = SessionLocal()
        
        # Get all radio stations
        stations = session.query(RadioStation).all()
        
        # Format data for display
        station_data = []
        for station in stations:
            station_data.append([
                station.id,
                station.name,
                station.country,
                station.language,
                station.status.value,
                station.is_active,
                station.last_checked.isoformat() if station.last_checked else None
            ])
        
        # Print table
        headers = ['ID', 'Name', 'Country', 'Language', 'Status', 'Active', 'Last Checked']
        print("\nRadio Stations in Database:")
        print(tabulate(station_data, headers=headers, tablefmt='grid'))
        print(f"\nTotal stations: {len(stations)}")
        
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    check_database()
