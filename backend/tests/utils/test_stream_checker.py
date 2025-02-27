"""Tests for the StreamChecker utility."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from datetime import datetime, timedelta
import asyncio
from aioresponses import aioresponses
from utils.streams.stream_checker import StreamChecker

# Mock Redis configuration
with patch('backend.utils.streams.redis_config.get_redis', new_callable=AsyncMock) as mock_redis:
    mock_redis.return_value = AsyncMock()
    from backend.utils.streams.stream_checker import StreamChecker

TEST_STREAM_URL = 'http://test-stream.com/stream'

@pytest.fixture
async def test_server():
    """Create a test server."""
    app = web.Application()
    
    async def handle_head(request):
        return web.Response(
            status=200,
            headers={
                'Content-Type': 'audio/mpeg',
                'icy-name': 'Test Radio',
                'icy-genre': 'Test Genre'
            }
        )
        
    async def handle_get(request):
        return web.Response(
            status=200,
            headers={
                'Content-Type': 'audio/mpeg',
                'icy-name': 'Test Radio',
                'icy-genre': 'Test Genre'
            }
        )
        
    app.router.add_head('/stream', handle_head)
    app.router.add_get('/stream', handle_get)
    
    server = TestServer(app)
    await server.start_server()
    
    yield server
    
    await server.close()

@pytest.fixture
async def test_client(test_server):
    """Create a test client."""
    client = TestClient(test_server)
    await client.start_server()
    
    yield client
    
    await client.close()

@pytest.fixture
def mock_response_headers():
    return {
        'icy-name': 'Test Radio',
        'icy-description': 'Test Description',
        'icy-genre': 'Test Genre',
        'icy-br': '128'
    }

@pytest.fixture
def stream_checker():
    return StreamChecker(timeout=1, max_retries=2)

@pytest.mark.asyncio
async def test_check_stream_availability_success(stream_checker):
    try:
        with aioresponses() as m:
            m.head(TEST_STREAM_URL, status=200, headers={'Content-Type': 'audio/mpeg'})
            result = await stream_checker.check_stream_availability(TEST_STREAM_URL)
            assert result['is_available'] is True
            assert result['is_audio_stream'] is True
            assert result['status_code'] == 200
    finally:
        await stream_checker.close()

@pytest.mark.asyncio
async def test_check_stream_availability_timeout(stream_checker):
    try:
        with aioresponses() as m:
            m.head(TEST_STREAM_URL, timeout=True)
            result = await stream_checker.check_stream_availability(TEST_STREAM_URL)
            assert result['is_available'] is False
            assert result['error'] == 'timeout'
            assert result['status_code'] == 408
    finally:
        await stream_checker.close()

@pytest.mark.asyncio
async def test_check_stream_availability_error(stream_checker):
    try:
        with aioresponses() as m:
            m.head(TEST_STREAM_URL, exception=aiohttp.ClientError())
            result = await stream_checker.check_stream_availability(TEST_STREAM_URL)
            assert result['is_available'] is False
            assert result['error'] == 'connection_error'
            assert result['status_code'] == 503
    finally:
        await stream_checker.close()

@pytest.mark.asyncio
async def test_get_stream_metadata_success(stream_checker, mock_response_headers):
    try:
        with aioresponses() as m:
            m.get(TEST_STREAM_URL, headers=mock_response_headers)
            metadata = await stream_checker.get_stream_metadata(TEST_STREAM_URL)
            assert metadata is not None
            assert metadata['name'] == 'Test Radio'
            assert metadata['description'] == 'Test Description'
            assert metadata['genre'] == 'Test Genre'
            assert metadata['bitrate'] == '128'
    finally:
        await stream_checker.close()

@pytest.mark.asyncio
async def test_get_stream_metadata_no_metadata(stream_checker):
    try:
        with aioresponses() as m:
            m.get(TEST_STREAM_URL, headers={})
            metadata = await stream_checker.get_stream_metadata(TEST_STREAM_URL)
            assert metadata is None
    finally:
        await stream_checker.close()

@pytest.mark.asyncio
async def test_health_metrics_calculation(stream_checker):
    try:
        with aioresponses() as m:
            # Mock 3 successful checks and 2 failed checks
            m.head(TEST_STREAM_URL, status=200, headers={'Content-Type': 'audio/mpeg'})
            m.head(TEST_STREAM_URL, status=200, headers={'Content-Type': 'audio/mpeg'})
            m.head(TEST_STREAM_URL, timeout=True)
            m.head(TEST_STREAM_URL, status=200, headers={'Content-Type': 'audio/mpeg'})
            m.head(TEST_STREAM_URL, timeout=True)
            
            for _ in range(5):
                await stream_checker.check_stream_availability(TEST_STREAM_URL)
            
            metrics = stream_checker.get_health_metrics(TEST_STREAM_URL)
            assert metrics['uptime_percentage'] == 60.0  # 3/5 * 100
            assert metrics['average_latency'] >= 0
            assert metrics['checks_count'] == 5
            assert isinstance(metrics['last_check'], datetime)
    finally:
        await stream_checker.close()

@pytest.mark.asyncio
async def test_monitor_stream_health(stream_checker):
    try:
        with aioresponses() as m:
            # Mock multiple successful responses for the duration of monitoring
            m.head(TEST_STREAM_URL, repeat=True, status=200, headers={'Content-Type': 'audio/mpeg'})
            
            # Create a task that will run for a short time
            monitor_task = asyncio.create_task(
                stream_checker.monitor_stream_health(TEST_STREAM_URL, interval=0.1)
            )
            
            # Let it run for a bit
            await asyncio.sleep(0.3)  # Increased sleep time to ensure multiple checks
            
            # Cancel the task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

            # Get and verify metrics
            metrics = stream_checker.get_health_metrics(TEST_STREAM_URL)
            assert metrics['checks_count'] >= 2  # Should have at least 2 checks
            assert metrics['uptime_percentage'] == 100.0
            assert metrics['average_latency'] >= 0
    finally:
        await stream_checker.close()

@pytest.mark.asyncio
async def test_health_history_limit(stream_checker):
    try:
        with aioresponses() as m:
            # Mock 150 successful checks
            for _ in range(150):
                m.head(TEST_STREAM_URL, status=200, headers={'Content-Type': 'audio/mpeg'})
                await stream_checker.check_stream_availability(TEST_STREAM_URL)
            
            # Verify that history is limited to 100 entries
            assert len(stream_checker._health_history[TEST_STREAM_URL]) == 100
    finally:
        await stream_checker.close() 