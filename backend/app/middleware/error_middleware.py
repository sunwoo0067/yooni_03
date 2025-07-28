"""
드롭쉬핑 프로젝트용 에러 미들웨어

통합 에러 핸들링, 모니터링, 로깅을 제공하는
포괄적인 에러 처리 미들웨어입니다.
"""

import asyncio
import time
import uuid
import traceback
from typing import Callable, Dict, Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import HTTPException

from app.core.exceptions import AppException, ErrorSeverity
from app.core.error_handler import ErrorHandler
from app.core.logging_utils import get_logger, LogCategory
from app.core.monitoring import dropshipping_monitor
from app.core.retry import initialize_recovery_strategies

logger = get_logger("dropshipping.middleware.error")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """통합 에러 처리 미들웨어"""
    
    def __init__(self, app, enable_monitoring: bool = True, enable_recovery: bool = True):
        super().__init__(app)
        self.error_handler = ErrorHandler()
        self.enable_monitoring = enable_monitoring
        self.enable_recovery = enable_recovery
        
        # 복구 전략 초기화
        if enable_recovery:
            initialize_recovery_strategies()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """미들웨어 실행"""
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 로깅 컨텍스트 설정
        logger.set_context(correlation_id=request_id)
        
        # 요청 시작 시간
        start_time = time.time()
        
        # 요청 정보 로깅
        await self._log_request_start(request, request_id)
        
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 성공 응답 로깅
            await self._log_request_success(request, response, start_time, request_id)
            
            return response
            
        except Exception as e:
            # 에러 처리 및 응답 생성
            return await self._handle_error(request, e, start_time, request_id)
    
    async def _log_request_start(self, request: Request, request_id: str):
        """요청 시작 로깅"""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        logger.info(
            f"Request started: {request.method} {request.url}",
            category=LogCategory.SYSTEM,
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=client_ip,
            user_agent=user_agent,
            content_type=request.headers.get("content-type"),
            content_length=request.headers.get("content-length")
        )
        
        # 모니터링 메트릭
        if self.enable_monitoring:
            dropshipping_monitor.metrics_collector.increment_counter(
                "http_requests_total",
                tags={
                    "method": request.method,
                    "path": request.url.path
                }
            )
    
    async def _log_request_success(
        self,
        request: Request,
        response: Response,
        start_time: float,
        request_id: str
    ):
        """성공 응답 로깅"""
        process_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Request completed: {request.method} {request.url}",
            category=LogCategory.SYSTEM,
            request_id=request_id,
            status_code=response.status_code,
            process_time_ms=process_time,
            response_size=len(response.body) if hasattr(response, 'body') else None
        )
        
        # 성능 메트릭
        if self.enable_monitoring:
            dropshipping_monitor.metrics_collector.record_timer(
                "http_request_duration",
                process_time,
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
            
            dropshipping_monitor.metrics_collector.increment_counter(
                "http_responses_total",
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
    
    async def _handle_error(
        self,
        request: Request,
        exception: Exception,
        start_time: float,
        request_id: str
    ) -> JSONResponse:
        """에러 처리"""
        process_time = (time.time() - start_time) * 1000
        
        # 에러 컨텍스트 수집
        error_context = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "process_time_ms": process_time,
            "traceback": traceback.format_exc()
        }
        
        # 사용자 정보 추가 (가능한 경우)
        if hasattr(request.state, "user_id"):
            error_context["user_id"] = request.state.user_id
        
        # AppException으로 변환 (필요한 경우)
        if not isinstance(exception, AppException):
            exception = self._convert_to_app_exception(exception, error_context)
        
        # 에러 로깅
        logger.log_exception(
            exception,
            context=error_context,
            include_traceback=True
        )
        
        # 모니터링에 에러 기록
        if self.enable_monitoring:
            await dropshipping_monitor.record_error(exception, error_context)
            
            # 에러 메트릭
            dropshipping_monitor.metrics_collector.increment_counter(
                "http_errors_total",
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "error_code": exception.error_code,
                    "severity": exception.severity.value
                }
            )
        
        # 에러 응답 생성
        return self.error_handler.handle_exception(exception, request)
    
    def _convert_to_app_exception(self, exception: Exception, context: Dict[str, Any]) -> AppException:
        """일반 예외를 AppException으로 변환"""
        
        # HTTPException 처리
        if isinstance(exception, HTTPException):
            return AppException(
                message=str(exception.detail),
                error_code="HTTP_ERROR",
                status_code=exception.status_code,
                severity=ErrorSeverity.LOW if exception.status_code < 500 else ErrorSeverity.HIGH,
                context=context
            )
        
        # 네트워크 관련 예외
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return AppException(
                message=f"네트워크 오류: {str(exception)}",
                error_code="NETWORK_ERROR",
                status_code=503,
                severity=ErrorSeverity.HIGH,
                context=context
            )
        
        # 파일 시스템 관련 예외
        if isinstance(exception, (FileNotFoundError, PermissionError)):
            return AppException(
                message=f"파일 시스템 오류: {str(exception)}",
                error_code="FILESYSTEM_ERROR",
                status_code=500,
                severity=ErrorSeverity.MEDIUM,
                context=context
            )
        
        # 기본 처리
        return AppException(
            message=f"예상치 못한 오류가 발생했습니다: {str(exception)}",
            error_code="UNEXPECTED_ERROR",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            context=context
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 뒤에 있는 경우)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 기본 클라이언트 주소
        if request.client:
            return request.client.host
        
        return "unknown"


