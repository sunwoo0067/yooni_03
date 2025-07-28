"""
Integration tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json
from decimal import Decimal
from datetime import datetime

from tests.conftest_enhanced import *
from tests.mocks import *


class TestProductEndpoints:
    """Test product-related API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_create_product_success(self, enhanced_test_client, test_user_token):
        """Test successful product creation"""
        product_data = {
            "name": "테스트 상품",
            "description": "테스트용 상품입니다",
            "price": 25000,
            "cost": 12500,
            "sku": "TEST-001",
            "category": "테스트 카테고리",
            "stock_quantity": 100,
            "min_stock_level": 10,
            "weight": 0.5,
            "dimensions": {"length": 10, "width": 8, "height": 5},
            "images": ["https://example.com/test-image.jpg"],
            "tags": ["테스트", "상품"],
            "supplier": "test_supplier",
            "supplier_product_id": "SUPP_001"
        }
        
        response = enhanced_test_client.post(
            "/api/v1/products/",
            json=product_data,
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["name"] == product_data["name"]
        assert result["price"] == product_data["price"]
        assert result["sku"] == product_data["sku"]
        assert "id" in result
        assert "created_at" in result
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_get_products_list(self, enhanced_test_client, test_user_token, product_factory):
        """Test getting products list"""
        # Create test products
        product_factory(name="상품 1", price=Decimal("15000"))
        product_factory(name="상품 2", price=Decimal("25000"))
        product_factory(name="상품 3", price=Decimal("35000"))
        
        response = enhanced_test_client.get(
            "/api/v1/products/",
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "size" in result
        assert len(result["items"]) >= 3
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_get_product_by_id(self, enhanced_test_client, test_user_token, product_factory):
        """Test getting specific product by ID"""
        product = product_factory(name="특정 상품", sku="SPECIFIC-001")
        
        response = enhanced_test_client.get(
            f"/api/v1/products/{product.id}",
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["id"] == str(product.id)
        assert result["name"] == "특정 상품"
        assert result["sku"] == "SPECIFIC-001"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_update_product(self, enhanced_test_client, test_user_token, product_factory):
        """Test updating product"""
        product = product_factory(name="원본 상품", price=Decimal("20000"))
        
        update_data = {
            "name": "수정된 상품",
            "price": 30000,
            "description": "수정된 설명"
        }
        
        response = enhanced_test_client.put(
            f"/api/v1/products/{product.id}",
            json=update_data,
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == "수정된 상품"
        assert result["price"] == 30000
        assert result["description"] == "수정된 설명"
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_delete_product(self, enhanced_test_client, test_user_token, product_factory):
        """Test deleting product"""
        product = product_factory(name="삭제할 상품")
        
        response = enhanced_test_client.delete(
            f"/api/v1/products/{product.id}",
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 204
        
        # Verify product is deleted
        get_response = enhanced_test_client.get(
            f"/api/v1/products/{product.id}",
            headers=test_user_token["headers"]
        )
        assert get_response.status_code == 404
    
    @pytest.mark.integration
    def test_search_products(self, enhanced_test_client, test_user_token, product_factory):
        """Test product search functionality"""
        # Create products with different characteristics
        product_factory(name="주방용품 칼", category="주방용품", tags=["칼", "주방"])
        product_factory(name="보석 목걸이", category="보석", tags=["목걸이", "액세서리"])
        product_factory(name="주방용품 팬", category="주방용품", tags=["팬", "주방"])
        
        # Search by category
        response = enhanced_test_client.get(
            "/api/v1/products/search?category=주방용품",
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        assert len([item for item in result["items"] if item["category"] == "주방용품"]) >= 2
        
        # Search by keyword
        response = enhanced_test_client.get(
            "/api/v1/products/search?q=칼",
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        assert any("칼" in item["name"] for item in result["items"])


class TestWholesalerEndpoints:
    """Test wholesaler-related API endpoints"""
    
    @pytest.mark.integration
    @patch('app.services.wholesalers.wholesaler_manager.WholesalerManager')
    def test_collect_products_from_wholesaler(self, mock_manager, enhanced_test_client, test_user_token):
        """Test collecting products from specific wholesaler"""
        # Setup mock
        mock_instance = mock_manager.return_value
        mock_instance.collect_products_from_supplier = AsyncMock(return_value=[
            {
                "id": "oc_001",
                "name": "테스트 보석",
                "price": 25000,
                "cost": 12500,
                "stock": 50,
                "category": "보석",
                "supplier": "ownerclan"
            }
        ])
        
        response = enhanced_test_client.post(
            "/api/v1/sourcing/collect-from-wholesaler",
            json={
                "supplier": "ownerclan",
                "category": "보석",
                "limit": 10
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "products" in result
        assert len(result["products"]) == 1
        assert result["products"][0]["supplier"] == "ownerclan"
    
    @pytest.mark.integration
    @patch('app.services.wholesalers.wholesaler_manager.WholesalerManager')
    def test_collect_products_from_all_wholesalers(self, mock_manager, enhanced_test_client, test_user_token):
        """Test collecting products from all wholesalers"""
        # Setup mock
        mock_instance = mock_manager.return_value
        mock_instance.collect_all_products = AsyncMock(return_value={
            "ownerclan": [{"id": "oc_001", "supplier": "ownerclan"}],
            "zentrade": [{"id": "zt_001", "supplier": "zentrade"}],
            "domeggook": [{"id": "dg_001", "supplier": "domeggook"}]
        })
        
        response = enhanced_test_client.post(
            "/api/v1/sourcing/collect-all-products",
            json={
                "category": "전체",
                "limit_per_supplier": 10
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "results" in result
        assert "ownerclan" in result["results"]
        assert "zentrade" in result["results"]
        assert "domeggook" in result["results"]
        assert result["summary"]["total_products"] == 3


class TestMarketplaceEndpoints:
    """Test marketplace-related API endpoints"""
    
    @pytest.mark.integration
    @patch('app.services.platforms.marketplace_manager.MarketplaceManager')
    def test_register_product_to_marketplace(self, mock_manager, enhanced_test_client, test_user_token, product_factory):
        """Test registering product to marketplace"""
        product = product_factory()
        
        # Setup mock
        mock_instance = mock_manager.return_value
        mock_instance.register_product = AsyncMock(return_value={
            "success": True,
            "platform_product_id": "CP_12345",
            "status": "registered"
        })
        
        response = enhanced_test_client.post(
            f"/api/v1/platforms/{product.id}/register",
            json={
                "platform": "coupang",
                "pricing_strategy": "competitive",
                "margin_rate": 0.3
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] is True
        assert "platform_product_id" in result
    
    @pytest.mark.integration
    @patch('app.services.platforms.marketplace_manager.MarketplaceManager')
    def test_register_product_to_all_platforms(self, mock_manager, enhanced_test_client, test_user_token, product_factory):
        """Test registering product to all platforms"""
        product = product_factory()
        
        # Setup mock
        mock_instance = mock_manager.return_value
        mock_instance.register_to_all_platforms = AsyncMock(return_value={
            "coupang": {"success": True, "product_id": "CP_12345"},
            "naver": {"success": True, "product_id": "NV_67890"},
            "eleventy": {"success": True, "product_id": "11_54321"}
        })
        
        response = enhanced_test_client.post(
            f"/api/v1/platforms/{product.id}/register-all",
            json={
                "margin_rate": 0.35,
                "pricing_strategy": "premium"
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "coupang" in result
        assert "naver" in result
        assert "eleventy" in result
        assert all(platform["success"] for platform in result.values())
    
    @pytest.mark.integration
    @patch('app.services.platforms.marketplace_manager.MarketplaceManager')
    def test_sync_stock_across_platforms(self, mock_manager, enhanced_test_client, test_user_token, product_factory):
        """Test stock synchronization across platforms"""
        product = product_factory(stock_quantity=75)
        
        # Setup mock
        mock_instance = mock_manager.return_value
        mock_instance.sync_stock = AsyncMock(return_value={
            "coupang": {"success": True, "updated_stock": 75},
            "naver": {"success": True, "updated_stock": 75},
            "eleventy": {"success": True, "updated_stock": 75}
        })
        
        response = enhanced_test_client.post(
            f"/api/v1/platforms/{product.id}/sync-stock",
            json={
                "stock_quantity": 75,
                "platforms": ["coupang", "naver", "eleventy"]
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert all(platform["success"] for platform in result.values())
        assert all(platform["updated_stock"] == 75 for platform in result.values())


class TestOrderEndpoints:
    """Test order-related API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_create_order(self, enhanced_test_client, test_user_token, product_factory):
        """Test creating new order"""
        product = product_factory(price=Decimal("25000"))
        
        order_data = {
            "platform": "coupang",
            "platform_order_id": "CP_ORD_123456",
            "customer_name": "홍길동",
            "customer_email": "hong@example.com",
            "customer_phone": "010-1234-5678",
            "shipping_address": {
                "name": "홍길동",
                "phone": "010-1234-5678",
                "address": "서울시 강남구 테스트동 123-45",
                "zipcode": "12345"
            },
            "order_items": [
                {
                    "product_id": str(product.id),
                    "name": product.name,
                    "quantity": 2,
                    "price": float(product.price),
                    "total": float(product.price * 2)
                }
            ],
            "total_amount": float(product.price * 2),
            "shipping_fee": 3000,
            "payment_method": "card",
            "payment_status": "paid"
        }
        
        response = enhanced_test_client.post(
            "/api/v1/orders/",
            json=order_data,
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["platform"] == "coupang"
        assert result["customer_name"] == "홍길동"
        assert result["total_amount"] == float(product.price * 2)
        assert "order_number" in result
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_get_orders_list(self, enhanced_test_client, test_user_token, order_factory):
        """Test getting orders list"""
        # Create test orders
        order_factory(platform="coupang", status="pending")
        order_factory(platform="naver", status="completed")
        order_factory(platform="eleventy", status="shipping")
        
        response = enhanced_test_client.get(
            "/api/v1/orders/",
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) >= 3
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_update_order_status(self, enhanced_test_client, test_user_token, order_factory):
        """Test updating order status"""
        order = order_factory(status="pending")
        
        response = enhanced_test_client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"status": "processing"},
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["status"] == "processing"
    
    @pytest.mark.integration
    @patch('app.services.platforms.marketplace_manager.MarketplaceManager')
    def test_sync_orders_from_platforms(self, mock_manager, enhanced_test_client, test_user_token):
        """Test syncing orders from all platforms"""
        # Setup mock
        mock_instance = mock_manager.return_value
        mock_instance.collect_all_orders = AsyncMock(return_value={
            "coupang": [
                {
                    "order_id": "CP_ORD_001",
                    "product_name": "테스트 상품",
                    "quantity": 1,
                    "total_price": 25000,
                    "status": "paid"
                }
            ],
            "naver": [],
            "eleventy": []
        })
        
        response = enhanced_test_client.post(
            "/api/v1/orders/sync-from-platforms",
            json={
                "platforms": ["coupang", "naver", "eleventy"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "synced_orders" in result
        assert result["synced_orders"]["coupang"] == 1
        assert result["synced_orders"]["total"] == 1


class TestAIEndpoints:
    """Test AI-related API endpoints"""
    
    @pytest.mark.integration
    @patch('app.services.ai.ai_service_manager.AIServiceManager')
    def test_generate_product_description(self, mock_ai_manager, enhanced_test_client, test_user_token, product_factory):
        """Test AI product description generation"""
        product = product_factory()
        
        # Setup mock
        mock_instance = mock_ai_manager.return_value
        mock_instance.generate_description = AsyncMock(return_value={
            "description": "AI가 생성한 매력적인 상품 설명입니다.",
            "keywords": ["고품질", "프리미엄", "추천"],
            "confidence": 0.92
        })
        
        response = enhanced_test_client.post(
            f"/api/v1/ai/generate-description/{product.id}",
            json={
                "style": "marketing",
                "length": "detailed"
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "description" in result
        assert "keywords" in result
        assert "confidence" in result
        assert result["confidence"] > 0.8
    
    @pytest.mark.integration
    @patch('app.services.ai.ai_service_manager.AIServiceManager')
    def test_analyze_market_trends(self, mock_ai_manager, enhanced_test_client, test_user_token):
        """Test AI market trend analysis"""
        # Setup mock
        mock_instance = mock_ai_manager.return_value
        mock_instance.analyze_market = AsyncMock(return_value={
            "category": "주방용품",
            "trend": "상승",
            "demand_score": 85,
            "competition_level": "중간",
            "recommendations": ["키워드 최적화", "가격 조정"]
        })
        
        response = enhanced_test_client.post(
            "/api/v1/ai/analyze-market",
            json={
                "category": "주방용품",
                "period": "30d"
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["category"] == "주방용품"
        assert result["trend"] in ["상승", "안정", "하락"]
        assert 0 <= result["demand_score"] <= 100
    
    @pytest.mark.integration
    @patch('app.services.ai.ai_service_manager.AIServiceManager')
    def test_optimize_pricing(self, mock_ai_manager, enhanced_test_client, test_user_token, product_factory):
        """Test AI pricing optimization"""
        product = product_factory(price=Decimal("25000"), cost=Decimal("12500"))
        
        # Setup mock
        mock_instance = mock_ai_manager.return_value
        mock_instance.optimize_price = AsyncMock(return_value={
            "current_price": 25000,
            "suggested_price": 28000,
            "margin_rate": 0.55,
            "confidence": 0.88,
            "reasoning": ["시장 평균가 대비 적정", "목표 마진율 달성"]
        })
        
        response = enhanced_test_client.post(
            f"/api/v1/ai/optimize-price/{product.id}",
            json={
                "target_margin": 0.5,
                "market_position": "competitive"
            },
            headers=test_user_token["headers"]
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "suggested_price" in result
        assert "margin_rate" in result
        assert "confidence" in result
        assert result["suggested_price"] != 25000  # Should suggest different price


class TestAuthEndpoints:
    """Test authentication-related API endpoints"""
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_user_registration(self, enhanced_test_client):
        """Test user registration"""
        user_data = {
            "username": "newuser123",
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "새로운 사용자",
            "business_info": {
                "company_name": "테스트 회사",
                "business_number": "123-45-67890"
            }
        }
        
        response = enhanced_test_client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["username"] == user_data["username"]
        assert result["email"] == user_data["email"]
        assert "password" not in result  # Password should not be returned
        assert "id" in result
    
    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_user_login(self, enhanced_test_client, user_factory):
        """Test user login"""
        # Create user
        user = user_factory(username="testlogin", password="loginpassword123")
        
        login_data = {
            "username": "testlogin",
            "password": "loginpassword123"
        }
        
        response = enhanced_test_client.post(
            "/api/v1/auth/login",
            data=login_data  # Form data for OAuth2
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert "access_token" in result
        assert "token_type" in result
        assert result["token_type"] == "bearer"
    
    @pytest.mark.integration
    def test_protected_endpoint_without_auth(self, enhanced_test_client):
        """Test accessing protected endpoint without authentication"""
        response = enhanced_test_client.get("/api/v1/products/")
        
        assert response.status_code == 401
        result = response.json()
        assert "detail" in result
    
    @pytest.mark.integration
    def test_protected_endpoint_with_invalid_token(self, enhanced_test_client):
        """Test accessing protected endpoint with invalid token"""
        response = enhanced_test_client.get(
            "/api/v1/products/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401


class TestHealthAndMonitoring:
    """Test health check and monitoring endpoints"""
    
    @pytest.mark.integration
    def test_health_check(self, enhanced_test_client):
        """Test basic health check"""
        response = enhanced_test_client.get("/health")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "version" in result
    
    @pytest.mark.integration
    def test_detailed_health_check(self, enhanced_test_client):
        """Test detailed health check"""
        response = enhanced_test_client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        result = response.json()
        
        assert "database" in result
        assert "redis" in result
        assert "external_apis" in result
        assert result["overall_status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.integration
    def test_metrics_endpoint(self, enhanced_test_client):
        """Test metrics endpoint"""
        response = enhanced_test_client.get("/api/v1/monitoring/metrics")
        
        assert response.status_code == 200
        result = response.json()
        
        assert "system" in result
        assert "application" in result
        assert "business" in result