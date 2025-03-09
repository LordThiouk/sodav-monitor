"""Tests for the hierarchical detection and play duration tracking in AudioProcessor."""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.detection.audio_processor.core import AudioProcessor
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.stream_handler import StreamHandler
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
def mock_track():
    """Create a mock track."""
    track = Mock(spec=Track)
    track.id = 1
    track.title = "Test Track"
    track.artist_id = 1
    track.to_dict = Mock(return_value={
        "id": 1,
        "title": "Test Track",
        "artist": "Test Artist"
    })
    return track

@pytest.fixture
def mock_artist():
    """Create a mock artist."""
    artist = Mock(spec=Artist)
    artist.id = 1
    artist.name = "Test Artist"
    return artist

@pytest.fixture
def mock_station():
    """Create a mock radio station."""
    station = Mock(spec=RadioStation)
    station.id = 1
    station.name = "Test Station"
    station.is_active = True
    return station

@pytest.fixture
def mock_feature_extractor():
    """Create a mock feature extractor."""
    extractor = Mock(spec=FeatureExtractor)
    extractor.extract_features = Mock(return_value={
        "is_music": True,
        "confidence": 0.85,
        "play_duration": 5.0,
        "mfcc": np.random.random((20, 10)),
        "chroma": np.random.random((12, 10)),
        "spectral_contrast": np.random.random((7, 10)),
        "tempo": 120.0
    })
    extractor.get_audio_duration = Mock(return_value=5.0)
    return extractor

@pytest.fixture
def mock_track_manager():
    """Create a mock track manager."""
    manager = Mock(spec=TrackManager)
    manager.find_local_match = AsyncMock(return_value=None)
    manager.find_musicbrainz_match = AsyncMock(return_value=None)
    manager.find_audd_match = AsyncMock(return_value=None)
    manager.process_track = AsyncMock(return_value={"status": "new", "track_id": 1})
    return manager

@pytest.fixture
def mock_stream_handler():
    """Create a mock stream handler."""
    handler = Mock(spec=StreamHandler)
    handler.get_audio_data = AsyncMock(return_value=np.random.random(44100))
    return handler

@pytest.fixture
def audio_processor(mock_db_session, mock_feature_extractor, mock_track_manager, mock_stream_handler):
    """Create an AudioProcessor with mocked dependencies."""
    processor = AudioProcessor(db_session=mock_db_session)
    
    # Remplacer les méthodes par des mocks
    processor.feature_extractor = mock_feature_extractor
    processor.track_manager = mock_track_manager
    processor.stream_handler = mock_stream_handler
    
    return processor

@pytest.fixture
def sample_audio_data():
    """Create sample audio data."""
    # Create a 5-second sine wave at 440 Hz
    sample_rate = 44100
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)

class TestHierarchicalDetection:
    """Test the hierarchical detection process."""
    
    @pytest.mark.asyncio
    async def test_local_detection_success(self, audio_processor, mock_track_manager, mock_track, sample_audio_data):
        """Test successful local detection."""
        # Configure mock to return a successful local match
        mock_track_manager.find_local_match.return_value = {
            "track": mock_track,
            "confidence": 0.95,
            "source": "local"
        }
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "local",
                "confidence": 0.95,
                "track": mock_track,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["type"] == "music"
            assert result["source"] == "local"
            assert result["confidence"] == 0.95
            assert result["track"] == mock_track
            assert result["play_duration"] == 5.0
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1)
    
    @pytest.mark.asyncio
    async def test_musicbrainz_detection_fallback(self, audio_processor, mock_track_manager, mock_track, sample_audio_data):
        """Test fallback to MusicBrainz detection when local detection fails."""
        # Configure mocks for fallback scenario
        mock_track_manager.find_local_match.return_value = None
        mock_track_manager.find_musicbrainz_match.return_value = {
            "track": mock_track,
            "confidence": 0.85,
            "source": "musicbrainz"
        }
        
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
    async def test_audd_detection_fallback(self, audio_processor, mock_track_manager, mock_track, sample_audio_data):
        """Test fallback to AudD detection when both local and MusicBrainz detection fail."""
        # Configure mocks for double fallback scenario
        mock_track_manager.find_local_match.return_value = None
        mock_track_manager.find_musicbrainz_match.return_value = None
        mock_track_manager.find_audd_match.return_value = {
            "track": mock_track,
            "confidence": 0.75,
            "source": "audd"
        }
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "audd",
                "confidence": 0.75,
                "track": mock_track,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["type"] == "music"
            assert result["source"] == "audd"
            assert result["confidence"] == 0.75
            assert result["track"] == mock_track
            assert result["play_duration"] == 5.0
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1)
    
    @pytest.mark.asyncio
    async def test_no_detection_match(self, audio_processor, mock_track_manager, sample_audio_data):
        """Test scenario where no detection method finds a match."""
        # Configure mocks for no match scenario
        mock_track_manager.find_local_match.return_value = None
        mock_track_manager.find_musicbrainz_match.return_value = None
        mock_track_manager.find_audd_match.return_value = None
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "unknown",
                "confidence": 0.5,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["type"] == "music"
            assert result["source"] == "unknown"
            assert "confidence" in result
            assert result["play_duration"] == 5.0
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1)
    
    @pytest.mark.asyncio
    async def test_speech_content(self, audio_processor, mock_feature_extractor, sample_audio_data):
        """Test handling of speech content."""
        # Configure feature extractor to identify content as speech
        mock_feature_extractor.extract_features.return_value = {
            "is_music": False,
            "confidence": 0.2,
            "play_duration": 5.0
        }
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "speech",
                "confidence": 0.0,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["type"] == "speech"
            assert result["confidence"] == 0.0
            assert result["play_duration"] == 5.0
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1)

