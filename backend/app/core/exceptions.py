"""
드롭쉬핑 프로젝트용 커스텀 예외 클래스

도메인별로 구조화된 예외 체계를 제공하여
일관성 있는 에러 처리와 복구 전략을 지원합니다.
"""

from typing import Optional, Dict, Any, Union, List
from enum import Enum
import traceback
from datetime import datetime


class ErrorSeverity(str, Enum):
    """에러 심각도 레벨"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorRecoveryAction(str, Enum):
    """에러 복구 액션"""
    RETRY = "retry"
    FALLBACK = "fallback"
    MANUAL_INTERVENTION = "manual_intervention"
    CIRCUIT_BREAKER = "circuit_breaker"
    NONE = "none"


class AppException(Exception):
    """기본 애플리케이션 예외 클래스"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_action: ErrorRecoveryAction = ErrorRecoveryAction.NONE,
        user_message: Optional[str] = None,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.detail = detail or {}
        self.status_code = status_code
        self.severity = severity
        self.recovery_action = recovery_action
        self.user_message = user_message or message
        self.correlation_id = correlation_id
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "detail": self.detail,
            "status_code": self.status_code,
            "severity": self.severity.value,
            "recovery_action": self.recovery_action.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }
    
    def is_retryable(self) -> bool:
        """재시도 가능한 에러인지 확인"""
        return self.recovery_action == ErrorRecoveryAction.RETRY
    
    def is_critical(self) -> bool:
        """치명적 에러인지 확인"""
        return self.severity == ErrorSeverity.CRITICAL


# =============================================================================
# 인증 및 권한 관련 예외
# =============================================================================

class AuthenticationError(AppException):
    """인증 실패 예외"""
    
    def __init__(self, message: str = "인증이 필요합니다", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_001",
            status_code=401,
            severity=ErrorSeverity.MEDIUM,
            user_message="로그인이 필요합니다",
            **kwargs
        )


class AuthorizationError(AppException):
    """권한 부족 예외"""
    
    def __init__(self, message: str = "권한이 부족합니다", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_002",
            status_code=403,
            severity=ErrorSeverity.MEDIUM,
            user_message="접근 권한이 없습니다",
            **kwargs
        )


class TokenExpiredError(AuthenticationError):
    """토큰 만료 예외"""
    
    def __init__(self, message: str = "토큰이 만료되었습니다", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTH_003",
            user_message="다시 로그인해 주세요",
            **kwargs
        )


# =============================================================================
# 비즈니스 로직 관련 예외
# =============================================================================

class ValidationError(AppException):
    """데이터 검증 실패 예외"""
    
    def __init__(self, message: str, field_errors: Optional[List[Dict]] = None, **kwargs):
        detail = {"field_errors": field_errors} if field_errors else {}
        super().__init__(
            message=message,
            error_code="VAL_001",
            status_code=422,
            severity=ErrorSeverity.LOW,
            detail=detail,
            user_message="입력한 정보를 확인해 주세요",
            **kwargs
        )


class NotFoundError(AppException):
    """리소스 없음 예외"""
    
    def __init__(self, resource: str = "리소스", **kwargs):
        message = f"{resource}를 찾을 수 없습니다"
        super().__init__(
            message=message,
            error_code="RES_001",
            status_code=404,
            severity=ErrorSeverity.LOW,
            user_message=message,
            **kwargs
        )


class BusinessLogicError(AppException):
    """비즈니스 로직 오류 예외"""
    
    def __init__(self, message: str, business_rule: Optional[str] = None, **kwargs):
        detail = {"business_rule": business_rule} if business_rule else {}
        super().__init__(
            message=message,
            error_code="BIZ_001",
            status_code=400,
            severity=ErrorSeverity.MEDIUM,
            detail=detail,
            **kwargs
        )


class ConflictError(AppException):
    """충돌 오류 예외"""
    
    def __init__(self, message: str = "리소스 충돌이 발생했습니다", **kwargs):
        super().__init__(
            message=message,
            error_code="CON_001",
            status_code=409,
            severity=ErrorSeverity.MEDIUM,
            user_message="이미 존재하는 데이터입니다",
            **kwargs
        )


# =============================================================================
# 드롭쉬핑 비즈니스 특화 예외
# =============================================================================

