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
        # Get Redis configuration from environment variables
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            # Fallback to constructing URL from individual components
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_password = os.getenv("REDIS_PASSWORD", "")
            redis_db = os.getenv("REDIS_DB", "0")
            
            if redis_password:
                redis_url = f"redis://default:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Mask password for logging
        masked_url = redis_url.replace(os.getenv("REDIS_PASSWORD", ""), "***") if os.getenv("REDIS_PASSWORD") else redis_url
        logger.info(f"Connecting to Redis at {masked_url}")
        
        redis = aioredis.from_url(
            redis_url,
            decode_responses=True,
            encoding="utf-8",
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            max_connections=10
        )
        
        # Test the connection
        await redis.ping()
        logger.info("Successfully connected to Redis")
        return redis
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        # Don't raise the exception, allow the application to start without Redis
        logger.warning("Application will start without Redis functionality")
        return None

async def get_redis() -> Optional[aioredis.Redis]:
    """Get Redis instance, initialize if not exists"""
    if redis is None:
        return await init_redis()
    return redis

async def close_redis():
    """Close Redis connection"""
    global redis
    if redis:
        await redis.close()
        redis = None
        logger.info("Redis connection closed") 