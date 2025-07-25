"""
고성능 캐시 관리 시스템
Redis를 활용한 다층 캐싱 및 캐시 최적화
"""

import json
import pickle
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import redis
from redis.exceptions import RedisError
import logging

from ...core.config import get_settings


class CacheManager:
    """Redis 기반 캐시 관리자"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Redis 연결 풀 설정
        self.connection_pool = redis.ConnectionPool(
            host=self.settings.REDIS_HOST,
            port=self.settings.REDIS_PORT,
            max_connections=50,
            retry_on_timeout=True,
            decode_responses=True
        )
        
        self.redis_client = redis.Redis(connection_pool=self.connection_pool)
        
        # 캐시 설정
        self.default_ttl = 3600  # 기본 1시간
        self.cache_prefix = "yooni_cache:"
        
        # 캐시 통계
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """캐시 키 생성"""
        return f"{self.cache_prefix}{namespace}:{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """값 직렬화"""
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (int, float, str, bool)):
                return str(value)
            else:
                # 복잡한 객체는 pickle 사용
                return pickle.dumps(value).hex()
        except Exception as e:
            logging.error(f"Serialization failed: {str(e)}")
            return str(value)
    
    def _deserialize_value(self, value: str, value_type: str = "auto") -> Any:
        """값 역직렬화"""
        try:
            if value_type == "json" or (value_type == "auto" and (value.startswith('{') or value.startswith('['))):
                return json.loads(value)
            elif value_type == "pickle" or (value_type == "auto" and len(value) > 100 and value.isalnum()):
                return pickle.loads(bytes.fromhex(value))
            else:
                # 기본 타입 처리
                if value.lower() == 'true':
                    return True
                elif value.lower() == 'false':
                    return False
                elif value.isdigit():
                    return int(value)
                elif '.' in value and value.replace('.', '').replace('-', '').isdigit():
                    return float(value)
                else:
                    return value
        except Exception as e:
            logging.error(f"Deserialization failed: {str(e)}")
            return value
    
    def get(self, key: str, namespace: str = "default", default: Any = None) -> Any:
        """캐시에서 값 조회"""
        try:
            cache_key = self._generate_cache_key(key, namespace)
            value = self.redis_client.get(cache_key)
            
            if value is not None:
                self.stats["hits"] += 1
                return self._deserialize_value(value)
            else:
                self.stats["misses"] += 1
                return default
                
        except RedisError as e:
            logging.error(f"Cache get failed: {str(e)}")
            self.stats["misses"] += 1
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            namespace: str = "default") -> bool:
        """캐시에 값 저장"""
        try:
            cache_key = self._generate_cache_key(key, namespace)
            serialized_value = self._serialize_value(value)
            ttl = ttl or self.default_ttl
            
            result = self.redis_client.setex(cache_key, ttl, serialized_value)
            
            if result:
                self.stats["sets"] += 1
                return True
            return False
            
        except RedisError as e:
            logging.error(f"Cache set failed: {str(e)}")
            return False
    
    def delete(self, key: str, namespace: str = "default") -> bool:
        """캐시에서 값 삭제"""
        try:
            cache_key = self._generate_cache_key(key, namespace)
            result = self.redis_client.delete(cache_key)
            
            if result:
                self.stats["deletes"] += 1
                return True
            return False
            
        except RedisError as e:
            logging.error(f"Cache delete failed: {str(e)}")
            return False
    
    def exists(self, key: str, namespace: str = "default") -> bool:
        """캐시 키 존재 여부 확인"""
        try:
            cache_key = self._generate_cache_key(key, namespace)
            return bool(self.redis_client.exists(cache_key))
        except RedisError:
            return False
    
    def expire(self, key: str, ttl: int, namespace: str = "default") -> bool:
        """캐시 만료 시간 설정"""
        try:
            cache_key = self._generate_cache_key(key, namespace)
            return bool(self.redis_client.expire(cache_key, ttl))
        except RedisError:
            return False
    
    def get_ttl(self, key: str, namespace: str = "default") -> int:
        """캐시 TTL 조회"""
        try:
            cache_key = self._generate_cache_key(key, namespace)
            return self.redis_client.ttl(cache_key)
        except RedisError:
            return -1
    
    def flush_namespace(self, namespace: str) -> int:
        """네임스페이스 전체 삭제"""
        try:
            pattern = self._generate_cache_key("*", namespace)
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                self.stats["deletes"] += deleted
                return deleted
            return 0
            
        except RedisError as e:
            logging.error(f"Cache flush failed: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        total_operations = sum(self.stats.values())
        hit_rate = (self.stats["hits"] / max(self.stats["hits"] + self.stats["misses"], 1)) * 100
        
        try:
            redis_info = self.redis_client.info()
            memory_usage = redis_info.get('used_memory_human', 'Unknown')
            connected_clients = redis_info.get('connected_clients', 0)
        except RedisError:
            memory_usage = 'Unknown'
            connected_clients = 0
        
        return {
            "cache_stats": self.stats.copy(),
            "hit_rate_percent": round(hit_rate, 2),
            "total_operations": total_operations,
            "redis_memory_usage": memory_usage,
            "connected_clients": connected_clients,
            "timestamp": datetime.now().isoformat()
        }
    
    def warm_up_cache(self, cache_config: Dict[str, Any]) -> Dict[str, int]:
        """캐시 워밍업"""
        warmed_counts = {}
        
        for namespace, config in cache_config.items():
            try:
                data_loader = config.get("data_loader")
                ttl = config.get("ttl", self.default_ttl)
                
                if callable(data_loader):
                    data = data_loader()
                    
                    if isinstance(data, dict):
                        count = 0
                        for key, value in data.items():
                            if self.set(key, value, ttl, namespace):
                                count += 1
                        warmed_counts[namespace] = count
                    
            except Exception as e:
                logging.error(f"Cache warm-up failed for {namespace}: {str(e)}")
                warmed_counts[namespace] = 0
        
        return warmed_counts


# 캐시 데코레이터
def cached(ttl: int = 3600, namespace: str = "default", key_func: Optional[Callable] = None):
    """함수 결과 캐싱 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = CacheManager()
            
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 함수 이름과 인자들로 키 생성
                key_parts = [func.__name__]
                key_parts.extend([str(arg) for arg in args])
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                
                key_string = ":".join(key_parts)
                cache_key = hashlib.md5(key_string.encode()).hexdigest()
            
            # 캐시에서 조회
            cached_result = cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # 함수 실행 및 결과 캐싱
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl, namespace)
            
            return result
        
        return wrapper
    return decorator


