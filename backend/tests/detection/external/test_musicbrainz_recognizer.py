"""Tests for the MusicBrainz recognizer module."""

import io
import logging
import os
import wave
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import acoustid
import musicbrainzngs
import numpy as np
import pytest
from pydub import AudioSegment
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.detection.audio_processor.external_services import ExternalServiceHandler
from backend.detection.audio_processor.fingerprint import AudioFingerprinter
from backend.detection.audio_processor.local_detection import LocalDetector
from backend.detection.external.musicbrainz_recognizer import MusicBrainzRecognizer


@pytest.fixture
def mock_audio_data():
    """Create mock audio data for testing."""
    # Generate a simple sine wave
    sample_rate = 44100  # Hz
    duration = 1.0  # seconds
    freq = 440.0  # Hz
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    samples = np.sin(2 * np.pi * freq * t)

    # Convert to 16-bit PCM
    samples = (samples * 32767).astype(np.int16)

    # Create WAV data in memory
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())

    # Get the WAV data as bytes
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def mock_settings():
    """Create mock settings with valid API keys."""
    settings = MagicMock(spec=Settings)
    settings.ACOUSTID_API_KEY = "test_acoustid_key"
    settings.AUDD_API_KEY = "test_audd_key"
    settings.MUSICBRAINZ_APP_NAME = "test_app"
    settings.MUSICBRAINZ_VERSION = "1.0"
    settings.MUSICBRAINZ_CONTACT = "test@test.com"
    settings.MIN_CONFIDENCE_THRESHOLD = 0.8
    settings.ACOUSTID_CONFIDENCE_THRESHOLD = 0.7
    settings.AUDD_CONFIDENCE_THRESHOLD = 0.6
    settings.LOCAL_CONFIDENCE_THRESHOLD = 0.8
    return settings


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_local_detector(mock_db_session):
    """Create a mock local detector."""
    detector = MagicMock(spec=LocalDetector)
    detector.search_local = MagicMock()
    return detector


@pytest.fixture
def mock_external_handler(mock_db_session):
    """Create a mock external service handler."""
    handler = MagicMock(spec=ExternalServiceHandler)
    handler.recognize_with_musicbrainz = MagicMock()
    handler.recognize_with_audd = MagicMock()
    return handler


def test_init_with_missing_acoustid_key(mock_db_session):
    """Test initialization with missing ACOUSTID_API_KEY."""
    with patch("backend.utils.musicbrainz_recognizer.Settings") as mock_settings:
        mock_settings.return_value.ACOUSTID_API_KEY = None
        mock_settings.return_value.AUDD_API_KEY = "test_audd_key"

        with pytest.raises(ValueError) as exc_info:
            MusicBrainzRecognizer(mock_db_session)
        assert "ACOUSTID_API_KEY est requis" in str(exc_info.value)


def test_init_with_missing_audd_key(mock_db_session):
    """Test initialization with missing AUDD_API_KEY."""
    with patch("backend.utils.musicbrainz_recognizer.Settings") as mock_settings:
        mock_settings.return_value.ACOUSTID_API_KEY = "test_acoustid_key"
        mock_settings.return_value.AUDD_API_KEY = None

        with pytest.raises(ValueError) as exc_info:
            MusicBrainzRecognizer(mock_db_session)
        assert "AUDD_API_KEY est requis" in str(exc_info.value)


def test_init_with_valid_keys(mock_settings, mock_db_session):
    """Test successful initialization with valid API keys."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer(mock_db_session)
        assert recognizer.acoustid_api_key == "test_acoustid_key"
        assert isinstance(recognizer.local_detector, LocalDetector)
        assert isinstance(recognizer.external_handler, ExternalServiceHandler)


@patch("librosa.feature.spectral_centroid")
@patch("librosa.feature.rms")
@patch("librosa.feature.zero_crossing_rate")
def test_analyze_audio_features(mock_zcr, mock_rms, mock_cent, mock_settings, mock_audio_data):
    """Test audio feature analysis."""
    mock_zcr.return_value = np.array([[0.1]])
    mock_rms.return_value = np.array([[0.5]])
    mock_cent.return_value = np.array([[1000]])

    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer()
        features = recognizer._analyze_audio_features(mock_audio_data)

        assert "centroid_mean" in features
        assert "zcr_mean" in features
        assert "rms_mean" in features
        assert "music_likelihood" in features
        assert isinstance(features["music_likelihood"], float)
        assert 0 <= features["music_likelihood"] <= 100


@pytest.mark.asyncio
async def test_recognize_from_audio_data_not_music(mock_settings):
    """Test rejection of non-musical audio."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer()
        with patch.object(recognizer, "_analyze_audio_features") as mock_analyze:
            mock_analyze.return_value = {"music_likelihood": 50}  # Below threshold
            result = await recognizer.recognize_from_audio_data(b"test_data")
            assert "error" in result
            assert "not appear to be music" in result["error"]


