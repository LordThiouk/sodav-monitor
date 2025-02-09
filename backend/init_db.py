from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime

from database import SessionLocal, engine
from models import Base, RadioStation, Track, TrackDetection, User, Report
from models import DetectionHourly, ArtistStats, TrackStats, AnalyticsData

def init_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Initializing database with default data...")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Initialize empty analytics tables
        now = datetime.utcnow()
        
        # Create initial analytics data
        analytics = AnalyticsData(
            timestamp=now,
            detection_count=0,
            detection_rate=0.0,
            active_stations=0,
            average_confidence=0.0
        )
        session.add(analytics)
        
        # Create initial hourly detection record
        hourly = DetectionHourly(
            hour=now.replace(minute=0, second=0, microsecond=0),
            count=0
        )
        session.add(hourly)
        
        session.commit()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    init_database()