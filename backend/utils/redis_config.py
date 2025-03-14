"""Redis configuration module."""

import redis.asyncio as redis

from backend.core.config import get_settings


async def init_redis_pool() -> redis.Redis:
    """Initialize Redis connection pool."""
    settings = get_settings()

    redis_pool = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        encoding="utf-8",
    )

    return redis_pool
