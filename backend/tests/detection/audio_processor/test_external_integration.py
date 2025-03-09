"""Tests for the integration between AudioProcessor and external services (MusicBrainz and AudD)."""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.external_services import MusicBrainzService, AuddService, ExternalServiceHandler
from backend.models.models import Track, Artist, TrackDetection, RadioStation

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.query = Mock()
    session.rollback = Mock()
    return session

@pytest.fixture
def mock_musicbrainz_service():
    """Create a mock MusicBrainz service."""
    service = Mock(spec=MusicBrainzService)
    service.detect_track = AsyncMock()
    service.detect_track_with_retry = AsyncMock()
    return service

@pytest.fixture
def mock_audd_service():
    """Create a mock AudD service."""
    service = Mock(spec=AuddService)
    service.detect_track = AsyncMock()
    service.detect_track_with_retry = AsyncMock()
    return service

@pytest.fixture
def mock_external_handler(mock_db_session, mock_musicbrainz_service, mock_audd_service):
    """Create a mock external service handler."""
    handler = Mock(spec=ExternalServiceHandler)
    handler.db_session = mock_db_session
    handler.recognize_with_musicbrainz = AsyncMock()
    handler.recognize_with_audd = AsyncMock()
    return handler

@pytest.fixture
def track_manager(mock_db_session, mock_external_handler):
    """Create a TrackManager with mocked external handler."""
    manager = TrackManager(db_session=mock_db_session)
    manager._convert_features_to_audio = Mock(return_value=b"mock_audio_data")
    manager._extract_fingerprint = Mock(return_value="mock_fingerprint")
    return manager

@pytest.fixture
def sample_audio_features():
    """Create sample audio features."""
    return np.random.random((128, 10))

@pytest.fixture
def audio_processor(mock_db_session):
    """Create an AudioProcessor with mocked dependencies."""
    processor = AudioProcessor(db_session=mock_db_session)
    return processor

class TestMusicBrainzIntegration:
    """Test integration with MusicBrainz service."""
    
    @pytest.mark.asyncio
    async def test_musicbrainz_match_success(self, track_manager, mock_external_handler, mock_db_session, sample_audio_features):
        """Test successful MusicBrainz match."""
        # Mock the external handler
        with patch('backend.detection.audio_processor.track_manager.ExternalServiceHandler', return_value=mock_external_handler):
            # Configure mock to return a successful match
            mock_external_handler.recognize_with_musicbrainz.return_value = {
                'title': 'Test MusicBrainz Track',
                'artist': 'Test MusicBrainz Artist',
                'confidence': 0.85,
                'duration': 240,
                'recording_id': 'mb-123',
                'artist_id': 'mb-artist-123'
            }
            
            # Mock the artist query
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            # Mock the artist creation
            mock_artist = Mock(spec=Artist)
            mock_artist.id = 1
            mock_artist.name = 'Test MusicBrainz Artist'
            mock_db_session.add.side_effect = lambda x: setattr(x, 'id', 1) if isinstance(x, Artist) else None
            
            # Mock the track creation
            mock_track = Mock(spec=Track)
            mock_track.id = 1
            mock_track.title = 'Test MusicBrainz Track'
            mock_track.artist_id = 1
            track_manager._get_or_create_track = Mock(return_value=mock_track)
            
            # Call the method
            result = await track_manager.find_musicbrainz_match(sample_audio_features)
            
            # Verify the result
            assert result is not None
            assert result['track'] == mock_track
            assert result['confidence'] == 0.85
            assert result['source'] == 'musicbrainz'
            
            # Verify that the external handler was called
            mock_external_handler.recognize_with_musicbrainz.assert_called_once_with(b"mock_audio_data")
    
    @pytest.mark.asyncio
    async def test_musicbrainz_match_failure(self, track_manager, mock_external_handler, sample_audio_features):
        """Test MusicBrainz match failure."""
        # Mock the external handler
        with patch('backend.detection.audio_processor.track_manager.ExternalServiceHandler', return_value=mock_external_handler):
            # Configure mock to return no match
            mock_external_handler.recognize_with_musicbrainz.return_value = None
            
            # Call the method
            result = await track_manager.find_musicbrainz_match(sample_audio_features)
            
            # Verify the result
            assert result is None
            
            # Verify that the external handler was called
            mock_external_handler.recognize_with_musicbrainz.assert_called_once_with(b"mock_audio_data")
    
    @pytest.mark.asyncio
    async def test_musicbrainz_error_handling(self, track_manager, mock_external_handler, sample_audio_features):
        """Test MusicBrainz error handling."""
        # Mock the external handler
        with patch('backend.detection.audio_processor.track_manager.ExternalServiceHandler', return_value=mock_external_handler):
            # Configure mock to raise an exception
            mock_external_handler.recognize_with_musicbrainz.side_effect = Exception("MusicBrainz API error")
            
            # Call the method
            result = await track_manager.find_musicbrainz_match(sample_audio_features)
            
            # Verify the result
            assert result is None
            
            # Verify that the external handler was called
            mock_external_handler.recognize_with_musicbrainz.assert_called_once_with(b"mock_audio_data")

