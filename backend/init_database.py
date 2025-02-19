import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from database import Base, engine, get_database_url
from datetime import datetime
# Import all models
from models import (
    RadioStation, User, Track, TrackDetection, Report, ReportStatus,
    StationStatus, TrackStats, StationStats, DetectionHourly,
    DetectionDaily, DetectionMonthly, ArtistStats, ArtistDaily,
    ArtistMonthly, TrackDaily, TrackMonthly, StationTrackStats,
    AnalyticsData, ReportSubscription, Base
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_database():
    """Create the database if it doesn't exist"""
    load_dotenv()
    
    env = os.getenv("ENV", "development")
    if env == "production":
        logger.warning("⚠️ Cannot create database in production environment")
        return
    
    db_url = get_database_url()
    db_name = os.getenv("POSTGRES_DB", "sodav_dev")
    
    # Extract connection parameters from environment
    params = {
        "user": os.getenv("POSTGRES_USER", "sodav"),
        "password": os.getenv("POSTGRES_PASSWORD", "sodav123"),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432")
    }
    
    try:
        logger.info(f"Attempting to connect to PostgreSQL server at {params['host']}:{params['port']} with user {params['user']}")
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            dbname="postgres",  # Connect to default postgres database first
            **params
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        logger.info(f"Checking if database {db_name} exists...")
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Creating database {db_name}...")
            cursor.execute(f'CREATE DATABASE {db_name}')
            logger.info(f"✅ Database {db_name} created successfully")
        else:
            logger.info(f"Database {db_name} already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Database creation error: {str(e)}")
        sys.exit(1)

def create_tables():
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {', '.join(tables)}")
            
    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        sys.exit(1)

def init_development_data():
    """Initialize development data"""
    try:
        logger.info("Initializing development data...")
        
        with Session(engine) as session:
            # Fetch Senegalese radio stations from Radio Browser API
            logger.info("Fetching Senegalese radio stations...")
            url = "https://de1.api.radio-browser.info/json/stations/bycountry/Senegal"
            response = requests.get(url, timeout=10)
            stations = response.json()
            
            logger.info(f"Found {len(stations)} Senegalese stations")
            
            # Process each station
            for station_data in stations:
                # Create station object with cleaned data
                station = RadioStation(
                    name=station_data['name'],
                    stream_url=station_data['url_resolved'],
                    status=StationStatus.active,
                    type="radio",
                    region=station_data.get('state', 'Dakar'),  # Default to Dakar if state not provided
                    language=station_data.get('language', 'Wolof'),  # Default to Wolof if language not provided
                    country="Senegal",
                    created_at=datetime.now(),
                    last_checked=datetime.now(),
                    is_active=True
                )
                session.add(station)
                logger.info(f"Added station: {station.name}")
            
            # Create test admin user
            admin_user = User(
                username="admin",
                email="admin@sodav.sn",
                is_active=True,
                role="admin",
                created_at=datetime.now()
            )
            admin_user.set_password("admin123")
            session.add(admin_user)
            
            # Commit all changes
            session.commit()
            
            # Log final count
            total_stations = session.query(RadioStation).count()
            logger.info(f"✅ Development data initialized successfully with {total_stations} stations")
            
    except Exception as e:
        logger.error(f"❌ Error initializing development data: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    create_database()
    create_tables()
    
    if os.getenv("ENV") == "development":
        init_development_data()
    
    logger.info("✅ Database initialization completed successfully") 