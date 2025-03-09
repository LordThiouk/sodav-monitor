from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Track, Base
import numpy as np

def add_sample_track():
    # Database setup
    engine = create_engine("sqlite:///./sodav_monitor.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create a sample track
    sample_track = Track(
        title="Sample Track",
        artist="Test Artist",
        fingerprint=",".join(map(str, np.random.randint(0, 255, 100))),  # Random fingerprint for testing
        fingerprint_hash="test_hash"
    )
    
    # Add to database
    session.add(sample_track)
    session.commit()
    print(f"Added sample track: {sample_track.title} by {sample_track.artist}")
    
    session.close()

if __name__ == "__main__":
    add_sample_track() 