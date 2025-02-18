import aioredis
import os
from typing import Optional
import logging
from urllib.parse import urlparse
import asyncio

logger = logging.getLogger(__name__)

# Global Redis instance
redis: Optional[aioredis.Redis] = None

async def init_redis() -> Optional[aioredis.Redis]:
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

        # Parse Redis URL to validate format
        parsed_url = urlparse(redis_url)
        if not all([parsed_url.hostname, parsed_url.port]):
            raise ValueError("Invalid Redis URL format")

        # Mask password for logging
        masked_url = redis_url
        if "@" in redis_url:
            prefix, rest = redis_url.split("@", 1)
            if ":" in prefix:
                protocol, password = prefix.rsplit(":", 1)
                masked_url = f"{protocol}:***@{rest}"
        logger.info(f"Connecting to Redis at {masked_url}")

        # Configure Redis client with retry options
        for retry_count in range(3):
            try:
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
            except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
                if retry_count < 2:
                    wait_time = (retry_count + 1) * 2
                    logger.warning(f"Redis connection attempt {retry_count + 1} failed, retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
                
    except aioredis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}")
        logger.warning("Application will start without Redis functionality")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        logger.warning("Application will start without Redis functionality")
        return None

async def get_redis() -> Optional[aioredis.Redis]:
    """Get Redis instance, initialize if not exists"""
    global redis
    if redis is None:
        return await init_redis()
    try:
        # Test if connection is still alive
        await redis.ping()
        return redis
    except:
        # Connection lost, try to reconnect
        return await init_redis()

async def close_redis():
    """Close Redis connection"""
    global redis
    if redis:
        await redis.close()
        redis = None
        logger.info("Redis connection closed") 