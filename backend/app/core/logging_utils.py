"""
드롭쉬핑 프로젝트용 구조화된 로깅 시스템

에러 추적, 성능 모니터링, 비즈니스 메트릭 수집을 위한
포괄적인 로깅 솔루션을 제공합니다.
"""

import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from contextlib import contextmanager
from functools import wraps
import asyncio
import inspect

from app.core.config import settings
from app.core.exceptions import AppException, ErrorSeverity


class LogLevel(str, Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """로그 카테고리"""
    SYSTEM = "system"
    BUSINESS = "business"
    SECURITY = "security"
    PERFORMANCE = "performance"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    USER_ACTION = "user_action"
    ERROR = "error"
    AUDIT = "audit"


class BusinessEventType(str, Enum):
    """비즈니스 이벤트 타입"""
    PRODUCT_SOURCED = "product_sourced"
    PRODUCT_LISTED = "product_listed"
    ORDER_RECEIVED = "order_received"
    ORDER_PROCESSED = "order_processed"
    PAYMENT_COMPLETED = "payment_completed"
    INVENTORY_UPDATED = "inventory_updated"
    PRICE_UPDATED = "price_updated"
    SYNC_COMPLETED = "sync_completed"
    AI_ANALYSIS_COMPLETED = "ai_analysis_completed"


class StructuredLogger:
    """구조화된 로거 클래스 (기존 호환성 유지 + 확장)"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.service_name = logger_name
        self.correlation_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None
        
    def set_context(
        self,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """로깅 컨텍스트 설정"""
        if correlation_id:
            self.correlation_id = correlation_id
        if user_id:
            self.user_id = user_id
        if session_id:
            self.session_id = session_id
    
    def _create_log_entry(
        self,
        level: str,
        message: str,
        category: Optional[LogCategory] = None,
        event_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """로그 엔트리 생성 (기존 호환성 유지 + 확장)"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "service": self.service_name,
            "message": message,
            "environment": settings.ENVIRONMENT,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "session_id": self.session_id
        }
        
        if category:
            log_entry["category"] = category.value
            
        if event_type:
            log_entry["event_type"] = event_type
            
        # 추가 필드 병합
        if kwargs:
            log_entry["context"] = kwargs
            
        # None 값 제거
        return {k: v for k, v in log_entry.items() if v is not None}
    
    def _log(self, level: LogLevel, log_entry: Dict[str, Any]):
        """실제 로깅 수행"""
        log_message = json.dumps(log_entry, ensure_ascii=False, default=str)
        
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message)
        elif level == LogLevel.INFO:
            self.logger.info(log_message)
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message)
        elif level == LogLevel.ERROR:
            self.logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message)
    
    # =============================================================================
    # 기존 메서드들 (호환성 유지)
    # =============================================================================
    
    def info(self, message: str, **kwargs):
        """정보 로그 (기존 호환성 유지)"""
        log_entry = self._create_log_entry("INFO", message, **kwargs)
        self.logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))
        
    def warning(self, message: str, **kwargs):
        """경고 로그 (기존 호환성 유지)"""
        log_entry = self._create_log_entry("WARNING", message, **kwargs)
        self.logger.warning(json.dumps(log_entry, ensure_ascii=False, default=str))
        
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """에러 로그 (기존 호환성 유지)"""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
            
        log_entry = self._create_log_entry("ERROR", message, **kwargs)
        self.logger.error(json.dumps(log_entry, ensure_ascii=False, default=str))
        
    def debug(self, message: str, **kwargs):
        """디버그 로그 (기존 호환성 유지)"""
        if settings.DEBUG:
            log_entry = self._create_log_entry("DEBUG", message, **kwargs)
            self.logger.debug(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def critical(self, message: str, **kwargs):
        """치명적 에러 로그"""
        log_entry = self._create_log_entry("CRITICAL", message, **kwargs)
        self.logger.critical(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    # =============================================================================
    # 새로운 특화된 로깅 메서드들
    # =============================================================================
    
    def log_business_event(
        self,
        event_type: BusinessEventType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """비즈니스 이벤트 로깅"""
        log_entry = self._create_log_entry(
            "INFO",
            message,
            category=LogCategory.BUSINESS,
            event_type=event_type.value,
            business_data=data or {},
            **kwargs
        )
        self.logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def log_api_call(
        self,
        service_name: str,
        endpoint: str,
        method: str,
        status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        **kwargs
    ):
        """외부 API 호출 로깅"""
        log_entry = self._create_log_entry(
            "INFO",
            f"API call to {service_name}",
            category=LogCategory.EXTERNAL_API,
            api_service_name=service_name,
            api_endpoint=endpoint,
            api_method=method,
            api_status_code=status_code,
            api_response_time_ms=response_time_ms,
            api_request_size=request_size,
            api_response_size=response_size,
            **kwargs
        )
        self.logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def log_database_operation(
        self,
        operation: str,
        table: str,
        query_time_ms: Optional[float] = None,
        affected_rows: Optional[int] = None,
        **kwargs
    ):
        """데이터베이스 작업 로깅"""
        log_entry = self._create_log_entry(
            "DEBUG",
            f"Database {operation} on {table}",
            category=LogCategory.DATABASE,
            db_operation=operation,
            db_table=table,
            db_query_time_ms=query_time_ms,
            db_affected_rows=affected_rows,
            **kwargs
        )
        if settings.DEBUG:
            self.logger.debug(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def log_user_action(
        self,
        action: str,
        resource: str,
        result: str = "success",
        **kwargs
    ):
        """사용자 액션 로깅"""
        log_entry = self._create_log_entry(
            "INFO",
            f"User action: {action} on {resource}",
            category=LogCategory.USER_ACTION,
            user_action=action,
            user_resource=resource,
            user_result=result,
            **kwargs
        )
        self.logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = "medium",
        ip_address: Optional[str] = None,
        **kwargs
    ):
        """보안 이벤트 로깅"""
        level = "WARNING" if severity == "medium" else "ERROR"
        log_entry = self._create_log_entry(
            level,
            description,
            category=LogCategory.SECURITY,
            security_event_type=event_type,
            security_severity=severity,
            security_ip_address=ip_address,
            **kwargs
        )
        
        if level == "WARNING":
            self.logger.warning(json.dumps(log_entry, ensure_ascii=False, default=str))
        else:
            self.logger.error(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: str,
        tags: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """성능 메트릭 로깅"""
        log_entry = self._create_log_entry(
            "INFO",
            f"Performance metric: {metric_name}",
            category=LogCategory.PERFORMANCE,
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            metric_tags=tags or {},
            **kwargs
        )
        self.logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def log_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True
    ):
        """예외 로깅"""
        import traceback
        
        log_data = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception)
        }
        
        if include_traceback:
            log_data["traceback"] = traceback.format_exc()
            
        if isinstance(exception, AppException):
            log_data.update({
                "error_code": exception.error_code,
                "severity": exception.severity.value,
                "recovery_action": exception.recovery_action.value,
                "user_message": exception.user_message,
                "exception_context": exception.context,
                "exception_detail": exception.detail
            })
            
        if context:
            log_data["context"] = context
            
        log_entry = self._create_log_entry(
            "ERROR",
            f"Exception occurred: {type(exception).__name__}",
            category=LogCategory.ERROR,
            **log_data
        )
        self.logger.error(json.dumps(log_entry, ensure_ascii=False, default=str))
    
    def log_audit_event(
        self,
        action: str,
        resource: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        **kwargs
    ):
        """감사 로그"""
        log_entry = self._create_log_entry(
            "INFO",
            f"Audit: {action} on {resource}",
            category=LogCategory.AUDIT,
            audit_action=action,
            audit_resource=resource,
            audit_old_value=old_value,
            audit_new_value=new_value,
            **kwargs
        )
        self.logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))


