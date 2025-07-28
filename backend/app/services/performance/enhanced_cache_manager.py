"""
고급 캐시 관리 시스템
압축, 분산 캐싱, 스마트 무효화, 성능 최적화
"""

import json
import hashlib
import asyncio
import gzip
import pickle
import time
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import redis
from redis.exceptions import RedisError
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar('T')


class CacheStrategy(Enum):
    """캐시 전략"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"


@dataclass
class CacheConfig:
    """캐시 설정"""
    strategy: CacheStrategy = CacheStrategy.TTL
    ttl: int = 3600
    compression_enabled: bool = True
    compression_threshold: int = 1024
    serialization_method: str = "json"  # json, pickle
    namespace: str = "default"
    hit_rate_threshold: float = 0.8  # 히트율 목표


class EnhancedCacheManager:
    """고성능 캐시 매니저 (압축, 분산, 스마트 무효화 지원)"""
    
    def __init__(self):
        self.settings = get_settings()
        self._init_redis_client()
        
        # 캐시 설정
        self.default_config = CacheConfig()
        self.cache_prefix = "yooni_enhanced:"
        
        # 압축 설정
        self.compression_enabled = getattr(self.settings, 'CACHE_COMPRESSION_ENABLED', True)
        self.compression_threshold = getattr(self.settings, 'CACHE_COMPRESSION_THRESHOLD', 1024)
        self.compression_level = getattr(self.settings, 'CACHE_COMPRESSION_LEVEL', 6)
        
        # 성능 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "compressions": 0,
            "compression_ratio": 0.0,
            "avg_get_time": 0.0,
            "avg_set_time": 0.0,
            "memory_saved_bytes": 0
        }
        
        # 성능 추적
        self._operation_times = []
        self._hit_rate_window = []
        self._max_window_size = 1000
        
        # 메모리 캐시 (L1 캐시)
        self._memory_cache: Dict[str, Any] = {}
        self._memory_cache_ttl: Dict[str, float] = {}
        self._max_memory_cache_size = 1000
        
        # 스마트 무효화 규칙
        self._invalidation_rules: Dict[str, List[str]] = {}
        self._dependency_graph: Dict[str, List[str]] = {}
    
    def _init_redis_client(self):
        """Redis 클라이언트 초기화"""
        try:
            if getattr(self.settings, 'REDIS_CLUSTER_ENABLED', False):
                from rediscluster import RedisCluster
                self.redis_client = RedisCluster(
                    startup_nodes=self.settings.REDIS_CLUSTER_NODES,
                    decode_responses=False,
                    password=self.settings.REDIS_CLUSTER_PASSWORD.get_secret_value() if self.settings.REDIS_CLUSTER_PASSWORD else None,
                    skip_full_coverage_check=True
                )
                self.is_cluster = True
            else:
                self.connection_pool = redis.ConnectionPool(
                    host=self.settings.REDIS_HOST,
                    port=self.settings.REDIS_PORT,
                    db=getattr(self.settings, 'REDIS_DB', 0),
                    password=self.settings.REDIS_PASSWORD.get_secret_value() if self.settings.REDIS_PASSWORD else None,
                    max_connections=getattr(self.settings, 'REDIS_POOL_SIZE', 50),
                    retry_on_timeout=True,
                    decode_responses=False
                )
                self.redis_client = redis.Redis(connection_pool=self.connection_pool)
                self.is_cluster = False
        except Exception as e:
            logger.error(f"Redis client initialization failed: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """캐시 키 생성 (해시로 최적화)"""
        if len(key) > 200:  # 긴 키는 해시로 변환
            key = hashlib.sha256(key.encode()).hexdigest()
        return f"{self.cache_prefix}{namespace}:{key}"
    
    def _serialize_and_compress(self, value: Any, config: CacheConfig) -> bytes:
        """값 직렬화 및 압축"""
        start_time = time.time()
        
        try:
            # 직렬화
            if config.serialization_method == "pickle":
                serialized = pickle.dumps(value)
            else:
                serialized = json.dumps(value, ensure_ascii=False, default=str).encode('utf-8')
            
            original_size = len(serialized)
            
            # 압축 여부 결정
            if (self.compression_enabled and 
                config.compression_enabled and 
                original_size > config.compression_threshold):
                
                compressed = gzip.compress(serialized, compresslevel=self.compression_level)
                compression_ratio = len(compressed) / original_size
                
                # 압축이 효과적인 경우만 사용
                if compression_ratio < 0.9:
                    self.stats["compressions"] += 1
                    self.stats["compression_ratio"] = (
                        (self.stats["compression_ratio"] * (self.stats["compressions"] - 1) + compression_ratio)
                        / self.stats["compressions"]
                    )
                    self.stats["memory_saved_bytes"] += original_size - len(compressed)
                    
                    # 압축 플래그와 함께 저장
                    result = b"COMPRESSED:" + compressed
                else:
                    result = b"RAW:" + serialized
            else:
                result = b"RAW:" + serialized
            
            # 성능 추적
            operation_time = time.time() - start_time
            self._operation_times.append(operation_time)
            if len(self._operation_times) > self._max_window_size:
                self._operation_times.pop(0)
            
            return result
            
        except Exception as e:
            logger.error(f"Serialization/compression failed: {e}")
            # 기본 JSON 직렬화로 폴백
            return b"RAW:" + json.dumps(str(value)).encode('utf-8')
    
    def _decompress_and_deserialize(self, data: bytes, config: CacheConfig) -> Any:
        """압축 해제 및 역직렬화"""
        try:
            if data.startswith(b"COMPRESSED:"):
                # 압축 해제
                compressed_data = data[11:]  # "COMPRESSED:" 제거
                decompressed = gzip.decompress(compressed_data)
                
                if config.serialization_method == "pickle":
                    return pickle.loads(decompressed)
                else:
                    return json.loads(decompressed.decode('utf-8'))
                    
            elif data.startswith(b"RAW:"):
                # 압축되지 않은 데이터
                raw_data = data[4:]  # "RAW:" 제거
                
                if config.serialization_method == "pickle":
                    return pickle.loads(raw_data)
                else:
                    return json.loads(raw_data.decode('utf-8'))
            else:
                # 레거시 데이터 처리
                return json.loads(data.decode('utf-8'))
                
        except Exception as e:
            logger.error(f"Decompression/deserialization failed: {e}")
            return None
    
    def get(self, key: str, config: Optional[CacheConfig] = None, default: Any = None) -> Any:
        """고성능 캐시 조회 (L1 + L2 캐시)"""
        if config is None:
            config = self.default_config
            
        cache_key = self._generate_cache_key(key, config.namespace)
        start_time = time.time()
        
        try:
            # L1 캐시 (메모리) 확인
            if cache_key in self._memory_cache:
                if self._memory_cache_ttl.get(cache_key, 0) > time.time():
                    self.stats["hits"] += 1
                    self._update_hit_rate(True)
                    return self._memory_cache[cache_key]
                else:
                    # 만료된 메모리 캐시 삭제
                    del self._memory_cache[cache_key]
                    del self._memory_cache_ttl[cache_key]
            
            # L2 캐시 (Redis) 확인
            if not self.redis_client:
                self.stats["misses"] += 1
                self._update_hit_rate(False)
                return default
                
            raw_data = self.redis_client.get(cache_key)
            
            if raw_data is not None:
                value = self._decompress_and_deserialize(raw_data, config)
                
                if value is not None:
                    # L1 캐시에 저장 (크기 제한)
                    self._store_in_memory_cache(cache_key, value, config.ttl)
                    
                    self.stats["hits"] += 1
                    self._update_hit_rate(True)
                    return value
            
            self.stats["misses"] += 1
            self._update_hit_rate(False)
            return default
            
        except RedisError as e:
            logger.error(f"Cache get failed: {e}")
            self.stats["misses"] += 1
            self._update_hit_rate(False)
            return default
        finally:
            operation_time = time.time() - start_time
            self._update_avg_time("get", operation_time)
    
    def set(self, key: str, value: Any, config: Optional[CacheConfig] = None) -> bool:
        """고성능 캐시 저장"""
        if config is None:
            config = self.default_config
            
        cache_key = self._generate_cache_key(key, config.namespace)
        start_time = time.time()
        
        try:
            # L1 캐시에 저장
            self._store_in_memory_cache(cache_key, value, config.ttl)
            
            # L2 캐시 (Redis)에 저장
            if self.redis_client:
                serialized_data = self._serialize_and_compress(value, config)
                
                if config.strategy == CacheStrategy.TTL:
                    result = self.redis_client.setex(cache_key, config.ttl, serialized_data)
                else:
                    result = self.redis_client.set(cache_key, serialized_data)
                
                if result:
                    self.stats["sets"] += 1
                    
                    # 의존성 기반 무효화 규칙 적용
                    self._apply_dependency_rules(key, config.namespace)
                    
                    return True
            
            return False
            
        except RedisError as e:
            logger.error(f"Cache set failed: {e}")
            return False
        finally:
            operation_time = time.time() - start_time
            self._update_avg_time("set", operation_time)
    
    def _store_in_memory_cache(self, cache_key: str, value: Any, ttl: int):
        """L1 메모리 캐시에 저장 (LRU 방식)"""
        # 크기 제한 확인
        if len(self._memory_cache) >= self._max_memory_cache_size:
            # 가장 오래된 항목 제거 (간단한 LRU)
            oldest_key = min(self._memory_cache_ttl.keys(), key=self._memory_cache_ttl.get)
            del self._memory_cache[oldest_key]
            del self._memory_cache_ttl[oldest_key]
        
        self._memory_cache[cache_key] = value
        self._memory_cache_ttl[cache_key] = time.time() + ttl
    
    def delete(self, key: str, config: Optional[CacheConfig] = None) -> bool:
        """캐시 삭제"""
        if config is None:
            config = self.default_config
            
        cache_key = self._generate_cache_key(key, config.namespace)
        
        # L1 캐시에서 삭제
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
            del self._memory_cache_ttl[cache_key]
        
        # L2 캐시에서 삭제
        try:
            if self.redis_client:
                result = self.redis_client.delete(cache_key)
                if result:
                    self.stats["deletes"] += 1
                    return True
            return False
        except RedisError as e:
            logger.error(f"Cache delete failed: {e}")
            return False
    
    def exists(self, key: str, config: Optional[CacheConfig] = None) -> bool:
        """캐시 존재 여부 확인"""
        if config is None:
            config = self.default_config
            
        cache_key = self._generate_cache_key(key, config.namespace)
        
        # L1 캐시 확인
        if cache_key in self._memory_cache:
            if self._memory_cache_ttl.get(cache_key, 0) > time.time():
                return True
            else:
                del self._memory_cache[cache_key]
                del self._memory_cache_ttl[cache_key]
        
        # L2 캐시 확인
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(cache_key))
            return False
        except RedisError:
            return False
    
    def flush_namespace(self, namespace: str) -> int:
        """네임스페이스 전체 삭제 (최적화됨)"""
        pattern = f"{self.cache_prefix}{namespace}:*"
        deleted_count = 0
        
        try:
            if self.redis_client:
                if self.is_cluster:
                    # 클러스터 환경에서는 각 노드별로 처리
                    for node in self.redis_client.get_nodes():
                        keys = node.keys(pattern)
                        if keys:
                            deleted_count += node.delete(*keys)
                else:
                    # 단일 인스턴스 환경
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=1000)
                        if keys:
                            deleted_count += self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                
                # L1 캐시에서도 해당 네임스페이스 삭제
                l1_pattern = f"{self.cache_prefix}{namespace}:"
                keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(l1_pattern)]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                    del self._memory_cache_ttl[key]
                
                self.stats["deletes"] += deleted_count
            
            return deleted_count
            
        except RedisError as e:
            logger.error(f"Cache flush failed: {e}")
            return 0
    
    def add_dependency_rule(self, trigger_key: str, dependent_namespaces: List[str]):
        """의존성 무효화 규칙 추가"""
        if trigger_key not in self._dependency_graph:
            self._dependency_graph[trigger_key] = []
        self._dependency_graph[trigger_key].extend(dependent_namespaces)
    
    def _apply_dependency_rules(self, key: str, namespace: str):
        """의존성 규칙 적용"""
        cache_key = f"{namespace}:{key}"
        
        if cache_key in self._dependency_graph:
            for dependent_namespace in self._dependency_graph[cache_key]:
                self.flush_namespace(dependent_namespace)
                logger.info(f"Invalidated dependent namespace: {dependent_namespace}")
    
    def _update_hit_rate(self, hit: bool):
        """히트율 업데이트"""
        self._hit_rate_window.append(hit)
        if len(self._hit_rate_window) > self._max_window_size:
            self._hit_rate_window.pop(0)
    
    def _update_avg_time(self, operation: str, time_taken: float):
        """평균 시간 업데이트"""
        stat_key = f"avg_{operation}_time"
        current_avg = self.stats[stat_key]
        operation_count = self.stats.get(f"{operation}s", 1)
        
        self.stats[stat_key] = ((current_avg * (operation_count - 1)) + time_taken) / operation_count
    
    def get_hit_rate(self) -> float:
        """현재 히트율 반환"""
        if not self._hit_rate_window:
            return 0.0
        return sum(self._hit_rate_window) / len(self._hit_rate_window)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        total_operations = sum([
            self.stats["hits"], 
            self.stats["misses"], 
            self.stats["sets"], 
            self.stats["deletes"]
        ])
        
        hit_rate = self.get_hit_rate()
        
        try:
            if self.redis_client:
                redis_info = self.redis_client.info()
                memory_usage = redis_info.get('used_memory_human', 'Unknown')
                connected_clients = redis_info.get('connected_clients', 0)
            else:
                memory_usage = 'Unknown'
                connected_clients = 0
        except RedisError:
            memory_usage = 'Unknown'
            connected_clients = 0
        
        return {
            "cache_stats": self.stats.copy(),
            "hit_rate_percent": round(hit_rate * 100, 2),
            "total_operations": total_operations,
            "redis_memory_usage": memory_usage,
            "connected_clients": connected_clients,
            "l1_cache_size": len(self._memory_cache),
            "l1_cache_hit_eligible": len([k for k, ttl in self._memory_cache_ttl.items() if ttl > time.time()]),
            "compression_efficiency": f"{self.stats['compression_ratio']:.2%}" if self.stats['compressions'] > 0 else "N/A",
            "memory_saved_mb": round(self.stats['memory_saved_bytes'] / (1024 * 1024), 2),
            "performance_score": self._calculate_performance_score(hit_rate),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_performance_score(self, hit_rate: float) -> float:
        """성능 점수 계산 (1-10)"""
        # 히트율, 응답시간, 압축 효율성을 종합한 점수
        hit_rate_score = hit_rate * 4  # 40% 가중치
        
        avg_response_time = (self.stats["avg_get_time"] + self.stats["avg_set_time"]) / 2
        response_time_score = max(0, 3 - (avg_response_time * 1000))  # 30% 가중치 (1ms = 1점 감점)
        
        compression_score = min(3, self.stats['compression_ratio'] * 3) if self.stats['compressions'] > 0 else 1.5  # 30% 가중치
        
        return min(10, max(1, hit_rate_score + response_time_score + compression_score))
    
    def warm_up_cache(self, cache_configs: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """캐시 워밍업 (병렬 처리)"""
        async def warm_up_async():
            tasks = []
            for namespace, config in cache_configs.items():
                task = self._warm_up_namespace(namespace, config)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return dict(zip(cache_configs.keys(), results))
        
        return asyncio.run(warm_up_async())
    
    async def _warm_up_namespace(self, namespace: str, config: Dict[str, Any]) -> int:
        """특정 네임스페이스 워밍업"""
        try:
            data_loader = config.get("data_loader")
            ttl = config.get("ttl", self.default_config.ttl)
            
            if callable(data_loader):
                data = data_loader()
                cache_config = CacheConfig(namespace=namespace, ttl=ttl)
                
                if isinstance(data, dict):
                    count = 0
                    for key, value in data.items():
                        if self.set(key, value, cache_config):
                            count += 1
                    return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache warm-up failed for {namespace}: {e}")
            return 0
    
    def clear_all_stats(self):
        """모든 통계 초기화"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "compressions": 0,
            "compression_ratio": 0.0,
            "avg_get_time": 0.0,
            "avg_set_time": 0.0,
            "memory_saved_bytes": 0
        }
        self._operation_times.clear()
        self._hit_rate_window.clear()
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            if self.redis_client:
                if hasattr(self.redis_client, 'close'):
                    await self.redis_client.close()
                elif hasattr(self.connection_pool, 'disconnect'):
                    self.connection_pool.disconnect()
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")


