from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
import logging
from sqlalchemy.sql import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def get_database_url():
    """Get database URL based on environment"""
    env = os.getenv("ENV", "development")
    
    if env == "test":
        # Use test PostgreSQL database
        db_url = os.getenv("TEST_DATABASE_URL", "postgresql://sodav:sodav123@localhost:5432/sodav_test")
        logger.info("Using test database")
    elif env == "production":
        # Use production PostgreSQL URL
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL not set in production environment")
    else:
        # Use development PostgreSQL database
        db_url = os.getenv("DEV_DATABASE_URL", "postgresql://sodav:sodav123@localhost:5432/sodav_dev")
        logger.info("Using development database")
    
    # Handle special case for postgres:// URLs
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    logger.info(f"Database environment: {env}")
    return db_url

# Get database URL
DATABASE_URL = get_database_url()

# Configure engine with PostgreSQL-specific settings
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    poolclass=QueuePool,
    connect_args={
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "application_name": "sodav_monitor"
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables if they don't exist"""
    try:
        logger.info("Using development database")
        logger.info("Database environment: development")
        
        # Import all models to ensure they are registered
        from ..models.models import (
            User, Report, ReportSubscription, RadioStation,
            Artist, Track, TrackDetection, DetectionHourly,
            DetectionDaily, DetectionMonthly, StationStats,
            TrackDaily, TrackMonthly, ArtistDaily, ArtistMonthly,
            StationTrackStats, AnalyticsData, ArtistStats, TrackStats
        )
        
        # Create all tables without dropping
        logger.info("Creating tables if they don't exist...")
        Base.metadata.create_all(bind=engine)
        
        # Add unique constraint to hour column if it doesn't exist
        with engine.begin() as conn:
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'detection_hourly_hour_key'
                    ) THEN
                        ALTER TABLE detection_hourly ADD CONSTRAINT detection_hourly_hour_key UNIQUE (hour);
                    END IF;
                END $$;
            """))
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# Test database configuration
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://sodav:sodav123@localhost:5432/sodav_test")
test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_size=5,
    max_overflow=0,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    poolclass=QueuePool,
    connect_args={
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "application_name": "sodav_monitor_test"
    }
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
