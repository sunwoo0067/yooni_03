"""
테스트 공통 픽스처 및 설정
"""
import pytest
import asyncio
import tempfile
import os
import shutil
from typing import Generator, Dict, Any
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from redis import Redis
from fakeredis import FakeRedis

# 테스트용 설정 임포트
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import Settings, DevelopmentSettings
from app.core.database import Base


# 테스트용 설정 오버라이드
@pytest.fixture(scope="session")
def test_settings():
    """테스트용 설정"""
    # 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()
    
    return DevelopmentSettings(
        DATABASE_URL=f"sqlite:///{temp_dir}/test.db",
        REDIS_URL="redis://localhost:6379/15",  # 테스트용 DB
        TESTING=True,
        LOG_LEVEL="DEBUG",
        SECRET_KEY="test-secret-key-123456789",
        API_KEY_EXPIRE_MINUTES=30,
        UPLOAD_DIR=f"{temp_dir}/uploads",
        LOG_DIR=f"{temp_dir}/logs"
    )


# 테스트 데이터베이스
@pytest.fixture(scope="session")
def test_engine(test_settings):
    """테스트용 데이터베이스 엔진"""
    engine = create_engine(
        test_settings.DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "isolation_level": None  # 자동 커밋 모드
        },
        poolclass=StaticPool,
        echo=False  # SQL 로깅 비활성화
    )
    
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    yield engine
    
    # 정리
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """테스트용 데이터베이스 세션"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_engine
    )
    
    # 트랜잭션 시작
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# Redis 모킹
@pytest.fixture(scope="function")
def mock_redis():
    """모킹된 Redis"""
    return FakeRedis()


# 파일 업로드 테스트용 임시 디렉토리
@pytest.fixture(scope="function")
def temp_upload_dir():
    """임시 업로드 디렉토리"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# 샘플 데이터 픽스처
@pytest.fixture
def sample_product_data():
    """테스트용 샘플 상품 데이터"""
    return {
        "name": "테스트 상품",
        "description": "테스트용 상품입니다",
        "price": 10000,
        "cost": 5000,
        "category": "테스트",
        "sku": "TEST-001",
        "stock_quantity": 100,
        "status": "active"
    }


@pytest.fixture
def sample_platform_data():
    """테스트용 샘플 플랫폼 데이터"""
    return {
        "platform": "coupang",
        "name": "테스트 쿠팡 계정",
        "account_id": "TEST_COUPANG_001",
        "status": "active",
        "is_connected": True
    }


@pytest.fixture
def sample_order_data():
    """테스트용 샘플 주문 데이터"""
    return {
        "order_number": "TEST-ORDER-001",
        "customer_name": "테스트 고객",
        "customer_email": "test@example.com",
        "customer_phone": "010-1234-5678",
        "total_amount": 50000,
        "status": "pending",
        "payment_status": "paid",
        "platform": "coupang"
    }


# 모킹 헬퍼
@pytest.fixture
def mock_ai_service(monkeypatch):
    """AI 서비스 모킹"""
    def mock_generate(*args, **kwargs):
        return "모킹된 AI 응답"
    
    monkeypatch.setattr("app.services.ai.ai_service.generate", mock_generate)
    

@pytest.fixture
def mock_wholesaler_api(monkeypatch):
    """도매처 API 모킹"""
    async def mock_collect(*args, **kwargs):
        return [{
            "name": "모킹된 상품",
            "price": 10000,
            "stock": 100
        }]
    
    monkeypatch.setattr("app.services.wholesalers.base_wholesaler.collect_products", mock_collect)


# FastAPI 테스트 클라이언트
@pytest.fixture(scope="function")
def test_client(test_db, test_settings, mock_redis):
    """테스트용 FastAPI 클라이언트"""
    from main_unified import app
    
    # 의존성 오버라이드
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    def override_get_settings():
        return test_settings
    
    def override_get_redis():
        return mock_redis
    
    # 의존성 주입
    try:
        from app.api.v1.dependencies.database import get_db
        from app.api.v1.dependencies.auth import get_settings
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_settings] = override_get_settings
    except ImportError:
        # 백업 방식
        pass
    
    with TestClient(app) as client:
        yield client
    
    # 의존성 오버라이드 제거
    app.dependency_overrides.clear()


# 비동기 테스트를 위한 이벤트 루프
@pytest.fixture(scope="session")
def event_loop():
    """비동기 테스트용 이벤트 루프"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# 인증 관련 픽스처
@pytest.fixture
def test_user_data():
    """테스트 사용자 데이터"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "테스트 사용자",
        "is_active": True
    }


@pytest.fixture
def authenticated_client(test_client, test_user_data):
    """인증된 테스트 클라이언트"""
    # 사용자 등록
    response = test_client.post("/api/v1/auth/register", json=test_user_data)
    
    # 로그인하여 토큰 획득
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }
    response = test_client.post("/api/v1/auth/login", data=login_data)
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        test_client.headers.update({"Authorization": f"Bearer {token}"})
    
    return test_client


# AI 서비스 모킹 개선
@pytest.fixture
def mock_ai_service_advanced():
    """고급 AI 서비스 모킹"""
    mock = Mock()
    mock.generate_description = Mock(return_value="AI가 생성한 상품 설명")
    mock.analyze_market_trend = Mock(return_value={
        "trend": "상승",
        "score": 85,
        "recommendations": ["키워드 최적화", "가격 조정"]
    })
    mock.optimize_price = Mock(return_value={
        "suggested_price": 12000,
        "confidence": 0.85
    })
    return mock


# 테스트 데이터 팩토리
@pytest.fixture
def product_factory(test_db):
    """상품 생성 팩토리"""
    def create_product(**kwargs):
        from app.models.product import Product
        
        defaults = {
            "name": "테스트 상품",
            "price": 10000,
            "cost": 5000,
            "sku": f"TEST-{id(kwargs)}",
            "status": "active"
        }
        defaults.update(kwargs)
        
        product = Product(**defaults)
        test_db.add(product)
        test_db.commit()
        test_db.refresh(product)
        return product
    
    return create_product


# 성능 테스트용 픽스처
@pytest.fixture
def performance_data():
    """성능 테스트용 대량 데이터"""
    return {
        "products": [
            {
                "name": f"성능테스트 상품 {i}",
                "price": 10000 + i * 1000,
                "sku": f"PERF-{i:04d}"
            }
            for i in range(100)
        ]
    }