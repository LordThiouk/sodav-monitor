from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import logging
from database import get_database_url
from models import Base, Artist, ArtistStats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database():
    """Check database structure and data"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Get inspector
            inspector = inspect(engine)
            
            # List all tables
            tables = inspector.get_table_names()
            logger.info(f"\nFound tables: {', '.join(tables)}")
            
            # Check artists table
            logger.info("\nArtists table structure:")
            for column in inspector.get_columns('artists'):
                logger.info(f"  - {column['name']}: {column['type']}")
            
            # Check artist_stats table
            logger.info("\nArtist_stats table structure:")
            for column in inspector.get_columns('artist_stats'):
                logger.info(f"  - {column['name']}: {column['type']}")
            
            # Check foreign keys
            logger.info("\nForeign keys in artist_stats:")
            for fk in inspector.get_foreign_keys('artist_stats'):
                logger.info(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            
            # Check indexes
            logger.info("\nIndexes in artist_stats:")
            for index in inspector.get_indexes('artist_stats'):
                logger.info(f"  - {index['name']}: {index['column_names']}")
            
            # Check data
            artists = session.query(Artist).all()
            logger.info(f"\nFound {len(artists)} artists:")
            for artist in artists:
                logger.info(f"  - {artist.name} (Label: {artist.label or 'N/A'})")
            
            # Check artist stats
            stats = session.query(ArtistStats).all()
            logger.info(f"\nFound {len(stats)} artist statistics records:")
            for stat in stats:
                artist = session.query(Artist).get(stat.artist_id)
                if artist:
                    logger.info(
                        f"  - {artist.name}:\n"
                        f"    * Detection count: {stat.detection_count}\n"
                        f"    * Total play time: {stat.total_play_time}\n"
                        f"    * Average confidence: {stat.average_confidence:.2f}%"
                    )
            
            logger.info("\nDatabase check completed successfully!")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        raise

if __name__ == "__main__":
    check_database() 