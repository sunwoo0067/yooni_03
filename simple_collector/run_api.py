#!/usr/bin/env python3
"""
API 서버 실행 스크립트 (독립 실행용)
"""

import sys
import os
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("Simple Collector API 서버 시작...")

try:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import JSONResponse
    
    # 기본 FastAPI 앱 생성
    app = FastAPI(
        title="Simple Product Collector API",
        version="1.0.0",
        description="단순화된 상품 수집 시스템"
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 정적 파일 서빙
    static_path = Path("static")
    static_path.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root():
        return {"message": "Simple Collector API", "status": "running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "message": "API 서버가 정상 작동 중입니다"}

    # 기본 엔드포인트들만 등록
    from api.excel_endpoints import router as excel_router
    from api.supplier_settings import router as settings_router
    
    app.include_router(excel_router)
    app.include_router(settings_router)

    # 추가 라우터들 (오류 발생 시 건너뛰기)
    try:
        from api.collection_endpoints import router as collection_router
        app.include_router(collection_router)
        print("✓ 수집 엔드포인트 등록됨")
    except Exception as e:
        print(f"⚠ 수집 엔드포인트 건너뛰기: {e}")

    try:
        from api.bestseller_endpoints import router as bestseller_router
        app.include_router(bestseller_router)
        print("✓ 베스트셀러 엔드포인트 등록됨")
    except Exception as e:
        print(f"⚠ 베스트셀러 엔드포인트 건너뛰기: {e}")

    try:
        from api.ai_sourcing_endpoints import router as ai_sourcing_router
        app.include_router(ai_sourcing_router)
        print("✓ AI 소싱 엔드포인트 등록됨")
    except Exception as e:
        print(f"⚠ AI 소싱 엔드포인트 건너뛰기: {e}")

    try:
        from api.image_endpoints import router as image_router
        app.include_router(image_router)
        print("✓ 이미지 엔드포인트 등록됨")
    except Exception as e:
        print(f"⚠ 이미지 엔드포인트 건너뛰기: {e}")

    try:
        from api.scheduler_endpoints import router as scheduler_router
        app.include_router(scheduler_router)
        print("✓ 스케줄러 엔드포인트 등록됨")
    except Exception as e:
        print(f"⚠ 스케줄러 엔드포인트 건너뛰기: {e}")

    print("API 서버 구성 완료")
    print("서버 시작 중...")

    # 서버 실행
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,  # 다른 포트 사용
        reload=False,
        log_level="info",
        access_log=False
    )

except Exception as e:
    print(f"❌ API 서버 시작 실패: {e}")
    print("\n필수 라이브러리 설치:")
    print("pip install fastapi uvicorn python-multipart")
    
if __name__ == "__main__":
    pass