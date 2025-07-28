"""
모니터링 API 엔드포인트
헬스 체크, 메트릭 조회, 알림 설정 관리
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.monitoring.health_checker import health_checker, HealthStatus
from app.services.monitoring.metrics_collector import metrics_collector, BusinessMetrics
from app.services.monitoring.alert_manager import alert_manager, AlertRule, AlertSeverity, AlertChannel
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str
    timestamp: str
    checks: Dict[str, Any]


class MetricsSummaryResponse(BaseModel):
    """메트릭 요약 응답 모델"""
    uptime_seconds: float
    counters: Dict[str, int]
    timings: Dict[str, Dict[str, float]]
    gauges: Dict[str, Dict[str, Any]]


class AlertRuleCreate(BaseModel):
    """알림 규칙 생성 모델"""
    name: str = Field(..., description="규칙 이름")
    metric_name: str = Field(..., description="모니터링할 메트릭 이름")
    threshold: float = Field(..., description="임계값")
    operator: str = Field(..., description="비교 연산자 (gt, lt, gte, lte, eq)")
    severity: AlertSeverity = Field(..., description="심각도")
    channels: List[AlertChannel] = Field(..., description="알림 채널")
    message_template: str = Field(..., description="알림 메시지 템플릿")
    cooldown_minutes: int = Field(5, description="재알림 쿨다운 (분)")
    consecutive_failures: int = Field(1, description="연속 실패 횟수")


class AlertHistoryResponse(BaseModel):
    """알림 이력 응답 모델"""
    alerts: List[Dict[str, Any]]
    total: int


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    시스템 헬스 체크
    
    모든 주요 컴포넌트의 상태를 확인합니다:
    - 데이터베이스 연결
    - Redis 연결
    - 디스크 공간
    - 메모리 사용량
    - 외부 API 연결
    """
    result = await health_checker.check_all()
    
    # 전체 상태가 unhealthy면 503 반환
    if result["status"] == HealthStatus.UNHEALTHY.value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )
        
    return result


@router.get("/health/ready")
async def readiness_check():
    """
    준비 상태 체크 (Kubernetes readiness probe용)
    
    서비스가 트래픽을 받을 준비가 되었는지 확인
    """
    result = await health_checker.check_all()
    
    if result["status"] == HealthStatus.UNHEALTHY.value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
        
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check():
    """
    생존 상태 체크 (Kubernetes liveness probe용)
    
    애플리케이션이 살아있는지만 확인
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/metrics", response_model=MetricsSummaryResponse)
async def get_metrics(
    current_user: User = Depends(get_current_admin_user)
):
    """
    시스템 메트릭 조회 (관리자 전용)
    
    수집된 모든 메트릭의 요약 정보를 반환합니다.
    """
    return metrics_collector.get_metrics_summary()


@router.get("/metrics/api")
async def get_api_metrics(
    current_user: User = Depends(get_current_admin_user)
):
    """
    API 메트릭 조회 (관리자 전용)
    
    API 관련 상세 메트릭:
    - 엔드포인트별 응답 시간
    - 상태 코드별 통계
    - 에러율
    """
    summary = metrics_collector.get_metrics_summary()
    
    # API 관련 메트릭만 필터링
    api_metrics = {
        "response_times": {
            k: v for k, v in summary["timings"].items()
            if k.startswith("api.")
        },
        "status_codes": {
            k: v for k, v in summary["counters"].items()
            if k.startswith("api.status.")
        },
        "methods": {
            k: v for k, v in summary["counters"].items()
            if k.startswith("api.method.")
        },
        "errors": {
            k: v for k, v in summary["counters"].items()
            if k.startswith("api.errors.")
        }
    }
    
    # 에러율 계산
    total_requests = sum(api_metrics["status_codes"].values())
    total_errors = summary["counters"].get("api.errors.total", 0)
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    
    api_metrics["error_rate"] = round(error_rate, 2)
    api_metrics["total_requests"] = total_requests
    
    return api_metrics


@router.get("/metrics/business")
async def get_business_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    비즈니스 메트릭 조회 (관리자 전용)
    
    비즈니스 관련 메트릭:
    - 주문 통계
    - 매출 정보
    - 결제 성공률
    """
    # 비즈니스 메트릭 수집
    await BusinessMetrics.collect_order_metrics(db)
    await BusinessMetrics.collect_payment_metrics(db)
    
    summary = metrics_collector.get_metrics_summary()
    
    # 비즈니스 메트릭 추출
    business_metrics = {
        k.replace("business.", ""): v 
        for k, v in summary["gauges"].items()
        if k.startswith("business.")
    }
    
    return business_metrics


