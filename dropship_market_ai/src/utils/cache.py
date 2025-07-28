"""Redis cache utilities"""
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class RedisCache:
    """Async Redis cache wrapper"""
    
    def __init__(self, config: dict):
        """Initialize Redis connection"""
        self.config = config
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Create Redis connection"""
        self.redis_client = redis.Redis(
            host=self.config['host'],
            port=self.config['port'],
            db=self.config['db'],
            decode_responses=self.config.get('decode_responses', True),
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            retry_on_error=[redis.ConnectionError, redis.TimeoutError],
            max_connections=50
        )
    
    async def get(
        self, 
        key: str, 
        default: Any = None,
        deserialize: bool = True
    ) -> Any:
        """Get value from cache"""
        try:
            value = await self.redis_client.get(key)
            
            if value is None:
                return default
            
            if deserialize and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
            
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache"""
        try:
            if serialize and not isinstance(value, (str, bytes)):
                value = json.dumps(value)
            
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
            
            if expire:
                await self.redis_client.setex(key, expire, value)
            else:
                await self.redis_client.set(key, value)
            
            return True
            
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error("cache_exists_error", key=key, error=str(e))
            return False
    
    async def expire(
        self,
        key: str,
        expire: Union[int, timedelta]
    ) -> bool:
        """Set expiration on existing key"""
        try:
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
            
            return await self.redis_client.expire(key, expire)
        except Exception as e:
            logger.error("cache_expire_error", key=key, error=str(e))
            return False
    
    async def increment(
        self,
        key: str,
        amount: int = 1
    ) -> Optional[int]:
        """Increment value"""
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error("cache_increment_error", key=key, error=str(e))
            return None
    
    async def get_many(
        self,
        keys: list[str],
        deserialize: bool = True
    ) -> dict[str, Any]:
        """Get multiple values"""
        try:
            values = await self.redis_client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    if deserialize and isinstance(value, str):
                        try:
                            result[key] = json.loads(value)
                        except json.JSONDecodeError:
                            result[key] = value
                    else:
                        result[key] = value
            
            return result
            
        except Exception as e:
            logger.error("cache_get_many_error", keys=keys, error=str(e))
            return {}
    
    async def set_many(
        self,
        mapping: dict[str, Any],
        expire: Optional[Union[int, timedelta]] = None,
        serialize: bool = True
    ) -> bool:
        """Set multiple values"""
        try:
            if serialize:
                processed_mapping = {}
                for key, value in mapping.items():
                    if not isinstance(value, (str, bytes)):
                        processed_mapping[key] = json.dumps(value)
                    else:
                        processed_mapping[key] = value
            else:
                processed_mapping = mapping
            
            # Set all values
            await self.redis_client.mset(processed_mapping)
            
            # Set expiration if needed
            if expire:
                if isinstance(expire, timedelta):
                    expire = int(expire.total_seconds())
                
                pipeline = self.redis_client.pipeline()
                for key in processed_mapping:
                    pipeline.expire(key, expire)
                await pipeline.execute()
            
            return True
            
        except Exception as e:
            logger.error("cache_set_many_error", error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.redis_client.delete(*keys)
            
            return 0
            
        except Exception as e:
            logger.error("cache_clear_pattern_error", pattern=pattern, error=str(e))
            return 0
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    # Context manager support
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class CacheKey:
    """Cache key generator"""
    
    @staticmethod
    def product_info(product_id: str, marketplace: str) -> str:
        return f"product:{marketplace}:{product_id}"
    
    @staticmethod
    def product_performance(product_id: str, date: str) -> str:
        return f"performance:{product_id}:{date}"
    
    @staticmethod
    def rankings(marketplace: str, category: str, date: str) -> str:
        return f"rankings:{marketplace}:{category}:{date}"
    
    @staticmethod
    def search_results(marketplace: str, keyword: str) -> str:
        return f"search:{marketplace}:{keyword}"
    
    @staticmethod
    def prediction(product_id: str, model_type: str, date: str) -> str:
        return f"prediction:{model_type}:{product_id}:{date}"
    
    @staticmethod
    def optimization(product_id: str, optimization_type: str) -> str:
        return f"optimization:{optimization_type}:{product_id}"