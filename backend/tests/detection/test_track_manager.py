"""Tests for the Track Manager component."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from datetime import datetime, timedelta

from detection.audio_processor.track_manager import TrackManager
from models.models import Track, TrackDetection, RadioStation

@pytest.fixture
def db_session():
    """Create a mock database session."""
    return Mock()

@pytest.fixture
def track_manager(db_session):
    """Create a TrackManager instance for testing."""
    return TrackManager(db_session)

@pytest.fixture
def sample_track():
    """Create a sample track for testing."""
    return Track(
        id=1,
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        duration=180,
        fingerprint="test_fingerprint",
        fingerprint_raw=b"raw_fingerprint_data"
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
    """Test successful local track match."""
    # Mock database query
    db_session.query.return_value.filter.return_value.first.return_value = sample_track
    
    # Mock fingerprint comparison
    with patch('acoustid.compare_fingerprints', return_value=0.95):
        match = await track_manager.find_local_match(b"test_audio_data")
        
        assert match is not None
        assert match['confidence'] == 0.95
        assert match['track']['id'] == sample_track.id
        assert match['track']['title'] == sample_track.title

@pytest.mark.asyncio
async def test_find_local_match_no_match(track_manager, db_session):
    """Test local match with no results."""
    # Mock empty database result
    db_session.query.return_value.filter.return_value.first.return_value = None
    
    match = await track_manager.find_local_match(b"test_audio_data")
    assert match is None

@pytest.mark.asyncio
async def test_find_musicbrainz_match_success(track_manager):
    """Test successful MusicBrainz match."""
    mock_mb_response = {
        'recordings': [{
            'id': 'mb-id',
            'title': 'MB Track',
            'artist-credit': [{'name': 'MB Artist'}],
            'releases': [{'title': 'MB Album'}]
        }]
    }
    
    with patch('musicbrainzngs.search_recordings', return_value=mock_mb_response):
        match = await track_manager.find_musicbrainz_match(b"test_audio_data")
        
        assert match is not None
        assert match['confidence'] > 0
        assert match['track']['title'] == 'MB Track'
        assert match['track']['artist'] == 'MB Artist'

@pytest.mark.asyncio
async def test_find_musicbrainz_match_no_results(track_manager):
    """Test MusicBrainz match with no results."""
    mock_mb_response = {'recordings': []}
    
    with patch('musicbrainzngs.search_recordings', return_value=mock_mb_response):
        match = await track_manager.find_musicbrainz_match(b"test_audio_data")
        assert match is None

@pytest.mark.asyncio
async def test_find_audd_match_success(track_manager):
    """Test successful Audd match."""
    mock_audd_response = {
        'status': 'success',
        'result': {
            'title': 'Audd Track',
            'artist': 'Audd Artist',
            'album': 'Audd Album',
            'score': 0.85
        }
    }
    
    with patch('aiohttp.ClientSession.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_audd_response
        )
        
        match = await track_manager.find_audd_match(b"test_audio_data")
        
        assert match is not None
        assert match['confidence'] == 0.85
        assert match['track']['title'] == 'Audd Track'
        assert match['track']['artist'] == 'Audd Artist'

@pytest.mark.asyncio
async def test_find_audd_match_no_result(track_manager):
    """Test Audd match with no results."""
    mock_audd_response = {'status': 'success', 'result': None}
    
    with patch('aiohttp.ClientSession.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_audd_response
        )
        
        match = await track_manager.find_audd_match(b"test_audio_data")
        assert match is None

@pytest.mark.asyncio
async def test_save_detection(track_manager, sample_track, sample_detection, db_session):
    """Test saving a track detection."""
    detection_data = {
        'track_id': sample_track.id,
        'station_id': 1,
        'confidence': 0.95,
        'play_duration': 180
    }
    
    # Mock database operations
    db_session.add = Mock()
    db_session.commit = Mock()
    
    await track_manager.save_detection(detection_data)
    
    # Verify database operations were called
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_track_stats(track_manager, sample_track, db_session):
    """Test updating track statistics."""
    # Mock database query and update
    db_session.query.return_value.filter.return_value.first.return_value = sample_track
    db_session.commit = Mock()
    
    stats_data = {
        'play_count': 1,
        'total_play_time': 180,
        'average_confidence': 0.95
    }
    
    await track_manager.update_track_stats(sample_track.id, stats_data)
    
    # Verify track was updated
    assert sample_track.play_count == 1
    assert sample_track.total_play_time == 180
    assert sample_track.average_confidence == 0.95
    db_session.commit.assert_called_once()

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
            await track_manager.find_local_match(b"test_audio_data")
    
    # Test MusicBrainz API error
    with patch('musicbrainzngs.search_recordings', side_effect=Exception("MB API error")):
        match = await track_manager.find_musicbrainz_match(b"test_audio_data")
        assert match is None
    
    # Test Audd API error
    with patch('aiohttp.ClientSession.post', side_effect=Exception("Audd API error")):
        match = await track_manager.find_audd_match(b"test_audio_data")
        assert match is None 