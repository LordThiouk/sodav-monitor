"""Tests for the external services module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import os
import aiohttp
import musicbrainzngs
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.orm import Session
from backend.detection.audio_processor.external_services import ExternalServiceHandler, MusicBrainzService, AuddService
from backend.detection.audio_processor.audio_analysis import AudioAnalyzer

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
def mock_audio_data():
    """Create mock audio data for testing."""
    return b"mock_audio_data"

@pytest.fixture
def mock_large_audio_data():
    """Create mock large audio data for testing."""
    return b"mock_audio_data" * 1000  # Simulate 1MB audio data

@pytest.fixture
def handler(mock_db_session):
    """Create an ExternalServiceHandler instance for testing."""
    return ExternalServiceHandler(
        db_session=mock_db_session,
        audd_api_key='test_audd_key'
    )

@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""
    mock = AsyncMock()
    mock.status = 200
    mock.json = AsyncMock(return_value={'status': 'success'})
    return mock

class TestServiceInitialization:
    """Test service initialization and configuration."""

    def test_initialize_with_valid_keys(self, handler):
        """Test initialization with valid API keys."""
        handler.initialize()
        assert handler.initialized
        assert handler.audd_api_key == 'test_audd_key'

    def test_initialize_without_keys(self, mock_db_session):
        """Test initialization without API keys."""
        with patch.dict('os.environ', {}, clear=True):  # Clear all environment variables
            handler = ExternalServiceHandler(db_session=mock_db_session, audd_api_key=None)
            handler.initialize()
            assert handler.initialized
            assert handler.audd_api_key is None

class TestMusicBrainzIntegration:
    """Test MusicBrainz integration."""

    @pytest.mark.asyncio
    async def test_musicbrainz_success(self, handler, mock_audio_data):
        """Test successful MusicBrainz recognition."""
        mock_features = {'duration': 180}
        mock_response = {
            'recordings': [{
                'id': 'mb-123',
                'title': 'MB Track',
                'artist-credit': [{'name': 'MB Artist'}],
                'duration': 180000  # milliseconds
            }]
        }
        
        with patch.object(handler.audio_analyzer, 'extract_features', return_value=mock_features):
            with patch.object(musicbrainzngs, 'search_recordings', return_value=mock_response):
                result = await handler.recognize_with_musicbrainz(mock_audio_data)
                assert result is not None
                assert result['title'] == 'MB Track'
                assert result['artist'] == 'MB Artist'
                assert result['confidence'] >= 0.7

    @pytest.mark.asyncio
    async def test_musicbrainz_rate_limit(self, handler, mock_audio_data):
        """Test MusicBrainz rate limit handling."""
        mock_features = {'duration': 180}
        with patch.object(handler.audio_analyzer, 'extract_features', return_value=mock_features):
            with patch.object(musicbrainzngs, 'search_recordings') as mock_search:
                mock_search.side_effect = [
                    musicbrainzngs.WebServiceError('Rate limit exceeded'),
                    {
                        'recordings': [{
                            'id': 'mb-123',
                            'title': 'MB Track',
                            'artist-credit': [{'name': 'MB Artist'}],
                            'duration': 180000
                        }]
                    }
                ]
                result = await handler.recognize_with_musicbrainz(mock_audio_data)
                assert result is not None
                assert result['title'] == 'MB Track'

    @pytest.mark.asyncio
    async def test_musicbrainz_invalid_response(self, handler, mock_audio_data):
        """Test handling of invalid MusicBrainz responses."""
        mock_features = {'duration': 180}
        with patch.object(handler.audio_analyzer, 'extract_features', return_value=mock_features):
            with patch.object(musicbrainzngs, 'search_recordings', return_value={'recordings': []}):
                result = await handler.recognize_with_musicbrainz(mock_audio_data)
                assert result is None

class TestAuddIntegration:
    """Test Audd integration."""

    @pytest.mark.asyncio
    async def test_audd_success(self, handler, mock_audio_data):
        """Test successful Audd recognition."""
        mock_response = {
            'status': 'success',
            'result': {
                'title': 'Audd Track',
                'artist': 'Audd Artist',
                'album': 'Audd Album',
                'release_date': '2024',
                'label': 'Test Label',
                'song_id': 'audd-123'
            }
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await handler.recognize_with_audd(mock_audio_data)
            assert result is not None
            assert result['title'] == 'Audd Track'
            assert result['artist'] == 'Audd Artist'

    @pytest.mark.asyncio
    async def test_audd_retry(self, handler, mock_audio_data):
        """Test Audd retry logic."""
        mock_response = {
            'status': 'success',
            'result': {
                'title': 'Retry Track',
                'artist': 'Retry Artist'
            }
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.side_effect = [
                aiohttp.ClientError(),
                AsyncMock(
                    status=200,
                    json=AsyncMock(return_value=mock_response)
                )
            ]
            
            result = await handler.recognize_with_audd(mock_audio_data)
            assert result is not None
            assert result['title'] == 'Retry Track'
            assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_audd_large_audio(self, handler, mock_large_audio_data):
        """Test handling of large audio files."""
        mock_response = {
            'status': 'success',
            'result': {
                'title': 'Large Track',
                'artist': 'Test Artist'
            }
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await handler.recognize_with_audd(mock_large_audio_data)
            assert result is not None
            assert result['title'] == 'Large Track'

class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_network_errors(self, handler, mock_audio_data):
        """Test handling of network errors."""
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError()):
            result = await handler.recognize_with_audd(mock_audio_data)
            assert result is None

    @pytest.mark.asyncio
    async def test_timeout_handling(self, handler, mock_audio_data):
        """Test handling of timeouts."""
        with patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError()):
            result = await handler.recognize_with_audd(mock_audio_data)
            assert result is None

class TestPerformance:
    """Test performance aspects."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, handler, mock_audio_data):
        """Test handling of concurrent requests."""
        mock_response = {
            'status': 'success',
            'result': {
                'title': 'Test Track',
                'artist': 'Test Artist'
            }
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            tasks = [handler.recognize_with_audd(mock_audio_data) for _ in range(5)]
            results = await asyncio.gather(*tasks)
            assert len(results) == 5
            assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_memory_usage(self, handler, mock_large_audio_data):
        """Test memory usage during recognition."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        await handler.recognize_with_audd(mock_large_audio_data)
        
        final_memory = process.memory_info().rss
        memory_used = final_memory - initial_memory
        assert memory_used < 100 * 1024 * 1024  # Should use less than 100MB

    @pytest.mark.asyncio
    async def test_response_time(self, handler, mock_audio_data):
        """Test response time performance."""
        start_time = datetime.now()
        await handler.recognize_with_audd(mock_audio_data)
        duration = (datetime.now() - start_time).total_seconds()
        assert duration < 5.0  # Should complete within 5 seconds 