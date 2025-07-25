"""
Rate Limiting 미들웨어
API 요청 속도 제한
"""
from typing import Callable, Optional
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
from datetime import datetime, timedelta
import json
import hashlib

from ..core.config_v2 import settings


class RateLimiter:
    """커스텀 Rate Limiter"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_limit = self._parse_rate_limit(settings.RATE_LIMIT_DEFAULT)
    
    def _parse_rate_limit(self, limit_string: str) -> tuple[int, int]:
        """Rate limit 문자열 파싱 (예: "100/minute")"""
        count, period = limit_string.split("/")
        count = int(count)
        
        period_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        return count, period_seconds.get(period, 60)
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Rate limit 키 생성"""
        return f"rate_limit:{identifier}:{endpoint}"
    
    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: Optional[str] = None
    ) -> tuple[bool, dict]:
        """Rate limit 확인"""
        if limit:
            max_requests, window_seconds = self._parse_rate_limit(limit)
        else:
            max_requests, window_seconds = self.default_limit
        
        key = self._get_key(identifier, endpoint)
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # 현재 윈도우의 요청 수 확인
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start.timestamp())
        pipe.zcard(key)
        pipe.zadd(key, {str(now.timestamp()): now.timestamp()})
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        request_count = results[1]
        
        # Rate limit 정보
        headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(max(0, max_requests - request_count - 1)),
            "X-RateLimit-Reset": str(int((now + timedelta(seconds=window_seconds)).timestamp()))
        }
        
        if request_count >= max_requests:
            return False, headers
        
        return True, headers


class RateLimitMiddleware:
    """Rate Limiting 미들웨어"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        
        # Redis 연결
        if settings.RATE_LIMIT_ENABLED and settings.RATE_LIMIT_STORAGE_URL:
            self.redis_client = redis.from_url(
                str(settings.RATE_LIMIT_STORAGE_URL),
                decode_responses=True
            )
            self.rate_limiter = RateLimiter(self.redis_client)
        else:
            self.rate_limiter = None
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """미들웨어 실행"""
        if not self.rate_limiter or not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Rate limit 체크 제외 경로
        excluded_paths = ["/docs", "/redoc", "/openapi.json", "/health"]
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return await call_next(request)
        
        # 식별자 추출 (IP 주소 또는 인증된 사용자)
        identifier = get_remote_address(request)
        
        # 인증된 사용자는 더 높은 제한
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # 토큰에서 사용자 ID 추출 (간단한 해시 사용)
            token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:8]
            identifier = f"user:{token_hash}"
            limit = "1000/minute"  # 인증된 사용자는 더 높은 제한
        else:
            limit = None  # 기본 제한 사용
        
        # Rate limit 확인
        allowed, headers = await self.rate_limiter.check_rate_limit(
            identifier,
            request.url.path,
            limit
        )
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": 429,
                        "message": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
                        "type": "rate_limit_exceeded"
                    }
                },
                headers=headers
            )
        
        # 요청 처리
        response = await call_next(request)
        
        # Rate limit 헤더 추가
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


def setup_rate_limiting(app: FastAPI):
    """Rate limiting 설정"""
    if settings.RATE_LIMIT_ENABLED:
        # SlowAPI 기본 limiter 설정
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[settings.RATE_LIMIT_DEFAULT],
            storage_uri=str(settings.RATE_LIMIT_STORAGE_URL) if settings.RATE_LIMIT_STORAGE_URL else None
        )
        
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        
        # 커스텀 미들웨어 추가
        app.add_middleware(RateLimitMiddleware)
        
        return limiter
    
    return None