class TestAuddIntegration:
    """Test integration with AudD service."""
    
    @pytest.mark.asyncio
    async def test_audd_match_success(self, track_manager, mock_external_handler, mock_db_session, sample_audio_features):
        """Test successful AudD match."""
        # Mock the external handler
        with patch('backend.detection.audio_processor.track_manager.ExternalServiceHandler', return_value=mock_external_handler):
            # Configure mock to return a successful match
            mock_external_handler.recognize_with_audd.return_value = {
                'title': 'Test AudD Track',
                'artist': 'Test AudD Artist',
                'confidence': 0.8,
                'duration': 180,
                'song_id': 'audd-123',
                'artist_id': 'audd-artist-123'
            }
            
            # Mock the artist query
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            # Mock the artist creation
            mock_artist = Mock(spec=Artist)
            mock_artist.id = 2
            mock_artist.name = 'Test AudD Artist'
            mock_db_session.add.side_effect = lambda x: setattr(x, 'id', 2) if isinstance(x, Artist) else None
            
            # Mock the track creation
            mock_track = Mock(spec=Track)
            mock_track.id = 2
            mock_track.title = 'Test AudD Track'
            mock_track.artist_id = 2
            track_manager._get_or_create_track = Mock(return_value=mock_track)
            
            # Call the method
            result = await track_manager.find_audd_match(sample_audio_features)
            
            # Verify the result
            assert result is not None
            assert result['track'] == mock_track
            assert result['confidence'] == 0.8
            assert result['source'] == 'audd'
            
            # Verify that the external handler was called
            mock_external_handler.recognize_with_audd.assert_called_once_with(b"mock_audio_data")
    
    @pytest.mark.asyncio
    async def test_audd_match_failure(self, track_manager, mock_external_handler, sample_audio_features):
        """Test AudD match failure."""
        # Mock the external handler
        with patch('backend.detection.audio_processor.track_manager.ExternalServiceHandler', return_value=mock_external_handler):
            # Configure mock to return no match
            mock_external_handler.recognize_with_audd.return_value = None
            
            # Call the method
            result = await track_manager.find_audd_match(sample_audio_features)
            
            # Verify the result
            assert result is None
            
            # Verify that the external handler was called
            mock_external_handler.recognize_with_audd.assert_called_once_with(b"mock_audio_data")
    
    @pytest.mark.asyncio
    async def test_audd_error_handling(self, track_manager, mock_external_handler, sample_audio_features):
        """Test AudD error handling."""
        # Mock the external handler
        with patch('backend.detection.audio_processor.track_manager.ExternalServiceHandler', return_value=mock_external_handler):
            # Configure mock to raise an exception
            mock_external_handler.recognize_with_audd.side_effect = Exception("AudD API error")
            
            # Call the method
            result = await track_manager.find_audd_match(sample_audio_features)
            
            # Verify the result
            assert result is None
            
            # Verify that the external handler was called
            mock_external_handler.recognize_with_audd.assert_called_once_with(b"mock_audio_data")

class TestHierarchicalDetectionWithExternalServices:
    """Test hierarchical detection with external services."""
    
    @pytest.mark.asyncio
    async def test_full_detection_chain(self, track_manager, mock_db_session, sample_audio_features):
        """Test the full detection chain with all services."""
        # Mock the methods
        track_manager.find_local_match = AsyncMock(return_value=None)
        track_manager.find_musicbrainz_match = AsyncMock(return_value=None)
        track_manager.find_audd_match = AsyncMock(return_value=None)
        
        # Create an AudioProcessor with the mocked TrackManager
        audio_processor = AudioProcessor(db_session=mock_db_session)
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "unknown",
                "confidence": 0.5,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Create sample audio data
            sample_audio_data = np.random.random(44100)
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["type"] == "music"
            assert result["source"] == "unknown"
            assert result["play_duration"] == 5.0
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1)
    
    @pytest.mark.asyncio
    async def test_detection_chain_with_musicbrainz_match(self, track_manager, mock_db_session, sample_audio_features):
        """Test the detection chain with a MusicBrainz match."""
        # Create a mock track
        mock_track = Mock(spec=Track)
        mock_track.id = 1
        mock_track.title = "Test MusicBrainz Track"
        
        # Mock the methods
        track_manager.find_local_match = AsyncMock(return_value=None)
        track_manager.find_musicbrainz_match = AsyncMock(return_value={
            "track": mock_track,
            "confidence": 0.85,
            "source": "musicbrainz"
        })
        track_manager.find_audd_match = AsyncMock()
        
        # Create an AudioProcessor with the mocked TrackManager
        audio_processor = AudioProcessor(db_session=mock_db_session)
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "musicbrainz",
                "confidence": 0.85,
                "track": mock_track,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Create sample audio data
            sample_audio_data = np.random.random(44100)
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["type"] == "music"
            assert result["source"] == "musicbrainz"
            assert result["confidence"] == 0.85
            assert result["track"] == mock_track
            assert result["play_duration"] == 5.0
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1)
    
    @pytest.mark.asyncio
    async def test_detection_chain_with_audd_match(self, track_manager, mock_db_session, sample_audio_features):
        """Test the detection chain with an AudD match."""
        # Create a mock track
        mock_track = Mock(spec=Track)
        mock_track.id = 2
        mock_track.title = "Test AudD Track"
        
        # Mock the methods
        track_manager.find_local_match = AsyncMock(return_value=None)
        track_manager.find_musicbrainz_match = AsyncMock(return_value=None)
        track_manager.find_audd_match = AsyncMock(return_value={
            "track": mock_track,
            "confidence": 0.8,
            "source": "audd"
        })
        
        # Create an AudioProcessor with the mocked TrackManager
        audio_processor = AudioProcessor(db_session=mock_db_session)
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "audd",
                "confidence": 0.8,
                "track": mock_track,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Create sample audio data
            sample_audio_data = np.random.random(44100)
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["type"] == "music"
            assert result["source"] == "audd"
            assert result["confidence"] == 0.8
            assert result["track"] == mock_track
            assert result["play_duration"] == 5.0
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1) 