"""
Performance Optimization Module - 통합 성능 관리 시스템
"""
import asyncio
import functools
import time
import logging
import psutil
import gc
from typing import Any, Callable, Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import redis.asyncio as redis
import aiocache
from aiocache import Cache
from aiocache.serializers import JsonSerializer, PickleSerializer
import aiohttp
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import uvloop
import orjson
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
import numpy as np

# Set uvloop as the default event loop for better performance
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)

# Performance Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
db_query_duration = Histogram('db_query_duration_seconds', 'Database query duration', ['query_type'])
cache_hits = Counter('cache_hits_total', 'Total cache hits', ['cache_type'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['cache_type'])
active_connections = Gauge('active_connections', 'Number of active connections')
memory_usage = Gauge('memory_usage_bytes', 'Memory usage in bytes')
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')


class PerformanceOptimizer:
    """통합 성능 최적화 관리자"""
    
    def __init__(self, redis_url: str, enable_monitoring: bool = True):
        self.redis_url = redis_url
        self.enable_monitoring = enable_monitoring
        self._redis_pool = None
        self._cache_configs = {}
        self._setup_caches()
        
    def _setup_caches(self):
        """다층 캐시 설정"""
        # L1 Cache - In-memory (빠른 접근)
        self._cache_configs['l1'] = {
            'cache': Cache.MEMORY,
            'serializer': PickleSerializer(),
            'ttl': 300,  # 5분
            'namespace': 'l1',
        }
        
        # L2 Cache - Redis (분산 캐시)
        self._cache_configs['l2'] = {
            'cache': Cache.REDIS,
            'endpoint': self.redis_url.split('://')[1].split('/')[0],
            'port': 6379,
            'serializer': JsonSerializer(),
            'ttl': 3600,  # 1시간
            'namespace': 'l2',
        }
        
    async def get_redis_pool(self) -> redis.Redis:
        """Redis 연결 풀 획득"""
        if not self._redis_pool:
            self._redis_pool = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=100,
                health_check_interval=30,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._redis_pool
    
    async def close(self):
        """리소스 정리"""
        if self._redis_pool:
            await self._redis_pool.close()
            
    # 캐싱 데코레이터
    def cached(
        self,
        ttl: int = 3600,
        key_builder: Optional[Callable] = None,
        cache_type: str = 'l2',
        namespace: Optional[str] = None
    ):
        """비동기 캐싱 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # 캐시 키 생성
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = self._default_key_builder(func.__name__, *args, **kwargs)
                
                # 캐시 설정 가져오기
                cache_config = self._cache_configs.get(cache_type, self._cache_configs['l2'])
                cache = aiocache.caches.get('default')
                
                # 캐시에서 조회
                try:
                    cached_value = await cache.get(cache_key)
                    if cached_value is not None:
                        cache_hits.labels(cache_type=cache_type).inc()
                        return cached_value
                except Exception as e:
                    logger.warning(f"Cache get error: {e}")
                
                cache_misses.labels(cache_type=cache_type).inc()
                
                # 함수 실행
                result = await func(*args, **kwargs)
                
                # 결과 캐싱
                try:
                    await cache.set(cache_key, result, ttl=ttl)
                except Exception as e:
                    logger.warning(f"Cache set error: {e}")
                
                return result
            return wrapper
        return decorator
    
    def cached_sync(
        self,
        ttl: int = 3600,
        key_builder: Optional[Callable] = None,
        namespace: Optional[str] = None
    ):
        """동기 함수용 캐싱 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Run async cache in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    cache_key = self._default_key_builder(func.__name__, *args, **kwargs)
                    
                    # Try to get from cache
                    redis_client = loop.run_until_complete(self.get_redis_pool())
                    cached_value = loop.run_until_complete(redis_client.get(cache_key))
                    
                    if cached_value:
                        cache_hits.labels(cache_type='sync').inc()
                        return orjson.loads(cached_value)
                    
                    cache_misses.labels(cache_type='sync').inc()
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Cache result
                    loop.run_until_complete(
                        redis_client.setex(cache_key, ttl, orjson.dumps(result))
                    )
                    
                    return result
                finally:
                    loop.close()
            return wrapper
        return decorator
    
    def _default_key_builder(self, func_name: str, *args, **kwargs) -> str:
        """기본 캐시 키 생성기"""
        key_parts = [func_name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)
    
    # 성능 모니터링 데코레이터
    def monitor_performance(self, name: Optional[str] = None):
        """함수 성능 모니터링 데코레이터"""
        def decorator(func: Callable) -> Callable:
            metric_name = name or func.__name__
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    request_duration.labels(method='async', endpoint=metric_name).observe(duration)
                    
                    if duration > 1.0:  # 1초 이상 걸린 작업 로깅
                        logger.warning(f"Slow operation: {metric_name} took {duration:.2f}s")
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    request_duration.labels(method='sync', endpoint=metric_name).observe(duration)
                    
                    if duration > 1.0:
                        logger.warning(f"Slow operation: {metric_name} took {duration:.2f}s")
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    # 배치 처리 헬퍼
    async def batch_process(
        self,
        items: List[Any],
        processor: Callable,
        batch_size: int = 100,
        max_concurrency: int = 10
    ) -> List[Any]:
        """대량 데이터 배치 처리"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_batch(batch):
            async with semaphore:
                return await processor(batch)
        
        # 배치 생성
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        # 병렬 처리
        tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 병합
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Batch processing error: {batch_result}")
                continue
            results.extend(batch_result)
        
        return results
    
    # 리소스 모니터링
    async def monitor_resources(self):
        """시스템 리소스 모니터링"""
        while self.enable_monitoring:
            try:
                # CPU 사용률
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_usage.set(cpu_percent)
                
                # 메모리 사용률
                memory = psutil.Process().memory_info()
                memory_usage.set(memory.rss)
                
                # 활성 연결 수
                connections = len(psutil.net_connections())
                active_connections.set(connections)
                
                # 가비지 컬렉션 최적화
                if memory.rss > 500 * 1024 * 1024:  # 500MB 이상
                    gc.collect()
                    
                await asyncio.sleep(30)  # 30초마다 체크
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(60)
    
    # 데이터베이스 쿼리 최적화
    @staticmethod
    def optimize_query(query: str) -> str:
        """SQL 쿼리 최적화 힌트 추가"""
        optimizations = [
            ("SELECT", "SELECT /*+ INDEX_SCAN */"),
            ("JOIN", "JOIN /*+ USE_HASH */"),
            ("WHERE id IN", "WHERE id = ANY(VALUES")
        ]
        
        optimized_query = query
        for pattern, replacement in optimizations:
            if pattern in query.upper():
                optimized_query = optimized_query.replace(pattern, replacement)
        
        return optimized_query
    
    # 응답 압축
    @staticmethod
    def compress_response(data: Any) -> bytes:
        """응답 데이터 압축"""
        import gzip
        json_data = orjson.dumps(data)
        return gzip.compress(json_data)
    
    @staticmethod
    def decompress_response(compressed_data: bytes) -> Any:
        """압축된 응답 데이터 해제"""
        import gzip
        json_data = gzip.decompress(compressed_data)
        return orjson.loads(json_data)


# 데이터베이스 연결 풀 이벤트 리스너
@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 성능 최적화 설정"""
    if 'sqlite' in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB mmap
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA wal_autocheckpoint = 1000")
        cursor.close()


@event.listens_for(Engine, "connect")
def set_postgresql_search_path(dbapi_connection, connection_record):
    """PostgreSQL 성능 최적화 설정"""
    if 'postgresql' in str(dbapi_connection):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET jit = 'on'")
            cursor.execute("SET random_page_cost = 1.1")
            cursor.execute("SET effective_cache_size = '4GB'")
            cursor.execute("SET shared_buffers = '1GB'")
            cursor.execute("SET work_mem = '16MB'")
            cursor.execute("SET maintenance_work_mem = '256MB'")
            cursor.execute("SET synchronous_commit = 'off'")
            cursor.execute("SET checkpoint_completion_target = 0.9")


# 전역 인스턴스
performance_optimizer = None


def init_performance_optimizer(redis_url: str, enable_monitoring: bool = True):
    """성능 최적화 모듈 초기화"""
    global performance_optimizer
    performance_optimizer = PerformanceOptimizer(redis_url, enable_monitoring)
    return performance_optimizer


def get_performance_optimizer() -> PerformanceOptimizer:
    """성능 최적화 인스턴스 반환"""
    if not performance_optimizer:
        raise RuntimeError("Performance optimizer not initialized")
    return performance_optimizer