# =============================================================================
# 기존 함수들 (호환성 유지)
# =============================================================================

def get_logger(service_name: str) -> StructuredLogger:
    """
    서비스용 구조화된 로거 생성 (기존 호환성 유지)
    
    Usage:
        logger = get_logger("OrderService")
        logger.info("Order created", order_id=order.id, user_id=user.id)
    """
    return StructuredLogger(service_name)


def log_execution_time(operation_name: str = None):
    """
    함수 실행 시간을 로깅하는 데코레이터 (기존 호환성 유지 + 확장)
    
    Usage:
        @log_execution_time("order_processing")
        def process_order(order_id):
            # 주문 처리 로직
            pass
    """
    def decorator(func):
        nonlocal operation_name
        if not operation_name:
            operation_name = func.__name__
            
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.log_performance_metric(
                    metric_name=f"{operation_name}_execution_time",
                    value=round(execution_time * 1000, 2),
                    unit="milliseconds"
                )
                
                logger.info(
                    f"{operation_name} completed",
                    operation=operation_name,
                    execution_time_ms=round(execution_time * 1000, 2),
                    status="success"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.log_exception(
                    e,
                    context={
                        "operation": operation_name,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "status": "failed"
                    }
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.log_performance_metric(
                    metric_name=f"{operation_name}_execution_time",
                    value=round(execution_time * 1000, 2),
                    unit="milliseconds"
                )
                
                logger.info(
                    f"{operation_name} completed",
                    operation=operation_name,
                    execution_time_ms=round(execution_time * 1000, 2),
                    status="success"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.log_exception(
                    e,
                    context={
                        "operation": operation_name,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "status": "failed"
                    }
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def log_api_request(endpoint: str):
    """
    API 요청을 로깅하는 데코레이터 (기존 호환성 유지 + 확장)
    
    Usage:
        @log_api_request("/api/v1/orders")
        async def create_order(request: Request, order_data: OrderCreate):
            # API 핸들러 로직
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger("API")
            request = None
            
            # Request 객체 찾기
            for arg in args:
                if hasattr(arg, "method") and hasattr(arg, "url"):
                    request = arg
                    break
                    
            start_time = time.time()
            
            # 상관관계 ID 설정
            correlation_id = str(uuid.uuid4())
            if request:
                request.state.correlation_id = correlation_id
                logger.set_context(correlation_id=correlation_id)
            
            try:
                # 요청 로깅
                if request:
                    logger.info(
                        "API request received",
                        endpoint=endpoint,
                        method=request.method,
                        path=str(request.url.path),
                        client=request.client.host if request.client else "unknown",
                        user_agent=request.headers.get("user-agent")
                    )
                
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 성능 메트릭 로깅
                logger.log_performance_metric(
                    metric_name=f"api_request_{endpoint.replace('/', '_')}",
                    value=round(execution_time * 1000, 2),
                    unit="milliseconds",
                    tags={"method": request.method if request else "unknown"}
                )
                
                # 응답 로깅
                logger.info(
                    "API request completed",
                    endpoint=endpoint,
                    execution_time_ms=round(execution_time * 1000, 2),
                    status="success"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.log_exception(
                    e,
                    context={
                        "endpoint": endpoint,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "status": "failed"
                    }
                )
                raise
                
        return wrapper
    return decorator


# =============================================================================
# 새로운 데코레이터들
# =============================================================================

def log_business_operation(
    event_type: BusinessEventType,
    resource: Optional[str] = None
):
    """비즈니스 오퍼레이션 로깅 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            operation_resource = resource or func.__name__
            
            logger.log_business_event(
                event_type=event_type,
                message=f"Starting {operation_resource}",
                data={"status": "started"}
            )
            
            try:
                result = await func(*args, **kwargs)
                
                logger.log_business_event(
                    event_type=event_type,
                    message=f"Completed {operation_resource}",
                    data={"status": "completed", "result": str(result)[:200]}
                )
                
                return result
                
            except Exception as e:
                logger.log_business_event(
                    event_type=event_type,
                    message=f"Failed {operation_resource}",
                    data={"status": "failed", "error": str(e)}
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            operation_resource = resource or func.__name__
            
            logger.log_business_event(
                event_type=event_type,
                message=f"Starting {operation_resource}",
                data={"status": "started"}
            )
            
            try:
                result = func(*args, **kwargs)
                
                logger.log_business_event(
                    event_type=event_type,
                    message=f"Completed {operation_resource}",
                    data={"status": "completed", "result": str(result)[:200]}
                )
                
                return result
                
            except Exception as e:
                logger.log_business_event(
                    event_type=event_type,
                    message=f"Failed {operation_resource}",
                    data={"status": "failed", "error": str(e)}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# =============================================================================
# 컨텍스트 매니저 (기존 호환성 유지 + 확장)
# =============================================================================

class LogContext:
    """
    로깅 컨텍스트 관리자 (기존 호환성 유지 + 확장)
    
    Usage:
        with LogContext(logger, operation="order_processing", order_id=order_id):
            # 이 블록 내의 모든 로그에 컨텍스트 정보가 자동으로 추가됨
            process_order_items(order)
    """
    
    def __init__(self, logger: StructuredLogger, **context):
        self.logger = logger
        self.context = context
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        operation = self.context.get('operation', 'operation')
        self.logger.info(f"Starting {operation}", **self.context)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        operation = self.context.get('operation', 'operation')
        
        if exc_type is None:
            self.logger.info(
                f"Completed {operation}",
                execution_time_ms=round(execution_time * 1000, 2),
                status="success",
                **self.context
            )
        else:
            self.logger.log_exception(
                exc_val,
                context={
                    "operation": operation,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "status": "failed",
                    **self.context
                }
            )
        
        return False  # 예외를 전파


@contextmanager
def log_operation_context(
    logger: StructuredLogger,
    operation_name: str,
    category: LogCategory = LogCategory.SYSTEM,
    log_result: bool = True
):
    """오퍼레이션 컨텍스트 로깅"""
    start_time = time.time()
    logger.info(f"Starting {operation_name}")
    
    try:
        yield
        execution_time = (time.time() - start_time) * 1000
        
        if log_result:
            logger.info(
                f"Completed {operation_name}",
                execution_time_ms=execution_time
            )
            
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.log_exception(
            e,
            context={
                "operation": operation_name,
                "execution_time_ms": execution_time
            }
        )
        raise


# =============================================================================
# 로깅 설정 함수
# =============================================================================

def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None
):
    """로깅 시스템 설정"""
    # 로그 레벨 설정
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 로그 포맷 설정
    if log_format.lower() == "json":
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # 핸들러 설정
    handlers = []
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # 파일 핸들러 (선택적)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # 루트 로거 설정
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True
    )


# =============================================================================
# 전역 로거 인스턴스들
# =============================================================================

system_logger = get_logger("dropshipping.system")
business_logger = get_logger("dropshipping.business")
api_logger = get_logger("dropshipping.api")
database_logger = get_logger("dropshipping.database")
security_logger = get_logger("dropshipping.security")
performance_logger = get_logger("dropshipping.performance")