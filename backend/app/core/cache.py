"""
캐싱 시스템 - Redis 기반 고성능 캐싱
"""
import json
import hashlib
import gzip
import base64
import logging
from typing import Any, Optional, Callable, Union, Dict
from functools import wraps
from datetime import timedelta
import asyncio
import redis.asyncio as redis
from redis.exceptions import RedisError

from .config import get_settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis 기반 캐시 매니저"""
    
    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        self._compression_stats = {
            "compressed_count": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "avg_compression_ratio": 0.0
        }
    
    async def connect(self):
        """Redis 연결"""
        if self._connected:
            return
            
        try:
            if self.settings.REDIS_URL:
                self._redis = await redis.from_url(
                    self.settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self._redis.ping()
                self._connected = True
            else:
                # Redis가 없으면 메모리 캐시 사용 (개발용)
                self._redis = None
                self._memory_cache = {}
                self._connected = True
                
        except RedisError as e:
            print(f"Redis 연결 실패, 메모리 캐시 사용: {e}")
            self._redis = None
            self._memory_cache = {}
            self._connected = True
    
    async def disconnect(self):
        """Redis 연결 종료"""
        if self._redis:
            await self._redis.close()
        self._connected = False
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        # 인자를 JSON으로 직렬화하여 해시 생성
        data = {"args": args, "kwargs": kwargs}
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.md5(json_str.encode()).hexdigest()
        
        return f"{self.settings.CACHE_KEY_PREFIX}{prefix}:{hash_value}"
    
    async def get(self, key: str, compressed: bool = True) -> Optional[Any]:
        """캐시에서 값 가져오기 (압축 지원)"""
        if not self._connected:
            await self.connect()
            
        try:
            if self._redis:
                value = await self._redis.get(key)
                if value:
                    self._stats["hits"] += 1
                    # 압축된 데이터인지 확인
                    if compressed and value.startswith("gzip:"):
                        # 압축 해제
                        compressed_data = base64.b64decode(value[5:])
                        decompressed_data = gzip.decompress(compressed_data)
                        return json.loads(decompressed_data.decode('utf-8'))
                    else:
                        return json.loads(value)
                else:
                    self._stats["misses"] += 1
            else:
                # 메모리 캐시
                value = self._memory_cache.get(key)
                if value is not None:
                    self._stats["hits"] += 1
                    return value
                else:
                    self._stats["misses"] += 1
                
        except Exception as e:
            self._stats["errors"] += 1
            print(f"캐시 조회 실패: {e}")
            
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        compress: Optional[bool] = None,
        compress_threshold: Optional[int] = None
    ) -> bool:
        """캐시에 값 저장 (압축 지원)"""
        if not self._connected:
            await self.connect()
            
        # 설정에서 기본값 가져오기
        if compress is None:
            compress = self.settings.CACHE_COMPRESSION_ENABLED
        if compress_threshold is None:
            compress_threshold = self.settings.CACHE_COMPRESSION_THRESHOLD
            
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            
            # 압축 여부 결정
            should_compress = compress and len(json_value) > compress_threshold
            
            if self._redis:
                if should_compress:
                    # 데이터 압축
                    compressed_data = gzip.compress(
                        json_value.encode('utf-8'), 
                        compresslevel=self.settings.CACHE_COMPRESSION_LEVEL
                    )
                    encoded_data = "gzip:" + base64.b64encode(compressed_data).decode('utf-8')
                    
                    # 압축 통계 업데이트
                    self._compression_stats["compressed_count"] += 1
                    self._compression_stats["total_original_size"] += len(json_value)
                    self._compression_stats["total_compressed_size"] += len(compressed_data)
                    
                    # 평균 압축률 계산
                    if self._compression_stats["compressed_count"] > 0:
                        self._compression_stats["avg_compression_ratio"] = (
                            self._compression_stats["total_compressed_size"] / 
                            self._compression_stats["total_original_size"]
                        )
                    
                    # 압축률 로깅 (디버그용)
                    compression_ratio = len(compressed_data) / len(json_value)
                    if compression_ratio < 0.8:  # 20% 이상 압축된 경우만 로깅
                        logger.debug(f"Cache compression for {key}: {len(json_value)} -> {len(compressed_data)} bytes ({compression_ratio:.2%})")
                    
                    final_value = encoded_data
                else:
                    final_value = json_value
                
                if ttl:
                    await self._redis.setex(key, ttl, final_value)
                else:
                    await self._redis.set(key, final_value)
            else:
                # 메모리 캐시는 압축하지 않음 (성능 우선)
                self._memory_cache[key] = value
                # 간단한 TTL 구현은 생략 (개발용)
                
            self._stats["sets"] += 1
            return True
            
        except Exception as e:
            self._stats["errors"] += 1
            print(f"캐시 저장 실패: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if not self._connected:
            await self.connect()
            
        try:
            if self._redis:
                await self._redis.delete(key)
            else:
                self._memory_cache.pop(key, None)
            return True
            
        except Exception as e:
            print(f"캐시 삭제 실패: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """패턴과 일치하는 모든 키 삭제"""
        if not self._connected:
            await self.connect()
            
        deleted = 0
        try:
            if self._redis:
                # Redis SCAN을 사용하여 패턴 매칭
                async for key in self._redis.scan_iter(match=pattern):
                    await self._redis.delete(key)
                    deleted += 1
            else:
                # 메모리 캐시
                keys_to_delete = [k for k in self._memory_cache.keys() if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                    deleted += 1
                    
        except Exception as e:
            print(f"패턴 삭제 실패: {e}")
            
        self._stats["deletes"] += deleted
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보 반환"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "errors": self._stats["errors"],
            "total_requests": total_requests
        }
        
        # 압축 통계 추가
        if hasattr(self, '_compression_stats'):
            stats["compression"] = self._compression_stats
            
        return stats
    
    def reset_stats(self):
        """통계 초기화"""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        self._compression_stats = {
            "compressed_count": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "avg_compression_ratio": 0.0
        }


# 전역 캐시 매니저 인스턴스
# 설정에 따라 클러스터 매니저 또는 일반 매니저 사용
_settings = get_settings()
if _settings.REDIS_CLUSTER_ENABLED:
    from .cache_cluster import cluster_cache_manager
    cache_manager = cluster_cache_manager
else:
    cache_manager = CacheManager()


def cache_result(
    prefix: str,
    ttl: Union[int, timedelta] = 300,
    key_builder: Optional[Callable] = None
):
    """
    함수 결과를 캐싱하는 데코레이터
    
    Args:
        prefix: 캐시 키 접두사
        ttl: Time To Live (초 단위 또는 timedelta)
        key_builder: 커스텀 키 생성 함수
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # TTL 변환
            ttl_seconds = ttl.total_seconds() if isinstance(ttl, timedelta) else ttl
            
            # 캐시 키 생성
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            
            # 캐시 조회
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 함수 실행
            result = await func(*args, **kwargs)
            
            # 결과 캐싱
            await cache_manager.set(cache_key, result, int(ttl_seconds))
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 동기 함수용 래퍼
            loop = asyncio.get_event_loop()
            
            # 캐시 키 생성
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_key(prefix, *args, **kwargs)
            
            # 캐시 조회
            cached_value = loop.run_until_complete(cache_manager.get(cache_key))
            if cached_value is not None:
                return cached_value
            
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 결과 캐싱
            ttl_seconds = ttl.total_seconds() if isinstance(ttl, timedelta) else ttl
            loop.run_until_complete(cache_manager.set(cache_key, result, int(ttl_seconds)))
            
            return result
        
        # 함수가 코루틴인지 확인
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def invalidate_cache(pattern: str):
    """
    캐시 무효화 데코레이터
    함수 실행 후 패턴과 일치하는 캐시를 삭제
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await cache_manager.clear_pattern(pattern)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(cache_manager.clear_pattern(pattern))
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator