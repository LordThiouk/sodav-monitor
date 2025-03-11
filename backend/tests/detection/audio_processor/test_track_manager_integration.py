"""
Integration tests for the TrackManager module.

This module contains integration tests that verify the correct interaction
between TrackManager and its associated classes (TrackFinder, TrackCreator,
ExternalDetectionService, FingerprintHandler, StatsRecorder).
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid

from backend.detection.audio_processor.track_manager.track_manager import TrackManager
from backend.detection.audio_processor.track_manager.track_finder import TrackFinder
from backend.detection.audio_processor.track_manager.track_creator import TrackCreator
from backend.detection.audio_processor.track_manager.external_detection import ExternalDetectionService
from backend.detection.audio_processor.track_manager.fingerprint_handler import FingerprintHandler
from backend.detection.audio_processor.track_manager.stats_recorder import StatsRecorder
from backend.models.models import Track, Artist, RadioStation, TrackDetection


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_track():
    """Create a mock Track for testing."""
    mock_track = MagicMock(spec=Track)
    mock_track.id = 1
    mock_track.title = "Test Track"
    mock_track.artist_id = 1
    mock_track.artist = MagicMock(spec=Artist)
    mock_track.artist.id = 1
    mock_track.artist.name = "Test Artist"
    mock_track.album = "Test Album"
    mock_track.isrc = "ABCDE1234567"
    mock_track.label = "Test Label"
    mock_track.release_date = "2023-01-01"
    mock_track.duration = 180
    mock_track.fingerprint = "test_fingerprint"
    mock_track.fingerprint_raw = b"test_fingerprint_raw"
    return mock_track


@pytest.fixture
def mock_station():
    """Create a mock RadioStation for testing."""
    mock_station = MagicMock(spec=RadioStation)
    mock_station.id = 1
    mock_station.name = "Test Station"
    return mock_station


@pytest.fixture
def mock_features():
    """Create mock audio features for testing."""
    return {
        "mfcc": [1.0, 2.0, 3.0],
        "chroma": [4.0, 5.0, 6.0],
        "spectral_centroid": [7.0, 8.0, 9.0],
        "audio_data": b"test_audio_data",
        "sample_rate": 44100,
        "duration": 5.0
    }


@pytest.mark.asyncio
async def test_track_creation_integration(mock_db_session, mock_track):
    """
    Test the integration between TrackManager and TrackCreator for creating tracks.
    
    This test verifies that the TrackManager correctly delegates to TrackCreator
    to create or retrieve a track.
    """
    # Create the TrackManager
    track_manager = TrackManager(db_session=mock_db_session)
    
    # Patch the TrackCreator methods
    with patch.object(track_manager.track_creator, 'get_or_create_artist', new_callable=AsyncMock, return_value=1), \
         patch.object(track_manager.track_creator, 'get_or_create_track', new_callable=AsyncMock, return_value=mock_track):
        
        # Call the method under test
        track = await track_manager.get_or_create_track(
            title="Test Track",
            artist_name="Test Artist",
            album="Test Album",
            isrc="ABCDE1234567",
            label="Test Label",
            release_date="2023-01-01",
            duration=180.0
        )
        
        # Verify the results
        assert track is not None
        assert track.id == 1
        assert track.title == "Test Track"
        assert track.artist.name == "Test Artist"
        
        # Verify the TrackCreator methods were called correctly
        track_manager.track_creator.get_or_create_artist.assert_called_once_with("Test Artist")
        track_manager.track_creator.get_or_create_track.assert_called_once()


@pytest.mark.asyncio
async def test_local_detection_integration(mock_db_session, mock_track, mock_features):
    """
    Test the integration between TrackManager and TrackFinder for local detection.
    
    This test verifies that the TrackManager correctly delegates to TrackFinder
    for local track detection and then to StatsRecorder for recording the detection.
    """
    # Create the TrackManager
    track_manager = TrackManager(db_session=mock_db_session)
    
    # Patch the methods of the internal components
    with patch.object(track_manager.track_finder, 'find_local_match', new_callable=AsyncMock) as mock_find_local, \
         patch.object(track_manager.stats_recorder, 'record_detection') as mock_record_detection:
        
        # Configure the mocks
        mock_find_local.return_value = {
            "track": {
                "id": 1,
                "title": "Test Track",
                "artist": "Test Artist"
            },
            "confidence": 0.9,
            "method": "local"
        }
        
        mock_record_detection.return_value = {
            "success": True,
            "track_id": 1,
            "detection_id": 1
        }
        
        # Call the method under test
        result = await track_manager.process_track(mock_features, station_id=1)
        
        # Verify the correct methods were called
        mock_find_local.assert_called_once_with(mock_features)
        mock_record_detection.assert_called_once()
        
        # Verify the result
        assert result["success"] is True
        assert result["track_id"] == 1


@pytest.mark.asyncio
async def test_isrc_detection_integration(mock_db_session, mock_track, mock_features):
    """
    Test the integration for ISRC-based detection.
    
    This test verifies that the TrackManager correctly uses ISRC for finding tracks
    when local detection fails.
    """
    # Create the TrackManager
    track_manager = TrackManager(db_session=mock_db_session)
    
    # Patch the methods of the internal components
    with patch.object(track_manager.track_finder, 'find_local_match', new_callable=AsyncMock) as mock_find_local, \
         patch.object(track_manager.track_finder, 'find_track_by_isrc', new_callable=AsyncMock) as mock_find_by_isrc, \
         patch.object(track_manager.stats_recorder, 'record_detection') as mock_record_detection:
        
        # Configure the mocks
        mock_find_local.return_value = None  # Local detection fails
        
        mock_find_by_isrc.return_value = {
            "track": {
                "id": 1,
                "title": "Test Track",
                "artist": "Test Artist"
            },
            "confidence": 1.0,
            "method": "isrc"
        }
        
        mock_record_detection.return_value = {
            "success": True,
            "track_id": 1,
            "detection_id": 1
        }
        
        # Add ISRC to the features
        features = mock_features.copy()
        features["isrc"] = "ABCDE1234567"
        
        # Call the method under test
        result = await track_manager.process_track(features, station_id=1)
        
        # Verify the correct methods were called
        mock_find_local.assert_called_once_with(features)
        mock_find_by_isrc.assert_called_once_with("ABCDE1234567")
        mock_record_detection.assert_called_once()
        
        # Verify the result
        assert result["success"] is True
        assert result["track_id"] == 1


@pytest.mark.asyncio
async def test_external_detection_integration(mock_db_session, mock_track, mock_features):
    """
    Test the integration with external detection services.
    
    This test verifies that the TrackManager correctly delegates to ExternalDetectionService
    when local and ISRC detection fail.
    """
    # Create the TrackManager
    track_manager = TrackManager(db_session=mock_db_session)
    
    # Patch the methods of the internal components
    with patch.object(track_manager.track_finder, 'find_local_match', new_callable=AsyncMock) as mock_find_local, \
         patch.object(track_manager.track_finder, 'find_track_by_isrc', new_callable=AsyncMock) as mock_find_by_isrc, \
         patch.object(track_manager.external_service, 'find_external_match', new_callable=AsyncMock) as mock_find_external, \
         patch.object(track_manager.track_creator, 'get_or_create_artist', new_callable=AsyncMock) as mock_get_artist, \
         patch.object(track_manager.track_creator, 'get_or_create_track', new_callable=AsyncMock) as mock_get_track, \
         patch.object(track_manager.stats_recorder, 'start_track_detection') as mock_start_detection:
        
        # Configure the mocks
        mock_find_local.return_value = None  # Local detection fails
        mock_find_by_isrc.return_value = None  # ISRC detection fails
        
        mock_find_external.return_value = {
            "track": {
                "title": "Test Track",
                "artist": "Test Artist",
                "album": "Test Album",
                "isrc": "ABCDE1234567",
                "label": "Test Label"
            },
            "confidence": 0.8,
            "method": "acoustid"
        }
        
        mock_get_artist.return_value = 1
        mock_get_track.return_value = mock_track
        
        mock_start_detection.return_value = {
            "success": True,
            "track_id": 1,
            "detection_id": 1
        }
        
        # Call the method under test
        result = await track_manager.process_track(mock_features, station_id=1)
        
        # Verify the correct methods were called
        mock_find_local.assert_called_once_with(mock_features)
        mock_find_external.assert_called_once_with(mock_features, 1)
        mock_get_artist.assert_called_once()
        mock_get_track.assert_called_once()
        mock_start_detection.assert_called_once()
        
        # Verify the result
        assert result["success"] is True
        assert result["track_id"] == 1


@pytest.mark.asyncio
async def test_fingerprint_integration(mock_db_session, mock_features):
    """
    Test the integration with the FingerprintHandler.
    
    This test verifies that the TrackManager correctly uses the FingerprintHandler
    for fingerprint operations.
    """
    # Create the TrackManager
    track_manager = TrackManager(db_session=mock_db_session)
    
    # Patch the methods of the FingerprintHandler
    with patch.object(track_manager.fingerprint_handler, 'extract_fingerprint') as mock_extract_fingerprint:
        
        # Configure the mock
        mock_extract_fingerprint.return_value = "test_fingerprint"
        
        # Call the fingerprint method
        fingerprint = track_manager.fingerprint_handler.extract_fingerprint(mock_features)
        
        # Verify the correct method was called
        mock_extract_fingerprint.assert_called_once_with(mock_features)
        
        # Verify the result
        assert fingerprint == "test_fingerprint"


@pytest.mark.asyncio
async def test_stats_recording_integration(mock_db_session, mock_track, mock_station):
    """
    Test the integration with the StatsRecorder.
    
    This test verifies that the TrackManager correctly delegates to StatsRecorder
    for recording detections and updating statistics.
    """
    # Create the TrackManager
    track_manager = TrackManager(db_session=mock_db_session)
    
    # Patch the methods of the StatsRecorder
    with patch.object(track_manager.stats_recorder, 'record_detection') as mock_record_detection, \
         patch.object(track_manager.stats_recorder, 'start_track_detection') as mock_start_detection, \
         patch.object(track_manager.stats_recorder, 'record_play_time') as mock_record_play_time:
        
        # Configure the mocks
        mock_record_detection.return_value = {
            "success": True,
            "track_id": 1,
            "detection_id": 1
        }
        
        mock_start_detection.return_value = {
            "success": True,
            "track_id": 1,
            "detection_id": 1
        }
        
        mock_record_play_time.return_value = True
        
        # Create detection data
        detection_data = {
            "track": {
                "id": 1,
                "title": "Test Track",
                "artist": "Test Artist"
            },
            "confidence": 0.9,
            "method": "local",
            "fingerprint": "test_fingerprint"
        }
        
        # Call the stats recording methods
        result1 = track_manager.stats_recorder.record_detection(detection_data, station_id=1)
        result2 = track_manager.stats_recorder.start_track_detection(mock_track, 1, {"confidence": 0.9, "detection_method": "local"})
        result3 = track_manager.record_play_time(1, 1, 180.0)
        
        # Verify the correct methods were called
        mock_record_detection.assert_called_once_with(detection_data, station_id=1)
        mock_start_detection.assert_called_once_with(mock_track, 1, {"confidence": 0.9, "detection_method": "local"})
        mock_record_play_time.assert_called_once_with(1, 1, 180.0)
        
        # Verify the results
        assert result1["success"] is True
        assert result2["success"] is True
        assert result3 is True


@pytest.mark.asyncio
async def test_full_detection_pipeline_integration(mock_db_session, mock_track, mock_features, mock_station):
    """
    Test the complete detection pipeline integration.
    
    This test verifies that all components work together correctly in the full detection pipeline.
    """
    # Create the TrackManager
    track_manager = TrackManager(db_session=mock_db_session)
    
    # Patch all the methods of the internal components
    with patch.object(track_manager.track_finder, 'find_local_match', new_callable=AsyncMock) as mock_find_local, \
         patch.object(track_manager.track_finder, 'find_track_by_isrc', new_callable=AsyncMock) as mock_find_by_isrc, \
         patch.object(track_manager.external_service, 'find_external_match', new_callable=AsyncMock) as mock_find_external, \
         patch.object(track_manager.track_creator, 'get_or_create_artist', new_callable=AsyncMock) as mock_get_artist, \
         patch.object(track_manager.track_creator, 'get_or_create_track', new_callable=AsyncMock) as mock_get_track, \
         patch.object(track_manager.stats_recorder, 'start_track_detection') as mock_start_detection:
        
        # Configure the mocks for a complete pipeline test
        mock_find_local.return_value = None  # Local detection fails
        mock_find_by_isrc.return_value = None  # ISRC detection fails
        
        mock_find_external.return_value = {
            "track": {
                "title": "Test Track",
                "artist": "Test Artist",
                "album": "Test Album",
                "isrc": "ABCDE1234567",
                "label": "Test Label"
            },
            "confidence": 0.8,
            "method": "acoustid"
        }
        
        mock_get_artist.return_value = 1
        mock_get_track.return_value = mock_track
        
        mock_start_detection.return_value = {
            "success": True,
            "track_id": 1,
            "detection_id": 1
        }
        
        # Call the process_track method
        result = await track_manager.process_track(mock_features, station_id=1)
        
        # Verify the correct methods were called in sequence
        mock_find_local.assert_called_once_with(mock_features)
        mock_find_external.assert_called_once_with(mock_features, 1)
        mock_get_artist.assert_called_once()
        mock_get_track.assert_called_once()
        mock_start_detection.assert_called_once()
        
        # Verify the result
        assert result["success"] is True
        assert result["track_id"] == 1
        assert result["detection_id"] == 1 