"""Tests for the local detection module."""

import hashlib
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from sqlalchemy.orm import Session

from backend.detection.audio_processor.local_detection import LocalDetector
from backend.models.models import Artist, Track, TrackDetection


@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = Mock(spec=Session)
    session.query = Mock(return_value=session)
    session.filter = Mock(return_value=session)
    session.first = Mock(return_value=None)
    return session


@pytest.fixture
def mock_audio_data():
    """Create mock audio data for testing."""
    return b"mock_audio_data"


@pytest.fixture
def detector(db_session):
    """Create a LocalDetector instance for testing."""
    return LocalDetector(db_session)


@pytest.mark.asyncio
async def test_initialize(detector):
    """Test detector initialization."""
    assert not detector.initialized
    await detector.initialize()
    assert detector.initialized


def test_calculate_audio_hash(detector, mock_audio_data):
    """Test audio hash calculation."""
    expected_hash = hashlib.sha256(mock_audio_data).hexdigest()
    calculated_hash = detector._calculate_audio_hash(mock_audio_data)
    assert calculated_hash == expected_hash


def test_get_cached_fingerprint_hit(detector):
    """Test getting cached fingerprint with a hit."""
    mock_detection = Mock(spec=TrackDetection)
    mock_detection.duration = 180.0
    mock_detection.fingerprint = "test_fingerprint"

    detector.db_session.query.return_value.filter.return_value.first.return_value = mock_detection

    result = detector._get_cached_fingerprint("test_hash")
    assert result == (180.0, "test_fingerprint")


def test_get_cached_fingerprint_miss(detector):
    """Test getting cached fingerprint with a miss."""
    detector.db_session.query.return_value.filter.return_value.first.return_value = None
    result = detector._get_cached_fingerprint("test_hash")
    assert result is None


@pytest.mark.asyncio
async def test_save_fingerprint(detector, mock_audio_data):
    """Test saving fingerprint to database."""
    mock_track = Mock(spec=Track)
    mock_track.id = 1

    mock_detection = Mock(spec=TrackDetection)

    with patch.object(
        detector.fingerprinter, "generate_fingerprint", return_value=(180.0, "test_fingerprint", {})
    ):
        with patch.object(detector.db_session, "add") as mock_add:
            await detector._save_fingerprint(mock_audio_data, mock_track)
            mock_add.assert_called_once()
            detector.db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_search_local_with_cache(detector, mock_audio_data):
    """Test local search with cached fingerprint."""
    mock_track = Mock(spec=Track)
    mock_track.id = 1
    mock_track.title = "Test Track"
    mock_track.artist = Mock(spec=Artist)
    mock_track.artist.name = "Test Artist"

    # Mock cached fingerprint
    with patch.object(
        detector, "_get_cached_fingerprint", return_value=(180.0, "test_fingerprint")
    ):
        # Mock database query
        mock_query = MagicMock()
        mock_query.all.return_value = [(mock_track, "test_fingerprint", 1)]
        detector.db_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value = (
            mock_query
        )

        # Mock fingerprint comparison
        with patch.object(detector.fingerprinter, "compare_fingerprints", return_value=0.9):
            result = await detector.search_local(mock_audio_data)

            assert result is not None
            assert result["title"] == "Test Track"
            assert result["artist"] == "Test Artist"
            assert result["confidence"] == 0.9
            assert result["source"] == "local"


@pytest.mark.asyncio
async def test_search_local_no_match(detector, mock_audio_data):
    """Test local search with no matches."""
    # Mock fingerprint generation
    with patch.object(
        detector.fingerprinter,
        "generate_fingerprint",
        return_value=(180.0, "test_fingerprint", None),
    ):
        # Mock empty database result
        mock_query = MagicMock()
        mock_query.all.return_value = []
        detector.db_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value = (
            mock_query
        )

        result = await detector.search_local(mock_audio_data)
        assert result is None


@pytest.mark.asyncio
async def test_search_local_low_confidence(detector, mock_audio_data):
    """Test local search with low confidence match."""
    mock_track = Mock(spec=Track)

    with patch.object(
        detector.fingerprinter,
        "generate_fingerprint",
        return_value=(180.0, "test_fingerprint", None),
    ):
        mock_query = MagicMock()
        mock_query.all.return_value = [(mock_track, "test_fingerprint", 1)]
        detector.db_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value = (
            mock_query
        )

        # Mock low confidence comparison
        with patch.object(
            detector.fingerprinter, "compare_fingerprints", return_value=0.7
        ):  # Below 0.8 threshold
            result = await detector.search_local(mock_audio_data)
            assert result is None


@pytest.mark.asyncio
async def test_error_handling(detector, mock_audio_data):
    """Test error handling during local search."""
    with patch.object(
        detector.fingerprinter, "generate_fingerprint", side_effect=Exception("Test error")
    ):
        result = await detector.search_local(mock_audio_data)
        assert result is None
