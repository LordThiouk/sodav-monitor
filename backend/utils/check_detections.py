from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
import sys
sys.path.append('.')
from database import get_database_url
from models import Track, TrackDetection, Artist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_detections():
    """Check track detections in the database"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            logger.info("Checking track detections...")
            
            # Count total detections
            detection_count = session.query(func.count(TrackDetection.id)).scalar()
            logger.info(f"Total track detections: {detection_count}")
            
            # Get tracks with detections
            tracks_with_detections = session.query(
                Track,
                func.count(TrackDetection.id).label('detection_count'),
                func.sum(TrackDetection.play_duration).label('total_play_time'),
                func.avg(TrackDetection.confidence).label('avg_confidence')
            ).join(
                TrackDetection
            ).group_by(
                Track.id
            ).all()
            
            logger.info(f"\nFound {len(tracks_with_detections)} tracks with detections:")
            for track, count, play_time, confidence in tracks_with_detections:
                artist = session.query(Artist).get(track.artist_id)
                logger.info(
                    f"\nTrack: {track.title}\n"
                    f"Artist: {artist.name if artist else 'Unknown'}\n"
                    f"  - Detection count: {count}\n"
                    f"  - Total play time: {play_time}\n"
                    f"  - Average confidence: {confidence:.2f}%"
                )
            
            # Get recent detections
            recent_detections = session.query(TrackDetection).order_by(
                TrackDetection.detected_at.desc()
            ).limit(5).all()
            
            logger.info("\nMost recent detections:")
            for detection in recent_detections:
                track = session.query(Track).get(detection.track_id)
                if track:
                    artist = session.query(Artist).get(track.artist_id)
                    logger.info(
                        f"\nDetection at {detection.detected_at}:\n"
                        f"Track: {track.title}\n"
                        f"Artist: {artist.name if artist else 'Unknown'}\n"
                        f"  - Confidence: {detection.confidence:.2f}%\n"
                        f"  - Play duration: {detection.play_duration}"
                    )
            
            logger.info("\nCheck completed successfully!")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error checking detections: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        check_detections()
    except Exception as e:
        logger.error("Failed to check detections")
        sys.exit(1) 