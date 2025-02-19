from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def get_database_url():
    """Get database URL based on environment"""
    env = os.getenv("ENV", "development")
    
    if env == "production":
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
    """Initialize database with required tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"✅ Database initialized successfully on {DATABASE_URL.split('@')[1]}")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise
