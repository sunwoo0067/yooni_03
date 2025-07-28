"""
GraphQL 쿼리 결과 캐싱 시스템
"""
import json
import hashlib
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps

from .cache import cache_manager
from .config import get_settings

logger = logging.getLogger(__name__)


class GraphQLCacheManager:
    """GraphQL 쿼리 전용 캐시 매니저"""
    
    def __init__(self):
        self.settings = get_settings()
        self.default_ttl = 300  # 기본 5분
        
    def _generate_cache_key(
        self, 
        query: str, 
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None
    ) -> str:
        """GraphQL 쿼리용 캐시 키 생성"""
        # 쿼리 정규화 (공백, 줄바꿈 제거)
        normalized_query = ' '.join(query.split())
        
        # 캐시 키 구성 요소
        cache_data = {
            "query": normalized_query,
            "variables": variables or {},
            "operation_name": operation_name
        }
        
        # JSON 직렬화 후 해시 생성
        json_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.md5(json_str.encode()).hexdigest()
        
        return f"{self.settings.CACHE_KEY_PREFIX}graphql:{hash_value}"
        
    async def get_cached_result(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """캐시된 GraphQL 쿼리 결과 조회"""
        cache_key = self._generate_cache_key(query, variables, operation_name)
        
        try:
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"GraphQL cache hit for operation: {operation_name or 'unnamed'}")
                return cached_result
        except Exception as e:
            logger.error(f"Error retrieving GraphQL cache: {e}")
            
        return None
        
    async def cache_result(
        self,
        query: str,
        result: Dict[str, Any],
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """GraphQL 쿼리 결과 캐싱"""
        # 오류 응답은 캐싱하지 않음
        if "errors" in result and result["errors"]:
            return False
            
        cache_key = self._generate_cache_key(query, variables, operation_name)
        ttl = ttl or self.default_ttl
        
        try:
            success = await cache_manager.set(cache_key, result, ttl)
            if success:
                logger.debug(
                    f"Cached GraphQL result for operation: {operation_name or 'unnamed'} "
                    f"(TTL: {ttl}s)"
                )
            return success
        except Exception as e:
            logger.error(f"Error caching GraphQL result: {e}")
            return False
            
    async def invalidate_by_type(self, type_name: str):
        """특정 타입과 관련된 모든 캐시 무효화"""
        # GraphQL 캐시 패턴으로 삭제
        pattern = f"{self.settings.CACHE_KEY_PREFIX}graphql:*"
        deleted = await cache_manager.clear_pattern(pattern)
        logger.info(f"Invalidated {deleted} GraphQL cache entries for type: {type_name}")
        return deleted


# 싱글톤 인스턴스
graphql_cache_manager = GraphQLCacheManager()


def cache_graphql_query(
    ttl: Optional[int] = None,
    cache_errors: bool = False,
    key_fields: Optional[list] = None
):
    """
    GraphQL 쿼리 결과를 캐싱하는 데코레이터
    
    Args:
        ttl: 캐시 TTL (초)
        cache_errors: 오류 응답도 캐싱할지 여부
        key_fields: 캐시 키에 포함할 추가 필드
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
            self,
            query: str,
            variables: Optional[Dict[str, Any]] = None,
            *args,
            **kwargs
        ):
            # 캐싱이 비활성화된 경우
            if not self.settings.AI_CACHE_ENABLED:
                return await func(self, query, variables, *args, **kwargs)
                
            # 작업 이름 추출 (있는 경우)
            operation_name = kwargs.get('operation_name')
            if not operation_name:
                # 쿼리에서 작업 이름 추출 시도
                operation_match = query.strip().split()[1] if query.strip().split() else None
                operation_name = operation_match
                
            # 캐시된 결과 확인
            cached_result = await graphql_cache_manager.get_cached_result(
                query, variables, operation_name
            )
            if cached_result is not None:
                return cached_result
                
            # 실제 쿼리 실행
            result = await func(self, query, variables, *args, **kwargs)
            
            # 결과 캐싱
            if result and (cache_errors or "errors" not in result):
                await graphql_cache_manager.cache_result(
                    query, result, variables, operation_name, ttl
                )
                
            return result
            
        return wrapper
    return decorator


def invalidate_graphql_cache(type_names: list):
    """
    GraphQL 캐시를 무효화하는 데코레이터
    뮤테이션 실행 후 관련 캐시를 자동으로 무효화
    
    Args:
        type_names: 무효화할 GraphQL 타입 이름 목록
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 함수 실행
            result = await func(*args, **kwargs)
            
            # 성공한 경우 캐시 무효화
            if result and "errors" not in result:
                for type_name in type_names:
                    await graphql_cache_manager.invalidate_by_type(type_name)
                    
            return result
            
        return wrapper
    return decorator