"""
로깅 미들웨어
요청/응답 로깅, 에러 추적, 성능 모니터링
"""
import time
import json
import logging
import traceback
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
import uuid
from datetime import datetime

from ..core.config_v2 import settings
from ..utils.logger import setup_logger, get_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.excluded_paths = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """미들웨어 처리"""
        # 제외 경로 확인
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 요청 정보 수집
        start_time = time.time()
        request_body = None
        
        # Body 읽기 (POST, PUT, PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                request_body = body_bytes.decode("utf-8")
                # Body를 다시 사용할 수 있도록 설정
                async def receive() -> Message:
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
            except Exception as e:
                self.logger.warning(f"Failed to read request body: {e}")
        
        # 요청 로깅
        self.logger.info(
            f"REQUEST {request_id} - {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "body": self._sanitize_body(request_body) if request_body else None
            }
        )
        
        # 요청 처리
        response = None
        error_detail = None
        
        try:
            response = await call_next(request)
        except Exception as e:
            # 에러 로깅
            error_detail = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            
            self.logger.error(
                f"ERROR {request_id} - {type(e).__name__}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error": error_detail
                }
            )
            
            # 에러 응답
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": 500,
                        "message": "내부 서버 오류가 발생했습니다",
                        "type": "internal_error",
                        "request_id": request_id
                    }
                }
            )
        
        # 처리 시간 계산
        process_time = time.time() - start_time
        
        # 응답 헤더 추가
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        # 응답 로깅
        log_level = logging.INFO
        if response.status_code >= 400:
            log_level = logging.WARNING
        if response.status_code >= 500:
            log_level = logging.ERROR
        
        self.logger.log(
            log_level,
            f"RESPONSE {request_id} - {response.status_code} in {process_time:.3f}s",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": process_time,
                "path": request.url.path,
                "method": request.method,
                "error": error_detail
            }
        )
        
        # 느린 요청 경고
        if process_time > 1.0:
            self.logger.warning(
                f"SLOW REQUEST {request_id} - {request.method} {request.url.path} took {process_time:.3f}s"
            )
        
        return response
    
    def _sanitize_body(self, body: str, max_length: int = 1000) -> str:
        """요청 본문 정리 (민감한 정보 제거)"""
        if not body:
            return ""
        
        # JSON 파싱 시도
        try:
            data = json.loads(body)
            
            # 민감한 필드 마스킹
            sensitive_fields = {
                "password", "token", "secret", "api_key", "credit_card",
                "card_number", "cvv", "pin", "ssn", "social_security"
            }
            
            def mask_sensitive(obj):
                if isinstance(obj, dict):
                    return {
                        k: "***MASKED***" if k.lower() in sensitive_fields else mask_sensitive(v)
                        for k, v in obj.items()
                    }
                elif isinstance(obj, list):
                    return [mask_sensitive(item) for item in obj]
                else:
                    return obj
            
            sanitized = mask_sensitive(data)
            result = json.dumps(sanitized, ensure_ascii=False)
            
        except json.JSONDecodeError:
            # JSON이 아닌 경우 그대로 사용
            result = body
        
        # 길이 제한
        if len(result) > max_length:
            result = result[:max_length] + "..."
        
        return result


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """에러 추적 미들웨어 (Sentry 연동)"""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.logger = get_logger(__name__)
        
        # Sentry 초기화
        if settings.SENTRY_DSN:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.fastapi import FastAPIIntegration
                from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
                
                sentry_sdk.init(
                    dsn=settings.SENTRY_DSN,
                    integrations=[
                        FastAPIIntegration(transaction_style="endpoint"),
                        SqlalchemyIntegration(),
                    ],
                    traces_sample_rate=0.1 if settings.is_production else 1.0,
                    environment=settings.ENVIRONMENT,
                    release=settings.APP_VERSION,
                )
                
                self.sentry_enabled = True
                self.logger.info("Sentry error tracking initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Sentry: {e}")
                self.sentry_enabled = False
        else:
            self.sentry_enabled = False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """에러 추적 처리"""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Sentry에 에러 전송
            if self.sentry_enabled:
                import sentry_sdk
                sentry_sdk.capture_exception(e)
            
            # 에러 로깅
            request_id = getattr(request.state, "request_id", "unknown")
            self.logger.error(
                f"Unhandled exception in request {request_id}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            # 에러 응답
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": 500,
                        "message": "서버 오류가 발생했습니다",
                        "type": "internal_error",
                        "request_id": request_id
                    }
                }
            )


def setup_logging_middleware(app: FastAPI):
    """로깅 미들웨어 설정"""
    # 로거 설정
    setup_logger()
    
    # 미들웨어 추가 (순서 중요)
    app.add_middleware(ErrorTrackingMiddleware)
    app.add_middleware(LoggingMiddleware)