def async_cached(ttl: int = 3600, namespace: str = "default", key_func: Optional[Callable] = None):
    """비동기 함수 결과 캐싱 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_manager = CacheManager()
            
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend([str(arg) for arg in args])
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                
                key_string = ":".join(key_parts)
                cache_key = hashlib.md5(key_string.encode()).hexdigest()
            
            # 캐시에서 조회
            cached_result = cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # 함수 실행 및 결과 캐싱
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl, namespace)
            
            return result
        
        return wrapper
    return decorator


class CacheInvalidator:
    """캐시 무효화 관리"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.invalidation_rules = {}
    
    def add_invalidation_rule(self, trigger: str, affected_namespaces: List[str]):
        """무효화 규칙 추가"""
        if trigger not in self.invalidation_rules:
            self.invalidation_rules[trigger] = []
        self.invalidation_rules[trigger].extend(affected_namespaces)
    
    def invalidate_by_trigger(self, trigger: str) -> Dict[str, int]:
        """트리거에 의한 캐시 무효화"""
        invalidated_counts = {}
        
        if trigger in self.invalidation_rules:
            for namespace in self.invalidation_rules[trigger]:
                count = self.cache_manager.flush_namespace(namespace)
                invalidated_counts[namespace] = count
        
        return invalidated_counts
    
    def setup_default_rules(self):
        """기본 무효화 규칙 설정"""
        # 상품 관련 무효화
        self.add_invalidation_rule("product_updated", ["products", "inventory", "recommendations"])
        self.add_invalidation_rule("product_created", ["products", "categories"])
        self.add_invalidation_rule("product_deleted", ["products", "inventory", "recommendations"])
        
        # 고객 관련 무효화
        self.add_invalidation_rule("customer_updated", ["customers", "segments", "analytics"])
        self.add_invalidation_rule("order_created", ["customers", "analytics", "recommendations"])
        
        # 캠페인 관련 무효화
        self.add_invalidation_rule("campaign_updated", ["marketing", "segments"])
        self.add_invalidation_rule("campaign_executed", ["marketing", "analytics"])


# 글로벌 캐시 매니저 인스턴스
cache_manager = CacheManager()
cache_invalidator = CacheInvalidator(cache_manager)

# 기본 무효화 규칙 설정
cache_invalidator.setup_default_rules()