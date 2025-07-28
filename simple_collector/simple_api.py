#!/usr/bin/env python3
"""
간단한 API 서버 (테스트용)
"""

import sys
import os
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("Simple API Server 시작...")

try:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    
    app = FastAPI(title="Simple Collector API")

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"message": "Simple Collector API", "status": "running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/dashboard/stats")
    async def dashboard_stats():
        return {
            "total_products": 0,
            "total_suppliers": 4,
            "collection_status": "ready",
            "last_sync": None
        }

    @app.get("/api/suppliers")
    async def get_suppliers():
        return {
            "suppliers": [
                {"id": 1, "name": "Zentrade", "code": "zentrade", "is_active": True},
                {"id": 2, "name": "OwnerClan", "code": "ownerclan", "is_active": True},
                {"id": 3, "name": "도매꾹", "code": "domeggook", "is_active": True},
                {"id": 4, "name": "도모매", "code": "domomae", "is_active": True},
            ]
        }

    @app.get("/api/products")
    async def get_products():
        return {
            "products": [],
            "total": 0,
            "page": 1,
            "per_page": 20
        }

    print("API 서버 구성 완료")
    print("서버 시작 중...")
    print("API URL: http://localhost:8002")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
        reload=False,
        log_level="info"
    )

except Exception as e:
    print(f"API 서버 시작 실패: {e}")
    print("FastAPI와 uvicorn이 설치되어 있는지 확인하세요.")

if __name__ == "__main__":
    pass