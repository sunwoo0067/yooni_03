"""
Enhanced test configuration with comprehensive fixtures for dropshipping system
"""
import pytest
import asyncio
import tempfile
import os
import shutil
import json
from typing import Generator, Dict, Any, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from redis import Redis
from fakeredis import FakeRedis
import httpx
from unittest.mock import MagicMock

# Test settings import
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import Settings, DevelopmentSettings
from app.core.database import Base, get_async_session
from app.models.base import BaseModel


# Enhanced Test Settings
@pytest.fixture(scope="session")
def enhanced_test_settings():
    """Enhanced test settings with all necessary configurations"""
    temp_dir = tempfile.mkdtemp()
    
    return DevelopmentSettings(
        DATABASE_URL=f"sqlite:///{temp_dir}/test_enhanced.db",
        REDIS_URL="redis://localhost:6379/15",
        TESTING=True,
        LOG_LEVEL="DEBUG",
        SECRET_KEY="test-secret-key-enhanced-dropshipping-123456789",
        API_KEY_EXPIRE_MINUTES=30,
        UPLOAD_DIR=f"{temp_dir}/uploads",
        LOG_DIR=f"{temp_dir}/logs",
        
        # AI Service Settings (mocked)
        GEMINI_API_KEY="test-gemini-key",
        OPENAI_API_KEY="test-openai-key",
        ANTHROPIC_API_KEY="test-anthropic-key",
        OLLAMA_BASE_URL="http://localhost:11434",
        
        # Wholesaler API Settings (mocked)
        OWNERCLAN_BASE_URL="https://api.ownerclan.com",
        ZENTRADE_BASE_URL="https://api.zentrade.com",
        DOMEGGOOK_BASE_URL="https://api.domeggook.com",
        
        # Marketplace API Settings (mocked)
        COUPANG_VENDOR_ID="test-vendor",
        COUPANG_ACCESS_KEY="test-access-key",
        COUPANG_SECRET_KEY="test-secret-key",
        NAVER_CLIENT_ID="test-naver-client",
        NAVER_CLIENT_SECRET="test-naver-secret",
        ELEVENTY_API_KEY="test-11st-key",
        
        # Redis Settings
        REDIS_EXPIRY=300,
        CACHE_ENABLED=True,
        
        # Rate Limiting
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_REQUESTS=100,
        RATE_LIMIT_WINDOW=60,
    )


