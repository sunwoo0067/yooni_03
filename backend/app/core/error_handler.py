"""
중앙 집중식 에러 처리기

모든 에러를 일관되게 처리하고 로깅
"""

import logging
import traceback
from typing import Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
import json

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.core.exceptions import (
    AppException, ErrorSeverity, ErrorRecoveryAction,
    ExternalServiceError, WholesalerAPIError, MarketplaceAPIError,
    AIServiceError, DatabaseError, ValidationError as AppValidationError,
    RateLimitError, ServiceUnavailableError, ConfigurationError,
    NotFoundError, AuthorizationError, ConflictError, BusinessLogicError
)


logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """에러 코드 정의"""
    # 일반 에러
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    BAD_REQUEST = "BAD_REQUEST"
    
    # 비즈니스 로직 에러
    BUSINESS_ERROR = "BUSINESS_ERROR"
    INVENTORY_ERROR = "INVENTORY_ERROR"
    ORDER_ERROR = "ORDER_ERROR"
    PAYMENT_ERROR = "PAYMENT_ERROR"
    
    # 외부 서비스 에러
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    WHOLESALER_API_ERROR = "WHOLESALER_API_ERROR"
    MARKETPLACE_API_ERROR = "MARKETPLACE_API_ERROR"
    
    # 데이터베이스 에러
    DATABASE_ERROR = "DATABASE_ERROR"
    DUPLICATE_ERROR = "DUPLICATE_ERROR"
    
    # 시스템 에러
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorResponse:
    """에러 응답 구조"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: Optional[Any] = None,
        request_id: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.request_id = request_id
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        response = {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "timestamp": self.timestamp
            }
        }
        
        if self.detail:
            response["error"]["detail"] = self.detail
            
        if self.request_id:
            response["error"]["request_id"] = self.request_id
            
        return response


class ErrorHandler:
    """드롭쉬핑 특화 중앙 집중식 에러 처리기"""
    
    def __init__(self):
        # 에러별 복구 전략 매핑
        self.recovery_strategies = {
            ErrorRecoveryAction.RETRY: self._handle_retry_strategy,
            ErrorRecoveryAction.FALLBACK: self._handle_fallback_strategy,
            ErrorRecoveryAction.CIRCUIT_BREAKER: self._handle_circuit_breaker_strategy,
            ErrorRecoveryAction.MANUAL_INTERVENTION: self._handle_manual_intervention_strategy,
            ErrorRecoveryAction.NONE: self._handle_no_recovery_strategy
        }
        
        # 서비스별 폴백 매핑
        self.service_fallbacks = {
            "Ownerclan": ["Zentrade", "Domeggook"],
            "Zentrade": ["Ownerclan", "Domeggook"],
            "Domeggook": ["Ownerclan", "Zentrade"],
            "Gemini": ["Ollama", "OpenAI"],
            "Ollama": ["Gemini", "OpenAI"],
            "OpenAI": ["Gemini", "Ollama"]
        }
    
    def handle_exception(
        self,
        exception: Exception,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """예외를 처리하고 JSON 응답 반환"""
        
        # 요청 ID 및 상관관계 ID 추출
        request_id = self._extract_request_id(request)
        correlation_id = self._extract_correlation_id(request, exception)
        
        # 에러 컨텍스트 수집
        error_context = self._collect_error_context(request, exception)
        
        try:
            # AppException 처리 (드롭쉬핑 특화 예외)
            if isinstance(exception, AppException):
                return self._handle_app_exception(exception, request_id, error_context)
                
            # Pydantic Validation 에러 처리
            if isinstance(exception, ValidationError):
                return self._handle_pydantic_validation_error(exception, request_id, error_context)
                
            # SQLAlchemy 에러 처리
            if isinstance(exception, SQLAlchemyError):
                return self._handle_database_error(exception, request_id, error_context)
                
            # HTTP 예외 처리 (FastAPI HTTPException)
            if hasattr(exception, 'status_code') and hasattr(exception, 'detail'):
                return self._handle_http_exception(exception, request_id, error_context)
                
            # 시스템 에러들
            if isinstance(exception, FileNotFoundError):
                return self._handle_file_not_found(exception, request_id, error_context)
                
            if isinstance(exception, PermissionError):
                return self._handle_permission_error(exception, request_id, error_context)
                
            if isinstance(exception, ConnectionError):
                return self._handle_connection_error(exception, request_id, error_context)
                
            if isinstance(exception, TimeoutError):
                return self._handle_timeout_error(exception, request_id, error_context)
                
            # 알 수 없는 에러
            return self._handle_unknown_error(exception, request_id, error_context)
            
        except Exception as handler_error:
            # 에러 핸들러 자체에서 오류가 발생한 경우
            logger.critical(
                f"Error in error handler: {handler_error}",
                exc_info=True,
                extra={"original_exception": str(exception), "request_id": request_id}
            )
            return self._create_fallback_error_response(request_id)
        
    def _handle_app_exception(
        self,
        exception: AppException,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """AppException 처리 (드롭쉬핑 특화)"""
        
        # 상관관계 ID 설정
        if not exception.correlation_id:
            exception.correlation_id = request_id
        
        # 컨텍스트 정보 추가
        exception.context.update(error_context)
        
        # 에러 로깅
        self._log_structured_error(exception, request_id, error_context)
        
        # 복구 전략 실행
        recovery_result = self._execute_recovery_strategy(exception)
        
        # 모니터링 메트릭 전송
        self._send_error_metrics(exception)
        
        # 알림 발송 (치명적 에러의 경우)
        if exception.is_critical():
            self._send_error_alert(exception)
        
        # 응답 생성
        response_data = exception.to_dict()
        
        # 복구 정보 추가
        if recovery_result:
            response_data['recovery'] = recovery_result
        
        # 보안을 위해 프로덕션에서는 상세 정보 제한
        if self._is_production():
            response_data = self._sanitize_error_response(response_data)
        
        return JSONResponse(
            status_code=exception.status_code,
            content=response_data,
            headers=self._get_error_headers(exception)
        )
        
    def _handle_pydantic_validation_error(
        self,
        exception: ValidationError,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """Pydantic ValidationError 처리"""
        
        # 검증 에러 상세 정보 추출
        field_errors = []
        for error in exception.errors():
            field_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        # AppValidationError로 변환
        app_exception = AppValidationError(
            message="입력 데이터 검증 실패",
            field_errors=field_errors,
            correlation_id=request_id,
            context=error_context
        )
        
        return self._handle_app_exception(app_exception, request_id, error_context)
        
    def _handle_database_error(
        self,
        exception: SQLAlchemyError,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """데이터베이스 에러 처리"""
        
        error_str = str(exception).lower()
        
        # 구체적인 데이터베이스 에러 타입 분석
        if "duplicate" in error_str or "unique" in error_str:
            app_exception = ConflictError(
                message="중복된 데이터가 존재합니다",
                correlation_id=request_id,
                context=error_context,
                detail={"db_error": str(exception)}
            )
        elif "foreign key" in error_str:
            app_exception = BusinessLogicError(
                message="관련된 데이터가 존재하지 않습니다",
                business_rule="foreign_key_constraint",
                correlation_id=request_id,
                context=error_context
            )
        elif "connection" in error_str or "timeout" in error_str:
            app_exception = DatabaseError(
                message="데이터베이스 연결 오류",
                operation="connection",
                correlation_id=request_id,
                context=error_context,
                severity=ErrorSeverity.CRITICAL,
                recovery_action=ErrorRecoveryAction.RETRY
            )
        else:
            app_exception = DatabaseError(
                message="데이터베이스 처리 중 오류가 발생했습니다",
                operation="unknown",
                correlation_id=request_id,
                context=error_context,
                detail={"db_error": str(exception)}
            )
        
        return self._handle_app_exception(app_exception, request_id, error_context)
        
    def _handle_unknown_error(
        self,
        exception: Exception,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """알 수 없는 에러 처리"""
        
        # 알 수 없는 에러를 시스템 예외로 변환
        app_exception = AppException(
            message="예상치 못한 오류가 발생했습니다",
            error_code="UNKNOWN_ERROR",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            recovery_action=ErrorRecoveryAction.MANUAL_INTERVENTION,
            user_message="일시적인 서버 오류입니다. 잠시 후 다시 시도해 주세요",
            correlation_id=request_id,
            context=error_context,
            detail={
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            }
        )
        
        return self._handle_app_exception(app_exception, request_id, error_context)
    
    def _handle_http_exception(
        self,
        exception: Exception,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """FastAPI HTTPException 처리"""
        app_exception = AppException(
            message=str(exception.detail),
            error_code="HTTP_ERROR",
            status_code=exception.status_code,
            severity=ErrorSeverity.LOW if exception.status_code < 500 else ErrorSeverity.HIGH,
            correlation_id=request_id,
            context=error_context
        )
        return self._handle_app_exception(app_exception, request_id, error_context)
    
    def _handle_file_not_found(
        self,
        exception: FileNotFoundError,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """파일 없음 에러 처리"""
        app_exception = NotFoundError(
            resource="파일",
            correlation_id=request_id,
            context=error_context,
            detail={"file_path": str(exception)}
        )
        return self._handle_app_exception(app_exception, request_id, error_context)
    
    def _handle_permission_error(
        self,
        exception: PermissionError,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """권한 에러 처리"""
        app_exception = AuthorizationError(
            message="파일 접근 권한이 없습니다",
            correlation_id=request_id,
            context=error_context
        )
        return self._handle_app_exception(app_exception, request_id, error_context)
    
    def _handle_connection_error(
        self,
        exception: ConnectionError,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """연결 에러 처리"""
        app_exception = ExternalServiceError(
            service_name="외부 서비스",
            message="연결 실패",
            correlation_id=request_id,
            context=error_context,
            severity=ErrorSeverity.HIGH,
            recovery_action=ErrorRecoveryAction.RETRY
        )
        return self._handle_app_exception(app_exception, request_id, error_context)
    
    def _handle_timeout_error(
        self,
        exception: TimeoutError,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ) -> JSONResponse:
        """타임아웃 에러 처리"""
        app_exception = ExternalServiceError(
            service_name="외부 서비스",
            message="요청 시간 초과",
            correlation_id=request_id,
            context=error_context,
            severity=ErrorSeverity.MEDIUM,
            recovery_action=ErrorRecoveryAction.RETRY
        )
        return self._handle_app_exception(app_exception, request_id, error_context)
    
    # =============================================================================
    # 헬퍼 메서드들
    # =============================================================================
    
    def _extract_request_id(self, request: Optional[Request]) -> Optional[str]:
        """요청 ID 추출"""
        if request and hasattr(request.state, "request_id"):
            return request.state.request_id
        return None
    
    def _extract_correlation_id(self, request: Optional[Request], exception: Exception) -> Optional[str]:
        """상관관계 ID 추출"""
        if hasattr(exception, 'correlation_id') and exception.correlation_id:
            return exception.correlation_id
        return self._extract_request_id(request)
    
    def _collect_error_context(self, request: Optional[Request], exception: Exception) -> Dict[str, Any]:
        """에러 컨텍스트 수집"""
        context = {}
        
        if request:
            context.update({
                "method": request.method,
                "url": str(request.url),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type")
            })
            
            # 사용자 정보 추가 (가능한 경우)
            if hasattr(request.state, "user_id"):
                context["user_id"] = request.state.user_id
                
        context.update({
            "exception_type": type(exception).__name__,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return context
    
    def _log_structured_error(
        self,
        exception: AppException,
        request_id: Optional[str],
        error_context: Dict[str, Any]
    ):
        """구조화된 에러 로깅"""
        log_data = {
            "error_code": exception.error_code,
            "severity": exception.severity.value,
            "recovery_action": exception.recovery_action.value,
            "message": exception.message,
            "user_message": exception.user_message,
            "correlation_id": exception.correlation_id,
            "request_id": request_id,
            "context": exception.context,
            "detail": exception.detail,
            "timestamp": exception.timestamp.isoformat()
        }
        log_data.update(error_context)
        
        log_message = json.dumps(log_data, ensure_ascii=False, default=str)
        
        if exception.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL_ERROR: {log_message}", exc_info=True)
        elif exception.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH_ERROR: {log_message}", exc_info=True)
        elif exception.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM_ERROR: {log_message}")
        else:
            logger.info(f"LOW_ERROR: {log_message}")
    
    def _execute_recovery_strategy(self, exception: AppException) -> Optional[Dict[str, Any]]:
        """복구 전략 실행"""
        recovery_strategy = self.recovery_strategies.get(exception.recovery_action)
        if recovery_strategy:
            return recovery_strategy(exception)
        return None
    
    def _handle_retry_strategy(self, exception: AppException) -> Dict[str, Any]:
        """재시도 전략 처리"""
        return {
            "action": "retry",
            "max_retries": 3,
            "retry_delay": 1.0,
            "backoff_factor": 2.0,
            "suggestion": "잠시 후 다시 시도해 주세요"
        }
    
    def _handle_fallback_strategy(self, exception: AppException) -> Dict[str, Any]:
        """폴백 전략 처리"""
        service_name = exception.context.get("service_name", "")
        fallback_services = self.service_fallbacks.get(service_name, [])
        
        return {
            "action": "fallback",
            "fallback_services": fallback_services,
            "suggestion": "다른 서비스로 대체 처리됩니다"
        }
    
    def _handle_circuit_breaker_strategy(self, exception: AppException) -> Dict[str, Any]:
        """회로 차단기 전략 처리"""
        return {
            "action": "circuit_breaker",
            "timeout": 300,  # 5분
            "suggestion": "서비스 복구 중입니다. 잠시 후 다시 이용해 주세요"
        }
    
    def _handle_manual_intervention_strategy(self, exception: AppException) -> Dict[str, Any]:
        """수동 개입 전략 처리"""
        return {
            "action": "manual_intervention",
            "suggestion": "관리자에게 문의해 주세요",
            "support_contact": "support@example.com"
        }
    
    def _handle_no_recovery_strategy(self, exception: AppException) -> Dict[str, Any]:
        """복구 전략 없음"""
        return {
            "action": "none",
            "suggestion": "요청을 다시 확인해 주세요"
        }
    
    def _send_error_metrics(self, exception: AppException):
        """에러 메트릭 전송"""
        # TODO: Prometheus 메트릭 전송 구현
        pass
    
    def _send_error_alert(self, exception: AppException):
        """에러 알림 전송"""
        # TODO: Slack, Discord, 이메일 등 알림 전송 구현
        pass
    
    def _is_production(self) -> bool:
        """프로덕션 환경 확인"""
        import os
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    def _sanitize_error_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """프로덕션용 에러 응답 정리"""
        # 민감한 정보 제거
        sanitized = {
            "error_code": response_data.get("error_code"),
            "user_message": response_data.get("user_message"),
            "timestamp": response_data.get("timestamp"),
            "correlation_id": response_data.get("correlation_id")
        }
        
        # 복구 정보는 유지
        if "recovery" in response_data:
            sanitized["recovery"] = response_data["recovery"]
            
        return sanitized
    
    def _get_error_headers(self, exception: AppException) -> Dict[str, str]:
        """에러 응답 헤더 생성"""
        headers = {
            "X-Error-Code": exception.error_code,
            "X-Error-Severity": exception.severity.value
        }
        
        if exception.correlation_id:
            headers["X-Correlation-ID"] = exception.correlation_id
            
        if isinstance(exception, RateLimitError) and exception.detail.get("retry_after"):
            headers["Retry-After"] = str(exception.detail["retry_after"])
            
        return headers
    
    def _create_fallback_error_response(self, request_id: Optional[str]) -> JSONResponse:
        """폴백 에러 응답 생성"""
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "HANDLER_ERROR",
                    "message": "에러 처리 중 문제가 발생했습니다",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    @staticmethod
    def log_error(
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error"
    ):
        """기존 호환성을 위한 정적 로깅 메서드"""
        log_data = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc()
        }
        
        if context:
            log_data.update(context)
            
        log_message = f"Error occurred: {json.dumps(log_data, ensure_ascii=False, default=str)}"
        
        if level == "critical":
            logger.critical(log_message)
        elif level == "warning":
            logger.warning(log_message)
        else:
            logger.error(log_message)


# 전역 에러 처리기 인스턴스
error_handler = ErrorHandler()


# FastAPI 예외 핸들러 등록용 함수
async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI 앱 예외 핸들러"""
    return error_handler.handle_exception(exc, request)


# 특정 에러 타입별 핸들러
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """검증 에러 핸들러"""
    return error_handler.handle_exception(exc, request)


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """데이터베이스 에러 핸들러"""
    return error_handler.handle_exception(exc, request)