# 고성능 캐시 데코레이터
def enhanced_cached(
    ttl: int = 3600,
    namespace: str = "default",
    compression: bool = True,
    key_func: Optional[Callable] = None,
    serialization_method: str = "json"
):
    """향상된 캐시 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_config = CacheConfig(
                ttl=ttl,
                namespace=namespace,
                compression_enabled=compression,
                serialization_method=serialization_method
            )
            
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend([str(arg) for arg in args])
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                cache_key = ":".join(key_parts)
            
            # 캐시에서 조회
            cached_result = enhanced_cache_manager.get(cache_key, cache_config)
            if cached_result is not None:
                return cached_result
            
            # 함수 실행 및 결과 캐싱
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            enhanced_cache_manager.set(cache_key, result, cache_config)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 글로벌 인스턴스
enhanced_cache_manager = EnhancedCacheManager()

# 기존 cache_manager와의 호환성
cache_manager = enhanced_cache_manager

# 기본 의존성 규칙 설정
def setup_default_dependency_rules():
    """기본 의존성 규칙 설정"""
    # 상품 관련 무효화
    enhanced_cache_manager.add_dependency_rule("products:updated", ["products", "inventory", "recommendations"])
    enhanced_cache_manager.add_dependency_rule("products:created", ["products", "categories", "search"])
    enhanced_cache_manager.add_dependency_rule("products:deleted", ["products", "inventory", "recommendations", "search"])
    
    # 주문 관련 무효화
    enhanced_cache_manager.add_dependency_rule("orders:created", ["customers", "analytics", "recommendations", "inventory"])
    enhanced_cache_manager.add_dependency_rule("orders:updated", ["analytics", "reports"])
    
    # 재고 관련 무효화
    enhanced_cache_manager.add_dependency_rule("inventory:updated", ["products", "availability", "analytics"])
    
    # 고객 관련 무효화
    enhanced_cache_manager.add_dependency_rule("customers:updated", ["customers", "segments", "analytics"])

# 기본 규칙 적용
setup_default_dependency_rules()