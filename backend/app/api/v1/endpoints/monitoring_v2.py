"""
Monitoring dashboard API endpoints.
모니터링 대시보드 API 엔드포인트.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import PlainTextResponse

from app.core.logging_utils import get_logger
from app.services.monitoring.monitoring_service_v2 import MonitoringServiceV2
from app.api.v1.dependencies.auth import get_current_admin_user


router = APIRouter()
logger = get_logger("MonitoringAPI")


# 전역 모니터링 서비스 인스턴스 (실제로는 의존성 주입 사용)
monitoring_service = None


def get_monitoring_service() -> MonitoringServiceV2:
    """모니터링 서비스 의존성"""
    global monitoring_service
    if not monitoring_service:
        # 실제로는 적절한 초기화 필요
        monitoring_service = MonitoringServiceV2()
    return monitoring_service


@router.get("/metrics")
async def get_metrics(
    format: str = Query("json", enum=["json", "prometheus"]),
    admin_user = Depends(get_current_admin_user),
    service: MonitoringServiceV2 = Depends(get_monitoring_service)
):
    """
    시스템 메트릭 조회.
    
    - **format**: 응답 형식 (json 또는 prometheus)
    """
    try:
        if format == "prometheus":
            content = service.export_metrics(format="prometheus")
            return PlainTextResponse(content=content)
        else:
            return service.get_metrics_summary()
            
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/metrics/system")
async def get_system_metrics(
    last_minutes: int = Query(5, ge=1, le=60),
    admin_user = Depends(get_current_admin_user),
    service: MonitoringServiceV2 = Depends(get_monitoring_service)
):
    """
    시스템 리소스 메트릭 조회.
    
    - **last_minutes**: 조회할 시간 범위 (분)
    """
    last_seconds = last_minutes * 60
    
    return {
        "cpu": service.metrics_collector.calculate_stats(
            "system.cpu.usage", 
            last_seconds=last_seconds
        ),
        "memory": service.metrics_collector.calculate_stats(
            "system.memory.usage", 
            last_seconds=last_seconds
        ),
        "disk": service.metrics_collector.calculate_stats(
            "system.disk.usage", 
            last_seconds=last_seconds
        ),
        "network": {
            "bytes_sent": service.metrics_collector.calculate_stats(
                "system.network.bytes_sent", 
                last_seconds=last_seconds
            ),
            "bytes_recv": service.metrics_collector.calculate_stats(
                "system.network.bytes_recv", 
                last_seconds=last_seconds
            )
        }
    }


@router.get("/metrics/application")
async def get_application_metrics(
    last_minutes: int = Query(5, ge=1, le=60),
    endpoint: Optional[str] = None,
    admin_user = Depends(get_current_admin_user),
    service: MonitoringServiceV2 = Depends(get_monitoring_service)
):
    """
    애플리케이션 메트릭 조회.
    
    - **last_minutes**: 조회할 시간 범위 (분)
    - **endpoint**: 특정 엔드포인트 필터 (선택)
    """
    last_seconds = last_minutes * 60
    tags = {"endpoint": endpoint} if endpoint else None
    
    return {
        "requests": {
            "total": service.metrics_collector.calculate_stats(
                "http.request.count", 
                tags=tags,
                last_seconds=last_seconds
            ),
            "errors": service.metrics_collector.calculate_stats(
                "http.request.error", 
                tags=tags,
                last_seconds=last_seconds
            ),
            "duration": service.metrics_collector.calculate_stats(
                "http.request.duration", 
                tags=tags,
                last_seconds=last_seconds
            )
        },
        "database": {
            "queries": service.metrics_collector.calculate_stats(
                "db.query.count", 
                last_seconds=last_seconds
            ),
            "duration": service.metrics_collector.calculate_stats(
                "db.query.duration", 
                last_seconds=last_seconds
            )
        },
        "cache": {
            "operations": service.metrics_collector.calculate_stats(
                "cache.operation.count", 
                last_seconds=last_seconds
            ),
            "hit_rate": _calculate_cache_hit_rate(service, last_seconds)
        }
    }


@router.get("/metrics/business")
async def get_business_metrics(
    metric_name: str,
    last_hours: int = Query(24, ge=1, le=168),  # 최대 1주일
    admin_user = Depends(get_current_admin_user),
    service: MonitoringServiceV2 = Depends(get_monitoring_service)
):
    """
    비즈니스 메트릭 조회.
    
    - **metric_name**: 메트릭 이름 (예: orders.created, revenue.total)
    - **last_hours**: 조회할 시간 범위 (시간)
    """
    last_seconds = last_hours * 3600
    
    metrics = service.metrics_collector.get_metrics(
        f"business.{metric_name}",
        last_seconds=last_seconds
    )
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")
        
    # 시간별 집계
    hourly_data = _aggregate_by_hour(metrics)
    
    return {
        "metric_name": metric_name,
        "period": f"last_{last_hours}_hours",
        "stats": service.metrics_collector.calculate_stats(
            f"business.{metric_name}",
            last_seconds=last_seconds
        ),
        "hourly_data": hourly_data
    }


@router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    admin_user = Depends(get_current_admin_user),
    service: MonitoringServiceV2 = Depends(get_monitoring_service)
):
    """
    알림 목록 조회.
    
    - **active_only**: 활성 알림만 조회
    - **limit**: 최대 조회 개수
    """
    alerts = list(service.alert_manager.alert_history)[-limit:]
    
    if active_only:
        # 최근 5분 이내 알림만
        cutoff_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        alerts = [a for a in alerts if a["timestamp"] >= cutoff_time]
        
    return {
        "total": len(alerts),
        "alerts": alerts
    }


@router.post("/alerts/rules")
async def add_alert_rule(
    rule_data: Dict[str, Any],
    admin_user = Depends(get_current_admin_user),
    service: MonitoringServiceV2 = Depends(get_monitoring_service)
):
    """
    새 알림 규칙 추가.
    
    Request body:
    ```json
    {
        "name": "High CPU Usage",
        "metric_name": "system.cpu.usage",
        "condition": "gt",
        "threshold": 90.0,
        "duration": 300
    }
    ```
    """
    try:
        service.alert_manager.add_rule(
            name=rule_data["name"],
            metric_name=rule_data["metric_name"],
            condition=rule_data["condition"],
            threshold=rule_data["threshold"],
            duration=rule_data.get("duration", 60),
            tags=rule_data.get("tags")
        )
        
        return {"message": "Alert rule added successfully"}
        
    except Exception as e:
        logger.error(f"Failed to add alert rule: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health/detailed")
async def get_detailed_health(
    admin_user = Depends(get_current_admin_user),
    service: MonitoringServiceV2 = Depends(get_monitoring_service)
):
    """상세 헬스 체크"""
    # 최근 1분간의 메트릭으로 건강 상태 판단
    cpu_stats = service.metrics_collector.calculate_stats(
        "system.cpu.usage", 
        last_seconds=60
    )
    memory_stats = service.metrics_collector.calculate_stats(
        "system.memory.usage", 
        last_seconds=60
    )
    error_stats = service.metrics_collector.calculate_stats(
        "http.request.error", 
        last_seconds=60
    )
    
    # 상태 판단
    health_status = "healthy"
    issues = []
    
    if cpu_stats["avg"] > 80:
        health_status = "degraded"
        issues.append(f"High CPU usage: {cpu_stats['avg']:.1f}%")
        
    if memory_stats["avg"] > 90:
        health_status = "degraded"
        issues.append(f"High memory usage: {memory_stats['avg']:.1f}%")
        
    if error_stats["count"] > 10:
        health_status = "unhealthy"
        issues.append(f"High error rate: {error_stats['count']} errors/min")
        
    return {
        "status": health_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "cpu": {
                "status": "ok" if cpu_stats["avg"] <= 80 else "warning",
                "value": cpu_stats["avg"]
            },
            "memory": {
                "status": "ok" if memory_stats["avg"] <= 90 else "warning",
                "value": memory_stats["avg"]
            },
            "errors": {
                "status": "ok" if error_stats["count"] <= 10 else "critical",
                "value": error_stats["count"]
            }
        },
        "issues": issues
    }


# 헬퍼 함수들
def _calculate_cache_hit_rate(service: MonitoringServiceV2, last_seconds: int) -> float:
    """캐시 히트율 계산"""
    hit_stats = service.metrics_collector.calculate_stats(
        "cache.operation.count",
        tags={"result": "hit"},
        last_seconds=last_seconds
    )
    miss_stats = service.metrics_collector.calculate_stats(
        "cache.operation.count",
        tags={"result": "miss"},
        last_seconds=last_seconds
    )
    
    total = hit_stats["count"] + miss_stats["count"]
    if total == 0:
        return 0.0
        
    return (hit_stats["count"] / total) * 100


def _aggregate_by_hour(metrics: list) -> list:
    """시간별 메트릭 집계"""
    from collections import defaultdict
    
    hourly = defaultdict(list)
    
    for metric in metrics:
        # 타임스탬프를 시간 단위로 반올림
        dt = datetime.fromtimestamp(metric["timestamp"])
        hour = dt.replace(minute=0, second=0, microsecond=0)
        hourly[hour].append(metric["value"])
        
    # 평균값 계산
    result = []
    for hour, values in sorted(hourly.items()):
        result.append({
            "timestamp": hour.isoformat(),
            "value": sum(values) / len(values),
            "count": len(values)
        })
        
    return result