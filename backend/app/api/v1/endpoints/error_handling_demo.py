"""
통합 에러 핸들링 시스템 데모 API

새로운 에러 핸들링 시스템의 기능들을 시연하고
테스트할 수 있는 데모 엔드포인트들을 제공합니다.
"""

import asyncio
import random
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppException, ErrorSeverity, ErrorRecoveryAction,
    WholesalerAPIError, MarketplaceAPIError, AIServiceError,
    ProductError, InventoryError, OrderError, PaymentError,
    DatabaseError, ValidationError, NotFoundError,
    create_wholesaler_connection_error, create_marketplace_auth_error,
    create_product_not_found_error, create_insufficient_stock_error
)
from app.core.retry import (
    with_retry, with_circuit_breaker, with_fallback, with_resilience,
    dropshipping_resilient, RetryStrategy, RetryConfig, CircuitBreakerConfig
)
from app.core.logging_utils import (
    get_logger, log_execution_time, log_business_operation,
    BusinessEventType, LogCategory
)
from app.core.monitoring import (
    dropshipping_monitor, monitor_wholesaler_api, monitor_marketplace_operation
)

router = APIRouter(prefix="/error-handling-demo", tags=["Error Handling Demo"])
logger = get_logger("dropshipping.demo")


# =============================================================================
# 예외 데모 엔드포인트들
# =============================================================================

@router.get("/test-exceptions/{exception_type}")
async def test_exception_types(
    exception_type: str,
    severity: str = Query("medium", description="에러 심각도"),
    message: str = Query("테스트 에러 메시지", description="에러 메시지")
):
    """다양한 타입의 예외를 테스트하는 엔드포인트"""
    
    severity_enum = ErrorSeverity(severity)
    
    if exception_type == "wholesaler":
        raise WholesalerAPIError(
            wholesaler_name="TestWholesaler",
            message=message,
            severity=severity_enum
        )
    elif exception_type == "marketplace":
        raise MarketplaceAPIError(
            marketplace_name="TestMarketplace",
            message=message,
            severity=severity_enum
        )
    elif exception_type == "ai":
        raise AIServiceError(
            ai_service="TestAI",
            message=message,
            severity=severity_enum
        )
    elif exception_type == "product":
        raise ProductError(
            message=message,
            product_id="test-product-123",
            severity=severity_enum
        )
    elif exception_type == "inventory":
        raise InventoryError(
            message=message,
            product_id="test-product-123",
            current_stock=5,
            severity=severity_enum
        )
    elif exception_type == "order":
        raise OrderError(
            message=message,
            order_id="test-order-123",
            severity=severity_enum
        )
    elif exception_type == "payment":
        raise PaymentError(
            message=message,
            payment_id="test-payment-123",
            amount=99.99,
            severity=severity_enum
        )
    elif exception_type == "database":
        raise DatabaseError(
            message=message,
            operation="test_query",
            severity=severity_enum
        )
    elif exception_type == "validation":
        raise ValidationError(
            message=message,
            field_errors=[
                {"field": "test_field", "message": "유효하지 않은 값", "type": "value_error"}
            ],
            severity=severity_enum
        )
    elif exception_type == "not_found":
        raise NotFoundError(
            resource="테스트 리소스",
            severity=severity_enum
        )
    elif exception_type == "http":
        raise HTTPException(status_code=400, detail="HTTP 예외 테스트")
    elif exception_type == "python":
        raise ValueError("일반 Python 예외 테스트")
    else:
        return {"message": "알 수 없는 예외 타입", "available_types": [
            "wholesaler", "marketplace", "ai", "product", "inventory",
            "order", "payment", "database", "validation", "not_found",
            "http", "python"
        ]}


@router.get("/test-factory-exceptions")
async def test_factory_exceptions():
    """팩토리 함수로 생성된 예외들을 테스트"""
    
    error_type = random.choice([
        "wholesaler_connection",
        "marketplace_auth",
        "product_not_found",
        "insufficient_stock",
        "order_processing"
    ])
    
    if error_type == "wholesaler_connection":
        raise create_wholesaler_connection_error("OwnerClan", "네트워크 연결 실패")
    elif error_type == "marketplace_auth":
        raise create_marketplace_auth_error("Coupang")
    elif error_type == "product_not_found":
        raise create_product_not_found_error("PROD-12345")
    elif error_type == "insufficient_stock":
        raise create_insufficient_stock_error("PROD-12345", requested=10, available=3)
    elif error_type == "order_processing":
        from app.core.exceptions import create_order_processing_error
        raise create_order_processing_error("ORD-12345", "payment", "결제 승인 실패")


