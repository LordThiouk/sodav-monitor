from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from models import Base, TrackDetection, Track, RadioStation
from database import get_database_url
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_detections():
    """Check track detections and their durations"""
    try:
        # Get database URL and create engine
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Create session
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Get total number of detections
            total_detections = db.query(TrackDetection).count()
            logger.info(f"Total number of detections: {total_detections}")
            
            # Get number of detections with zero duration
            zero_duration_count = db.query(TrackDetection).filter(
                (TrackDetection.play_duration == timedelta(0)) | 
                (TrackDetection.play_duration == None)
            ).count()
            logger.info(f"Number of detections with zero/null duration: {zero_duration_count}")
            
            # Calculate percentage
            if total_detections > 0:
                zero_duration_percentage = (zero_duration_count / total_detections) * 100
                logger.info(f"Percentage of zero/null durations: {zero_duration_percentage:.2f}%")
            
            # Get recent detections
            logger.info("\nMost recent detections:")
            recent_detections = db.query(TrackDetection).join(Track).join(RadioStation).order_by(
                desc(TrackDetection.detected_at)
            ).limit(10).all()
            
            for detection in recent_detections:
                logger.info(
                    f"Detection ID: {detection.id}\n"
                    f"  Track: {detection.track.title} by {detection.track.artist}\n"
                    f"  Station: {detection.station.name}\n"
                    f"  Duration: {detection.play_duration or 'None'}\n"
                    f"  Detected at: {detection.detected_at}\n"
                    f"  Confidence: {detection.confidence}\n"
                )
            
            # Check tracks with most zero/null duration detections
            logger.info("\nTracks with most zero/null duration detections:")
            problematic_tracks = db.query(
                Track,
                func.count(TrackDetection.id).label('zero_duration_count')
            ).join(TrackDetection).filter(
                (TrackDetection.play_duration == timedelta(0)) | 
                (TrackDetection.play_duration == None)
            ).group_by(Track.id).order_by(
                desc('zero_duration_count')
            ).limit(5).all()
            
            for track, count in problematic_tracks:
                logger.info(
                    f"Track: {track.title} by {track.artist}\n"
                    f"  Zero/null duration detections: {count}\n"
                    f"  Total play time: {track.total_play_time}\n"
                    f"  Play count: {track.play_count}\n"
                )
            
            # Check stations with most zero/null duration detections
            logger.info("\nStations with most zero/null duration detections:")
            problematic_stations = db.query(
                RadioStation,
                func.count(TrackDetection.id).label('zero_duration_count')
            ).join(TrackDetection).filter(
                (TrackDetection.play_duration == timedelta(0)) | 
                (TrackDetection.play_duration == None)
            ).group_by(RadioStation.id).order_by(
                desc('zero_duration_count')
            ).limit(5).all()
            
            for station, count in problematic_stations:
                logger.info(
                    f"Station: {station.name}\n"
                    f"  Zero/null duration detections: {count}\n"
                    f"  Total play time: {station.total_play_time}\n"
                )
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking detections: {str(e)}")
        raise

if __name__ == "__main__":
    check_detections() 