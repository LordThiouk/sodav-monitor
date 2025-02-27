"""Tests for the Track Manager module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import Track, TrackDetection, RadioStation

@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session

@pytest.fixture
def track_manager(db_session):
    """Create a TrackManager instance for testing."""
    return TrackManager(db_session)

@pytest.fixture
def sample_track():
    """Create a sample track for testing."""
    return Track(
        id=1,
        title="Test Song",
        artist="Test Artist",
        fingerprint=np.random.random(1000).tobytes(),
        fingerprint_raw=np.random.random(1000).tobytes(),
        detection_count=10,
        total_play_time=3600,  # 1 hour
        last_detected=datetime.now(),
        average_confidence=0.85
    )

@pytest.fixture
def sample_station():
    """Create a sample radio station for testing."""
    return RadioStation(
        id=1,
        name="Test Radio",
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        is_active=True
    )

@pytest.fixture
def sample_detection():
    """Create a sample track detection for testing."""
    return TrackDetection(
        id=1,
        track_id=1,
        station_id=1,
        detected_at=datetime.now(),
        confidence=0.95,
        play_duration=180
    )

@pytest.mark.asyncio
async def test_init_track_manager(track_manager):
    """Test TrackManager initialization."""
    assert track_manager is not None
    assert track_manager.db is not None
    assert hasattr(track_manager, 'find_local_match')
    assert hasattr(track_manager, 'find_musicbrainz_match')
    assert hasattr(track_manager, 'find_audd_match')

@pytest.mark.asyncio
async def test_find_local_match_success(track_manager, sample_track, db_session):
    """Test successful local track matching."""
    # Mock database query
    db_session.query.return_value.filter.return_value.first.return_value = sample_track
    
    # Test fingerprint matching
    fingerprint = np.random.random(1000)
    match = await track_manager.find_local_match(fingerprint)
    
    assert match is not None
    assert match['confidence'] > 0
    assert match['track']['id'] == sample_track.id
    assert match['track']['title'] == sample_track.title

@pytest.mark.asyncio
async def test_find_local_match_no_match(track_manager, db_session):
    """Test local matching with no match found."""
    # Mock database query with no result
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    fingerprint = np.random.random(1000)
    match = await track_manager.find_local_match(fingerprint)
    
    assert match is None

@pytest.mark.asyncio
async def test_find_musicbrainz_match_success(track_manager):
    """Test successful MusicBrainz matching."""
    mock_response = {
        'recordings': [{
            'id': 'mb-123',
            'title': 'MB Track',
            'artist-credit': [{'name': 'MB Artist'}],
            'score': 90
        }]
    }
    
    with patch('musicbrainzngs.acoustid.lookup', return_value=mock_response):
        fingerprint = np.random.random(1000)
        match = await track_manager.find_musicbrainz_match(fingerprint)
        
        assert match is not None
        assert match['confidence'] > 0
        assert match['track']['title'] == 'MB Track'
        assert match['track']['artist'] == 'MB Artist'

@pytest.mark.asyncio
async def test_find_musicbrainz_match_no_match(track_manager):
    """Test MusicBrainz matching with no match found."""
    with patch('musicbrainzngs.acoustid.lookup', return_value={'recordings': []}):
        fingerprint = np.random.random(1000)
        match = await track_manager.find_musicbrainz_match(fingerprint)
        
        assert match is None

@pytest.mark.asyncio
async def test_find_audd_match_success(track_manager):
    """Test successful Audd matching."""
    mock_response = {
        'status': 'success',
        'result': {
            'title': 'Audd Track',
            'artist': 'Audd Artist',
            'score': 0.8
        }
    }
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        
        audio_data = np.random.random(44100)
        match = await track_manager.find_audd_match(audio_data)
        
        assert match is not None
        assert match['confidence'] > 0
        assert match['track']['title'] == 'Audd Track'
        assert match['track']['artist'] == 'Audd Artist'

@pytest.mark.asyncio
async def test_find_audd_match_no_match(track_manager):
    """Test Audd matching with no match found."""
    mock_response = {
        'status': 'success',
        'result': None
    }
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
        
        audio_data = np.random.random(44100)
        match = await track_manager.find_audd_match(audio_data)
        
        assert match is None

@pytest.mark.asyncio
async def test_save_detection_success(track_manager, sample_track, sample_station, db_session):
    """Test successful detection saving."""
    detection_data = {
        'track': sample_track,
        'station': sample_station,
        'confidence': 0.9,
        'play_duration': 180,  # 3 minutes
        'detected_at': datetime.now()
    }
    
    await track_manager.save_detection(detection_data)
    
    # Verify database operations
    assert db_session.add.called
    assert db_session.commit.called
    
    # Verify track stats update
    track = detection_data['track']
    assert track.detection_count == 11  # Incremented from 10
    assert track.total_play_time == 3780  # Previous 3600 + 180
    assert isinstance(track.last_detected, datetime)

@pytest.mark.asyncio
async def test_save_detection_database_error(track_manager, sample_track, sample_station, db_session):
    """Test detection saving with database error."""
    detection_data = {
        'track': sample_track,
        'station': sample_station,
        'confidence': 0.9,
        'play_duration': 180
    }
    
    # Simulate database error
    db_session.commit.side_effect = SQLAlchemyError("Database error")
    
    with pytest.raises(SQLAlchemyError):
        await track_manager.save_detection(detection_data)
    
    # Verify rollback was called
    assert db_session.rollback.called

@pytest.mark.asyncio
async def test_update_track_stats(track_manager, sample_track, db_session):
    """Test track statistics update."""
    new_detection = {
        'confidence': 0.95,
        'play_duration': 240,  # 4 minutes
        'detected_at': datetime.now()
    }
    
    await track_manager.update_track_stats(sample_track, new_detection)
    
    assert sample_track.detection_count == 11  # Incremented
    assert sample_track.total_play_time == 3840  # Previous 3600 + 240
    assert sample_track.average_confidence > 0.85  # Updated average
    assert isinstance(sample_track.last_detected, datetime)

@pytest.mark.asyncio
async def test_cleanup_old_detections(track_manager, db_session):
    """Test cleanup of old detections."""
    # Mock old detections query
    old_date = datetime.now() - timedelta(days=31)
    mock_query = Mock()
    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.delete.return_value = 5  # 5 records deleted
    
    deleted_count = await track_manager.cleanup_old_detections(days=30)
    
    assert deleted_count == 5
    assert db_session.commit.called

@pytest.mark.asyncio
async def test_get_recent_detections(track_manager, sample_detection, db_session):
    """Test retrieving recent detections."""
    # Mock database query
    db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sample_detection]
    
    detections = await track_manager.get_recent_detections(station_id=1, limit=10)
    
    assert len(detections) == 1
    assert detections[0].id == sample_detection.id
    assert detections[0].confidence == sample_detection.confidence

@pytest.mark.asyncio
async def test_error_handling(track_manager):
    """Test error handling in track manager operations."""
    # Test database error
    with patch.object(track_manager.db, 'query', side_effect=Exception("Database error")):
        with pytest.raises(Exception, match="Database error"):
            await track_manager.find_local_match(np.random.random(1000))
    
    # Test MusicBrainz API error
    with patch('musicbrainzngs.acoustid.lookup', side_effect=Exception("MB API error")):
        match = await track_manager.find_musicbrainz_match(np.random.random(1000))
        assert match is None
    
    # Test Audd API error
    with patch('aiohttp.ClientSession.post', side_effect=Exception("Audd API error")):
        match = await track_manager.find_audd_match(np.random.random(44100))
        assert match is None 