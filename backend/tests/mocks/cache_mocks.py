"""
Mock implementations for cache operations
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta


class MockRedisClient:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self.data = {}
        self.expires = {}
        self.connected = True
        
    async def get(self, key: str) -> Optional[str]:
        """Mock get operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        # Check if key has expired
        if key in self.expires and time.time() > self.expires[key]:
            del self.data[key]
            del self.expires[key]
            return None
            
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock set operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        self.data[key] = value
        
        if ex:
            self.expires[key] = time.time() + ex
        elif key in self.expires:
            del self.expires[key]
            
        return True
    
    async def delete(self, *keys: str) -> int:
        """Mock delete operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        deleted_count = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted_count += 1
            if key in self.expires:
                del self.expires[key]
                
        return deleted_count
    
    async def exists(self, key: str) -> bool:
        """Mock exists operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        # Check if key has expired
        if key in self.expires and time.time() > self.expires[key]:
            del self.data[key]
            del self.expires[key]
            return False
            
        return key in self.data
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Mock expire operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        if key in self.data:
            self.expires[key] = time.time() + seconds
            return True
        return False
    
    async def ttl(self, key: str) -> int:
        """Mock TTL operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        if key not in self.data:
            return -2  # Key doesn't exist
            
        if key not in self.expires:
            return -1  # Key exists but has no expire
            
        remaining = self.expires[key] - time.time()
        return max(0, int(remaining))
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Mock keys operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        # Simple pattern matching (just * for now)
        if pattern == "*":
            return list(self.data.keys())
        
        # Basic pattern matching
        import fnmatch
        return [key for key in self.data.keys() if fnmatch.fnmatch(key, pattern)]
    
    async def flushdb(self) -> bool:
        """Mock flushdb operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
            
        self.data.clear()
        self.expires.clear()
        return True
    
    async def ping(self) -> str:
        """Mock ping operation"""
        if not self.connected:
            raise ConnectionError("Redis connection lost")
        return "PONG"
    
    # Hash operations
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Mock hash get operation"""
        hash_data = self.data.get(name)
        if hash_data and isinstance(hash_data, dict):
            return hash_data.get(key)
        return None
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Mock hash set operation"""
        if name not in self.data:
            self.data[name] = {}
        
        if not isinstance(self.data[name], dict):
            self.data[name] = {}
            
        field_is_new = key not in self.data[name]
        self.data[name][key] = value
        return 1 if field_is_new else 0
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Mock hash delete operation"""
        if name not in self.data or not isinstance(self.data[name], dict):
            return 0
            
        deleted_count = 0
        for key in keys:
            if key in self.data[name]:
                del self.data[name][key]
                deleted_count += 1
                
        return deleted_count
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Mock hash get all operation"""
        hash_data = self.data.get(name)
        if hash_data and isinstance(hash_data, dict):
            return hash_data.copy()
        return {}
    
    # List operations
    async def lpush(self, name: str, *values: str) -> int:
        """Mock list left push operation"""
        if name not in self.data:
            self.data[name] = []
            
        if not isinstance(self.data[name], list):
            self.data[name] = []
            
        for value in reversed(values):  # lpush adds in reverse order
            self.data[name].insert(0, value)
            
        return len(self.data[name])
    
    async def rpop(self, name: str) -> Optional[str]:
        """Mock list right pop operation"""
        if name not in self.data or not isinstance(self.data[name], list):
            return None
            
        if self.data[name]:
            return self.data[name].pop()
        return None
    
    async def llen(self, name: str) -> int:
        """Mock list length operation"""
        if name not in self.data or not isinstance(self.data[name], list):
            return 0
        return len(self.data[name])
    
    # Set operations
    async def sadd(self, name: str, *values: str) -> int:
        """Mock set add operation"""
        if name not in self.data:
            self.data[name] = set()
            
        if not isinstance(self.data[name], set):
            self.data[name] = set()
            
        added_count = 0
        for value in values:
            if value not in self.data[name]:
                self.data[name].add(value)
                added_count += 1
                
        return added_count
    
    async def srem(self, name: str, *values: str) -> int:
        """Mock set remove operation"""
        if name not in self.data or not isinstance(self.data[name], set):
            return 0
            
        removed_count = 0
        for value in values:
            if value in self.data[name]:
                self.data[name].remove(value)
                removed_count += 1
                
        return removed_count
    
    async def smembers(self, name: str) -> set:
        """Mock set members operation"""
        if name not in self.data or not isinstance(self.data[name], set):
            return set()
        return self.data[name].copy()
    
    # Utility methods for testing
    def disconnect(self):
        """Simulate connection loss"""
        self.connected = False
        
    def reconnect(self):
        """Simulate reconnection"""
        self.connected = True
        
    def clear_expired(self):
        """Manually clear expired keys"""
        current_time = time.time()
        expired_keys = [
            key for key, expire_time in self.expires.items()
            if current_time > expire_time
        ]
        
        for key in expired_keys:
            if key in self.data:
                del self.data[key]
            del self.expires[key]


