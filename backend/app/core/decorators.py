"""
데이터베이스 작업을 위한 데코레이터
트랜잭션 관리, 캐싱, 재시도 등
"""
from functools import wraps
from typing import Any, Callable, Optional
import asyncio
import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def transactional(func: Callable) -> Callable:
    """
    트랜잭션 데코레이터
    함수 실행을 트랜잭션으로 감싸고 실패 시 자동 롤백
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        # 이미 트랜잭션 내부인 경우 그대로 실행
        if hasattr(self.db, 'in_transaction') and self.db.in_transaction():
            return await func(self, *args, **kwargs)
        
        # 새 트랜잭션 시작
        async with self.db.begin():
            try:
                result = await func(self, *args, **kwargs)
                logger.debug(f"Transaction completed for {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Transaction failed for {func.__name__}: {str(e)}")
                raise
    
    return wrapper


def cached_query(ttl: int = 300, key_prefix: Optional[str] = None):
    """
    쿼리 결과 캐싱 데코레이터
    
    Args:
        ttl: Time to live in seconds
        key_prefix: 캐시 키 접두사
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 캐시 매니저가 없으면 그냥 실행
            if not hasattr(self, 'cache'):
                return await func(self, *args, **kwargs)
            
            # 캐시 키 생성
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)
            
            # 캐시 확인
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return json.loads(cached_result)
            
            # 함수 실행
            result = await func(self, *args, **kwargs)
            
            # 결과 캐싱 (직렬화 가능한 경우만)
            try:
                await self.cache.set(cache_key, json.dumps(result, default=str), ttl)
                logger.debug(f"Cached result for {func.__name__}")
            except (TypeError, ValueError):
                logger.warning(f"Cannot cache result for {func.__name__} - not JSON serializable")
            
            return result
        
        return wrapper
    return decorator


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    에러 발생 시 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        delay: 초기 대기 시간 (초)
        backoff: 재시도마다 대기 시간 증가 배수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {str(e)}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All attempts failed for {func.__name__}")
            
            raise last_exception
        
        return wrapper
    return decorator


def measure_performance(func: Callable) -> Callable:
    """
    함수 실행 시간 측정 데코레이터
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = asyncio.get_event_loop().time()
        
        try:
            result = await func(*args, **kwargs)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed > 1.0:  # 1초 이상 걸린 경우 경고
                logger.warning(f"{func.__name__} took {elapsed:.2f}s")
            else:
                logger.debug(f"{func.__name__} took {elapsed:.3f}s")
            
            return result
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.2f}s: {str(e)}")
            raise
    
    return wrapper


def validate_input(**validators):
    """
    입력 값 검증 데코레이터
    
    Example:
        @validate_input(order_id=str, quantity=lambda x: x > 0)
        async def process_order(self, order_id: str, quantity: int):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 함수 시그니처에서 인수 이름 매핑
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # 검증 실행
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    
                    if isinstance(validator, type):
                        # 타입 검증
                        if not isinstance(value, validator):
                            raise TypeError(
                                f"{param_name} must be {validator.__name__}, got {type(value).__name__}"
                            )
                    elif callable(validator):
                        # 사용자 정의 검증
                        if not validator(value):
                            raise ValueError(f"Invalid value for {param_name}: {value}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def bulk_operation(batch_size: int = 100):
    """
    대량 작업을 배치로 처리하는 데코레이터
    
    Args:
        batch_size: 배치 크기
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, items: list, *args, **kwargs):
            results = []
            
            # 배치로 나누어 처리
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_results = await func(self, batch, *args, **kwargs)
                results.extend(batch_results)
                
                # 배치 간 짧은 대기 (DB 부하 방지)
                if i + batch_size < len(items):
                    await asyncio.sleep(0.1)
            
            return results
        
        return wrapper
    return decorator


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict, prefix: Optional[str]) -> str:
    """캐시 키 생성"""
    # 함수 이름과 모듈
    key_parts = [func.__module__, func.__name__]
    
    # 접두사 추가
    if prefix:
        key_parts.insert(0, prefix)
    
    # self 제외한 인수들
    if args and hasattr(args[0], '__class__'):
        # 첫 번째 인수가 self인 경우 제외
        key_args = args[1:]
    else:
        key_args = args
    
    # 인수를 문자열로 변환
    key_data = {
        'args': [str(arg) for arg in key_args],
        'kwargs': {k: str(v) for k, v in sorted(kwargs.items())}
    }
    
    # 해시 생성
    key_str = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()[:8]
    
    return f"{':'.join(key_parts)}:{key_hash}"