class ProductError(AppException):
    """상품 관련 예외"""
    
    def __init__(self, message: str, product_id: Optional[str] = None, **kwargs):
        context = {"product_id": product_id} if product_id else {}
        super().__init__(
            message=message,
            error_code="PROD_001",
            status_code=400,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **kwargs
        )


class InventoryError(AppException):
    """재고 관련 예외"""
    
    def __init__(self, message: str, product_id: Optional[str] = None, current_stock: Optional[int] = None, **kwargs):
        context = {
            "product_id": product_id,
            "current_stock": current_stock
        } if product_id else {}
        super().__init__(
            message=message,
            error_code="INV_001",
            status_code=400,
            severity=ErrorSeverity.HIGH,
            recovery_action=ErrorRecoveryAction.MANUAL_INTERVENTION,
            context=context,
            user_message="재고가 부족합니다",
            **kwargs
        )


class OrderError(AppException):
    """주문 관련 예외"""
    
    def __init__(self, message: str, order_id: Optional[str] = None, **kwargs):
        context = {"order_id": order_id} if order_id else {}
        super().__init__(
            message=message,
            error_code="ORD_001",
            status_code=400,
            severity=ErrorSeverity.HIGH,
            recovery_action=ErrorRecoveryAction.MANUAL_INTERVENTION,
            context=context,
            **kwargs
        )


class PaymentError(AppException):
    """결제 관련 예외"""
    
    def __init__(self, message: str, payment_id: Optional[str] = None, amount: Optional[float] = None, **kwargs):
        context = {
            "payment_id": payment_id,
            "amount": amount
        } if payment_id else {}
        super().__init__(
            message=message,
            error_code="PAY_001",
            status_code=400,
            severity=ErrorSeverity.CRITICAL,
            recovery_action=ErrorRecoveryAction.MANUAL_INTERVENTION,
            context=context,
            user_message="결제 처리 중 오류가 발생했습니다",
            **kwargs
        )


class PricingError(AppException):
    """가격 계산 관련 예외"""
    
    def __init__(self, message: str, product_id: Optional[str] = None, **kwargs):
        context = {"product_id": product_id} if product_id else {}
        super().__init__(
            message=message,
            error_code="PRC_001",
            status_code=400,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **kwargs
        )


# =============================================================================
# 외부 서비스 관련 예외
# =============================================================================

class ExternalServiceError(AppException):
    """외부 서비스 오류 예외"""
    
    def __init__(self, service_name: str, message: str, response_code: Optional[int] = None, **kwargs):
        context = {
            "service_name": service_name,
            "response_code": response_code
        }
        super().__init__(
            message=f"{service_name} 서비스 오류: {message}",
            error_code="EXT_001",
            status_code=503,
            severity=ErrorSeverity.HIGH,
            recovery_action=ErrorRecoveryAction.RETRY,
            context=context,
            user_message="외부 서비스 연결에 문제가 있습니다. 잠시 후 다시 시도해 주세요",
            **kwargs
        )


class WholesalerAPIError(ExternalServiceError):
    """도매처 API 오류 예외"""
    
    def __init__(self, wholesaler_name: str, message: str, **kwargs):
        super().__init__(
            service_name=f"도매처 {wholesaler_name}",
            message=message,
            error_code="WHI_001",
            recovery_action=ErrorRecoveryAction.FALLBACK,
            **kwargs
        )


class MarketplaceAPIError(ExternalServiceError):
    """마켓플레이스 API 오류 예외"""
    
    def __init__(self, marketplace_name: str, message: str, **kwargs):
        super().__init__(
            service_name=f"마켓플레이스 {marketplace_name}",
            message=message,
            error_code="MKT_001",
            **kwargs
        )


class AIServiceError(ExternalServiceError):
    """AI 서비스 오류 예외"""
    
    def __init__(self, ai_service: str, message: str, **kwargs):
        super().__init__(
            service_name=f"AI 서비스 {ai_service}",
            message=message,
            error_code="AI_001",
            recovery_action=ErrorRecoveryAction.FALLBACK,
            **kwargs
        )


# =============================================================================
# 일반 서비스 관련 예외
# =============================================================================

