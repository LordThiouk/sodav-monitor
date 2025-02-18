import os
from dotenv import load_dotenv
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import psycopg2
from database import SessionLocal, engine
from models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test PostgreSQL database connection and basic operations"""
    try:
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        # Print connection details (masking password)
        masked_url = database_url.replace(database_url.split("@")[0].split(":")[-1], "***")
        logger.info(f"Testing database connection to: {masked_url}")
        
        # Test direct connection with psycopg2
        logger.info("Testing direct connection with psycopg2...")
        conn_params = {
            "dbname": database_url.split("/")[-1],
            "user": database_url.split("://")[1].split(":")[0],
            "password": database_url.split("@")[0].split(":")[-1],
            "host": database_url.split("@")[1].split(":")[0],
            "port": database_url.split(":")[-1].split("/")[0]
        }
        
        conn = psycopg2.connect(**conn_params)
        logger.info("✅ Direct connection successful!")
        
        # Test query with psycopg2
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()
            logger.info(f"PostgreSQL version: {version[0]}")
        conn.close()
        
        # Test SQLAlchemy connection
        logger.info("\nTesting SQLAlchemy connection...")
        
        # Create tables if they don't exist
        logger.info("Creating database tables if they don't exist...")
        Base.metadata.create_all(bind=engine)
        
        # Test session creation and query
        logger.info("Testing database session and query...")
        db = SessionLocal()
        try:
            # Test simple query
            result = db.execute(text("SELECT 1")).scalar()
            logger.info(f"Test query result: {result}")
            
            # Get table names
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in db.execute(tables_query)]
            logger.info(f"Available tables: {', '.join(tables)}")
            
            logger.info("✅ SQLAlchemy connection and queries successful!")
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