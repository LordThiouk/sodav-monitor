import aioredis
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global Redis instance
redis: Optional[aioredis.Redis] = None

async def init_redis() -> aioredis.Redis:
    """Initialize Redis connection"""
    global redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        logger.info(f"Connecting to Redis at {redis_url.split('@')[-1]}")
        
        redis = aioredis.from_url(
            redis_url,
            decode_responses=True,
            encoding="utf-8",
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True
        )
        
        # Test the connection
        await redis.ping()
        logger.info("Successfully connected to Redis")
        return redis
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise

async def get_redis() -> aioredis.Redis:
    """Get Redis instance, initialize if not exists"""
    if redis is None:
        await init_redis()
    return redis

async def close_redis():
    """Close Redis connection"""
    global redis
    if redis:
        await redis.close()
        redis = None
        logger.info("Redis connection closed") 