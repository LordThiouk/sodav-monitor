import asyncio
import os
from dotenv import load_dotenv
from redis_config import init_redis, get_redis
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redis_connection():
    """Test Redis connection and basic operations"""
    try:
        # Initialize Redis
        logger.info("Initializing Redis connection...")
        redis = await init_redis()
        
        # Test SET operation
        logger.info("Testing SET operation...")
        await redis.set("test_key", "Hello SODAV!")
        
        # Test GET operation
        logger.info("Testing GET operation...")
        value = await redis.get("test_key")
        logger.info(f"Retrieved value: {value}")
        
        # Test DELETE operation
        logger.info("Testing DELETE operation...")
        await redis.delete("test_key")
        
        # Verify deletion
        value_after_delete = await redis.get("test_key")
        logger.info(f"Value after delete: {value_after_delete}")
        
        # Test PING
        logger.info("Testing PING...")
        pong = await redis.ping()
        logger.info(f"PING response: {pong}")
        
        logger.info("✅ All Redis tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis test failed: {str(e)}")
        return False
    finally:
        if redis:
            await redis.close()
            logger.info("Redis connection closed")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Print Redis configuration (without password)
    redis_url = os.getenv("REDIS_URL", "")
    masked_url = redis_url.replace(os.getenv("REDIS_PASSWORD", ""), "***")
    logger.info(f"Testing Redis connection to: {masked_url}")
    
    # Run the test
    asyncio.run(test_redis_connection()) 