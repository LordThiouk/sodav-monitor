import logging
import sys
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append("..")
from database import get_database_url
from models import Artist, ArtistStats, Base, Track
from sqlalchemy import inspect

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def verify_table_structure(session):
    """Verify the structure of the database tables"""
    try:
        # Get table information
        inspector = inspect(session.get_bind())

        # Check artists table
        logger.info("\nArtists table structure:")
        for column in inspector.get_columns("artists"):
            logger.info(f"  - {column['name']}: {column['type']}")

        # Check artist_stats table
        logger.info("\nArtist_stats table structure:")
        for column in inspector.get_columns("artist_stats"):
            logger.info(f"  - {column['name']}: {column['type']}")

        # Check foreign keys
        logger.info("\nForeign keys in artist_stats:")
        for fk in inspector.get_foreign_keys("artist_stats"):
            logger.info(
                f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
            )

        # Check indexes
        logger.info("\nIndexes in artist_stats:")
        for index in inspector.get_indexes("artist_stats"):
            logger.info(f"  - {index['name']}: {index['column_names']}")

        return True
    except Exception as e:
        logger.error(f"Error verifying table structure: {str(e)}")
        return False


def verify_database_state():
    """Verify the state of the database after migration"""
    try:
        logger.info("Starting database verification...")

        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Check artists
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

            # Check for artists without stats
            artists_without_stats = (
                session.query(Artist).outerjoin(ArtistStats).filter(ArtistStats.id == None).all()
            )

            if artists_without_stats:
                logger.warning(f"\nFound {len(artists_without_stats)} artists without statistics:")
                for artist in artists_without_stats:
                    logger.warning(f"  - {artist.name}")
            else:
                logger.info("\nAll artists have statistics records")

            logger.info("\nVerification completed successfully!")

        except Exception as e:
            logger.error(f"Error during verification: {str(e)}")
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        verify_database_state()
    except Exception as e:
        logger.error("Verification failed")
        sys.exit(1)
