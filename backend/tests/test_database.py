import os
from dotenv import load_dotenv
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from database import SessionLocal, engine, get_database_url
from models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test PostgreSQL database connection and basic operations"""
    try:
        # Get database URL
        database_url = get_database_url()
        
        # Print connection details (masking password)
        masked_url = database_url.replace(database_url.split("@")[0].split(":")[-1], "***")
        logger.info(f"Testing database connection to: {masked_url}")
        
        # Test SQLAlchemy connection
        logger.info("Testing SQLAlchemy connection...")
        
        # Create tables if they don't exist
        logger.info("Creating database tables if they don't exist...")
        Base.metadata.create_all(bind=engine)
        
        # Test session creation and query
        logger.info("Testing database session and query...")
        db = SessionLocal()
        try:
            # Test simple query using SQLAlchemy
            from sqlalchemy import text
            result = db.execute(text("SELECT version()")).scalar()
            logger.info(f"PostgreSQL version: {result}")
            
            # Get table names using SQLAlchemy inspector
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"Available tables: {', '.join(tables)}")
            
            logger.info("✅ Database connection and queries successful!")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Database test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    test_database_connection() 