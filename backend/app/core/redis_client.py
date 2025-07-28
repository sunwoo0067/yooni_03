"""
Redis client configuration
"""
import redis
from typing import Optional
from app.core.config import settings


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance"""
        if not self._client:
            self._client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )
        return self._client
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            return self.client.get(key)
        except Exception:
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis"""
        try:
            return self.client.set(key, value, ex=ex)
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            return bool(self.client.delete(key))
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.client.exists(key))
        except Exception:
            return False
    
    def ping(self) -> bool:
        """Check Redis connectivity"""
        try:
            return self.client.ping()
        except Exception:
            return False


# Global Redis client instance
redis_client = RedisClient()


def get_redis() -> RedisClient:
    """Get Redis client instance for dependency injection"""
    return redis_client