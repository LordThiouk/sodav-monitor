"""Test cases for the updated_at column functionality."""

import pytest
from datetime import datetime, timedelta
import time
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.models.models import User, Report, RadioStation, Artist, Track

@pytest.fixture(scope="function", autouse=True)
def ensure_updated_at_columns(db_session: Session):
    """Ensure that the updated_at columns exist in the test database."""
    # Add updated_at column to users table if it doesn't exist
    db_session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
            END IF;
            
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE reports ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
            END IF;
            
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'radio_stations' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE radio_stations ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
            END IF;
            
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'artists' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE artists ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
            END IF;
            
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'tracks' AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE tracks ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
            END IF;
        END $$;
    """))
    db_session.commit()
    
    # Return the session
    return db_session

def test_user_updated_at(db_session: Session):
    """Test that the updated_at column is updated when a User model is modified."""
    # Create a new user with unique email and username
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        username=f"test_user_{unique_id}",
        email=f"test_user_{unique_id}@example.com",
        password_hash="test_password_hash",
        is_active=True,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Store the initial updated_at value
    initial_updated_at = user.updated_at
    
    # Wait a moment to ensure the timestamp will be different
    time.sleep(1)
    
    # Update the user
    user.username = f"updated_test_user_{unique_id}"
    db_session.commit()
    db_session.refresh(user)
    
    # Check that updated_at has been updated
    assert user.updated_at > initial_updated_at
    
def test_report_updated_at(db_session: Session, test_user: User):
    """Test that the updated_at column is updated when a Report model is modified."""
    # Create a new report
    report = Report(
        title="Test Report",
        type="daily",
        report_type="daily",
        format="xlsx",
        status="pending",
        user_id=test_user.id,
        created_by=test_user.id
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    
    # Store the initial updated_at value
    initial_updated_at = report.updated_at
    
    # Wait a moment to ensure the timestamp will be different
    time.sleep(1)
    
    # Update the report
    report.status = "completed"
    db_session.commit()
    db_session.refresh(report)
    
    # Check that updated_at has been updated
    assert report.updated_at > initial_updated_at

def test_station_updated_at(db_session: Session):
    """Test that the updated_at column is updated when a RadioStation model is modified."""
    # Create a new station with unique name
    unique_id = uuid.uuid4().hex[:8]
    station = RadioStation(
        name=f"Test Station {unique_id}",
        stream_url=f"http://test{unique_id}.stream/audio",
        country="SN",
        language="fr",
        region="Dakar",
        type="radio",
        status="active",
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    
    # Store the initial updated_at value
    initial_updated_at = station.updated_at
    
    # Wait a moment to ensure the timestamp will be different
    time.sleep(1)
    
    # Update the station
    station.name = f"Updated Test Station {unique_id}"
    db_session.commit()
    db_session.refresh(station)
    
    # Check that updated_at has been updated
    assert station.updated_at > initial_updated_at

def test_artist_updated_at(db_session: Session):
    """Test that the updated_at column is updated when an Artist model is modified."""
    # Create a new artist with a unique name
    unique_id = uuid.uuid4().hex[:8]
    artist = Artist(
        name=f"Test Artist {unique_id}",
        country="SN",
        region="Dakar",
        type="musician",
        label="Test Label"
    )
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    
    # Store the initial updated_at value
    initial_updated_at = artist.updated_at
    
    # If updated_at is None, set it to a default value
    if initial_updated_at is None:
        # Set updated_at manually
        db_session.execute(text(f"UPDATE artists SET updated_at = NOW() WHERE id = {artist.id}"))
        db_session.commit()
        db_session.refresh(artist)
        initial_updated_at = artist.updated_at
        
    # Ensure we have a valid initial timestamp
    assert initial_updated_at is not None, "Initial updated_at timestamp is None"
    
    # Wait a moment to ensure the timestamp will be different
    time.sleep(1)
    
    # Update the artist with another unique name
    artist.name = f"Updated Test Artist {unique_id}"
    db_session.commit()
    db_session.refresh(artist)
    
    # Check that updated_at has been updated
    assert artist.updated_at is not None, "Updated updated_at timestamp is None"
    assert artist.updated_at > initial_updated_at

def test_track_updated_at(db_session: Session, test_artist: Artist):
    """Test that the updated_at column is updated when a Track model is modified."""
    # Create a new track with unique values
    unique_id = uuid.uuid4().hex[:8]
    track = Track(
        title=f"Test Track {unique_id}",
        artist_id=test_artist.id,
        isrc=f"US{unique_id}",
        label="Test Label",
        album="Test Album",
        fingerprint=f"test_fingerprint_{unique_id}"
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)
    
    # Store the initial updated_at value
    initial_updated_at = track.updated_at
    
    # If updated_at is None, set it to a default value
    if initial_updated_at is None:
        # Set updated_at manually
        db_session.execute(text(f"UPDATE tracks SET updated_at = NOW() WHERE id = {track.id}"))
        db_session.commit()
        db_session.refresh(track)
        initial_updated_at = track.updated_at
        
    # Ensure we have a valid initial timestamp
    assert initial_updated_at is not None, "Initial updated_at timestamp is None"
    
    # Wait a moment to ensure the timestamp will be different
    time.sleep(1)
    
    # Update the track
    track.title = f"Updated Test Track {unique_id}"
    db_session.commit()
    db_session.refresh(track)
    
    # Check that updated_at has been updated
    assert track.updated_at is not None, "Updated updated_at timestamp is None"
    assert track.updated_at > initial_updated_at 