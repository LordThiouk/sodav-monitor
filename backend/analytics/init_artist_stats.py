import logging
import sys
from datetime import datetime, timedelta

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

sys.path.append(".")
from database import get_database_url
from models import Artist, ArtistStats, Track, TrackDetection

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def init_artist_stats():
    """Initialize artist statistics based on existing track detections"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            logger.info("Starting artist statistics initialization...")

            # Get all artists
            artists = session.query(Artist).all()
            logger.info(f"Found {len(artists)} artists to process")

            for artist in artists:
                logger.info(f"Processing artist: {artist.name}")

                # Get all tracks for this artist
                tracks = session.query(Track).filter(Track.artist_id == artist.id).all()
                if not tracks:
                    logger.warning(f"No tracks found for artist: {artist.name}")
                    continue

                track_ids = [track.id for track in tracks]

                # Calculate statistics from track detections
                stats = (
                    session.query(
                        func.count(TrackDetection.id).label("detection_count"),
                        func.max(TrackDetection.detected_at).label("last_detected"),
                        func.sum(TrackDetection.play_duration).label("total_play_time"),
                        func.avg(TrackDetection.confidence).label("average_confidence"),
                    )
                    .filter(TrackDetection.track_id.in_(track_ids))
                    .first()
                )

                if not stats.detection_count:
                    logger.warning(f"No detections found for artist: {artist.name}")
                    continue

                # Create or update artist stats
                artist_stats = (
                    session.query(ArtistStats).filter(ArtistStats.artist_id == artist.id).first()
                )

                if not artist_stats:
                    artist_stats = ArtistStats(
                        artist_id=artist.id,
                        detection_count=stats.detection_count,
                        last_detected=stats.last_detected,
                        total_play_time=stats.total_play_time or timedelta(0),
                        average_confidence=stats.average_confidence or 0.0,
                    )
                    session.add(artist_stats)
                else:
                    artist_stats.detection_count = stats.detection_count
                    artist_stats.last_detected = stats.last_detected
                    artist_stats.total_play_time = stats.total_play_time or timedelta(0)
                    artist_stats.average_confidence = stats.average_confidence or 0.0

                # Update artist totals
                artist.total_plays = stats.detection_count
                artist.total_play_time = stats.total_play_time or timedelta(0)
                artist.updated_at = datetime.utcnow()

                logger.info(
                    f"Statistics for {artist.name}:\n"
                    f"  - Detections: {stats.detection_count}\n"
                    f"  - Total play time: {stats.total_play_time}\n"
                    f"  - Average confidence: {stats.average_confidence:.2f}%"
                )

            session.commit()
            logger.info("✅ Artist statistics initialized successfully!")

        except Exception as e:
            logger.error(f"Error initializing artist stats: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        init_artist_stats()
    except Exception as e:
        logger.error("Failed to initialize artist statistics")
        sys.exit(1)