# =============================================================================
# 재시도 메커니즘 데모
# =============================================================================

@router.get("/test-retry-simple")
@with_retry(max_attempts=3, base_delay=1.0, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
async def test_simple_retry():
    """기본 재시도 메커니즘 테스트"""
    
    # 70% 확률로 실패
    if random.random() < 0.7:
        raise ConnectionError("임시 연결 오류")
    
    return {"message": "성공!", "attempts": "재시도를 통해 성공"}


@router.get("/test-retry-advanced")
async def test_advanced_retry():
    """고급 재시도 설정 테스트"""
    
    @with_retry(
        max_attempts=5,
        base_delay=0.5,
        max_delay=10.0,
        strategy=RetryStrategy.JITTERED_BACKOFF,
        retryable_exceptions=[WholesalerAPIError, ConnectionError]
    )
    async def flaky_wholesaler_call():
        # 60% 확률로 실패
        if random.random() < 0.6:
            raise WholesalerAPIError("OwnerClan", "일시적 서비스 오류")
        return {"data": "도매처 상품 데이터"}
    
    result = await flaky_wholesaler_call()
    return {"message": "고급 재시도 성공", "result": result}


# =============================================================================
# 회로 차단기 데모
# =============================================================================

@router.get("/test-circuit-breaker")
@with_circuit_breaker(
    service_name="demo_service",
    failure_threshold=3,
    success_threshold=2,
    timeout=30.0,
    expected_exception=ExternalServiceError
)
async def test_circuit_breaker():
    """회로 차단기 메커니즘 테스트"""
    
    # 80% 확률로 실패 (회로 차단기 트리거용)
    if random.random() < 0.8:
        raise ExternalServiceError(
            service_name="demo_service",
            message="서비스 응답 없음"
        )
    
    return {"message": "회로 차단기 테스트 성공"}


@router.get("/test-circuit-breaker-status")
async def get_circuit_breaker_status():
    """회로 차단기 상태 확인"""
    from app.core.retry import retry_manager
    
    circuit_breaker = retry_manager.circuit_breakers.get("demo_service")
    if circuit_breaker:
        return {
            "service": "demo_service",
            "state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
            "success_count": circuit_breaker.success_count,
            "last_failure_time": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None,
            "next_attempt_time": circuit_breaker.next_attempt_time.isoformat() if circuit_breaker.next_attempt_time else None
        }
    else:
        return {"message": "회로 차단기가 아직 생성되지 않았습니다"}


# =============================================================================
# 폴백 메커니즘 데모
# =============================================================================

@router.get("/test-fallback")
@with_fallback("demo_fallback_service")
async def test_fallback():
    """폴백 메커니즘 테스트"""
    
    # 항상 실패 (폴백 트리거용)
    raise ExternalServiceError(
        service_name="demo_fallback_service",
        message="주 서비스 실패"
    )


# 폴백 함수 등록
from app.core.retry import register_fallback

@register_fallback("demo_fallback_service")
async def demo_fallback_function(*args, **kwargs):
    """데모 폴백 함수"""
    return {"message": "폴백 함수에서 처리됨", "fallback": True}


# =============================================================================
# 통합 복원력 데모
# =============================================================================

@router.get("/test-resilience")
@with_resilience(
    service_name="demo_resilient_service",
    retry_config=RetryConfig(max_attempts=3, base_delay=1.0),
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
    enable_fallback=True
)
async def test_resilience():
    """통합 복원력 테스트 (재시도 + 회로 차단기 + 폴백)"""
    
    # 90% 확률로 실패
    if random.random() < 0.9:
        raise ExternalServiceError(
            service_name="demo_resilient_service",
            message="서비스 오류"
        )
    
    return {"message": "통합 복원력 테스트 성공"}


# =============================================================================
# 드롭쉬핑 특화 데코레이터 데모
# =============================================================================

@router.get("/test-dropshipping-wholesaler")
@dropshipping_resilient("wholesaler", "demo_wholesaler", max_attempts=3)
async def test_dropshipping_wholesaler():
    """드롭쉬핑 도매처 특화 복원력 테스트"""
    
    if random.random() < 0.8:
        raise WholesalerAPIError("demo_wholesaler", "도매처 API 오류")
    
    return {"message": "드롭쉬핑 도매처 테스트 성공"}


@router.get("/test-dropshipping-marketplace")
@dropshipping_resilient("marketplace", "demo_marketplace", max_attempts=2)
async def test_dropshipping_marketplace():
    """드롭쉬핑 마켓플레이스 특화 복원력 테스트"""
    
    if random.random() < 0.7:
        raise MarketplaceAPIError("demo_marketplace", "마켓플레이스 API 오류")
    
    return {"message": "드롭쉬핑 마켓플레이스 테스트 성공"}


@router.get("/test-dropshipping-ai")
@dropshipping_resilient("ai", "demo_ai", max_attempts=2)
async def test_dropshipping_ai():
    """드롭쉬핑 AI 서비스 특화 복원력 테스트"""
    
    if random.random() < 0.6:
        raise AIServiceError("demo_ai", "AI 서비스 오류")
    
    return {"message": "드롭쉬핑 AI 테스트 성공"}


# =============================================================================
# 로깅 시스템 데모
# =============================================================================

@router.get("/test-logging")
@log_execution_time("demo_logging_operation")
async def test_logging():
    """구조화된 로깅 시스템 테스트"""
    
    logger.info("데모 로깅 테스트 시작")
    
    # 비즈니스 이벤트 로깅
    logger.log_business_event(
        BusinessEventType.PRODUCT_SOURCED,
        "테스트 상품 소싱 완료",
        data={"product_count": 10, "source": "demo"}
    )
    
    # API 호출 로깅
    logger.log_api_call(
        service_name="demo_service",
        endpoint="/test",
        method="GET",
        status_code=200,
        response_time_ms=150.5
    )
    
    # 사용자 액션 로깅
    logger.log_user_action(
        action="view_product",
        resource="demo_product",
        result="success"
    )
    
    # 성능 메트릭 로깅
    logger.log_performance_metric(
        metric_name="demo_processing_time",
        value=125.3,
        unit="milliseconds"
    )
    
    await asyncio.sleep(0.1)  # 시뮬레이션 지연
    
    return {"message": "로깅 테스트 완료"}


@router.get("/test-business-operation")
@log_business_operation(BusinessEventType.ORDER_PROCESSED, "demo_order_processing")
async def test_business_operation():
    """비즈니스 오퍼레이션 로깅 테스트"""
    
    await asyncio.sleep(0.2)  # 처리 시뮬레이션
    
    return {
        "order_id": "DEMO-12345",
        "status": "processed",
        "items": 3,
        "total": 89.99
    }


# =============================================================================
# 모니터링 시스템 데모
# =============================================================================

@router.get("/test-monitoring")
@monitor_wholesaler_api("demo_wholesaler")
async def test_monitoring():
    """모니터링 시스템 테스트"""
    
    # 랜덤하게 성공/실패
    if random.random() < 0.3:
        raise WholesalerAPIError("demo_wholesaler", "모니터링 테스트 실패")
    
    return {"message": "모니터링 테스트 성공"}


@router.get("/test-marketplace-monitoring")
@monitor_marketplace_operation("demo_marketplace")
async def test_marketplace_monitoring():
    """마켓플레이스 모니터링 테스트"""
    
    if random.random() < 0.4:
        raise MarketplaceAPIError("demo_marketplace", "마켓플레이스 모니터링 테스트 실패")
    
    return {"message": "마켓플레이스 모니터링 테스트 성공"}


@router.get("/monitoring-status")
async def get_monitoring_status():
    """모니터링 시스템 상태 확인"""
    return dropshipping_monitor.get_status_report()


@router.get("/trigger-alert")
async def trigger_test_alert():
    """테스트 알림 발송"""
    from app.core.monitoring import Alert, AlertType, AlertChannel
    from datetime import datetime
    
    alert = Alert(
        alert_id=f"test_alert_{int(asyncio.get_event_loop().time())}",
        alert_type=AlertType.WARNING,
        title="테스트 알림",
        message="이것은 테스트 알림입니다",
        severity=ErrorSeverity.MEDIUM,
        timestamp=datetime.utcnow(),
        context={"test": True},
        channels=[AlertChannel.SLACK]
    )
    
    await dropshipping_monitor.alert_manager.send_alert(alert)
    
    return {"message": "테스트 알림이 발송되었습니다"}


# =============================================================================
# 성능 및 부하 테스트
# =============================================================================

@router.get("/stress-test")
async def stress_test(
    error_rate: float = Query(0.5, description="에러 발생률 (0.0-1.0)"),
    delay_ms: int = Query(100, description="처리 지연 시간 (밀리초)")
):
    """스트레스 테스트용 엔드포인트"""
    
    # 지연 시뮬레이션
    await asyncio.sleep(delay_ms / 1000.0)
    
    # 에러 발생
    if random.random() < error_rate:
        error_types = [
            lambda: WholesalerAPIError("stress_test", "스트레스 테스트 에러"),
            lambda: MarketplaceAPIError("stress_test", "스트레스 테스트 에러"),
            lambda: DatabaseError("스트레스 테스트 DB 에러", "stress_query"),
            lambda: TimeoutError("스트레스 테스트 타임아웃"),
            lambda: ConnectionError("스트레스 테스트 연결 오류")
        ]
        raise random.choice(error_types)()
    
    return {
        "message": "스트레스 테스트 성공",
        "error_rate": error_rate,
        "delay_ms": delay_ms
    }


# =============================================================================
# 시스템 상태 및 헬스체크
# =============================================================================

@router.get("/health")
async def health_check():
    """에러 핸들링 시스템 헬스체크"""
    
    from app.core.monitoring import run_health_diagnostics
    
    diagnostics = await run_health_diagnostics()
    
    # 간단한 상태 요약
    health_status = "healthy"
    health_score = dropshipping_monitor._calculate_health_score({
        "errors": dropshipping_monitor.error_aggregator.get_error_summary(),
        "metrics": dropshipping_monitor.metrics_collector.get_metrics_summary()
    })
    
    if health_score < 70:
        health_status = "degraded"
    if health_score < 50:
        health_status = "unhealthy"
    
    return {
        "status": health_status,
        "health_score": health_score,
        "error_handling_enabled": True,
        "monitoring_enabled": dropshipping_monitor.monitoring_enabled,
        "diagnostics": diagnostics
    }


# =============================================================================
# 설정 및 관리
# =============================================================================

@router.post("/reset-monitoring")
async def reset_monitoring():
    """모니터링 데이터 초기화"""
    
    dropshipping_monitor.error_aggregator.error_counts.clear()
    dropshipping_monitor.error_aggregator.error_history.clear()
    dropshipping_monitor.metrics_collector.metrics.clear()
    dropshipping_monitor.alert_manager.alert_history.clear()
    dropshipping_monitor.alert_manager.throttle_cache.clear()
    
    from app.core.retry import retry_manager
    retry_manager.circuit_breakers.clear()
    
    return {"message": "모니터링 데이터가 초기화되었습니다"}


@router.get("/demo-summary")
async def get_demo_summary():
    """데모 시스템 요약 정보"""
    
    return {
        "title": "드롭쉬핑 통합 에러 핸들링 시스템 데모",
        "description": "포괄적인 에러 처리, 복구, 모니터링 기능을 제공합니다",
        "features": {
            "exception_handling": {
                "description": "도메인별 구조화된 예외 처리",
                "endpoints": ["/test-exceptions/{type}", "/test-factory-exceptions"]
            },
            "retry_mechanisms": {
                "description": "지능형 재시도 전략",
                "endpoints": ["/test-retry-simple", "/test-retry-advanced"]
            },
            "circuit_breaker": {
                "description": "회로 차단기 패턴",
                "endpoints": ["/test-circuit-breaker", "/test-circuit-breaker-status"]
            },
            "fallback": {
                "description": "폴백 메커니즘",
                "endpoints": ["/test-fallback"]
            },
            "resilience": {
                "description": "통합 복원력 (재시도+회로차단기+폴백)",
                "endpoints": ["/test-resilience"]
            },
            "dropshipping_specialized": {
                "description": "드롭쉬핑 특화 복원력",
                "endpoints": [
                    "/test-dropshipping-wholesaler",
                    "/test-dropshipping-marketplace",
                    "/test-dropshipping-ai"
                ]
            },
            "logging": {
                "description": "구조화된 로깅 시스템",
                "endpoints": ["/test-logging", "/test-business-operation"]
            },
            "monitoring": {
                "description": "실시간 모니터링 및 알림",
                "endpoints": [
                    "/test-monitoring",
                    "/test-marketplace-monitoring",
                    "/monitoring-status",
                    "/trigger-alert"
                ]
            },
            "performance": {
                "description": "성능 테스트 및 분석",
                "endpoints": ["/stress-test"]
            },
            "health": {
                "description": "시스템 상태 확인",
                "endpoints": ["/health"]
            }
        },
        "usage_tips": [
            "각 엔드포인트를 호출하여 다양한 에러 처리 기능을 테스트해보세요",
            "/monitoring-status에서 실시간 시스템 상태를 확인하세요",
            "/stress-test로 부하 상황에서의 동작을 확인하세요",
            "/reset-monitoring으로 테스트 데이터를 초기화할 수 있습니다"
        ]
    }