class ServiceException(AppException):
    """일반 서비스 예외"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        context = {"service_name": service_name} if service_name else {}
        super().__init__(
            message=message,
            error_code="SRV_001",
            status_code=500,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **kwargs
        )


# =============================================================================
# 시스템 관련 예외
# =============================================================================

class DatabaseError(AppException):
    """데이터베이스 오류 예외"""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        context = {"operation": operation} if operation else {}
        super().__init__(
            message=message,
            error_code="DB_001",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            recovery_action=ErrorRecoveryAction.RETRY,
            context=context,
            user_message="일시적인 서버 오류입니다. 잠시 후 다시 시도해 주세요",
            **kwargs
        )


class RateLimitError(AppException):
    """요청 제한 예외"""
    
    def __init__(self, message: str = "요청 한도를 초과했습니다", retry_after: Optional[int] = None, **kwargs):
        detail = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            error_code="RATE_001",
            status_code=429,
            severity=ErrorSeverity.MEDIUM,
            detail=detail,
            user_message="요청이 너무 많습니다. 잠시 후 다시 시도해 주세요",
            **kwargs
        )


class ServiceUnavailableError(AppException):
    """서비스 이용 불가 예외"""
    
    def __init__(self, message: str = "서비스를 사용할 수 없습니다", **kwargs):
        super().__init__(
            message=message,
            error_code="SVC_001",
            status_code=503,
            severity=ErrorSeverity.HIGH,
            recovery_action=ErrorRecoveryAction.CIRCUIT_BREAKER,
            user_message="서비스 점검 중입니다. 잠시 후 다시 시도해 주세요",
            **kwargs
        )


class ConfigurationError(AppException):
    """설정 오류 예외"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        context = {"config_key": config_key} if config_key else {}
        super().__init__(
            message=message,
            error_code="CFG_001",
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            recovery_action=ErrorRecoveryAction.MANUAL_INTERVENTION,
            context=context,
            user_message="시스템 설정에 문제가 있습니다",
            **kwargs
        )


# =============================================================================
# 동기화 관련 예외
# =============================================================================

class SyncError(AppException):
    """동기화 오류 예외"""
    
    def __init__(self, message: str, sync_type: Optional[str] = None, **kwargs):
        context = {"sync_type": sync_type} if sync_type else {}
        super().__init__(
            message=message,
            error_code="SYNC_001",
            status_code=500,
            severity=ErrorSeverity.HIGH,
            recovery_action=ErrorRecoveryAction.RETRY,
            context=context,
            user_message="데이터 동기화 중 오류가 발생했습니다",
            **kwargs
        )


class InventorySyncError(SyncError):
    """재고 동기화 오류 예외"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SYNC_002",
            sync_type="inventory",
            **kwargs
        )


class OrderSyncError(SyncError):
    """주문 동기화 오류 예외"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SYNC_003",
            sync_type="order",
            **kwargs
        )


# =============================================================================
# 예외 팩토리 함수들
# =============================================================================

def create_wholesaler_connection_error(wholesaler_name: str, error_details: str) -> WholesalerAPIError:
    """도매처 연결 오류 생성"""
    return WholesalerAPIError(
        wholesaler_name=wholesaler_name,
        message=f"{wholesaler_name} API 연결 실패: {error_details}",
        severity=ErrorSeverity.HIGH,
        recovery_action=ErrorRecoveryAction.FALLBACK
    )


def create_marketplace_auth_error(marketplace_name: str) -> MarketplaceAPIError:
    """마켓플레이스 인증 오류 생성"""
    return MarketplaceAPIError(
        marketplace_name=marketplace_name,
        message=f"{marketplace_name} 인증 실패",
        severity=ErrorSeverity.CRITICAL,
        recovery_action=ErrorRecoveryAction.MANUAL_INTERVENTION
    )


def create_product_not_found_error(product_id: str) -> NotFoundError:
    """상품 없음 오류 생성"""
    return NotFoundError(
        resource="상품",
        context={"product_id": product_id}
    )


def create_insufficient_stock_error(product_id: str, requested: int, available: int) -> InventoryError:
    """재고 부족 오류 생성"""
    return InventoryError(
        message=f"재고 부족: 요청량 {requested}, 가용량 {available}",
        product_id=product_id,
        current_stock=available,
        detail={"requested_quantity": requested, "available_quantity": available}
    )


def create_order_processing_error(order_id: str, step: str, reason: str) -> OrderError:
    """주문 처리 오류 생성"""
    return OrderError(
        message=f"주문 처리 실패 ({step}): {reason}",
        order_id=order_id,
        detail={"processing_step": step, "failure_reason": reason}
    )