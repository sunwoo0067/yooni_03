"""
Cache service for V2 patterns.
V2 패턴을 위한 캐시 서비스.
"""
from typing import Any, Optional, Dict
import json
import pickle
from datetime import timedelta

from app.core.cache_utils import CacheManager, CacheService as BaseCacheService
from app.core.logging_utils import get_logger


class CacheService(BaseCacheService):
    """향상된 캐시 서비스"""
    
    def __init__(self, cache_manager: CacheManager, namespace: str = "default"):
        super().__init__(cache_manager, namespace)
        self.logger = get_logger(f"CacheService.{namespace}")
        
    async def get_or_set(
        self,
        key: str,
        factory_func,
        ttl: Optional[int] = None,
        use_cache: bool = True
    ) -> Any:
        """캐시에서 가져오거나 없으면 생성 후 저장"""
        if not use_cache:
            return await factory_func()
            
        # 캐시에서 조회
        cached = await self.get(key)
        if cached is not None:
            self.logger.debug(f"Cache hit: {key}")
            return cached
            
        # 캐시 미스 - 데이터 생성
        self.logger.debug(f"Cache miss: {key}")
        result = await factory_func()
        
        # 캐시에 저장
        if result is not None:
            await self.set(key, result, ttl)
            
        return result
        
    async def invalidate_pattern(self, pattern: str):
        """패턴과 일치하는 모든 키 무효화"""
        full_pattern = self._make_key(pattern)
        count = await self.cache_manager.delete_pattern(full_pattern)
        self.logger.info(f"Invalidated {count} keys matching pattern: {pattern}")
        return count
        
    async def get_many(self, keys: list) -> Dict[str, Any]:
        """여러 키 동시 조회"""
        full_keys = [self._make_key(key) for key in keys]
        results = await self.cache_manager.mget(full_keys)
        
        return {
            key: self._deserialize(value) if value else None
            for key, value in zip(keys, results)
        }
        
    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None):
        """여러 키 동시 저장"""
        pipe = self.cache_manager.redis.pipeline()
        
        for key, value in items.items():
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            
            if ttl:
                pipe.setex(full_key, ttl, serialized)
            else:
                pipe.set(full_key, serialized)
                
        await pipe.execute()
        
    def _serialize(self, value: Any) -> str:
        """값 직렬화"""
        try:
            # JSON으로 시도
            return json.dumps(value)
        except (TypeError, ValueError):
            # 실패하면 pickle 사용
            return pickle.dumps(value).hex()
            
    def _deserialize(self, value: str) -> Any:
        """값 역직렬화"""
        try:
            # JSON으로 시도
            return json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            # 실패하면 pickle 시도
            try:
                return pickle.loads(bytes.fromhex(value))
            except:
                # 그냥 문자열로 반환
                return value


# 전역 캐시 서비스 인스턴스
_cache_service = None


def get_cache_service() -> Optional[CacheService]:
    """캐시 서비스 인스턴스 조회"""
    return _cache_service


def set_cache_service(service: CacheService):
    """캐시 서비스 인스턴스 설정"""
    global _cache_service
    _cache_service = service