"""Rate limiting middleware for FastAPI."""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable, Dict, Optional, Tuple, Any
import time
import asyncio
from redis.asyncio import Redis
from starlette.types import ASGIApp, Receive, Scope, Send
from ..config import get_settings

settings = get_settings()

class RateLimiter:
    """Rate limiting implementation using Redis."""
    
    def __init__(self, redis: Redis):
        """Initialize rate limiter.
        
        Args:
            redis: Redis client instance
        """
        self.redis = redis
        self.rate_limit_requests = settings.RATE_LIMIT_REQUESTS
        self.rate_limit_period = settings.RATE_LIMIT_PERIOD
        
    async def is_rate_limited(self, key: str) -> Tuple[bool, Optional[int]]:
        """Check if request should be rate limited.
        
        Args:
            key: Unique identifier for the client
            
        Returns:
            Tuple of (is_limited, retry_after)
        """
        current = int(time.time())
        period_start = current - (current % self.rate_limit_period)
        
        # Get current count
        count_key = f"{settings.CACHE_PREFIX}ratelimit:{key}:{period_start}"
        
        # Increment counter and set expiry
        count = await self.redis.incr(count_key)
        await self.redis.expire(count_key, self.rate_limit_period)
        
        if count > self.rate_limit_requests:
            retry_after = period_start + self.rate_limit_period - current
            return True, retry_after
            
        return False, None

class RateLimitMiddleware:
    """Middleware for rate limiting requests."""
    
    def __init__(self, app: ASGIApp, redis: Redis):
        """Initialize middleware.
        
        Args:
            app: ASGI application instance
            redis: Redis client instance
        """
        self.app = app
        self.limiter = RateLimiter(redis)
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """Process request with rate limiting.
        
        Args:
            scope: ASGI connection scope
            receive: ASGI receive function
            send: ASGI send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
            
        if not settings.RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return
            
        # Skip rate limiting for excluded paths
        if self._should_skip_rate_limiting(request.url.path):
            await self.app(scope, receive, send)
            return
            
        # Get client identifier (IP or API key)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        is_limited, retry_after = await self.limiter.is_rate_limited(client_id)
        
        if is_limited:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
            await response(scope, receive, send)
            return
            
        await self.app(scope, receive, send)
        
    def _should_skip_rate_limiting(self, path: str) -> bool:
        """Check if path should skip rate limiting.
        
        Args:
            path: Request path
            
        Returns:
            True if path should skip rate limiting
        """
        excluded_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
            "/health"
        ]
        return any(path.startswith(excluded) for excluded in excluded_paths)
        
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for client.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client identifier string
        """
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key}"
            
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
            
        return f"ip:{request.client.host}" 