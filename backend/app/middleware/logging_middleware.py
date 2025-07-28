"""
로깅 미들웨어
모든 HTTP 요청/응답을 로깅하고 성능 메트릭을 수집
"""
import time
import json
import uuid
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import logging

logger = logging.getLogger(__name__)
# Temporarily disabled due to dependency issues
# from app.services.monitoring.metrics_collector import metrics_collector, APIMetrics
# from app.core.redis_client import get_redis


class LoggingMiddleware(BaseHTTPMiddleware):
    """HTTP 요청/응답 로깅 미들웨어"""
    
    def __init__(self, app: ASGIApp, skip_paths: Optional[list] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 스킵할 경로 체크
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
            
        # 요청 시작 시간
        start_time = time.time()
        
        # 요청 정보 로깅
        request_body = await self._get_request_body(request)
        self._log_request(request, request_id, request_body)
        
        # 요청 처리
        response = None
        error_message = None
        
        try:
            response = await call_next(request)
            
            # 응답 시간 계산
            duration = (time.time() - start_time) * 1000  # 밀리초
            
            # 응답 로깅
            self._log_response(request, response, request_id, duration)
            
            # 메트릭 수집
            # APIMetrics.record_request(
            #     method=request.method,
            #     path=self._normalize_path(request.url.path),
            #     status_code=response.status_code,
            #     duration=duration
            # )
            
            # 느린 요청 감지
            if duration > 1000:  # 1초 이상
                await self._log_slow_request(request, response, duration, request_id)
                
            # 응답 헤더에 요청 ID 추가
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.2f}ms"
            
            return response
            
        except Exception as e:
            # 에러 처리
            duration = (time.time() - start_time) * 1000
            error_message = str(e)
            
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration,
                    "error": error_message
                },
                exc_info=True
            )
            
            # 에러 메트릭 수집 - APIMetrics가 구현되면 활성화
            # APIMetrics.record_request(
            #     method=request.method,
            #     path=self._normalize_path(request.url.path),
            #     status_code=500,
            #     duration=duration
            # )
            
            raise
            
    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """요청 바디 읽기 (주의: 스트림을 소비하므로 다시 설정 필요)"""
        if request.method not in ["POST", "PUT", "PATCH"]:
            return None
            
        try:
            body = await request.body()
            
            # 바디를 다시 읽을 수 있도록 설정
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
            
            # JSON 파싱 시도
            if body:
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return {"raw": body.decode("utf-8", errors="ignore")[:1000]}  # 최대 1000자
                    
        except Exception as e:
            logger.warning(f"Failed to read request body: {e}")
            
        return None
        
    def _log_request(self, request: Request, request_id: str, body: Optional[Dict[str, Any]]):
        """요청 로깅"""
        # 민감한 정보 제거
        safe_body = self._sanitize_data(body) if body else None
        safe_headers = self._sanitize_headers(dict(request.headers))
        
        logger.info(
            f"HTTP Request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": safe_headers,
                "body": safe_body,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
    def _log_response(self, request: Request, response: Response, request_id: str, duration: float):
        """응답 로깅"""
        logger.info(
            f"HTTP Response",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "content_length": response.headers.get("content-length", 0)
            }
        )
        
    async def _log_slow_request(self, request: Request, response: Response, duration: float, request_id: str):
        """느린 요청 상세 로깅"""
        logger.warning(
            f"Slow request detected",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration, 2),
                "status_code": response.status_code,
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        # Redis에 느린 요청 정보 저장
        try:
            redis = await get_redis()
            if redis:
                slow_request_data = {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                key = f"monitoring:slow_requests:{datetime.utcnow().strftime('%Y%m%d')}"
                await redis.lpush(key, json.dumps(slow_request_data))
                await redis.expire(key, 7 * 24 * 3600)  # 7일 보관
                
        except Exception as e:
            logger.error(f"Failed to log slow request to Redis: {e}")
            
    def _normalize_path(self, path: str) -> str:
        """경로 정규화 (파라미터 제거)"""
        # /users/123 -> /users/{id}
        # /orders/abc-123 -> /orders/{id}
        parts = path.strip("/").split("/")
        normalized_parts = []
        
        for i, part in enumerate(parts):
            # UUID 패턴
            if len(part) == 36 and part.count("-") == 4:
                normalized_parts.append("{id}")
            # 숫자 ID
            elif part.isdigit():
                normalized_parts.append("{id}")
            # 일반적인 ID 패턴 (영숫자와 대시)
            elif i > 0 and len(part) > 10 and "-" in part:
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)
                
        return "/" + "/".join(normalized_parts)
        
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """민감한 정보 제거"""
        if not isinstance(data, dict):
            return data
            
        sensitive_fields = [
            "password", "token", "secret", "api_key", "authorization",
            "credit_card", "card_number", "cvv", "ssn"
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
                
        return sanitized
        
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """헤더에서 민감한 정보 제거"""
        sensitive_headers = ["authorization", "cookie", "x-api-key", "x-auth-token"]
        
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
                
        return sanitized


class RequestContextMiddleware(BaseHTTPMiddleware):
    """요청 컨텍스트 설정 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 요청 컨텍스트 설정
        request.state.start_time = time.time()
        
        # 사용자 정보 추가 (인증 후)
        if hasattr(request.state, "user"):
            request.state.user_id = request.state.user.id
            request.state.user_email = request.state.user.email
            
        response = await call_next(request)
        
        return response


# 커스텀 APIRoute 클래스 (자동 로깅)
class LoggingAPIRoute(APIRoute):
    """자동 로깅이 적용된 APIRoute"""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # 엔드포인트 이름 로깅
            logger.debug(
                f"Endpoint called: {self.endpoint.__name__}",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "endpoint": self.endpoint.__name__,
                    "path": self.path,
                    "methods": list(self.methods)
                }
            )
            
            return await original_route_handler(request)
            
        return custom_route_handler