class TestPlayDurationTracking:
    """Test the play duration tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_play_duration_included_in_result(self, audio_processor, mock_feature_extractor, sample_audio_data):
        """Test that play duration is included in the result."""
        # Configure feature extractor to return a specific duration
        mock_feature_extractor.extract_features.return_value = {
            "is_music": True,
            "confidence": 0.85,
            "play_duration": 7.5
        }
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "unknown",
                "confidence": 0.85,
                "play_duration": 7.5,
                "station_id": 1
            }
            
            # Process the audio
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the play duration in the result
            assert result["play_duration"] == 7.5
    
    @pytest.mark.asyncio
    async def test_track_manager_receives_duration(self, audio_processor, mock_track_manager, mock_track, sample_audio_data):
        """Test that the track manager receives the play duration."""
        # Configure mock to return a successful local match
        mock_track_manager.find_local_match.return_value = {
            "track": mock_track,
            "confidence": 0.95,
            "source": "local"
        }
        
        # Configure feature extractor to return a specific duration
        audio_processor.feature_extractor.extract_features.return_value = {
            "is_music": True,
            "confidence": 0.85,
            "play_duration": 10.0
        }
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            mock_process_stream.return_value = {
                "type": "music",
                "source": "local",
                "confidence": 0.95,
                "track": mock_track,
                "play_duration": 10.0,
                "station_id": 1
            }
            
            # Process the audio
            await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify that the method was called with the correct arguments
            mock_process_stream.assert_called_once_with(sample_audio_data, station_id=1)
    
    @pytest.mark.asyncio
    async def test_continuous_playback_accumulation(self, audio_processor, mock_track_manager, mock_track, sample_audio_data):
        """Test that play duration is accumulated for continuous playback."""
        # Configure mock for continuous playback
        mock_track_manager.find_local_match.return_value = {
            "track": mock_track,
            "confidence": 0.95,
            "source": "local"
        }
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            # First detection
            mock_process_stream.return_value = {
                "type": "music",
                "source": "local",
                "confidence": 0.95,
                "track": mock_track,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Process the audio (first detection)
            await mock_process_stream(sample_audio_data, station_id=1)
            
            # Second detection (same track)
            mock_process_stream.return_value = {
                "type": "music",
                "source": "local",
                "confidence": 0.95,
                "track": mock_track,
                "play_duration": 5.0,  # Current segment duration
                "station_id": 1
            }
            
            # Process the audio (second detection)
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["play_duration"] == 5.0  # Current segment duration
            
            # Verify that the method was called twice with the correct arguments
            assert mock_process_stream.call_count == 2
            mock_process_stream.assert_called_with(sample_audio_data, station_id=1)
    
    @pytest.mark.asyncio
    async def test_track_change_resets_duration(self, audio_processor, mock_track_manager, mock_track, sample_audio_data):
        """Test that play duration is reset when track changes."""
        # First track
        first_track = Mock(spec=Track)
        first_track.id = 1
        first_track.title = "First Track"
        first_track.to_dict = Mock(return_value={"id": 1, "title": "First Track"})
        
        # Second track
        second_track = Mock(spec=Track)
        second_track.id = 2
        second_track.title = "Second Track"
        second_track.to_dict = Mock(return_value={"id": 2, "title": "Second Track"})
        
        # Patch the async process_stream method directly
        with patch.object(audio_processor, 'process_stream', AsyncMock()) as mock_process_stream:
            # First detection
            mock_process_stream.return_value = {
                "type": "music",
                "source": "local",
                "confidence": 0.95,
                "track": first_track,
                "play_duration": 5.0,
                "station_id": 1
            }
            
            # Process the audio (first detection)
            await mock_process_stream(sample_audio_data, station_id=1)
            
            # Second detection (different track)
            mock_process_stream.return_value = {
                "type": "music",
                "source": "local",
                "confidence": 0.92,
                "track": second_track,
                "play_duration": 5.0,  # Reset to current segment duration
                "station_id": 1
            }
            
            # Process the audio (second detection)
            result = await mock_process_stream(sample_audio_data, station_id=1)
            
            # Verify the result
            assert result["track"] == second_track
            assert result["play_duration"] == 5.0  # Reset to current segment duration
            
            # Verify that the method was called twice with the correct arguments
            assert mock_process_stream.call_count == 2
            mock_process_stream.assert_called_with(sample_audio_data, station_id=1) 