class MockCacheManager:
    """Mock cache manager for testing"""
    
    def __init__(self, redis_client: MockRedisClient = None):
        self.redis = redis_client or MockRedisClient()
        self.namespace = "dropship:cache"
        self.default_ttl = 300  # 5 minutes
        
    def _make_key(self, key: str) -> str:
        """Create namespaced cache key"""
        return f"{self.namespace}:{key}"
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        try:
            cache_key = self._make_key(key)
            value = await self.redis.get(cache_key)
            
            if value is None:
                return default
                
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception:
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            cache_key = self._make_key(key)
            
            # Serialize value
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            expire_time = ttl or self.default_ttl
            return await self.redis.set(cache_key, serialized_value, ex=expire_time)
            
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            cache_key = self._make_key(key)
            deleted_count = await self.redis.delete(cache_key)
            return deleted_count > 0
        except Exception:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            cache_key = self._make_key(key)
            return await self.redis.exists(cache_key)
        except Exception:
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            cache_pattern = self._make_key(pattern)
            keys = await self.redis.keys(cache_pattern)
            
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception:
            return 0
    
    async def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None) -> Any:
        """Get value from cache or set it using factory function"""
        value = await self.get(key)
        
        if value is None:
            # Call factory function (could be async)
            if asyncio.iscoroutinefunction(factory_func):
                value = await factory_func()
            else:
                value = factory_func()
                
            await self.set(key, value, ttl)
            
        return value
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache"""
        try:
            cache_key = self._make_key(key)
            current_value = await self.redis.get(cache_key)
            
            if current_value is None:
                new_value = amount
            else:
                try:
                    new_value = int(current_value) + amount
                except (ValueError, TypeError):
                    new_value = amount
            
            await self.redis.set(cache_key, str(new_value))
            return new_value
            
        except Exception:
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            all_keys = await self.redis.keys(f"{self.namespace}:*")
            
            total_keys = len(all_keys)
            expired_keys = 0
            
            # Count expired keys
            for key in all_keys:
                ttl = await self.redis.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_keys += 1
            
            return {
                "total_keys": total_keys,
                "active_keys": total_keys - expired_keys,
                "expired_keys": expired_keys,
                "namespace": self.namespace,
                "default_ttl": self.default_ttl,
                "connection_status": "connected" if self.redis.connected else "disconnected"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "connection_status": "error"
            }


# Specialized Cache Classes for Different Data Types
class MockProductCacheManager(MockCacheManager):
    """Mock cache manager specifically for products"""
    
    def __init__(self, redis_client: MockRedisClient = None):
        super().__init__(redis_client)
        self.namespace = "dropship:products"
    
    async def cache_product(self, product_id: str, product_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache product data"""
        return await self.set(f"product:{product_id}", product_data, ttl)
    
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get cached product data"""
        return await self.get(f"product:{product_id}")
    
    async def cache_product_list(self, cache_key: str, products: List[Dict[str, Any]], ttl: int = 1800) -> bool:
        """Cache product list"""
        return await self.set(f"list:{cache_key}", products, ttl)
    
    async def get_product_list(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached product list"""
        return await self.get(f"list:{cache_key}")


class MockOrderCacheManager(MockCacheManager):
    """Mock cache manager specifically for orders"""
    
    def __init__(self, redis_client: MockRedisClient = None):
        super().__init__(redis_client)
        self.namespace = "dropship:orders"
    
    async def cache_order(self, order_id: str, order_data: Dict[str, Any], ttl: int = 7200) -> bool:
        """Cache order data"""
        return await self.set(f"order:{order_id}", order_data, ttl)
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get cached order data"""
        return await self.get(f"order:{order_id}")
    
    async def cache_user_orders(self, user_id: str, orders: List[Dict[str, Any]], ttl: int = 3600) -> bool:
        """Cache user's orders"""
        return await self.set(f"user_orders:{user_id}", orders, ttl)
    
    async def get_user_orders(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached user orders"""
        return await self.get(f"user_orders:{user_id}")


class MockAPIResponseCacheManager(MockCacheManager):
    """Mock cache manager for API responses"""
    
    def __init__(self, redis_client: MockRedisClient = None):
        super().__init__(redis_client)
        self.namespace = "dropship:api_cache"
    
    async def cache_api_response(self, endpoint: str, params_hash: str, response_data: Any, ttl: int = 600) -> bool:
        """Cache API response"""
        cache_key = f"api:{endpoint}:{params_hash}"
        return await self.set(cache_key, response_data, ttl)
    
    async def get_api_response(self, endpoint: str, params_hash: str) -> Optional[Any]:
        """Get cached API response"""
        cache_key = f"api:{endpoint}:{params_hash}"
        return await self.get(cache_key)
    
    async def invalidate_endpoint(self, endpoint: str) -> int:
        """Invalidate all cached responses for an endpoint"""
        pattern = f"api:{endpoint}:*"
        return await self.clear_pattern(pattern)