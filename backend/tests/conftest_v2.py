"""
Enhanced test configuration with V2 patterns.
V2 패턴이 적용된 향상된 테스트 설정.
기존 conftest.py와 함께 사용 가능.
"""
import asyncio
import pytest
import pytest_asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import Mock, AsyncMock
import redis
from fakeredis import FakeRedis

from app.models.base import Base
from app.core.config import settings
from app.core.cache_utils import CacheManager, CacheService
from app.core.logging_utils import get_logger


# 테스트 데이터베이스 URL
TEST_DATABASE_URL = "sqlite:///./test_v2.db"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./test_async_v2.db"


# 비동기 테스트 설정
@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 픽스처"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# 비동기 데이터베이스 픽스처
@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """테스트용 비동기 DB 엔진"""
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL, 
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 비동기 DB 세션"""
    async_session_maker = async_sessionmaker(
        async_engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        async with session.begin():
            yield session
            await session.rollback()


# 캐시 관련 픽스처
@pytest.fixture
def fake_redis():
    """테스트용 가짜 Redis"""
    return FakeRedis(decode_responses=True)


@pytest.fixture
def cache_manager(fake_redis):
    """테스트용 캐시 매니저"""
    return CacheManager(fake_redis, default_ttl=60)


@pytest.fixture
def cache_service(cache_manager):
    """테스트용 캐시 서비스"""
    return CacheService(cache_manager, "test", default_ttl=60)


# V2 서비스 픽스처
@pytest_asyncio.fixture
async def product_service_v2(async_session, cache_service):
    """V2 상품 서비스"""
    from app.services.product.product_service_v2 import ProductServiceV2
    return ProductServiceV2(async_session, cache_service)


@pytest_asyncio.fixture
async def order_processor_v2(async_session):
    """V2 주문 처리기"""
    from app.services.order_processing.order_processor_v2 import OrderProcessorV2
    return OrderProcessorV2(async_session)


@pytest.fixture
def ai_service_v2(cache_service):
    """V2 AI 서비스"""
    from app.services.ai.ai_service_v2 import AIServiceV2, AIProvider
    
    # Mock 프로바이더
    mock_provider = Mock(spec=AIProvider)
    mock_provider.name = "MockProvider"
    mock_provider.is_available = AsyncMock(return_value=True)
    mock_provider.generate_text = AsyncMock(return_value="Generated text")
    mock_provider.analyze_product = AsyncMock(return_value={
        "analysis": "Product analysis result"
    })
    
    return AIServiceV2([mock_provider], cache_service)


# 테스트 데이터 생성 헬퍼
class TestDataFactory:
    """테스트 데이터 생성 팩토리"""
    
    @staticmethod
    def create_product_data(**kwargs):
        """상품 데이터 생성"""
        from decimal import Decimal
        
        defaults = {
            "sku": f"TEST-{asyncio.get_event_loop().time():.0f}",
            "name": "Test Product",
            "description": "Test product description",
            "category": "Test Category",
            "price": Decimal("100.00"),
            "stock_quantity": 10
        }
        defaults.update(kwargs)
        return defaults
        
    @staticmethod
    def create_order_data(user_id: str, **kwargs):
        """주문 데이터 생성"""
        defaults = {
            "user_id": user_id,
            "items": [
                {
                    "product_id": "test-product-id",
                    "quantity": 2,
                    "price": "100.00"
                }
            ],
            "shipping_address": {
                "street": "123 Test St",
                "city": "Test City",
                "postal_code": "12345"
            },
            "payment_method": "credit_card"
        }
        defaults.update(kwargs)
        return defaults
        
    @staticmethod
    def create_user_data(**kwargs):
        """사용자 데이터 생성"""
        defaults = {
            "email": f"test-{asyncio.get_event_loop().time():.0f}@example.com",
            "username": f"testuser-{asyncio.get_event_loop().time():.0f}",
            "password": "testpassword123",
            "full_name": "Test User",
            "is_active": True
        }
        defaults.update(kwargs)
        return defaults


@pytest.fixture
def test_data_factory():
    """테스트 데이터 팩토리 인스턴스"""
    return TestDataFactory()


# Mock 외부 API 클라이언트
@pytest.fixture
def mock_marketplace_api():
    """Mock 마켓플레이스 API"""
    from app.core.external_api_utils import APIClient
    
    client = Mock(spec=APIClient)
    client.get = AsyncMock(return_value={"status": "success"})
    client.post = AsyncMock(return_value={"id": "created-id"})
    client.close = AsyncMock()
    
    return client


# 성능 테스트 헬퍼
@pytest.fixture
def performance_monitor():
    """성능 모니터링 헬퍼"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.measurements = {}
            
        def start(self, name: str):
            self.measurements[name] = {"start": time.time()}
            
        def end(self, name: str):
            if name in self.measurements:
                self.measurements[name]["end"] = time.time()
                self.measurements[name]["duration"] = (
                    self.measurements[name]["end"] - 
                    self.measurements[name]["start"]
                )
                
        def get_duration(self, name: str) -> float:
            return self.measurements.get(name, {}).get("duration", 0)
            
        def assert_performance(self, name: str, max_duration: float):
            duration = self.get_duration(name)
            assert duration <= max_duration, (
                f"{name} took {duration:.2f}s, "
                f"expected <= {max_duration}s"
            )
            
    return PerformanceMonitor()


# 통합 테스트 헬퍼
@pytest_asyncio.fixture
async def integration_helper(async_session, cache_service):
    """통합 테스트를 위한 헬퍼"""
    
    class IntegrationHelper:
        def __init__(self, session, cache):
            self.session = session
            self.cache = cache
            self.created_ids = []
            
        async def create_test_product(self, **kwargs):
            """테스트 상품 생성"""
            from app.models.product import Product
            from app.core.constants import ProductStatus
            
            product_data = TestDataFactory.create_product_data(**kwargs)
            product = Product(**product_data)
            product.status = ProductStatus.ACTIVE.value
            
            self.session.add(product)
            await self.session.commit()
            
            self.created_ids.append(("product", product.id))
            return product
            
        async def create_test_user(self, **kwargs):
            """테스트 사용자 생성"""
            from app.models.user import User
            
            user_data = TestDataFactory.create_user_data(**kwargs)
            # 비밀번호 해싱 (실제 구현에 맞게 조정)
            user_data["hashed_password"] = user_data.pop("password")
            
            user = User(**user_data)
            self.session.add(user)
            await self.session.commit()
            
            self.created_ids.append(("user", user.id))
            return user
            
        async def cleanup(self):
            """생성된 테스트 데이터 정리"""
            # 역순으로 삭제 (외래키 제약 고려)
            for entity_type, entity_id in reversed(self.created_ids):
                # 실제 삭제 로직 구현
                pass
                
    helper = IntegrationHelper(async_session, cache_service)
    yield helper
    await helper.cleanup()


# 테스트 마커
def pytest_configure(config):
    """pytest 마커 등록"""
    config.addinivalue_line(
        "markers", "unit: 단위 테스트"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트"
    )
    config.addinivalue_line(
        "markers", "slow: 느린 테스트"
    )
    config.addinivalue_line(
        "markers", "requires_db: 데이터베이스가 필요한 테스트"
    )
    config.addinivalue_line(
        "markers", "requires_redis: Redis가 필요한 테스트"
    )
    config.addinivalue_line(
        "markers", "requires_api_key: API 키가 필요한 테스트"
    )