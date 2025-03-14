"""Tests for middleware components."""

import asyncio
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.testclient import TestClient

from backend.core.config import get_settings
from backend.core.middleware.cache import CacheMiddleware, ResponseCache
from backend.core.middleware.rate_limit import RateLimiter, RateLimitMiddleware

settings = get_settings()


class AsyncContextManagerMock(AsyncMock):
    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


@pytest.fixture
async def redis_client():
    """Create a mock Redis client."""
    mock_redis = AsyncMock(spec=Redis)

    # Configure Redis methods
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=True)
    mock_redis.flushdb = AsyncMock(return_value=True)

    return mock_redis


@pytest.fixture
def app(redis_client):
    """Create FastAPI test app with middleware."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @app.post("/test")
    async def test_post_endpoint():
        return {"message": "test post"}

    @app.get("/cached")
    async def cached_endpoint():
        return {"data": "cached", "timestamp": datetime.now().isoformat()}

    app.add_middleware(RateLimitMiddleware, redis=redis_client)
    app.add_middleware(CacheMiddleware, redis=redis_client)

    return app


@pytest.fixture
def test_client(app):
    """Create test client."""
    return TestClient(app)


class TestRateLimiting:
    """Tests for rate limiting middleware."""

    async def test_rate_limit_not_exceeded(self, test_client, redis_client):
        """Test requests within rate limit."""
        # Configure mock to simulate requests under limit
        redis_client.incr = AsyncMock(return_value=1)

        for _ in range(settings.RATE_LIMIT_REQUESTS):
            response = test_client.get("/test")
            assert response.status_code == 200

    async def test_rate_limit_exceeded(self, test_client, redis_client):
        """Test exceeding rate limit."""
        # Configure mock to simulate exceeding limit
        redis_client.incr = AsyncMock(return_value=settings.RATE_LIMIT_REQUESTS + 1)

        response = test_client.get("/test")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    async def test_rate_limit_excluded_paths(self, test_client, redis_client):
        """Test excluded paths are not rate limited."""
        response = test_client.get("/docs")
        assert response.status_code == 200

        # Redis methods should not be called for excluded paths
        redis_client.incr.assert_not_called()
        redis_client.expire.assert_not_called()

    async def test_rate_limit_different_clients(self, test_client, redis_client):
        """Test rate limiting for different clients."""
        # Configure mock for first client
        request_count = 0

        def get_request_count(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            return request_count

        redis_client.incr = AsyncMock(side_effect=get_request_count)

        # First client uses some requests
        headers1 = {"X-API-Key": "client1"}
        for _ in range(settings.RATE_LIMIT_REQUESTS - 1):
            response = test_client.get("/test", headers=headers1)
            assert response.status_code == 200

        # Second client should have full quota
        headers2 = {"X-API-Key": "client2"}
        response = test_client.get("/test", headers=headers2)
        assert response.status_code == 200


class TestCaching:
    """Tests for caching middleware."""

    async def test_successful_cache(self, test_client, redis_client):
        """Test successful response caching."""
        test_data = {"data": "cached", "timestamp": datetime.now().isoformat()}

        # First request should not be cached
        redis_client.get = AsyncMock(return_value=None)
        response1 = test_client.get("/cached")
        assert response1.status_code == 200
        data1 = response1.json()

        # Second request should return cached response
        cached_response = {
            "content": data1,
            "status_code": 200,
            "headers": {"content-type": "application/json"},
        }
        redis_client.get = AsyncMock(return_value=json.dumps(cached_response))
        response2 = test_client.get("/cached")
        assert response2.status_code == 200
        data2 = response2.json()

        assert data1 == data2
        redis_client.setex.assert_called_once()

    async def test_cache_excluded_paths(self, test_client, redis_client):
        """Test paths excluded from caching."""
        # First request to excluded path
        response1 = test_client.get("/docs")
        assert response1.status_code == 200

        # Second request should not be cached
        response2 = test_client.get("/docs")
        assert response2.status_code == 200

        # Redis methods should not be called for excluded paths
        redis_client.get.assert_not_called()
        redis_client.setex.assert_not_called()

    async def test_cache_non_get_requests(self, test_client, redis_client):
        """Test non-GET requests are not cached."""
        # POST request should not be cached
        response1 = test_client.post("/test", json={"data": "test"})
        assert response1.status_code == 200

        # Redis methods should not be called for non-GET requests
        redis_client.get.assert_not_called()
        redis_client.setex.assert_not_called()

    async def test_cache_different_users(self, test_client, redis_client):
        """Test caching for different users."""
        test_data = {"data": "cached", "timestamp": datetime.now().isoformat()}

        # First user request
        redis_client.get = AsyncMock(return_value=None)
        headers1 = {"Authorization": "Bearer token1"}
        response1 = test_client.get("/cached", headers=headers1)
        assert response1.status_code == 200
        data1 = response1.json()

        # Second user should not get cached response
        headers2 = {"Authorization": "Bearer token2"}
        response2 = test_client.get("/cached", headers=headers2)
        assert response2.status_code == 200
        data2 = response2.json()

        assert data1 != data2


@pytest.mark.asyncio
async def test_redis_integration(redis_client):
    """Test Redis integration for middleware."""
    # Test rate limiter
    limiter = RateLimiter(redis_client)
    redis_client.incr = AsyncMock(return_value=1)

    is_limited, retry_after = await limiter.is_rate_limited("test_client")
    assert not is_limited
    assert retry_after is None

    # Test cache
    cache = ResponseCache(redis_client)
    test_data = {"test": "data"}

    # Test cache set
    await cache.set("test_key", test_data)
    redis_client.setex.assert_called_once()

    # Test cache get
    redis_client.get = AsyncMock(return_value=json.dumps(test_data))
    cached_data = await cache.get("test_key")
    assert cached_data == test_data

    # Test cache delete
    await cache.delete("test_key")
    redis_client.delete.assert_called_once()