@router.get("/alerts/rules")
async def get_alert_rules(
    current_user: User = Depends(get_current_admin_user)
):
    """
    알림 규칙 목록 조회 (관리자 전용)
    """
    return {"rules": alert_manager.get_rules()}


@router.post("/alerts/rules", status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    새 알림 규칙 생성 (관리자 전용)
    """
    # 연산자에 따른 조건 함수 생성
    operator_map = {
        "gt": lambda x, t: x > t,
        "lt": lambda x, t: x < t,
        "gte": lambda x, t: x >= t,
        "lte": lambda x, t: x <= t,
        "eq": lambda x, t: x == t
    }
    
    if rule_data.operator not in operator_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid operator: {rule_data.operator}"
        )
        
    condition = lambda x: operator_map[rule_data.operator](x, rule_data.threshold)
    
    # 규칙 생성
    rule = AlertRule(
        name=rule_data.name,
        metric_name=rule_data.metric_name,
        condition=condition,
        severity=rule_data.severity,
        channels=rule_data.channels,
        message_template=rule_data.message_template,
        cooldown_minutes=rule_data.cooldown_minutes,
        consecutive_failures=rule_data.consecutive_failures
    )
    
    alert_manager.add_rule(rule)
    
    return {
        "message": "Alert rule created successfully",
        "rule_name": rule_data.name
    }


@router.delete("/alerts/rules/{rule_name}")
async def delete_alert_rule(
    rule_name: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    알림 규칙 삭제 (관리자 전용)
    """
    alert_manager.remove_rule(rule_name)
    
    return {"message": "Alert rule deleted successfully"}


@router.get("/alerts/history", response_model=AlertHistoryResponse)
async def get_alert_history(
    hours: int = Query(24, description="조회할 시간 범위"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    알림 이력 조회 (관리자 전용)
    """
    alerts = await alert_manager.get_alert_history(hours)
    
    return {
        "alerts": alerts,
        "total": len(alerts)
    }


@router.post("/alerts/test/{rule_name}")
async def test_alert_rule(
    rule_name: str,
    test_value: float = Query(..., description="테스트할 값"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    알림 규칙 테스트 (관리자 전용)
    
    실제로 알림을 발송하지 않고 규칙이 트리거되는지 확인
    """
    if rule_name not in alert_manager.rules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule not found: {rule_name}"
        )
        
    rule = alert_manager.rules[rule_name]
    would_trigger = rule.condition(test_value)
    
    return {
        "rule_name": rule_name,
        "test_value": test_value,
        "would_trigger": would_trigger,
        "message": rule.format_message(test_value) if would_trigger else None
    }


@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_admin_user)
):
    """
    대시보드용 종합 데이터 (관리자 전용)
    
    모니터링 대시보드에 필요한 모든 데이터를 한 번에 제공
    """
    # 헬스 상태
    health_status = await health_checker.check_all()
    
    # 메트릭 요약
    metrics_summary = metrics_collector.get_metrics_summary()
    
    # 최근 알림
    recent_alerts = await alert_manager.get_alert_history(hours=6)
    
    # API 에러율 계산
    total_requests = sum(
        v for k, v in metrics_summary["counters"].items()
        if k.startswith("api.status.")
    )
    total_errors = metrics_summary["counters"].get("api.errors.total", 0)
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "health": {
            "overall_status": health_status["status"],
            "components": health_status["checks"]
        },
        "metrics": {
            "uptime_hours": round(metrics_summary["uptime_seconds"] / 3600, 2),
            "api_error_rate": round(error_rate, 2),
            "total_requests": total_requests,
            "cache_hit_rate": metrics_summary["gauges"].get("cache.hit_rate", {}).get("current", 0)
        },
        "recent_alerts": recent_alerts[:10],  # 최근 10개만
        "timestamp": datetime.utcnow().isoformat()
    }