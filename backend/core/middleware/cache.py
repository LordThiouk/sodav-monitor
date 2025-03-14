"""Response caching middleware for FastAPI."""

import hashlib
import json
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import get_settings

settings = get_settings()


class ResponseCache:
    """Cache implementation using Redis."""

    def __init__(self, redis: Redis):
        """Initialize cache.

        Args:
            redis: Redis client instance
        """
        self.redis = redis
        self.ttl = settings.CACHE_TTL

    async def get(self, key: str) -> Optional[dict]:
        """Get cached response.

        Args:
            key: Cache key

        Returns:
            Cached response data or None if not found
        """
        data = await self.redis.get(f"{settings.CACHE_PREFIX}cache:{key}")
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, response_data: dict):
        """Cache response data.

        Args:
            key: Cache key
            response_data: Response data to cache
        """
        await self.redis.setex(
            f"{settings.CACHE_PREFIX}cache:{key}", self.ttl, json.dumps(response_data)
        )

    async def delete(self, key: str):
        """Delete cached response.

        Args:
            key: Cache key
        """
        await self.redis.delete(f"{settings.CACHE_PREFIX}cache:{key}")


class CacheMiddleware:
    """Middleware for response caching."""

    def __init__(self, app: ASGIApp, redis: Redis):
        """Initialize middleware.

        Args:
            app: ASGI application instance
            redis: Redis client instance
        """
        self.app = app
        self.cache = ResponseCache(redis)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """Process request with caching.

        Args:
            scope: ASGI connection scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        if not settings.CACHE_ENABLED:
            await self.app(scope, receive, send)
            return

        # Skip caching for non-GET requests
        if request.method != "GET":
            await self.app(scope, receive, send)
            return

        # Skip caching for excluded paths
        if self._should_skip_caching(request.url.path):
            await self.app(scope, receive, send)
            return

        # Generate cache key
        cache_key = self._generate_cache_key(request)

        # Try to get from cache
        cached_data = await self.cache.get(cache_key)
        if cached_data is not None:
            response = JSONResponse(
                content=cached_data["content"],
                status_code=cached_data["status_code"],
                headers=cached_data["headers"],
            )
            await response(scope, receive, send)
            return

        # Intercept the response to cache it
        async def send_wrapper(message: dict):
            if message["type"] == "http.response.start":
                self.status_code = message["status"]
                self.headers = {
                    k.decode(): v.decode() if isinstance(v, bytes) else v
                    for k, v in message.get("headers", [])
                }
            elif message["type"] == "http.response.body":
                if (
                    self.status_code == 200
                    and self.headers.get("content-type") == "application/json"
                ):
                    body = message["body"]
                    response_data = {
                        "content": json.loads(body),
                        "status_code": self.status_code,
                        "headers": self.headers,
                    }
                    await self.cache.set(cache_key, response_data)
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _should_skip_caching(self, path: str) -> bool:
        """Check if path should skip caching.

        Args:
            path: Request path

        Returns:
            True if path should skip caching
        """
        excluded_paths = ["/docs", "/redoc", "/openapi.json", "/metrics", "/health", "/ws"]
        return any(path.startswith(excluded) for excluded in excluded_paths)

    def _generate_cache_key(self, request: Request) -> str:
        """Generate unique cache key for request.

        Args:
            request: FastAPI request

        Returns:
            Cache key string
        """
        # Include path and query params in key
        key_parts = [request.url.path, str(sorted(request.query_params.items()))]

        # Include auth token in key for user-specific caching
        auth_token = request.headers.get("Authorization")
        if auth_token:
            key_parts.append(auth_token)

        # Generate hash of key parts
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
