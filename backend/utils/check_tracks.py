from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
import sys
sys.path.append('.')
from database import get_database_url
from models import Track, TrackDetection, Artist, RadioStation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_tracks_and_detections():
    """Check tracks and track_detections tables in detail"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            logger.info("Checking tracks table...")
            
            # Get all tracks with their artists
            tracks = session.query(
                Track, Artist
            ).join(
                Artist, Track.artist_id == Artist.id
            ).all()
            
            logger.info(f"\nFound {len(tracks)} tracks:")
            for track, artist in tracks:
                logger.info(
                    f"\nTrack: {track.title}\n"
                    f"Artist: {artist.name}\n"
                    f"  - Created at: {track.created_at}\n"
                    f"  - Last played: {track.last_played or 'Never'}\n"
                    f"  - Play count: {track.play_count}\n"
                    f"  - Total play time: {track.total_play_time}\n"
                    f"  - Label: {track.label or 'N/A'}"
                )
            
            logger.info("\nChecking track_detections table...")
            
            # Get all detections with track and station info
            detections = session.query(
                TrackDetection,
                Track,
                Artist,
                RadioStation
            ).join(
                Track, TrackDetection.track_id == Track.id
            ).join(
                Artist, Track.artist_id == Artist.id
            ).join(
                RadioStation, TrackDetection.station_id == RadioStation.id
            ).order_by(
                TrackDetection.detected_at.desc()
            ).all()
            
            logger.info(f"\nFound {len(detections)} detections:")
            for detection, track, artist, station in detections:
                logger.info(
                    f"\nDetection at {detection.detected_at}:\n"
                    f"Track: {track.title}\n"
                    f"Artist: {artist.name}\n"
                    f"Station: {station.name}\n"
                    f"  - Confidence: {detection.confidence:.2f}%\n"
                    f"  - Play duration: {detection.play_duration or 'Not recorded'}"
                )
            
            # Get detection statistics
            stats = session.execute(text("""
                SELECT 
                    COUNT(*) as total_detections,
                    COUNT(DISTINCT track_id) as unique_tracks,
                    COUNT(DISTINCT station_id) as unique_stations,
                    AVG(confidence) as avg_confidence,
                    MIN(detected_at) as first_detection,
                    MAX(detected_at) as last_detection
                FROM track_detections
            """)).first()
            
            logger.info(
                f"\nDetection Statistics:\n"
                f"- Total detections: {stats.total_detections}\n"
                f"- Unique tracks detected: {stats.unique_tracks}\n"
                f"- Active stations: {stats.unique_stations}\n"
                f"- Average confidence: {stats.avg_confidence:.2f}%\n"
                f"- First detection: {stats.first_detection}\n"
                f"- Last detection: {stats.last_detection}"
            )
            
            logger.info("\nCheck completed successfully!")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error checking tracks and detections: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        check_tracks_and_detections()
    except Exception as e:
        logger.error("Failed to check tracks and detections")
        sys.exit(1) 