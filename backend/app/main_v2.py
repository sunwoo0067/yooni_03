"""
FastAPI application with V2 patterns applied.
V2 패턴이 적용된 FastAPI 애플리케이션.
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.logging_utils import get_logger
from app.core.cache_utils import CacheManager
from app.services.database import db_manager
from app.services.monitoring.monitoring_service_v2 import MonitoringServiceV2, MetricsCollector
from app.middleware.monitoring_middleware import MonitoringMiddleware
from app.api.v1 import api_router

# V2 서비스 임포트
from app.services.product.product_service_v2 import ProductServiceV2
from app.services.order_processing.order_processor_v2 import OrderProcessorV2
from app.services.ai.ai_service_v2 import AIServiceV2, GeminiProvider

# 로거 설정
logger = get_logger("FastAPI")


# 전역 서비스 인스턴스
cache_manager = None
monitoring_service = None
metrics_collector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    logger.info("Starting application with V2 patterns")
    
    global cache_manager, monitoring_service, metrics_collector
    
    try:
        # 데이터베이스 초기화
        logger.info("Initializing database connection")
        await db_manager.initialize()
        
        # 캐시 매니저 초기화
        if settings.REDIS_URL:
            import redis.asyncio as redis
            redis_client = await redis.from_url(settings.REDIS_URL)
            cache_manager = CacheManager(redis_client)
            logger.info("Cache manager initialized")
        
        # 모니터링 서비스 초기화
        metrics_collector = MetricsCollector()
        monitoring_service = MonitoringServiceV2(
            cache_service=cache_manager
        )
        
        # 모니터링 시작 (백그라운드 태스크)
        import asyncio
        monitoring_task = asyncio.create_task(
            monitoring_service.start_monitoring()
        )
        logger.info("Monitoring service started")
        
        # V2 서비스 초기화
        if settings.USE_V2_SERVICES:
            logger.info("Initializing V2 services")
            await initialize_v2_services()
            
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
        
    finally:
        # 정리 작업
        logger.info("Shutting down application")
        
        if monitoring_task:
            monitoring_task.cancel()
            
        await db_manager.close()
        
        if cache_manager:
            await cache_manager.redis.close()
            
        logger.info("Application shutdown complete")


async def initialize_v2_services():
    """V2 서비스 초기화"""
    # AI 서비스 초기화
    if settings.GEMINI_API_KEY:
        providers = [GeminiProvider(settings.GEMINI_API_KEY)]
        ai_service = AIServiceV2(providers, cache_service=cache_manager)
        
        # 서비스 등록 (의존성 주입을 위해)
        app.state.ai_service = ai_service
        
    logger.info("V2 services initialized")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)


# 미들웨어 설정
def setup_middleware():
    """미들웨어 설정"""
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted Host
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )
    
    # GZip 압축
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 모니터링 미들웨어
    if metrics_collector:
        app.add_middleware(
            MonitoringMiddleware,
            metrics_collector=metrics_collector
        )
    
    logger.info("Middleware configured")


# 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(
        f"Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )


# 라우터 등록
app.include_router(api_router, prefix="/api/v1")


# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """향상된 헬스체크"""
    try:
        # 데이터베이스 체크
        db_status = await db_manager.health_check()
        
        # 캐시 체크
        cache_status = "healthy"
        if cache_manager:
            try:
                await cache_manager.redis.ping()
            except:
                cache_status = "unhealthy"
                
        # 서비스 상태
        services_status = {
            "database": "healthy" if db_status else "unhealthy",
            "cache": cache_status,
            "monitoring": "healthy" if monitoring_service else "disabled",
            "v2_services": "enabled" if settings.USE_V2_SERVICES else "disabled"
        }
        
        # 전체 상태 결정
        overall_status = "healthy"
        if any(status == "unhealthy" for status in services_status.values()):
            overall_status = "degraded"
            
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "services": services_status,
            "metrics": monitoring_service.get_metrics_summary() if monitoring_service else None
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# 메트릭 엔드포인트
@app.get("/metrics")
async def metrics():
    """Prometheus 형식 메트릭"""
    if not monitoring_service:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Monitoring service not available"}
        )
        
    from fastapi.responses import PlainTextResponse
    metrics_data = monitoring_service.export_metrics(format="prometheus")
    return PlainTextResponse(content=metrics_data)


# 의존성 주입 헬퍼
def get_cache_service():
    """캐시 서비스 의존성"""
    return cache_manager


def get_monitoring_service():
    """모니터링 서비스 의존성"""
    return monitoring_service


def get_product_service(db, cache_service=None):
    """상품 서비스 의존성"""
    if settings.USE_V2_SERVICES:
        return ProductServiceV2(db, cache_service)
    else:
        # 기존 서비스
        from app.services.product_service import ProductService
        return ProductService(db)


def get_order_processor(db):
    """주문 처리기 의존성"""
    if settings.USE_V2_SERVICES:
        return OrderProcessorV2(db)
    else:
        from app.services.order_processing.order_processor import OrderProcessor
        return OrderProcessor(db)


# 미들웨어 설정 실행
setup_middleware()


# 개발 서버 실행
if __name__ == "__main__":
    uvicorn.run(
        "app.main_v2:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=True
    )