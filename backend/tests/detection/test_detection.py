"""Tests for the detection module."""

import json
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.detection.audio_processor import AudioProcessor
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import SessionLocal
from backend.models.models import RadioStation, StationStatus, Track, TrackDetection
from backend.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)


@pytest.fixture
def mock_db_session():
    """Fixture for mocking database session"""
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.all.return_value = [
        RadioStation(
            id=1,
            name="Test Station",
            stream_url="http://test.stream",
            status=StationStatus.active,
            is_active=True,
        )
    ]
    return mock_session


@pytest.fixture
def audio_processor(mock_db_session):
    """Create an AudioProcessor instance for testing."""
    return AudioProcessor(db_session=mock_db_session)


@pytest.fixture
def track_manager(mock_db_session):
    """Create a TrackManager instance for testing."""
    return TrackManager(db_session=mock_db_session)


@pytest.fixture
def mock_audio_stream():
    """Create a mock audio stream for testing."""
    return np.random.random(44100 * 10)  # 10 seconds of audio


@pytest.fixture
def mock_music_recognizer():
    """Mock music recognition service."""
    mock = Mock()
    mock.recognize.return_value = {
        "success": True,
        "track": {"title": "Test Track", "artist": "Test Artist", "confidence": 0.95},
    }
    return mock


# Main Detection Pipeline Tests
@pytest.mark.asyncio
async def test_detection_pipeline(audio_processor, track_manager, mock_audio_stream):
    """Test the complete detection pipeline."""
    # Process audio stream
    is_music, confidence = await audio_processor.process_stream(mock_audio_stream)
    assert isinstance(is_music, bool)
    assert 0 <= confidence <= 1

    if is_music and confidence > 0.5:
        # Extract features
        features = audio_processor.extract_features(mock_audio_stream)
        assert isinstance(features, dict)
        assert all(key in features for key in ["mfcc", "spectral_contrast", "chroma"])

        # Find match
        match = await track_manager.find_local_match(features)
        assert match is None or isinstance(match, dict)


@pytest.mark.asyncio
async def test_detection_with_speech(audio_processor, mock_audio_stream):
    """Test detection with speech audio."""
    # Modify audio to simulate speech
    speech_audio = mock_audio_stream * 0.5  # Lower amplitude

    is_music, confidence = await audio_processor.process_stream(speech_audio)
    assert not is_music
    assert confidence < 0.5


@pytest.mark.asyncio
async def test_detection_with_invalid_stream():
    """Test detection with invalid audio stream."""
    with pytest.raises(ValueError):
        await audio_processor.process_stream(np.array([]))


# Performance and Resource Tests
@pytest.mark.asyncio
async def test_detection_performance(audio_processor):
    """Test detection performance."""
    # Generate large audio stream
    large_stream = np.random.random(44100 * 30)  # 30 seconds

    start_time = datetime.now()
    await audio_processor.process_stream(large_stream)
    duration = (datetime.now() - start_time).total_seconds()

    assert duration < 5.0  # Should process within 5 seconds


@pytest.mark.asyncio
async def test_detection_memory_usage(audio_processor):
    """Test memory usage during detection."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Process multiple streams
    for _ in range(5):
        stream = np.random.random(44100 * 10)
        await audio_processor.process_stream(stream)

    final_memory = process.memory_info().rss
    memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

    assert memory_increase < 100  # Should use less than 100MB additional memory


@pytest.mark.asyncio
async def test_concurrent_detections(audio_processor):
    """Test handling multiple detections concurrently."""
    import asyncio

    streams = [np.random.random(44100 * 5) for _ in range(3)]
    tasks = [audio_processor.process_stream(stream) for stream in streams]

    results = await asyncio.gather(*tasks)
    assert len(results) == 3
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


# Edge Cases
@pytest.mark.asyncio
async def test_detection_with_noise(audio_processor):
    """Test detection with noisy audio."""
    noise = np.random.normal(0, 1, 44100 * 5)
    is_music, confidence = await audio_processor.process_stream(noise)
    assert not is_music
    assert confidence < 0.3


@pytest.mark.asyncio
async def test_detection_with_silence(audio_processor):
    """Test detection with silent audio."""
    silence = np.zeros(44100 * 5)
    is_music, confidence = await audio_processor.process_stream(silence)
    assert not is_music
    assert confidence < 0.1


# Main Function Tests
@pytest.mark.asyncio
async def test_main_successful_detection(mock_db_session, mock_music_recognizer, mock_audio_stream):
    """Test successful detection in main function."""
    with patch("detection.detect_music.get_db", return_value=mock_db_session):
        with patch("detection.detect_music.MusicRecognizer", return_value=mock_music_recognizer):
            result = await main()
            assert result["success"]
            assert "detections" in result
            assert len(result["detections"]) > 0


@pytest.mark.asyncio
async def test_main_no_active_stations(mock_db_session):
    """Test main function with no active stations."""
    mock_db_session.query.return_value.filter.return_value.all.return_value = []
    with patch("detection.detect_music.get_db", return_value=mock_db_session):
        result = await main()
        assert not result["success"]
        assert "error" in result
        assert "No active stations" in result["error"]


@pytest.mark.asyncio
async def test_main_handles_processing_error(mock_db_session, mock_music_recognizer):
    """Test error handling in main function."""
    mock_music_recognizer.recognize.side_effect = Exception("Processing error")
    with patch("detection.detect_music.get_db", return_value=mock_db_session):
        with patch("detection.detect_music.MusicRecognizer", return_value=mock_music_recognizer):
            result = await main()
            assert not result["success"]
            assert "error" in result
            assert "Processing error" in result["error"]
