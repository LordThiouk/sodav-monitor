from sqlalchemy import create_engine
from models import Base, RadioStation
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_database():
    # Create database engine
    engine = create_engine("sqlite:///./sodav_monitor.db", connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.drop_all(engine)  # Drop existing tables
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add default radio stations
    stations = [
        RadioStation(
            name="Sene Multimedia",
            stream_url="http://listen.senemultimedia.net:8090/stream",
            country="Senegal",
            language="French/Wolof",
            is_active=1,
            last_checked=datetime.now()
        ),
        RadioStation(
            name="Sud FM",
            stream_url="https://stream.zeno.fm/d970hwkm1f8uv",
            country="Senegal",
            language="French/Wolof",
            is_active=1,
            last_checked=datetime.now()
        )
    ]
    
    for station in stations:
        session.add(station)
    
    session.commit()
    
    print("Database initialized successfully!")
    print(f"Added {len(stations)} radio stations")
    
    session.close()

if __name__ == "__main__":
    init_database() 