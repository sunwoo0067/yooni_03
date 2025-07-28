"""
모니터링 시스템 설정 예제

이 파일은 모니터링 시스템을 사용하는 방법을 보여주는 예제입니다.
"""
import asyncio
from app.services.monitoring import (
    metrics_collector,
    track_time,
    APIMetrics,
    CacheMetrics,
    alert_manager,
    AlertRule,
    AlertSeverity,
    AlertChannel
)

# 1. 메트릭 수집 예제
async def example_metrics_collection():
    """메트릭 수집 사용 예제"""
    
    # API 요청 메트릭 기록
    APIMetrics.record_request(
        method="GET",
        path="/api/v1/products",
        status_code=200,
        duration=150.5  # 밀리초
    )
    
    # 캐시 메트릭
    await CacheMetrics.record_hit()  # 캐시 히트
    await CacheMetrics.record_miss()  # 캐시 미스
    
    # 커스텀 메트릭
    metrics_collector.increment_counter("custom.event.count", 1)
    metrics_collector.record_gauge("custom.queue.size", 42)
    metrics_collector.record_timing("custom.operation.duration", 0.123)
    
    # 메트릭 요약 조회
    summary = metrics_collector.get_metrics_summary()
    print("메트릭 요약:", summary)


# 2. 함수 실행 시간 추적 예제
@track_time("example.function.duration")
async def example_tracked_function():
    """실행 시간이 자동으로 추적되는 함수"""
    await asyncio.sleep(0.1)  # 시뮬레이션
    return "완료"


# 3. 커스텀 알림 규칙 추가 예제
def setup_custom_alerts():
    """커스텀 알림 규칙 설정"""
    
    # 사용자 등록 속도 알림
    alert_manager.add_rule(
        AlertRule(
            name="high_user_registration_rate",
            metric_name="business.users.registration_rate",
            condition=lambda x: x > 100,  # 시간당 100명 이상
            severity=AlertSeverity.INFO,
            channels=[AlertChannel.SLACK],
            message_template="사용자 등록 급증: 시간당 {value}명",
            cooldown_minutes=30
        )
    )
    
    # 결제 실패율 알림
    alert_manager.add_rule(
        AlertRule(
            name="high_payment_failure_rate",
            metric_name="business.payments.failure_rate",
            condition=lambda x: x > 5,  # 5% 이상
            severity=AlertSeverity.ERROR,
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
            message_template="결제 실패율 높음: {value:.1f}%",
            cooldown_minutes=10,
            consecutive_failures=2  # 2번 연속 실패시 알림
        )
    )
    
    # 재고 부족 알림
    alert_manager.add_rule(
        AlertRule(
            name="low_inventory",
            metric_name="business.inventory.low_stock_items",
            condition=lambda x: x > 10,  # 10개 이상 상품이 재고 부족
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.EMAIL],
            message_template="재고 부족 상품: {value}개",
            cooldown_minutes=60
        )
    )


# 4. 알림 테스트
async def test_alerts():
    """알림 시스템 테스트"""
    
    # 메트릭 값으로 알림 트리거
    await alert_manager.check_metric(
        metric_name="api.error_rate",
        value=15.5,  # 15.5% 에러율
        additional_data={"endpoint": "/api/v1/orders"}
    )
    
    # 알림 이력 조회
    history = await alert_manager.get_alert_history(hours=24)
    print(f"최근 24시간 알림: {len(history)}건")


# 5. 모니터링 대시보드 데이터 예제
async def get_monitoring_dashboard():
    """모니터링 대시보드용 데이터 조회"""
    
    from app.services.monitoring import health_checker
    
    # 헬스 체크
    health_status = await health_checker.check_all()
    
    # 메트릭 요약
    metrics = metrics_collector.get_metrics_summary()
    
    # 캐시 히트율
    cache_hit_rate = CacheMetrics.get_hit_rate()
    
    dashboard_data = {
        "health": health_status,
        "metrics": {
            "uptime_hours": metrics["uptime_seconds"] / 3600,
            "total_requests": sum(v for k, v in metrics["counters"].items() if k.startswith("api.status.")),
            "cache_hit_rate": cache_hit_rate,
            "active_alerts": len(await alert_manager.get_alert_history(hours=1))
        }
    }
    
    return dashboard_data


# 6. 환경 변수 설정 예제
"""
모니터링 관련 환경 변수 (.env 파일):

# 이메일 알림 설정
ADMIN_EMAIL=admin@example.com
EMAIL_SERVICE_URL=https://email-service.example.com

# 슬랙 알림 설정
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# 웹훅 알림 설정
ALERT_WEBHOOK_URL=https://your-monitoring-system.com/webhook

# 외부 API 모니터링
PAYMENT_API_URL=https://payment-gateway.com/health
EMAIL_SERVICE_URL=https://email-service.com/health
"""


# 7. FastAPI 통합 예제
"""
FastAPI 애플리케이션에서 모니터링 사용:

from fastapi import FastAPI
from app.middleware.logging_middleware import LoggingMiddleware
from app.services.monitoring import start_metrics_collection

app = FastAPI()

# 미들웨어 추가
app.add_middleware(
    LoggingMiddleware,
    skip_paths=["/health", "/metrics"]
)

# 시작시 메트릭 수집 시작
@app.on_event("startup")
async def startup_event():
    await start_metrics_collection()
    setup_custom_alerts()  # 커스텀 알림 규칙 추가

# API 엔드포인트에서 메트릭 수집
@app.post("/api/orders")
@track_time("api.orders.create")
async def create_order(order_data: dict):
    # 비즈니스 로직
    
    # 커스텀 메트릭 기록
    metrics_collector.increment_counter("business.orders.created")
    metrics_collector.record_gauge("business.orders.value", order_data["total"])
    
    return {"order_id": "12345"}
"""


if __name__ == "__main__":
    # 예제 실행
    async def main():
        print("=== 모니터링 시스템 예제 ===\n")
        
        print("1. 메트릭 수집 테스트")
        await example_metrics_collection()
        
        print("\n2. 함수 추적 테스트")
        await example_tracked_function()
        
        print("\n3. 알림 규칙 설정")
        setup_custom_alerts()
        print("알림 규칙:", alert_manager.get_rules())
        
        print("\n4. 대시보드 데이터")
        dashboard = await get_monitoring_dashboard()
        print("대시보드:", dashboard)
        
    asyncio.run(main())