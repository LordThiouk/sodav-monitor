import requests
import logging
from datetime import datetime
from database import SessionLocal, engine
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_senegal_stations():
    """Fetch and save Senegalese radio stations"""
    try:
        # Create database session
        db = SessionLocal()
        
        # Radio Browser API endpoint
        url = "https://de1.api.radio-browser.info/json/stations/bycountry/Senegal"
        
        # Fetch stations
        response = requests.get(url, timeout=10)
        stations = response.json()
        
        logger.info(f"Found {len(stations)} Senegalese stations")
        
        # Process each station
        for station_data in stations:
            # Check if station already exists
            result = db.execute(
                text("SELECT id FROM radio_stations WHERE stream_url = :url"),
                {"url": station_data['url_resolved']}
            ).fetchone()
            
            if result:
                # Update existing station
                db.execute(
                    text("""
                        UPDATE radio_stations 
                        SET name = :name,
                            stream_url = :url,
                            country = :country,
                            language = :language,
                            is_active = 1,
                            last_checked = datetime('now')
                        WHERE id = :id
                    """),
                    {
                        "name": station_data['name'],
                        "url": station_data['url_resolved'],
                        "country": 'Senegal',
                        "language": station_data.get('language', ''),
                        "id": result[0]
                    }
                )
                logger.info(f"Updated station: {station_data['name']}")
            else:
                # Create new station
                db.execute(
                    text("""
                        INSERT INTO radio_stations 
                        (name, stream_url, country, language, is_active, last_checked, status)
                        VALUES 
                        (:name, :url, :country, :language, 1, datetime('now'), 'active')
                    """),
                    {
                        "name": station_data['name'],
                        "url": station_data['url_resolved'],
                        "country": 'Senegal',
                        "language": station_data.get('language', '')
                    }
                )
                logger.info(f"Added new station: {station_data['name']}")
        
        # Commit changes
        db.commit()
        logger.info("Successfully saved all stations")
        
        # Log final count
        total_stations = db.execute(text("SELECT COUNT(*) FROM radio_stations")).scalar()
        logger.info(f"Total stations in database: {total_stations}")
        
    except Exception as e:
        logger.error(f"Error fetching stations: {str(e)}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    fetch_senegal_stations() 