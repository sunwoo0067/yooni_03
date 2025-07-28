"""
캐시 서비스
Redis를 사용한 안전한 캐싱 서비스 구현
"""
from typing import Any, Optional, Union
import json
import orjson
from datetime import timedelta, datetime
import redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import logger


class CacheService:
    """캐시 서비스"""
    
    def __init__(self):
        """Redis 연결 초기화"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if hasattr(settings, 'REDIS_PASSWORD') else None,
                decode_responses=False,  # 바이너리 데이터 지원
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 연결 테스트
            self.redis_client.ping()
            logger.info("Redis 연결 성공")
        except RedisError as e:
            logger.error(f"Redis 연결 실패: {str(e)}")
            self.redis_client = None
            
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        if not self.redis_client:
            return None
            
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
                
            # 안전한 JSON 역직렬화만 사용
            try:
                return orjson.loads(value)
            except (orjson.JSONDecodeError, TypeError, ValueError):
                # JSON이 아닌 데이터는 문자열로 반환
                return value.decode('utf-8') if isinstance(value, bytes) else value
                    
        except RedisError as e:
            logger.error(f"캐시 조회 실패: key={key}, error={str(e)}")
            return None
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """캐시에 값 저장"""
        if not self.redis_client:
            return False
            
        try:
            # 안전한 JSON 직렬화만 사용
            try:
                # datetime 객체 처리
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, dict):
                    value = self._convert_datetime_to_str(value)
                    
                serialized_value = orjson.dumps(value)
            except (TypeError, ValueError) as e:
                logger.warning(f"Cannot serialize value for cache: {e}")
                return False
                    
            # TTL 설정
            if ttl:
                return bool(self.redis_client.setex(key, ttl, serialized_value))
            else:
                return bool(self.redis_client.set(key, serialized_value))
                
        except RedisError as e:
            logger.error(f"캐시 저장 실패: key={key}, error={str(e)}")
            return False
            
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if not self.redis_client:
            return False
            
        try:
            return bool(self.redis_client.delete(key))
        except RedisError as e:
            logger.error(f"캐시 삭제 실패: key={key}, error={str(e)}")
            return False
            
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        if not self.redis_client:
            return False
            
        try:
            return bool(self.redis_client.exists(key))
        except RedisError as e:
            logger.error(f"캐시 존재 확인 실패: key={key}, error={str(e)}")
            return False
            
    async def expire(self, key: str, seconds: int) -> bool:
        """키 만료 시간 설정"""
        if not self.redis_client:
            return False
            
        try:
            return bool(self.redis_client.expire(key, seconds))
        except RedisError as e:
            logger.error(f"캐시 만료 설정 실패: key={key}, error={str(e)}")
            return False
            
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """값 증가"""
        if not self.redis_client:
            return None
            
        try:
            return self.redis_client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"캐시 증가 실패: key={key}, error={str(e)}")
            return None
            
    async def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """값 감소"""
        if not self.redis_client:
            return None
            
        try:
            return self.redis_client.decrby(key, amount)
        except RedisError as e:
            logger.error(f"캐시 감소 실패: key={key}, error={str(e)}")
            return None
            
    async def lpush(self, key: str, *values: Any) -> Optional[int]:
        """리스트 왼쪽에 값 추가"""
        if not self.redis_client:
            return None
            
        try:
            serialized_values = []
            for value in values:
                if isinstance(value, (str, int, float)):
                    serialized_values.append(str(value).encode('utf-8'))
                else:
                    serialized_values.append(json.dumps(value).encode('utf-8'))
                    
            return self.redis_client.lpush(key, *serialized_values)
        except RedisError as e:
            logger.error(f"리스트 추가 실패: key={key}, error={str(e)}")
            return None
            
    async def lrange(self, key: str, start: int, stop: int) -> Optional[list]:
        """리스트 범위 조회"""
        if not self.redis_client:
            return None
            
        try:
            values = self.redis_client.lrange(key, start, stop)
            result = []
            
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value.decode('utf-8') if isinstance(value, bytes) else value)
                    
            return result
        except RedisError as e:
            logger.error(f"리스트 조회 실패: key={key}, error={str(e)}")
            return None
            
    async def sadd(self, key: str, *values: Any) -> Optional[int]:
        """셋에 값 추가"""
        if not self.redis_client:
            return None
            
        try:
            serialized_values = []
            for value in values:
                if isinstance(value, (str, int, float)):
                    serialized_values.append(str(value).encode('utf-8'))
                else:
                    serialized_values.append(json.dumps(value).encode('utf-8'))
                    
            return self.redis_client.sadd(key, *serialized_values)
        except RedisError as e:
            logger.error(f"셋 추가 실패: key={key}, error={str(e)}")
            return None
            
    async def smembers(self, key: str) -> Optional[set]:
        """셋 멤버 조회"""
        if not self.redis_client:
            return None
            
        try:
            values = self.redis_client.smembers(key)
            result = set()
            
            for value in values:
                try:
                    result.add(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.add(value.decode('utf-8') if isinstance(value, bytes) else value)
                    
            return result
        except RedisError as e:
            logger.error(f"셋 조회 실패: key={key}, error={str(e)}")
            return None
            
    async def hset(self, key: str, field: str, value: Any) -> Optional[int]:
        """해시에 필드 설정"""
        if not self.redis_client:
            return None
            
        try:
            if isinstance(value, (str, int, float)):
                serialized_value = str(value).encode('utf-8')
            else:
                serialized_value = json.dumps(value).encode('utf-8')
                
            return self.redis_client.hset(key, field, serialized_value)
        except RedisError as e:
            logger.error(f"해시 설정 실패: key={key}, field={field}, error={str(e)}")
            return None
            
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """해시에서 필드 조회"""
        if not self.redis_client:
            return None
            
        try:
            value = self.redis_client.hget(key, field)
            if value is None:
                return None
                
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except RedisError as e:
            logger.error(f"해시 조회 실패: key={key}, field={field}, error={str(e)}")
            return None
            
    async def hgetall(self, key: str) -> Optional[dict]:
        """해시 전체 조회"""
        if not self.redis_client:
            return None
            
        try:
            values = self.redis_client.hgetall(key)
            result = {}
            
            for field, value in values.items():
                field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                try:
                    result[field_str] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field_str] = value.decode('utf-8') if isinstance(value, bytes) else value
                    
            return result
        except RedisError as e:
            logger.error(f"해시 전체 조회 실패: key={key}, error={str(e)}")
            return None
            
    async def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 키 삭제"""
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"패턴 삭제 실패: pattern={pattern}, error={str(e)}")
            return 0
    
    def _convert_datetime_to_str(self, obj):
        """딕셔너리 내의 datetime 객체를 문자열로 변환"""
        if isinstance(obj, dict):
            return {k: v.isoformat() if isinstance(v, datetime) else v for k, v in obj.items()}
        return obj
            
    def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            self.redis_client.close()


# 전역 캐시 서비스 인스턴스
cache_service = CacheService()