"""Tests for the database operations module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from backend.detection.audio_processor.db_operations import DatabaseHandler
from backend.models.models import Track, Artist, TrackDetection, StationTrackStats

@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.query = Mock(return_value=session)
    session.filter = Mock(return_value=session)
    session.first = Mock(return_value=None)
    return session

@pytest.fixture
def handler(db_session):
    """Create a DatabaseHandler instance for testing."""
    return DatabaseHandler(db_session)

def test_initialize(db_session):
    """Test database handler initialization"""
    handler = DatabaseHandler(db_session)
    handler.initialize()
    assert handler.initialized is True

def test_initialize_db_error(db_session):
    """Test database initialization with error"""
    db_session.query.side_effect = SQLAlchemyError("Test error")
    handler = DatabaseHandler(db_session)
    
    with pytest.raises(SQLAlchemyError):
        handler.initialize()

def test_get_or_create_unknown_track_existing(db_session):
    """Test getting existing unknown track"""
    handler = DatabaseHandler(db_session)
    mock_track = Mock(spec=Track)
    mock_track.title = "Unknown Track"
    db_session.query.return_value.filter.return_value.first.return_value = mock_track
    
    result = handler.get_or_create_unknown_track()
    
    assert result.title == "Unknown Track"
    db_session.add.assert_not_called()

def test_get_or_create_unknown_track_new(db_session):
    """Test creating new unknown track"""
    handler = DatabaseHandler(db_session)
    db_session.query.return_value.filter.return_value.first.return_value = None
    mock_artist = Mock(spec=Artist)
    mock_artist.id = 1
    handler.get_or_create_unknown_artist = Mock(return_value=mock_artist)
    
    result = handler.get_or_create_unknown_track()
    
    assert result.title == "Unknown Track"
    db_session.add.assert_called_once()

def test_save_track_to_db_new_track(db_session):
    """Test saving new track to database"""
    handler = DatabaseHandler(db_session)
    track_info = {
        'title': 'Test Track',
        'artist': 'Test Artist',
        'duration': 180
    }
    
    # Mock artist and track queries
    mock_artist = Mock(spec=Artist)
    mock_artist.id = 1
    db_session.query.return_value.filter.return_value.first.side_effect = [None, None]
    
    result = handler.save_track_to_db(track_info)
    
    assert isinstance(result, Track)
    assert result.title == track_info['title']
    assert db_session.add.call_count == 2  # Artist and Track

def test_save_track_to_db_existing_track(db_session):
    """Test saving existing track to database"""
    handler = DatabaseHandler(db_session)
    track_info = {
        'title': 'Test Track',
        'artist': 'Test Artist'
    }
    
    # Mock existing artist and track
    mock_artist = Mock(spec=Artist)
    mock_artist.id = 1
    mock_track = Mock(spec=Track)
    mock_track.title = track_info['title']
    db_session.query.return_value.filter.return_value.first.side_effect = [mock_artist, mock_track]
    
    result = handler.save_track_to_db(track_info)
    
    assert result == mock_track
    db_session.add.assert_not_called()

def test_save_track_to_db_invalid_info(db_session):
    """Test saving track with invalid info"""
    handler = DatabaseHandler(db_session)
    track_info = {'title': 'Test Track'}  # Missing artist
    
    result = handler.save_track_to_db(track_info)
    
    assert result is None
    db_session.add.assert_not_called()

def test_verify_detections(db_session):
    """Test verifying track detections"""
    handler = DatabaseHandler(db_session)
    mock_detection = Mock(spec=TrackDetection)
    detections = [mock_detection]
    
    handler.verify_detections(detections)
    
    assert mock_detection.verified is True
    assert mock_detection.verification_date is not None
    db_session.add.assert_called_once_with(mock_detection)

def test_verify_detections_error(db_session):
    """Test verifying detections with error"""
    handler = DatabaseHandler(db_session)
    db_session.commit.side_effect = SQLAlchemyError("Test error")
    mock_detection = Mock(spec=TrackDetection)
    
    with pytest.raises(SQLAlchemyError):
        handler.verify_detections([mock_detection])

def test_db_transaction_success(handler):
    """Test successful database transaction."""
    with handler._db_transaction():
        handler.db_session.add(Mock())
    handler.db_session.commit.assert_called_once()
    handler.db_session.rollback.assert_not_called()

def test_db_transaction_error(handler):
    """Test database transaction with error."""
    with pytest.raises(SQLAlchemyError):
        with handler._db_transaction():
            raise SQLAlchemyError("Test error")
    handler.db_session.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_save_track_to_db_new_track(handler):
    """Test saving new track to database."""
    track_info = {
        'title': 'Test Track',
        'artist': 'Test Artist',
        'duration': 180.0,
        'confidence': 0.9
    }
    
    # Mock artist and track queries
    mock_artist = Mock(spec=Artist)
    mock_track = Mock(spec=Track)
    handler.db_session.query.return_value.filter.return_value.first.side_effect = [None, None]
    
    with patch.object(handler.db_session, 'add'):
        result = await handler.save_track_to_db(track_info)
        assert isinstance(result, Track)
        assert handler.db_session.add.call_count == 2  # Artist and Track

@pytest.mark.asyncio
async def test_save_track_to_db_existing_track(handler):
    """Test saving existing track to database."""
    track_info = {
        'title': 'Test Track',
        'artist': 'Test Artist',
        'duration': 180.0,
        'confidence': 0.9
    }
    
    # Mock existing track
    mock_track = Mock(spec=Track)
    mock_track.title = track_info['title']
    mock_track.artist = track_info['artist']
    
    handler.db_session.query.return_value.filter.return_value.first.return_value = mock_track
    
    result = await handler.save_track_to_db(track_info)
    assert result == mock_track
    handler.db_session.add.assert_not_called()

@pytest.mark.asyncio
async def test_save_track_to_db_invalid_info(handler):
    """Test saving track with invalid information."""
    track_info = {'invalid': 'data'}
    result = await handler.save_track_to_db(track_info)
    assert result is None

@pytest.mark.asyncio
async def test_verify_detections(handler):
    """Test detection verification."""
    start_time = datetime.now()
    end_time = datetime.now()
    
    # Mock detections query
    mock_detection = Mock(spec=TrackDetection)
    mock_detection.track = Mock(spec=Track)
    mock_detection.station = Mock()
    mock_detection.confidence = 0.9
    mock_detection.duration_seconds = 180.0
    
    handler.db_session.query.return_value.filter.return_value.all.return_value = [mock_detection]
    
    # Mock stats query
    mock_stats = Mock(spec=StationTrackStats)
    handler.db_session.query.return_value.filter.return_value.first.return_value = mock_stats
    
    await handler.verify_detections(start_time, end_time)
    handler.db_session.commit.assert_called()

@pytest.mark.asyncio
async def test_verify_detections_error(handler):
    """Test detection verification with error."""
    with patch.object(handler.db_session, 'query', side_effect=Exception("Test error")):
        with pytest.raises(Exception):
            await handler.verify_detections() 