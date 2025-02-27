"""Redis configuration for stream handling."""

import aioredis
from typing import Optional
import os
from functools import lru_cache

@lru_cache()
def get_redis_url() -> str:
    """Get Redis URL from environment variables."""
    return os.getenv('REDIS_URL', 'redis://localhost:6379')

async def get_redis() -> aioredis.Redis:
    """Get Redis connection."""
    redis = await aioredis.from_url(
        get_redis_url(),
        encoding='utf-8',
        decode_responses=True
    )
    return redis

async def get_test_redis() -> aioredis.Redis:
    """Get Redis connection for testing."""
    redis = await aioredis.from_url(
        'redis://localhost:6379/1',  # Use database 1 for testing
        encoding='utf-8',
        decode_responses=True
    )
    return redis

async def check_redis_connection() -> bool:
    """Check if Redis connection is available."""
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception:
        return False

async def clear_redis_data() -> None:
    """Clear all Redis data (for testing purposes)."""
    redis = await get_test_redis()
    await redis.flushdb() 