@pytest.mark.asyncio
async def test_recognize_from_audio_data_local_success(
    mock_settings, mock_db_session, mock_local_detector, mock_audio_data
):
    """Test successful local detection."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer(mock_db_session)
        recognizer.local_detector = mock_local_detector

        with patch.object(recognizer, "_analyze_audio_features") as mock_analyze:
            mock_analyze.return_value = {"music_likelihood": 90}
            mock_local_detector.search_local.return_value = {
                "title": "Test Track",
                "artist": "Test Artist",
                "confidence": 0.95,
            }

            result = await recognizer.recognize_from_audio_data(mock_audio_data)
            assert "error" not in result
            assert result["title"] == "Test Track"
            assert result["confidence"] >= mock_settings.LOCAL_CONFIDENCE_THRESHOLD


@pytest.mark.asyncio
async def test_recognize_from_audio_data_acoustid_success(
    mock_settings, mock_db_session, mock_local_detector, mock_external_handler, mock_audio_data
):
    """Test successful AcoustID/MusicBrainz recognition."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer(mock_db_session)
        recognizer.local_detector = mock_local_detector
        recognizer.external_handler = mock_external_handler

        with patch.object(recognizer, "_analyze_audio_features") as mock_analyze:
            mock_analyze.return_value = {"music_likelihood": 90}
            mock_local_detector.search_local.return_value = None

            # Configure async mock for MusicBrainz recognition
            async def mock_musicbrainz_coro():
                return {"title": "AcoustID Track", "artist": "AcoustID Artist", "confidence": 0.8}

            mock_external_handler.recognize_with_musicbrainz.return_value = mock_musicbrainz_coro()

            result = await recognizer.recognize_from_audio_data(mock_audio_data)
            assert "error" not in result
            assert result["title"] == "AcoustID Track"
            assert result["confidence"] >= mock_settings.ACOUSTID_CONFIDENCE_THRESHOLD


@pytest.mark.asyncio
async def test_recognize_from_audio_data_audd_success(
    mock_settings, mock_db_session, mock_local_detector, mock_external_handler, mock_audio_data
):
    """Test successful Audd recognition."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer(mock_db_session)
        recognizer.local_detector = mock_local_detector
        recognizer.external_handler = mock_external_handler

        with patch.object(recognizer, "_analyze_audio_features") as mock_analyze:
            mock_analyze.return_value = {"music_likelihood": 90}
            mock_local_detector.search_local.return_value = None
            mock_external_handler.recognize_with_musicbrainz.return_value = None

            # Configure async mock for Audd recognition
            async def mock_audd_coro():
                return {"title": "Audd Track", "artist": "Audd Artist", "confidence": 0.7}

            mock_external_handler.recognize_with_audd.return_value = mock_audd_coro()

            result = await recognizer.recognize_from_audio_data(mock_audio_data)
            assert "error" not in result
            assert result["title"] == "Audd Track"
            assert result["confidence"] >= mock_settings.AUDD_CONFIDENCE_THRESHOLD


@pytest.mark.asyncio
async def test_recognize_from_audio_data_all_services_fail(
    mock_settings, mock_db_session, mock_local_detector, mock_external_handler, mock_audio_data
):
    """Test handling when all services fail."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer(mock_db_session)
        recognizer.local_detector = mock_local_detector
        recognizer.external_handler = mock_external_handler

        with patch.object(recognizer, "_analyze_audio_features") as mock_analyze:
            mock_analyze.return_value = {"music_likelihood": 90}
            mock_local_detector.search_local.return_value = None
            mock_external_handler.recognize_with_musicbrainz.return_value = None
            mock_external_handler.recognize_with_audd.return_value = None

            result = await recognizer.recognize_from_audio_data(mock_audio_data)
            assert "error" in result
            assert "All detection methods failed" in result["error"]


@pytest.mark.asyncio
async def test_recognize_from_audio_data_low_confidence_results(
    mock_settings, mock_db_session, mock_local_detector, mock_external_handler, mock_audio_data
):
    """Test handling of low confidence results from all services."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer(mock_db_session)
        recognizer.local_detector = mock_local_detector
        recognizer.external_handler = mock_external_handler

        with patch.object(recognizer, "_analyze_audio_features") as mock_analyze:
            mock_analyze.return_value = {"music_likelihood": 90}

            # Configure all services to return low confidence results
            mock_local_detector.search_local.return_value = {
                "title": "Local Track",
                "artist": "Local Artist",
                "confidence": 0.5,  # Below LOCAL_CONFIDENCE_THRESHOLD
            }

            async def mock_musicbrainz_coro():
                return {
                    "title": "MusicBrainz Track",
                    "artist": "MusicBrainz Artist",
                    "confidence": 0.4,  # Below ACOUSTID_CONFIDENCE_THRESHOLD
                }

            mock_external_handler.recognize_with_musicbrainz.return_value = mock_musicbrainz_coro()

            async def mock_audd_coro():
                return {
                    "title": "Audd Track",
                    "artist": "Audd Artist",
                    "confidence": 0.3,  # Below AUDD_CONFIDENCE_THRESHOLD
                }

            mock_external_handler.recognize_with_audd.return_value = mock_audd_coro()

            result = await recognizer.recognize_from_audio_data(mock_audio_data)
            assert "error" in result
            assert "low confidence results" in result["error"]


@pytest.mark.asyncio
async def test_service_error_handling(
    mock_settings, mock_db_session, mock_local_detector, mock_external_handler, mock_audio_data
):
    """Test handling of service errors."""
    with patch("backend.utils.musicbrainz_recognizer.Settings", return_value=mock_settings):
        recognizer = MusicBrainzRecognizer(mock_db_session)
        recognizer.local_detector = mock_local_detector
        recognizer.external_handler = mock_external_handler

        with patch.object(recognizer, "_analyze_audio_features") as mock_analyze:
            mock_analyze.return_value = {"music_likelihood": 90}
            mock_local_detector.search_local.side_effect = Exception("Local detection error")
            mock_external_handler.recognize_with_musicbrainz.side_effect = Exception(
                "AcoustID error"
            )
            mock_external_handler.recognize_with_audd.side_effect = Exception("Audd error")

            result = await recognizer.recognize_from_audio_data(mock_audio_data)
            assert "error" in result
            assert "All detection methods failed" in result["error"]