# Enhanced Database Setup
@pytest.fixture(scope="session")
def enhanced_test_engine(enhanced_test_settings):
    """Enhanced test database engine with all tables"""
    engine = create_engine(
        enhanced_test_settings.DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "isolation_level": None
        },
        poolclass=StaticPool,
        echo=False
    )
    
    # Import all models to ensure tables are created
    from app.models import (
        user, product, platform_account, order_automation, 
        dropshipping, inventory, wholesaler, ai_log,
        collected_product, pipeline, base
    )
    
    # Create all tables
    BaseModel.metadata.create_all(bind=engine)
    yield engine
    
    # Cleanup
    BaseModel.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def enhanced_test_db(enhanced_test_engine) -> Generator[Session, None, None]:
    """Enhanced test database session with transaction rollback"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=enhanced_test_engine
    )
    
    connection = enhanced_test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# Enhanced Redis Mock
@pytest.fixture(scope="function")
def enhanced_mock_redis():
    """Enhanced Redis mock with realistic behavior"""
    fake_redis = FakeRedis()
    
    # Add common cache data
    fake_redis.set("cache:test:key", json.dumps({"test": "data"}))
    fake_redis.expire("cache:test:key", 300)
    
    return fake_redis


# Mock Utilities for External APIs
@pytest.fixture
def mock_wholesaler_apis():
    """Mock all wholesaler APIs"""
    mocks = {
        'ownerclan': AsyncMock(),
        'zentrade': AsyncMock(),
        'domeggook': AsyncMock()
    }
    
    # OwnerClan Mock Response
    mocks['ownerclan'].collect_products.return_value = [
        {
            "id": "oc_001",
            "name": "테스트 보석 상품",
            "price": 15000,
            "cost": 7500,
            "stock": 50,
            "category": "보석",
            "description": "고급 테스트 보석",
            "images": ["https://example.com/image1.jpg"],
            "supplier": "ownerclan"
        },
        {
            "id": "oc_002", 
            "name": "실버 반지",
            "price": 25000,
            "cost": 12500,
            "stock": 30,
            "category": "보석",
            "description": "순은 반지",
            "images": ["https://example.com/image2.jpg"],
            "supplier": "ownerclan"
        }
    ]
    
    # Zentrade Mock Response  
    mocks['zentrade'].collect_products.return_value = [
        {
            "id": "zt_001",
            "name": "주방용품 세트",
            "price": 35000,
            "cost": 17500,
            "stock": 100,
            "category": "주방용품",
            "description": "스테인리스 주방용품",
            "images": ["https://example.com/kitchen1.jpg"],
            "supplier": "zentrade"
        }
    ]
    
    # Domeggook Mock Response
    mocks['domeggook'].collect_products.return_value = [
        {
            "id": "dg_001",
            "name": "생활용품 모음",
            "price": 20000,
            "cost": 10000,
            "stock": 200,
            "category": "생활용품",
            "description": "일상 생활용품 세트",
            "images": ["https://example.com/daily1.jpg"],
            "supplier": "domeggook"
        }
    ]
    
    return mocks


@pytest.fixture
def mock_marketplace_apis():
    """Mock all marketplace APIs"""
    mocks = {
        'coupang': AsyncMock(),
        'naver': AsyncMock(),
        'eleventy': AsyncMock()
    }
    
    # Coupang Mock Responses
    mocks['coupang'].create_product.return_value = {
        "success": True,
        "product_id": "cp_12345",
        "status": "registered",
        "vendor_item_id": "VI001"
    }
    
    mocks['coupang'].get_orders.return_value = [
        {
            "order_id": "cp_order_001",
            "product_id": "cp_12345",
            "quantity": 2,
            "price": 30000,
            "status": "paid",
            "customer": {
                "name": "홍길동",
                "phone": "010-1234-5678"
            }
        }
    ]
    
    # Naver Mock Responses
    mocks['naver'].create_product.return_value = {
        "success": True,
        "product_id": "nv_67890",
        "status": "registered"
    }
    
    # 11st Mock Responses
    mocks['eleventy'].create_product.return_value = {
        "success": True,
        "product_id": "11_54321",
        "status": "registered"
    }
    
    return mocks


@pytest.fixture
def mock_ai_services():
    """Mock all AI services"""
    mocks = {
        'gemini': AsyncMock(),
        'ollama': AsyncMock(),
        'langchain': AsyncMock()
    }
    
    # Gemini Mock Responses
    mocks['gemini'].generate_content.return_value = {
        "text": "AI로 생성된 상품 설명입니다. 이 제품은 고품질 소재로 제작되었으며 뛰어난 내구성을 자랑합니다.",
        "confidence": 0.95
    }
    
    mocks['gemini'].analyze_market_data.return_value = {
        "trend": "상승",
        "demand_score": 85,
        "competition_level": "중간",
        "recommended_price": 28000,
        "keywords": ["고품질", "내구성", "인기상품"]
    }
    
    # Ollama Mock Responses
    mocks['ollama'].generate.return_value = {
        "response": "로컬 AI로 생성된 컨텐츠",
        "model": "llama2"
    }
    
    # LangChain Mock Responses
    mocks['langchain'].process_chain.return_value = {
        "result": "체인 처리 결과",
        "steps": ["분석", "처리", "최적화"],
        "confidence": 0.88
    }
    
    return mocks


# Test Data Factories
@pytest.fixture
def product_factory(enhanced_test_db):
    """Enhanced product factory"""
    def create_product(**kwargs):
        from app.models.product import Product
        
        defaults = {
            "name": "테스트 상품",
            "description": "테스트용 상품 설명",
            "price": Decimal("15000"),
            "cost": Decimal("7500"),
            "sku": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "category": "테스트 카테고리",
            "stock_quantity": 100,
            "min_stock_level": 10,
            "status": "active",
            "weight": Decimal("0.5"),
            "dimensions": {"length": 10, "width": 8, "height": 5},
            "images": ["https://example.com/test-image.jpg"],
            "tags": ["테스트", "상품"],
            "margin_rate": Decimal("0.5"),
            "supplier": "test_supplier",
            "supplier_product_id": "SUPP_001"
        }
        defaults.update(kwargs)
        
        product = Product(**defaults)
        enhanced_test_db.add(product)
        enhanced_test_db.commit()
        enhanced_test_db.refresh(product)
        return product
    
    return create_product


@pytest.fixture
def user_factory(enhanced_test_db):
    """Enhanced user factory"""
    def create_user(**kwargs):
        from app.models.user import User
        from app.core.security import get_password_hash
        
        defaults = {
            "username": f"testuser_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "email": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
            "hashed_password": get_password_hash("testpassword123"),
            "full_name": "테스트 사용자",
            "is_active": True,
            "is_superuser": False,
            "business_info": {
                "company_name": "테스트 회사",
                "business_number": "123-45-67890"
            }
        }
        defaults.update(kwargs)
        
        user = User(**defaults)
        enhanced_test_db.add(user)
        enhanced_test_db.commit()
        enhanced_test_db.refresh(user)
        return user
    
    return create_user


@pytest.fixture 
def platform_account_factory(enhanced_test_db):
    """Enhanced platform account factory"""
    def create_platform_account(user_id=None, **kwargs):
        from app.models.platform_account import PlatformAccount
        
        defaults = {
            "user_id": user_id,
            "platform": "coupang",
            "account_name": "테스트 쿠팡 계정",
            "account_id": f"COUPANG_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "active",
            "is_connected": True,
            "connection_info": {
                "vendor_id": "test_vendor",
                "last_sync": datetime.utcnow().isoformat()
            },
            "settings": {
                "auto_order": True,
                "stock_sync": True,
                "price_sync": True
            }
        }
        defaults.update(kwargs)
        
        account = PlatformAccount(**defaults)
        enhanced_test_db.add(account)
        enhanced_test_db.commit()
        enhanced_test_db.refresh(account)
        return account
    
    return create_platform_account


@pytest.fixture
def order_factory(enhanced_test_db):
    """Enhanced order factory"""
    def create_order(user_id=None, **kwargs):
        from app.models.order_automation import Order
        
        defaults = {
            "user_id": user_id,
            "order_number": f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "platform": "coupang",
            "platform_order_id": f"CP_ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "customer_name": "테스트 고객",
            "customer_email": "customer@example.com",
            "customer_phone": "010-1234-5678",
            "shipping_address": {
                "name": "테스트 고객",
                "phone": "010-1234-5678",
                "address": "서울시 강남구 테스트동 123-45",
                "zipcode": "12345"
            },
            "total_amount": Decimal("45000"),
            "shipping_fee": Decimal("3000"),
            "status": "pending",
            "payment_status": "paid",
            "payment_method": "card",
            "order_items": [
                {
                    "product_id": "TEST_PROD_001",
                    "name": "테스트 상품",
                    "quantity": 2,
                    "price": Decimal("21000"),
                    "total": Decimal("42000")
                }
            ],
            "order_date": datetime.utcnow(),
            "notes": "테스트 주문"
        }
        defaults.update(kwargs)
        
        order = Order(**defaults)
        enhanced_test_db.add(order)
        enhanced_test_db.commit()
        enhanced_test_db.refresh(order)
        return order
    
    return create_order


# Performance Test Data
@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing"""
    return {
        "products": [
            {
                "name": f"성능테스트 상품 {i:04d}",
                "price": Decimal(str(10000 + i * 1000)),
                "cost": Decimal(str(5000 + i * 500)),
                "sku": f"PERF-{i:04d}",
                "category": f"카테고리 {i % 10}",
                "stock_quantity": 50 + i
            }
            for i in range(1000)
        ],
        "orders": [
            {
                "order_number": f"PERF_ORD_{i:06d}",
                "total_amount": Decimal(str(20000 + i * 1000)),
                "customer_name": f"고객 {i:04d}",
                "status": "completed" if i % 3 == 0 else "pending"
            }
            for i in range(500)
        ]
    }


