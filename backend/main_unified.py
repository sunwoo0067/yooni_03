"""
통합된 FastAPI 애플리케이션
개발/프로덕션 모드를 환경 변수로 제어
"""
import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# 환경 변수로 모드 결정
APP_MODE = os.getenv("APP_MODE", "development")  # development, production
APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG if APP_MODE == "development" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 개발 모드 설정
if APP_MODE == "development":
    # 간단한 설정
    from app.core.config import Settings
    settings = Settings()
    
    # 기본 데이터베이스만 초기화
    from app.services.database.database import init_db
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """개발 모드 생명주기"""
        logger.info(f"🚀 Starting in DEVELOPMENT mode on port {APP_PORT}")
        init_db()
        yield
        logger.info("👋 Shutting down...")
    
    # 개발용 간단한 앱
    app = FastAPI(
        title="Yooni Dropshipping System (Dev)",
        version="1.0.0",
        description="개발 모드 - 핵심 기능만 활성화",
        lifespan=lifespan
    )
    
    # 필수 라우터만 추가
    try:
        from app.api.v1.endpoints import products, platform_accounts, orders, wholesaler
        app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
        app.include_router(platform_accounts.router, prefix="/api/v1/platforms", tags=["platforms"]) 
        app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
        app.include_router(wholesaler.router, prefix="/api/v1/wholesaler", tags=["wholesaler"])
    except ImportError as e:
        logger.warning(f"일부 라우터 로드 실패 (개발 모드에서는 정상): {e}")
    
    # 한국 도매 사이트 수집 API (개발용)
    if Path("wholesaler_collector.py").exists():
        try:
            from wholesaler_collector import KoreanWholesalerCollector
            from fastapi import Form, HTTPException
            from typing import Optional
            
            @app.post("/api/v1/collect/products")
            async def collect_products(
                source: str = Form(...),
                keyword: str = Form(...),
                category: Optional[str] = Form(None),
                price_min: Optional[int] = Form(None),
                price_max: Optional[int] = Form(None),
                limit: int = Form(50),
                page: int = Form(1)
            ):
                """한국 도매 사이트에서 상품 수집 (개발용)"""
                supported_sources = ['ownerclan', 'domeme', 'gentrade']
                if source not in supported_sources:
                    raise HTTPException(status_code=400, detail=f"지원하지 않는 소스: {source}")
                
                collector = KoreanWholesalerCollector()
                products = await collector.collect_products(source, keyword, page)
                
                return {
                    "success": True,
                    "source": source,
                    "keyword": keyword,
                    "total": len(products),
                    "products": products[:10]  # 미리보기
                }
                
            @app.get("/api/v1/collect/sources")
            async def get_collection_sources():
                """지원하는 도매 사이트 목록"""
                return {
                    "sources": [
                        {"id": "ownerclan", "name": "오너클랜", "supported": True},
                        {"id": "domeme", "name": "도매매", "supported": True},
                        {"id": "gentrade", "name": "젠트레이드", "supported": True}
                    ]
                }
        except Exception as e:
            logger.warning(f"한국 도매 수집기 로드 실패: {e}")

# 프로덕션 모드 설정
else:
    # 전체 설정 로드
    from app.core.config import get_settings
    settings = get_settings()
    
    # 전체 데이터베이스 초기화
    from app.core.database import engine
    from app.db.base import Base
    from app.db.init_db import init_db
    from app.core.websocket import manager
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """프로덕션 모드 생명주기"""
        logger.info(f"🚀 Starting in PRODUCTION mode on port {APP_PORT}")
        
        # 데이터베이스 초기화
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await init_db()
        
        # WebSocket 매니저 초기화
        await manager.startup()
        
        yield
        
        # 정리 작업
        await manager.shutdown()
        await engine.dispose()
        logger.info("👋 Shutting down...")
    
    # 프로덕션용 전체 기능 앱
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan
    )
    
    # 전체 API 라우터 추가
    from app.api.v1 import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)

# 공통 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3006", "http://localhost:3010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if APP_MODE == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# 기본 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "Yooni Dropshipping System API",
        "mode": APP_MODE,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mode": APP_MODE,
        "timestamp": datetime.now().isoformat()
    }

# WebSocket 엔드포인트 (개발/프로덕션 공통)
if APP_MODE == "development":
    # 간단한 WebSocket 구현
    from fastapi import WebSocket, WebSocketDisconnect
    import json
    
    class SimpleConnectionManager:
        def __init__(self):
            self.active_connections: set[WebSocket] = set()
        
        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.add(websocket)
        
        def disconnect(self, websocket: WebSocket):
            self.active_connections.discard(websocket)
        
        async def broadcast(self, message: str):
            disconnected = set()
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.add(connection)
            for conn in disconnected:
                self.disconnect(conn)
    
    ws_manager = SimpleConnectionManager()
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                # 간단한 에코 또는 브로드캐스트
                await ws_manager.broadcast(data)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
else:
    # 프로덕션 WebSocket (기존 구현 사용)
    from app.api.v1.endpoints.websocket import router as websocket_router
    app.include_router(websocket_router)

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_unified:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=APP_MODE == "development",
        log_level="debug" if APP_MODE == "development" else "info"
    )