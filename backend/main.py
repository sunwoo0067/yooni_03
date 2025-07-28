"""
FastAPI main application entry point.
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.services.database import db_manager, health_check
from app.api.v1 import api_router
from app.middleware.logging_middleware import LoggingMiddleware, RequestContextMiddleware
from app.middleware.security_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    SQLInjectionProtectionMiddleware,
    RequestLoggingMiddleware
)


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOG_FILE, encoding='utf-8') if settings.LOG_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    try:
        # Check database connection
        logger.info("Checking database connection...")
        if not db_manager.check_connection():
            logger.error("Database connection failed!")
            raise Exception("Cannot connect to database")
        
        # Create database tables
        logger.info("Creating database tables...")
        await db_manager.create_tables_async()
        
        # Create upload directory
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload directory created: {upload_dir}")
        
        # Create logs directory
        log_dir = Path(settings.LOG_FILE).parent if settings.LOG_FILE else Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Logs directory created: {log_dir}")
        
        # Start scheduler service
        logger.info("Starting scheduler service...")
        try:
            from app.services.wholesale.scheduler_service import SchedulerManager
            scheduler_service = await SchedulerManager.get_scheduler_service()
            logger.info("Scheduler service started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler service: {e}")
            # 스케줄러 실패는 치명적이지 않으므로 애플리케이션은 계속 실행
        
        # Start task queue
        logger.info("Starting task queue...")
        try:
            from app.services.tasks.task_queue import task_queue
            await task_queue.start()
            logger.info("Task queue started successfully")
        except Exception as e:
            logger.error(f"Failed to start task queue: {e}")
            # 태스크 큐 실패는 치명적이지 않으므로 계속 진행
        
        # Start metrics collection
        logger.info("Starting metrics collection...")
        try:
            from app.services.monitoring import start_metrics_collection
            await start_metrics_collection()
            logger.info("Metrics collection started successfully")
        except Exception as e:
            logger.error(f"Failed to start metrics collection: {e}")
            # 메트릭 수집 실패는 치명적이지 않으므로 계속 진행
        
        # Start cache warmup in background
        logger.info("Starting cache warmup...")
        try:
            from app.services.cache.cache_warmup_service import run_cache_warmup
            import asyncio
            asyncio.create_task(run_cache_warmup())
            logger.info("Cache warmup started in background")
        except Exception as e:
            logger.warning(f"Cache warmup failed to start: {e}")
            # 캐시 워밍업 실패는 치명적이지 않으므로 계속 진행
            
        # Start cache refresh service
        logger.info("Starting cache refresh service...")
        try:
            from app.services.cache.cache_refresh_service import cache_refresh_service
            await cache_refresh_service.start()
            logger.info("Cache refresh service started")
        except Exception as e:
            logger.warning(f"Cache refresh service failed to start: {e}")
            # 캐시 갱신 서비스 실패는 치명적이지 않으므로 계속 진행
            
        # Start collection scheduler
        logger.info("Starting collection scheduler...")
        try:
            from app.services.collection import collection_scheduler
            await collection_scheduler.start()
            logger.info("Collection scheduler started")
        except Exception as e:
            logger.warning(f"Collection scheduler failed to start: {e}")
            # 수집 스케줄러 실패는 치명적이지 않으므로 계속 진행
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop cache refresh service
    try:
        from app.services.cache.cache_refresh_service import cache_refresh_service
        await cache_refresh_service.stop()
        logger.info("Cache refresh service stopped")
    except Exception as e:
        logger.error(f"Error stopping cache refresh service: {e}")
        
    # Stop collection scheduler
    try:
        from app.services.collection import collection_scheduler
        await collection_scheduler.stop()
        logger.info("Collection scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping collection scheduler: {e}")
    
    # Shutdown task queue
    try:
        from app.services.tasks.task_queue import task_queue
        await task_queue.stop()
        logger.info("Task queue shutdown completed")
    except Exception as e:
        logger.error(f"Error shutting down task queue: {e}")
    
    # Shutdown scheduler service
    try:
        from app.services.wholesale.scheduler_service import SchedulerManager
        await SchedulerManager.shutdown()
        logger.info("Scheduler service shutdown completed")
    except Exception as e:
        logger.error(f"Error shutting down scheduler service: {e}")
    
    logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="E-commerce management platform with AI integration",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# Add middleware
if settings.DEBUG:
    # Trust all hosts in debug mode
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*"]
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Gzip compression middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # 1KB 이상인 응답만 압축
)

# Logging middleware
app.add_middleware(
    LoggingMiddleware,
    skip_paths=["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]
)

# Request context middleware
app.add_middleware(RequestContextMiddleware)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_request_size=10 * 1024 * 1024)  # 10MB
app.add_middleware(SQLInjectionProtectionMiddleware)
app.add_middleware(RequestLoggingMiddleware)


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP {exc.status_code} error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "type": "validation_error",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error" if not settings.DEBUG else str(exc),
                "type": "internal_error"
            }
        }
    )


# Static files
if Path(settings.UPLOAD_DIR).exists():
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# Health check endpoint
@app.get("/health")
async def health_check_endpoint():
    """Health check endpoint."""
    try:
        health_status = await health_check()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": settings.APP_VERSION,
            "services": health_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": settings.APP_VERSION,
                "error": str(e)
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation not available in production",
        "health": "/health"
    }


# Include API routers
app.include_router(
    api_router,
    prefix="/api/v1",
    tags=["API v1"]
)

# Debug: Print all registered routes
logger.info("=== Registered Routes ===")
for i, route in enumerate(app.routes):
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        logger.info(f"{i+1:2d}. {route.methods} {route.path}")
logger.info(f"Total routes registered: {len(app.routes)}")


# Remove additional logging middleware since we now use LoggingMiddleware


# Run the application
if __name__ == "__main__":
    # Development server configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        access_log=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1 if settings.DEBUG else 4,
    )