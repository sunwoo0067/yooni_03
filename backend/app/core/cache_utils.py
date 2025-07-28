"""
Standardized caching utilities.
표준화된 캐싱 유틸리티.
"""
import json
import orjson
from typing import Optional, Any, Callable, Union
from datetime import timedelta, datetime
from functools import wraps
import hashlib
import asyncio
from redis import Redis
from redis.exceptions import RedisError

from app.core.constants import CacheKeys, Limits
from app.core.logging_utils import get_logger
from app.core.exceptions import ExternalServiceError

logger = get_logger(__name__)


class CacheManager:
    """캐시 관리자 클래스"""
    
    def __init__(self, redis_client: Redis, default_ttl: int = 3600):
        """
        Args:
            redis_client: Redis 클라이언트
            default_ttl: 기본 TTL (초 단위)
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        
    def _serialize_value(self, value: Any) -> bytes:
        """값을 안전하게 JSON으로 직렬화"""
        try:
            # datetime 객체를 ISO 문자열로 변환
            if isinstance(value, dict):
                value = self._convert_datetime_to_str(value)
            elif isinstance(value, (list, tuple)):
                value = [self._convert_datetime_to_str(item) if isinstance(item, dict) else item for item in value]
            elif isinstance(value, datetime):
                value = value.isoformat()
                
            # orjson이 더 빠르고 안전함
            return orjson.dumps(value)
        except (TypeError, ValueError) as e:
            # JSON 직렬화가 불가능한 객체는 캐싱하지 않음
            logger.warning(f"Cannot serialize value for cache: {e}")
            raise ValueError(f"Value cannot be cached - not JSON serializable: {type(value)}")
            
    def _deserialize_value(self, data: bytes) -> Any:
        """값을 안전하게 JSON에서 역직렬화"""
        if not data:
            return None
            
        try:
            return orjson.loads(data)
        except (orjson.JSONDecodeError, ValueError) as e:
            logger.error(f"Cache deserialization failed: {e}")
            return None
            
    def _convert_datetime_to_str(self, obj):
        """딕셔너리 내의 datetime 객체를 문자열로 변환"""
        if isinstance(obj, dict):
            return {k: v.isoformat() if isinstance(v, datetime) else v for k, v in obj.items()}
        return obj
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        try:
            data = self.redis.get(key)
            if data:
                logger.debug(f"Cache hit: {key}")
                return self._deserialize_value(data)
            logger.debug(f"Cache miss: {key}")
            return None
        except RedisError as e:
            logger.error(f"Redis error on get: {e}", key=key)
            return None
            
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """캐시에 값 저장"""
        try:
            serialized = self._serialize_value(value)
            ttl = ttl or self.default_ttl
            
            self.redis.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key}, TTL: {ttl}s")
            return True
        except RedisError as e:
            logger.error(f"Redis error on set: {e}", key=key)
            return False
            
    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            result = self.redis.delete(key)
            logger.debug(f"Cache delete: {key}, result: {result}")
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis error on delete: {e}", key=key)
            return False
            
    def delete_pattern(self, pattern: str) -> int:
        """패턴에 맞는 모든 키 삭제"""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except RedisError as e:
            logger.error(f"Redis error on delete_pattern: {e}", pattern=pattern)
            return 0
            
    def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        try:
            return bool(self.redis.exists(key))
        except RedisError as e:
            logger.error(f"Redis error on exists: {e}", key=key)
            return False
            
    def expire(self, key: str, ttl: int) -> bool:
        """키의 TTL 설정"""
        try:
            return bool(self.redis.expire(key, ttl))
        except RedisError as e:
            logger.error(f"Redis error on expire: {e}", key=key)
            return False


def cache_key_wrapper(
    prefix: str,
    ttl: Optional[int] = None,
    key_generator: Optional[Callable] = None
):
    """
    함수 결과를 캐싱하는 데코레이터.
    
    Args:
        prefix: 캐시 키 접두사
        ttl: TTL (초 단위)
        key_generator: 캐시 키 생성 함수
    
    Usage:
        @cache_key_wrapper("product", ttl=3600)
        def get_product(product_id: str):
            return db.query(Product).get(product_id)
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 캐시 매니저가 없으면 함수 직접 실행
            cache_manager = kwargs.pop('cache_manager', None)
            if not cache_manager:
                return func(*args, **kwargs)
                
            # 캐시 키 생성
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                # 기본 키 생성: prefix + 함수명 + 인자 해시
                key_parts = [prefix, func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_data = ":".join(key_parts)
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
            # 캐시 조회
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
                
            # 함수 실행 및 캐싱
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
            
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 비동기 버전
            cache_manager = kwargs.pop('cache_manager', None)
            if not cache_manager:
                return await func(*args, **kwargs)
                
            # 캐시 키 생성 (동기 버전과 동일)
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                key_parts = [prefix, func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_data = ":".join(key_parts)
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
            # 캐시 조회
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
                
            # 함수 실행 및 캐싱
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
            
        # 함수가 코루틴인지 확인
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def invalidate_cache(patterns: Union[str, list]):
    """
    캐시 무효화 데코레이터.
    
    Args:
        patterns: 삭제할 캐시 키 패턴 (문자열 또는 리스트)
    
    Usage:
        @invalidate_cache("product:*")
        def update_product(product_id: str, data: dict):
            # 제품 업데이트 로직
            pass
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 캐시 무효화
            cache_manager = kwargs.get('cache_manager')
            if cache_manager:
                pattern_list = patterns if isinstance(patterns, list) else [patterns]
                for pattern in pattern_list:
                    cache_manager.delete_pattern(pattern)
                    
            return result
            
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 캐시 무효화
            cache_manager = kwargs.get('cache_manager')
            if cache_manager:
                pattern_list = patterns if isinstance(patterns, list) else [patterns]
                for pattern in pattern_list:
                    cache_manager.delete_pattern(pattern)
                    
            return result
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


class CacheService:
    """
    도메인별 캐시 서비스 베이스 클래스.
    
    Usage:
        class ProductCacheService(CacheService):
            def __init__(self, cache_manager: CacheManager):
                super().__init__(cache_manager, "product", default_ttl=3600)
                
            def get_product(self, product_id: str) -> Optional[Product]:
                key = self.make_key("detail", product_id)
                return self.get(key)
                
            def set_product(self, product: Product) -> bool:
                key = self.make_key("detail", product.id)
                return self.set(key, product)
    """
    
    def __init__(
        self, 
        cache_manager: CacheManager, 
        prefix: str,
        default_ttl: Optional[int] = None
    ):
        self.cache_manager = cache_manager
        self.prefix = prefix
        self.default_ttl = default_ttl or cache_manager.default_ttl
        self.logger = get_logger(f"{prefix}CacheService")
        
    def make_key(self, *parts) -> str:
        """캐시 키 생성"""
        key_parts = [self.prefix] + [str(part) for part in parts]
        return ":".join(key_parts)
        
    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        return self.cache_manager.get(key)
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시 저장"""
        ttl = ttl or self.default_ttl
        return self.cache_manager.set(key, value, ttl)
        
    def delete(self, key: str) -> bool:
        """캐시 삭제"""
        return self.cache_manager.delete(key)
        
    def invalidate_all(self) -> int:
        """해당 서비스의 모든 캐시 삭제"""
        pattern = f"{self.prefix}:*"
        count = self.cache_manager.delete_pattern(pattern)
        self.logger.info(f"Invalidated all cache, deleted {count} keys")
        return count


# 자주 사용하는 캐시 패턴들
def cached_result(
    ttl: int = 3600,
    cache_none: bool = False
):
    """
    간단한 결과 캐싱 데코레이터.
    
    Args:
        ttl: TTL (초 단위)
        cache_none: None 값도 캐싱할지 여부
    
    Usage:
        @cached_result(ttl=600)
        async def get_expensive_data(param: str):
            # 비용이 큰 연산
            return result
    """
    def decorator(func):
        cache_data = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 간단한 인메모리 캐싱 (프로덕션에서는 Redis 사용 권장)
            cache_key = f"{args}:{kwargs}"
            
            if cache_key in cache_data:
                cached_time, cached_value = cache_data[cache_key]
                if (time.time() - cached_time) < ttl:
                    if cached_value is None and not cache_none:
                        # None은 캐싱하지 않음
                        pass
                    else:
                        return cached_value
                        
            result = await func(*args, **kwargs)
            
            if result is not None or cache_none:
                cache_data[cache_key] = (time.time(), result)
                
            return result
            
        return wrapper
    return decorator


import time  # 상단에 추가