# Mock HTTP Client for External APIs
@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external API calls"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    
    # Mock responses for different endpoints
    def mock_response(url, **kwargs):
        mock_resp = Mock()
        mock_resp.status_code = 200
        
        if "ownerclan" in str(url):
            mock_resp.json.return_value = {"success": True, "data": []}
        elif "zentrade" in str(url):
            mock_resp.text = "<xml><products></products></xml>"
        elif "domeggook" in str(url):
            mock_resp.json.return_value = {"products": []}
        elif "coupang" in str(url):
            mock_resp.json.return_value = {"code": "SUCCESS", "data": {}}
        elif "naver" in str(url):
            mock_resp.json.return_value = {"success": True}
        else:
            mock_resp.json.return_value = {"status": "ok"}
            
        return mock_resp
    
    mock_client.get.side_effect = mock_response
    mock_client.post.side_effect = mock_response
    mock_client.put.side_effect = mock_response
    mock_client.delete.side_effect = mock_response
    
    return mock_client


# Authentication Test Fixtures
@pytest.fixture
def test_user_token(enhanced_test_db, user_factory):
    """Create test user and return JWT token"""
    from app.core.security import create_access_token
    
    user = user_factory()
    token = create_access_token(data={"sub": user.username})
    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }


# Enhanced Test Client
@pytest.fixture(scope="function")
def enhanced_test_client(enhanced_test_db, enhanced_test_settings, enhanced_mock_redis):
    """Enhanced FastAPI test client with all dependencies mocked"""
    try:
        from main import app
    except ImportError:
        from main_unified import app
    
    # Override dependencies
    def override_get_db():
        try:
            yield enhanced_test_db
        finally:
            pass
    
    def override_get_settings():
        return enhanced_test_settings
    
    def override_get_redis():
        return enhanced_mock_redis
    
    # Apply dependency overrides
    try:
        from app.api.v1.dependencies.database import get_db
        from app.api.v1.dependencies.auth import get_settings
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_settings] = override_get_settings
    except ImportError:
        pass
    
    with TestClient(app) as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


# Async Test Session
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Test Markers Helper
@pytest.fixture
def test_markers():
    """Helper for test categorization"""
    return {
        "unit": "단위 테스트",
        "integration": "통합 테스트", 
        "e2e": "종단간 테스트",
        "api": "API 테스트",
        "performance": "성능 테스트",
        "security": "보안 테스트",
        "slow": "느린 테스트",
        "requires_db": "DB 필요",
        "requires_redis": "Redis 필요",
        "requires_api_key": "API 키 필요"
    }