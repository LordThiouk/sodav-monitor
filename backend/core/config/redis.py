"""Module de configuration Redis."""

import redis
from typing import Optional
from functools import lru_cache
from .settings import get_settings

settings = get_settings()

@lru_cache()
def get_redis() -> redis.Redis:
    """Obtenir une connexion Redis."""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )

def get_test_redis() -> redis.Redis:
    """Obtenir une connexion Redis pour les tests."""
    return redis.Redis(
        host="localhost",
        port=6379,
        db=1,  # Utiliser une base de données différente pour les tests
        decode_responses=True
    )

def check_redis_connection(redis_client: Optional[redis.Redis] = None) -> bool:
    """Vérifier la connexion Redis."""
    try:
        if redis_client is None:
            redis_client = get_redis()
        return redis_client.ping()
    except redis.ConnectionError:
        return False

def clear_redis_data(redis_client: Optional[redis.Redis] = None) -> None:
    """Effacer toutes les données Redis."""
    try:
        if redis_client is None:
            redis_client = get_redis()
        redis_client.flushdb()
    except redis.ConnectionError:
        pass

def get_redis_key(prefix: str, *args) -> str:
    """Generate a Redis key with prefix and arguments."""
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"

def set_redis_value(key: str, value: str, expire: Optional[int] = None) -> None:
    """Set a value in Redis with optional expiration."""
    redis_client = get_redis()
    redis_client.set(key, value)
    if expire:
        redis_client.expire(key, expire)

def get_redis_value(key: str) -> Optional[str]:
    """Get a value from Redis."""
    redis_client = get_redis()
    return redis_client.get(key)

def delete_redis_key(key: str) -> None:
    """Delete a key from Redis."""
    redis_client = get_redis()
    redis_client.delete(key) 