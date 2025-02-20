from sqlalchemy import create_engine, inspect
from database import get_database_url
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_reports_table():
    """Check the structure of the reports table"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Get inspector
        inspector = inspect(engine)
        
        # Check reports table structure
        logger.info("\nReports table structure:")
        for column in inspector.get_columns('reports'):
            logger.info(f"  - {column['name']}: {column['type']}")
            
    except Exception as e:
        logger.error(f"Error checking table structure: {str(e)}")

if __name__ == "__main__":
    check_reports_table() 