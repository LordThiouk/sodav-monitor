from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
import random
import sys
sys.path.append('.')
from backend.models.database import get_database_url
from backend.models.models import Track, TrackDetection, RadioStation, StationStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_detections():
    """Generate detections for all existing tracks"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Get all tracks
            tracks = session.query(Track).all()
            if not tracks:
                logger.warning("No tracks found in database")
                return

            logger.info(f"Found {len(tracks)} tracks to process")

            # Get active radio stations
            stations = session.query(RadioStation).filter(
                RadioStation.status == StationStatus.active
            ).all()

            if not stations:
                logger.warning("No active stations found, creating default station")
                station = RadioStation(
                    name="Radio Teranga FM",
                    stream_url="http://stream.teranga.sn/live",
                    country="Senegal",
                    region="Dakar",
                    language="Wolof",
                    status=StationStatus.active,
                    is_active=True,
                    last_checked=datetime.now()
                )
                session.add(station)
                session.flush()
                stations = [station]

            # Generate detections for each track
            now = datetime.now()
            total_detections = 0

            for track in tracks:
                # Generate 5-10 detections per track over the last 24 hours
                num_detections = random.randint(5, 10)
                
                for _ in range(num_detections):
                    # Random time in the last 24 hours
                    detection_time = now - timedelta(
                        hours=random.uniform(0, 24)
                    )
                    
                    # Random duration between 2-5 minutes
                    duration = timedelta(minutes=random.uniform(2, 5))
                    
                    # Random station
                    station = random.choice(stations)
                    
                    # Create detection with high confidence
                    detection = TrackDetection(
                        track_id=track.id,
                        station_id=station.id,
                        confidence=random.uniform(85, 95),
                        detected_at=detection_time,
                        play_duration=duration
                    )
                    session.add(detection)
                    total_detections += 1

                    # Update track stats
                    track.play_count += 1
                    track.total_play_time = (track.total_play_time or timedelta(0)) + duration
                    track.last_played = max(detection_time, track.last_played or detection_time)

                    # Update station stats
                    station.total_play_time = (station.total_play_time or timedelta(0)) + duration
                    station.last_detection_time = max(detection_time, station.last_detection_time or detection_time)

                logger.info(f"Generated {num_detections} detections for track: {track.title}")

            session.commit()
            logger.info(f"Successfully generated {total_detections} detections for {len(tracks)} tracks")

        except Exception as e:
            logger.error(f"Error generating detections: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        generate_detections()
    except Exception as e:
        logger.error("Failed to generate detections")
        sys.exit(1) 