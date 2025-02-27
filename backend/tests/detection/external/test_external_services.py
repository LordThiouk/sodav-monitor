import pytest
from unittest.mock import patch, MagicMock
from aioresponses import aioresponses
import json

from backend.detection.audio_processor.external_services import (
    MusicBrainzService,
    AuddService,
    ExternalServiceError
)

@pytest.fixture
def mock_musicbrainz_service():
    return MusicBrainzService(api_key="test_key")

@pytest.fixture
def mock_audd_service():
    return AuddService(api_key="test_key")

@pytest.mark.asyncio
async def test_musicbrainz_successful_detection(mock_musicbrainz_service):
    """Test successful track detection using MusicBrainz."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.musicbrainz.org/v1/lookup",
            status=200,
            payload={
                "results": [{
                    "id": "test_id",
                    "title": "Test Track",
                    "artist": "Test Artist",
                    "score": 0.95
                }]
            }
        )
        
        result = await mock_musicbrainz_service.detect_track(b"audio_data")
        assert result["title"] == "Test Track"
        assert result["artist"] == "Test Artist"
        assert result["confidence"] == 0.95

@pytest.mark.asyncio
async def test_musicbrainz_no_results(mock_musicbrainz_service):
    """Test MusicBrainz detection with no results."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.musicbrainz.org/v1/lookup",
            status=200,
            payload={"results": []}
        )
        
        result = await mock_musicbrainz_service.detect_track(b"audio_data")
        assert result is None

@pytest.mark.asyncio
async def test_musicbrainz_api_error(mock_musicbrainz_service):
    """Test MusicBrainz API error handling."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.musicbrainz.org/v1/lookup",
            status=500,
            body="Internal Server Error"
        )
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await mock_musicbrainz_service.detect_track(b"audio_data")
        assert "MusicBrainz API error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_audd_successful_detection(mock_audd_service):
    """Test successful track detection using Audd."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.audd.io/",
            status=200,
            payload={
                "status": "success",
                "result": {
                    "title": "Test Track",
                    "artist": "Test Artist",
                    "score": 0.85
                }
            }
        )
        
        result = await mock_audd_service.detect_track(b"audio_data")
        assert result["title"] == "Test Track"
        assert result["artist"] == "Test Artist"
        assert result["confidence"] == 0.85

@pytest.mark.asyncio
async def test_audd_no_match(mock_audd_service):
    """Test Audd detection with no match."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.audd.io/",
            status=200,
            payload={
                "status": "success",
                "result": None
            }
        )
        
        result = await mock_audd_service.detect_track(b"audio_data")
        assert result is None

@pytest.mark.asyncio
async def test_audd_api_error(mock_audd_service):
    """Test Audd API error handling."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.audd.io/",
            status=500,
            body="Internal Server Error"
        )
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await mock_audd_service.detect_track(b"audio_data")
        assert "Audd API error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_audd_invalid_response(mock_audd_service):
    """Test Audd invalid response handling."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.audd.io/",
            status=200,
            payload={
                "status": "error",
                "error": "Invalid API key"
            }
        )
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await mock_audd_service.detect_track(b"audio_data")
        assert "Invalid API key" in str(exc_info.value)

@pytest.mark.asyncio
async def test_musicbrainz_timeout(mock_musicbrainz_service):
    """Test MusicBrainz timeout handling."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.musicbrainz.org/v1/lookup",
            timeout=True
        )
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await mock_musicbrainz_service.detect_track(b"audio_data")
        assert "MusicBrainz request timed out" in str(exc_info.value)

@pytest.mark.asyncio
async def test_audd_timeout(mock_audd_service):
    """Test Audd timeout handling."""
    with aioresponses() as mock_response:
        mock_response.post(
            "https://api.audd.io/",
            timeout=True
        )
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await mock_audd_service.detect_track(b"audio_data")
        assert "Audd request timed out" in str(exc_info.value)

@pytest.mark.asyncio
async def test_musicbrainz_retry_success(mock_musicbrainz_service):
    """Test MusicBrainz successful retry after failure."""
    with aioresponses() as mock_response:
        # First request fails
        mock_response.post(
            "https://api.musicbrainz.org/v1/lookup",
            status=500,
            body="Internal Server Error"
        )
        # Second request succeeds
        mock_response.post(
            "https://api.musicbrainz.org/v1/lookup",
            status=200,
            payload={
                "results": [{
                    "id": "test_id",
                    "title": "Test Track",
                    "artist": "Test Artist",
                    "score": 0.95
                }]
            }
        )
        
        result = await mock_musicbrainz_service.detect_track_with_retry(b"audio_data")
        assert result["title"] == "Test Track"
        assert result["artist"] == "Test Artist"
        assert result["confidence"] == 0.95

@pytest.mark.asyncio
async def test_audd_retry_success(mock_audd_service):
    """Test Audd successful retry after failure."""
    with aioresponses() as mock_response:
        # First request fails
        mock_response.post(
            "https://api.audd.io/",
            status=500,
            body="Internal Server Error"
        )
        # Second request succeeds
        mock_response.post(
            "https://api.audd.io/",
            status=200,
            payload={
                "status": "success",
                "result": {
                    "title": "Test Track",
                    "artist": "Test Artist",
                    "score": 0.85
                }
            }
        )
        
        result = await mock_audd_service.detect_track_with_retry(b"audio_data")
        assert result["title"] == "Test Track"
        assert result["artist"] == "Test Artist"
        assert result["confidence"] == 0.85 