class SecurityMiddleware(BaseHTTPMiddleware):
    """보안 관련 미들웨어"""
    
    def __init__(self, app, rate_limit_enabled: bool = True):
        super().__init__(app)
        self.rate_limit_enabled = rate_limit_enabled
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """보안 체크 및 요청 처리"""
        
        # Rate limiting 체크
        if self.rate_limit_enabled:
            if not await self._check_rate_limit(request):
                logger.log_security_event(
                    "rate_limit_exceeded",
                    f"Rate limit exceeded for IP: {self._get_client_ip(request)}",
                    severity="medium",
                    ip_address=self._get_client_ip(request)
                )
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요",
                            "user_message": "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해 주세요"
                        }
                    },
                    headers={"Retry-After": "60"}
                )
        
        # 의심스러운 요청 패턴 감지
        await self._detect_suspicious_patterns(request)
        
        # 요청 처리
        response = await call_next(request)
        
        # 보안 헤더 추가
        self._add_security_headers(response)
        
        return response
    
    async def _check_rate_limit(self, request: Request, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """Rate limiting 체크"""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # 현재 시간 윈도우
        window_start = current_time - window_seconds
        
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {"requests": [], "last_reset": current_time}
        
        client_data = self.request_counts[client_ip]
        
        # 오래된 요청 기록 제거
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if req_time > window_start
        ]
        
        # 현재 요청 추가
        client_data["requests"].append(current_time)
        
        # Rate limit 확인
        return len(client_data["requests"]) <= max_requests
    
    async def _detect_suspicious_patterns(self, request: Request):
        """의심스러운 요청 패턴 감지"""
        
        # SQL 인젝션 패턴 감지
        suspicious_sql_patterns = [
            "union select", "drop table", "insert into", "delete from",
            "'; --", "' or 1=1", "' or '1'='1"
        ]
        
        query_string = str(request.url.query).lower()
        path = request.url.path.lower()
        
        for pattern in suspicious_sql_patterns:
            if pattern in query_string or pattern in path:
                logger.log_security_event(
                    "sql_injection_attempt",
                    f"Potential SQL injection attempt detected: {pattern}",
                    severity="high",
                    ip_address=self._get_client_ip(request),
                    request_path=request.url.path,
                    query_params=dict(request.query_params)
                )
                break
        
        # XSS 패턴 감지
        xss_patterns = ["<script", "javascript:", "onload=", "onerror="]
        
        for pattern in xss_patterns:
            if pattern in query_string:
                logger.log_security_event(
                    "xss_attempt",
                    f"Potential XSS attempt detected: {pattern}",
                    severity="high",
                    ip_address=self._get_client_ip(request),
                    request_path=request.url.path
                )
                break
    
    def _add_security_headers(self, response: Response):
        """보안 헤더 추가"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청 로깅 미들웨어"""
    
    def __init__(self, app, log_request_body: bool = False, log_response_body: bool = False):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청/응답 로깅"""
        
        # 요청 본문 로깅 (필요한 경우)
        request_body = None
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # 민감한 정보 마스킹
                    request_body = self._mask_sensitive_data(body.decode())
            except Exception:
                request_body = "Unable to read request body"
        
        # 요청 처리
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        # 상세 요청 로깅
        logger.info(
            f"Detailed request log: {request.method} {request.url}",
            category=LogCategory.AUDIT,
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time_ms=process_time,
            request_headers=dict(request.headers),
            response_headers=dict(response.headers),
            request_body=request_body if self.log_request_body else None,
            client_ip=self._get_client_ip(request)
        )
        
        return response
    
    def _mask_sensitive_data(self, data: str) -> str:
        """민감한 데이터 마스킹"""
        import re
        
        # 비밀번호 마스킹
        data = re.sub(r'"password"\s*:\s*"[^"]*"', '"password": "***"', data)
        data = re.sub(r'"token"\s*:\s*"[^"]*"', '"token": "***"', data)
        data = re.sub(r'"api_key"\s*:\s*"[^"]*"', '"api_key": "***"', data)
        
        # 신용카드 번호 마스킹
        data = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '****-****-****-****', data)
        
        return data
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """성능 모니터링 미들웨어"""
    
    def __init__(self, app, slow_request_threshold_ms: float = 1000):
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """성능 모니터링"""
        start_time = time.time()
        
        # 메모리 사용량 측정 (시작)
        import psutil
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        # 요청 처리
        response = await call_next(request)
        
        # 성능 메트릭 계산
        process_time = (time.time() - start_time) * 1000
        memory_after = process.memory_info().rss
        memory_delta = memory_after - memory_before
        
        # 성능 메트릭 기록
        if dropshipping_monitor.monitoring_enabled:
            dropshipping_monitor.metrics_collector.record_timer(
                "request_processing_time",
                process_time,
                tags={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
            
            dropshipping_monitor.metrics_collector.set_gauge(
                "memory_usage_bytes",
                memory_after,
                tags={"process": "main"}
            )
        
        # 느린 요청 감지
        if process_time > self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request detected: {request.method} {request.url}",
                category=LogCategory.PERFORMANCE,
                process_time_ms=process_time,
                memory_delta_bytes=memory_delta,
                threshold_ms=self.slow_request_threshold_ms
            )
            
            # 성능 알림 (필요한 경우)
            if process_time > self.slow_request_threshold_ms * 3:  # 3배 이상 느린 경우
                from app.core.monitoring import Alert, AlertType
                from app.core.monitoring import dropshipping_monitor
                
                alert = Alert(
                    alert_id=f"slow_request_{int(time.time())}",
                    alert_type=AlertType.WARNING,
                    title="매우 느린 요청 감지",
                    message=f"{request.method} {request.url} 요청이 {process_time:.1f}ms 소요되었습니다",
                    severity=ErrorSeverity.MEDIUM,
                    timestamp=datetime.utcnow(),
                    context={
                        "method": request.method,
                        "url": str(request.url),
                        "process_time_ms": process_time,
                        "memory_delta_bytes": memory_delta
                    },
                    channels=["slack"]
                )
                
                await dropshipping_monitor.alert_manager.send_alert(alert)
        
        # 성능 헤더 추가
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        response.headers["X-Memory-Delta"] = f"{memory_delta}bytes"
        
        return response


# =============================================================================
# 미들웨어 설정 헬퍼
# =============================================================================

def setup_error_middlewares(app, config: Optional[Dict[str, Any]] = None):
    """에러 처리 미들웨어 설정"""
    if config is None:
        config = {}
    
    # 성능 모니터링 미들웨어
    if config.get("enable_performance_monitoring", True):
        app.add_middleware(
            PerformanceMonitoringMiddleware,
            slow_request_threshold_ms=config.get("slow_request_threshold_ms", 1000)
        )
    
    # 요청 로깅 미들웨어
    if config.get("enable_request_logging", True):
        app.add_middleware(
            RequestLoggingMiddleware,
            log_request_body=config.get("log_request_body", False),
            log_response_body=config.get("log_response_body", False)
        )
    
    # 보안 미들웨어
    if config.get("enable_security", True):
        app.add_middleware(
            SecurityMiddleware,
            rate_limit_enabled=config.get("rate_limit_enabled", True)
        )
    
    # 에러 처리 미들웨어 (가장 바깥쪽)
    app.add_middleware(
        ErrorHandlingMiddleware,
        enable_monitoring=config.get("enable_monitoring", True),
        enable_recovery=config.get("enable_recovery", True)
    )
    
    logger.info("Error handling middlewares configured")


# =============================================================================
# 사용 예시
# =============================================================================

"""
# FastAPI 앱에서 미들웨어 설정
from fastapi import FastAPI
from app.middleware.error_middleware import setup_error_middlewares

app = FastAPI()

# 기본 설정으로 미들웨어 추가
setup_error_middlewares(app)

# 또는 커스텀 설정으로 추가
config = {
    "enable_monitoring": True,
    "enable_recovery": True,
    "enable_security": True,
    "enable_performance_monitoring": True,
    "slow_request_threshold_ms": 2000,
    "rate_limit_enabled": True,
    "log_request_body": False,
    "log_response_body": False
}
setup_error_middlewares(app, config)
"""