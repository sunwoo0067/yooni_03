"""
Yooni 드롭쉬핑 시스템 - 개인 사용자용 간소화된 설정
단순한 구조와 최소한의 기능만 포함
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings

# 설정 로드
settings = get_settings()


# 응답 모델들
class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    version: str
    environment: str


class SystemInfoResponse(BaseModel):
    project_name: str
    version: str
    environment: str
    database_type: str
    single_user_mode: bool


class ServiceStatusResponse(BaseModel):
    services: dict[str, bool]
    database_connected: bool
    api_keys_configured: dict[str, bool]


# 애플리케이션 라이프사이클
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수"""

    # 시작 시
    print("🚀 Yooni 드롭쉬핑 시스템 - 개인 사용자용")
    print(f"🌍 환경: {settings.ENVIRONMENT}")
    print(f"👤 단일 사용자 모드: {settings.SINGLE_USER_MODE}")
    
    # 데이터베이스 초기화
    try:
        from app.services.database.personal_database_service import init_db
        init_db()
        print("💾 데이터베이스 초기화 완료")
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")

    yield

    # 종료 시
    print("🛑 개인 사용자 시스템 종료 중...")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Yooni 드롭쉬핑 시스템 - 개인 사용자용 간소화 버전",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정 (개인 사용자용으로 단순화)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL] if settings.FRONTEND_URL else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": f"🎉 {settings.PROJECT_NAME} (개인 사용자용)",
        "version": settings.VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "single_user_mode": settings.SINGLE_USER_MODE,
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    from datetime import datetime

    return HealthResponse(
        status="healthy",
        message="개인 사용자 시스템 정상 작동",
        timestamp=datetime.now().isoformat(),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@app.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info():
    """시스템 정보 조회"""
    # 데이터베이스 유형 확인
    db_type = "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL"
    
    return SystemInfoResponse(
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database_type=db_type,
        single_user_mode=settings.SINGLE_USER_MODE,
    )


@app.get("/services/status", response_model=ServiceStatusResponse)
async def get_services_status():
    """서비스 상태 확인"""
    
    # 데이터베이스 연결 상태 확인
    database_connected = False
    try:
        from app.services.database.personal_database_service import db_manager
        database_connected = db_manager.check_connection(max_retries=1)
    except Exception:
        database_connected = False

    # API 키 설정 상태 확인
    api_keys_configured = {
        "coupang": bool(settings.COUPANG_VENDOR_ID and settings.COUPANG_ACCESS_KEY),
        "naver": bool(settings.NAVER_CLIENT_ID and settings.NAVER_CLIENT_SECRET),
        "ownerclan": bool(settings.OWNERCLAN_API_KEY),
        "zentrade": bool(settings.ZENTRADE_API_KEY),
        "domaekkuk": bool(settings.DOMAEKKUK_API_KEY),
    }

    # 기본 서비스 상태
    services = {
        "product_collection": True,  # 항상 활성화
        "product_registration": any([
            api_keys_configured["coupang"],
            api_keys_configured["naver"]
        ]),
        "order_processing": any([
            api_keys_configured["coupang"],
            api_keys_configured["naver"]
        ]),
    }

    return ServiceStatusResponse(
        services=services,
        database_connected=database_connected,
        api_keys_configured=api_keys_configured,
    )


@app.get("/personal/setup-guide")
async def get_personal_setup_guide():
    """개인 사용자 설정 가이드"""

    return {
        "title": "개인 사용자 설정 가이드",
        "steps": [
            {
                "step": 1,
                "title": "환경 파일 설정",
                "description": ".env.simple 파일을 .env로 복사하고 필요한 정보를 입력하세요",
                "details": [
                    "공급사 API 키 설정 (최소 1개)",
                    "마켓플레이스 API 키 설정 (최소 1개)",
                    "필요시 AI 서비스 API 키 추가"
                ]
            },
            {
                "step": 2,
                "title": "데이터베이스 초기화",
                "description": "시스템 처음 실행 시 데이터베이스가 자동으로 생성됩니다",
                "details": [
                    "SQLite 데이터베이스가 ./yooni_personal.db에 생성됩니다",
                    "필요시 기존 데이터베이스 백업"
                ]
            },
            {
                "step": 3,
                "title": "서버 시작",
                "description": "백엔드 서버를 시작합니다",
                "command": "python main.py",
                "details": [
                    "환경 변수 YOONI_ENV_MODE=personal로 설정",
                    "http://localhost:8000에서 서버 접속"
                ]
            },
            {
                "step": 4,
                "title": "프론트엔드 시작",
                "description": "프론트엔드 애플리케이션을 시작합니다",
                "command": "cd frontend && npm run dev",
                "details": [
                    "http://localhost:3000에서 웹 인터페이스 접속",
                    "초기 계정: personal@yooni.local / 기본 비밀번호"
                ]
            },
            {
                "step": 5,
                "title": "기본 설정",
                "description": "웹 인터페이스에서 기본 설정을 완료합니다",
                "details": [
                    "공급사 및 마켓플레이스 계정 연결 확인",
                    "자동 수집 및 등록 설정",
                    "주문 처리 설정"
                ]
            }
        ],
        "tips": [
            "개인 사용자는 SQLite 데이터베이스를 사용하여 복잡한 설정을 피할 수 있습니다",
            "하나의 마켓플레이스만 사용하는 것을 권장합니다",
            "필요한 API 키만 설정하여 보안을 강화할 수 있습니다",
            "문제 발생 시 로그 파일을 확인하세요: logs/personal_app.log"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    print("🚀 개인 사용자용 서버 시작")
    print(f"📍 주소: http://localhost:8000")
    print(f"📘 API 문서: http://localhost:8000/docs")

    uvicorn.run(
        "personal_simple:app",
        host="127.0.0.1",  # 외부 접근 차단을 위해 localhost만 허용
        port=8000,
        log_level="info",
        reload=settings.DEBUG,
        workers=1,  # 개인 사용자용으로 단일 워커만 사용
    )