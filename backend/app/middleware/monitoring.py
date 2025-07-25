"""
모니터링 미들웨어
Prometheus 메트릭 수집, 헬스체크
"""
import time
import psutil
import asyncio
from typing import Callable, Dict, Any
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response as StarletteResponse
from sqlalchemy import text

from ..core.config_v2 import settings
from ..core.database import engine
from ..utils.logger import get_logger


# Prometheus 메트릭 정의
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests in progress'
)

# 시스템 메트릭
system_cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
system_memory_usage = Gauge('system_memory_usage_percent', 'System memory usage percentage')
system_disk_usage = Gauge('system_disk_usage_percent', 'System disk usage percentage')

# 데이터베이스 메트릭
db_connection_pool_size = Gauge('db_connection_pool_size', 'Database connection pool size')
db_connection_pool_checked_out = Gauge('db_connection_pool_checked_out', 'Checked out connections')
db_connection_pool_overflow = Gauge('db_connection_pool_overflow', 'Overflow connections')

# 비즈니스 메트릭
orders_created_total = Counter('orders_created_total', 'Total orders created')
orders_processed_total = Counter('orders_processed_total', 'Total orders processed', ['status'])
products_created_total = Counter('products_created_total', 'Total products created')
revenue_total = Counter('revenue_total_krw', 'Total revenue in KRW')


class MonitoringMiddleware:
    """모니터링 미들웨어"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.logger = get_logger(__name__)
        
        # 시스템 메트릭 수집 시작
        if settings.PROMETHEUS_ENABLED:
            asyncio.create_task(self._collect_system_metrics())
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """메트릭 수집"""
        if not settings.PROMETHEUS_ENABLED:
            return await call_next(request)
        
        # 메트릭 엔드포인트는 제외
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # 진행 중인 요청 수 증가
        http_requests_in_progress.inc()
        
        # 요청 시작 시간
        start_time = time.time()
        
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 메트릭 수집
            duration = time.time() - start_time
            endpoint = self._get_endpoint_label(request)
            
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        finally:
            # 진행 중인 요청 수 감소
            http_requests_in_progress.dec()
    
    def _get_endpoint_label(self, request: Request) -> str:
        """엔드포인트 레이블 생성"""
        # 경로 파라미터를 일반화
        path = request.url.path
        
        # 일반적인 파라미터 패턴 치환
        import re
        path = re.sub(r'/\d+', '/{id}', path)
        path = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', path)
        
        return path
    
    async def _collect_system_metrics(self):
        """시스템 메트릭 주기적 수집"""
        while True:
            try:
                # CPU 사용률
                system_cpu_usage.set(psutil.cpu_percent(interval=1))
                
                # 메모리 사용률
                memory = psutil.virtual_memory()
                system_memory_usage.set(memory.percent)
                
                # 디스크 사용률
                disk = psutil.disk_usage('/')
                system_disk_usage.set(disk.percent)
                
                # 데이터베이스 연결 풀 상태
                if hasattr(engine.pool, 'size'):
                    db_connection_pool_size.set(engine.pool.size())
                    db_connection_pool_checked_out.set(engine.pool.checked_out())
                    db_connection_pool_overflow.set(engine.pool.overflow())
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
            
            # 30초마다 수집
            await asyncio.sleep(30)


async def metrics_endpoint(request: Request) -> StarletteResponse:
    """Prometheus 메트릭 엔드포인트"""
    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


async def health_check(request: Request) -> Dict[str, Any]:
    """헬스체크 엔드포인트"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    # 데이터베이스 체크
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time_ms": 0
            }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis 체크
    try:
        from ..core.cache import redis_client
        start = time.time()
        await redis_client.ping()
        response_time = (time.time() - start) * 1000
        
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "response_time_ms": round(response_time, 2)
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # 디스크 공간 체크
    disk_usage = psutil.disk_usage('/')
    if disk_usage.percent > 90:
        health_status["status"] = "unhealthy"
        health_status["checks"]["disk"] = {
            "status": "unhealthy",
            "usage_percent": disk_usage.percent,
            "error": "Disk usage too high"
        }
    else:
        health_status["checks"]["disk"] = {
            "status": "healthy",
            "usage_percent": disk_usage.percent
        }
    
    # 메모리 체크
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        health_status["status"] = "unhealthy"
        health_status["checks"]["memory"] = {
            "status": "unhealthy",
            "usage_percent": memory.percent,
            "error": "Memory usage too high"
        }
    else:
        health_status["checks"]["memory"] = {
            "status": "healthy",
            "usage_percent": memory.percent
        }
    
    return health_status


async def readiness_check(request: Request) -> Dict[str, Any]:
    """준비 상태 체크 (쿠버네티스용)"""
    try:
        # 데이터베이스 연결 체크
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Redis 연결 체크
        from ..core.cache import redis_client
        await redis_client.ping()
        
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


async def liveness_check(request: Request) -> Dict[str, Any]:
    """생존 체크 (쿠버네티스용)"""
    return {"status": "alive", "timestamp": time.time()}


def setup_monitoring(app: FastAPI):
    """모니터링 설정"""
    if settings.PROMETHEUS_ENABLED:
        # 미들웨어 추가
        app.add_middleware(MonitoringMiddleware)
        
        # 메트릭 엔드포인트 추가
        app.add_api_route("/metrics", metrics_endpoint, methods=["GET"])
    
    # 헬스체크 엔드포인트
    app.add_api_route("/health", health_check, methods=["GET"])
    app.add_api_route("/ready", readiness_check, methods=["GET"])
    app.add_api_route("/live", liveness_check, methods=["GET"])