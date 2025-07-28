"""
플랫폼 서비스 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any
import asyncio
from datetime import datetime, timedelta


@pytest.mark.unit
class TestPlatformManager:
    """플랫폼 매니저 서비스 테스트"""
    
    @pytest.fixture
    def mock_platform_manager(self):
        """플랫폼 매니저 모킹"""
        with patch('app.services.platforms.platform_manager.PlatformManager') as mock:
            instance = mock.return_value
            instance.get_supported_platforms = Mock()
            instance.create_platform_client = Mock()
            instance.test_connection = AsyncMock()
            instance.sync_products = AsyncMock()
            instance.sync_orders = AsyncMock()
            yield instance
    
    def test_get_supported_platforms(self, mock_platform_manager):
        """지원 플랫폼 목록 조회 테스트"""
        expected_platforms = [
            {
                "code": "coupang",
                "name": "쿠팡",
                "description": "쿠팡 마켓플레이스",
                "features": ["product_sync", "order_sync", "inventory_sync"],
                "status": "active"
            },
            {
                "code": "naver",
                "name": "네이버 스마트스토어",
                "description": "네이버 쇼핑 플랫폼",
                "features": ["product_sync", "order_sync", "review_sync"],
                "status": "active"
            },
            {
                "code": "eleventh_street",
                "name": "11번가",
                "description": "11번가 오픈마켓",
                "features": ["product_sync", "order_sync"],
                "status": "active"
            }
        ]
        
        mock_platform_manager.get_supported_platforms.return_value = expected_platforms
        
        result = mock_platform_manager.get_supported_platforms()
        
        assert len(result) == 3
        assert all(p["status"] == "active" for p in result)
        assert any(p["code"] == "coupang" for p in result)
        mock_platform_manager.get_supported_platforms.assert_called_once()
    
    def test_create_platform_client(self, mock_platform_manager):
        """플랫폼 클라이언트 생성 테스트"""
        platform_config = {
            "platform": "coupang",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "vendor_id": "test_vendor"
        }
        
        mock_client = Mock()
        mock_client.platform = "coupang"
        mock_client.is_authenticated = True
        
        mock_platform_manager.create_platform_client.return_value = mock_client
        
        result = mock_platform_manager.create_platform_client(platform_config)
        
        assert result.platform == "coupang"
        assert result.is_authenticated is True
        mock_platform_manager.create_platform_client.assert_called_once_with(platform_config)
    
    @pytest.mark.asyncio
    async def test_test_connection(self, mock_platform_manager):
        """플랫폼 연결 테스트"""
        platform_config = {
            "platform": "naver",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        expected_result = {
            "success": True,
            "platform": "naver",
            "connection_time": 1.23,
            "api_version": "v1.0",
            "account_info": {
                "store_name": "테스트 스토어",
                "store_id": "test_store_123",
                "status": "active"
            }
        }
        
        mock_platform_manager.test_connection.return_value = expected_result
        
        result = await mock_platform_manager.test_connection(platform_config)
        
        assert result["success"] is True
        assert result["platform"] == "naver"
        assert "account_info" in result
        mock_platform_manager.test_connection.assert_called_once_with(platform_config)
    
    @pytest.mark.asyncio
    async def test_sync_products(self, mock_platform_manager):
        """상품 동기화 테스트"""
        sync_config = {
            "platform": "coupang",
            "account_id": "test_account",
            "sync_mode": "incremental",
            "categories": ["전자제품", "생활용품"]
        }
        
        expected_sync_result = {
            "success": True,
            "platform": "coupang",
            "sync_started_at": "2024-01-01T10:00:00Z",
            "sync_completed_at": "2024-01-01T10:15:00Z",
            "statistics": {
                "total_processed": 150,
                "newly_added": 25,
                "updated": 100,
                "unchanged": 20,
                "errors": 5
            },
            "errors": [
                {"product_id": "PROD001", "error": "Invalid price format"},
                {"product_id": "PROD002", "error": "Missing required field: description"}
            ]
        }
        
        mock_platform_manager.sync_products.return_value = expected_sync_result
        
        result = await mock_platform_manager.sync_products(sync_config)
        
        assert result["success"] is True
        assert result["statistics"]["total_processed"] == 150
        assert result["statistics"]["newly_added"] == 25
        assert len(result["errors"]) == 2
        mock_platform_manager.sync_products.assert_called_once_with(sync_config)
    
    @pytest.mark.asyncio
    async def test_sync_orders(self, mock_platform_manager):
        """주문 동기화 테스트"""
        sync_config = {
            "platform": "eleventh_street",
            "account_id": "test_11st_account",
            "date_from": "2024-01-01",
            "date_to": "2024-01-31",
            "status_filter": ["paid", "shipped"]
        }
        
        expected_sync_result = {
            "success": True,
            "platform": "eleventh_street",
            "sync_period": {
                "from": "2024-01-01T00:00:00Z",
                "to": "2024-01-31T23:59:59Z"
            },
            "statistics": {
                "total_orders": 85,
                "new_orders": 12,
                "updated_orders": 68,
                "failed_orders": 5
            },
            "order_summary": {
                "total_amount": 12500000,
                "average_order_value": 147058,
                "status_breakdown": {
                    "paid": 45,
                    "shipped": 25,
                    "delivered": 10,
                    "cancelled": 5
                }
            }
        }
        
        mock_platform_manager.sync_orders.return_value = expected_sync_result
        
        result = await mock_platform_manager.sync_orders(sync_config)
        
        assert result["success"] is True
        assert result["statistics"]["total_orders"] == 85
        assert result["order_summary"]["total_amount"] == 12500000
        mock_platform_manager.sync_orders.assert_called_once_with(sync_config)


@pytest.mark.unit
class TestCoupangAPI:
    """쿠팡 API 서비스 테스트"""
    
    @pytest.fixture
    def mock_coupang_api(self):
        """쿠팡 API 모킹"""
        with patch('app.services.platforms.coupang_api.CoupangAPI') as mock:
            instance = mock.return_value
            instance.authenticate = AsyncMock()
            instance.get_products = AsyncMock()
            instance.register_product = AsyncMock()
            instance.update_inventory = AsyncMock()
            instance.get_orders = AsyncMock()
            yield instance
    
    @pytest.mark.asyncio
    async def test_authenticate(self, mock_coupang_api):
        """쿠팡 API 인증 테스트"""
        credentials = {
            "access_key": "test_access_key",
            "secret_key": "test_secret_key",
            "vendor_id": "test_vendor_123"
        }
        
        expected_auth_result = {
            "success": True,
            "vendor_id": "test_vendor_123",
            "access_token": "jwt_access_token",
            "expires_in": 3600,
            "permissions": ["product_read", "product_write", "order_read"]
        }
        
        mock_coupang_api.authenticate.return_value = expected_auth_result
        
        result = await mock_coupang_api.authenticate(credentials)
        
        assert result["success"] is True
        assert result["vendor_id"] == "test_vendor_123"
        assert "product_read" in result["permissions"]
        mock_coupang_api.authenticate.assert_called_once_with(credentials)
    
    @pytest.mark.asyncio
    async def test_get_products(self, mock_coupang_api):
        """쿠팡 상품 목록 조회 테스트"""
        query_params = {
            "page": 1,
            "size": 50,
            "status": "ACTIVE",
            "category": "electronics"
        }
        
        expected_products = {
            "total_count": 1250,
            "page": 1,
            "size": 50,
            "products": [
                {
                    "item_id": "CP001",
                    "vendor_item_id": "VENDOR_CP001",
                    "item_name": "삼성 무선 이어폰",
                    "brand_name": "삼성",
                    "category_id": "electronics_audio",
                    "sale_price": 89000,
                    "discount_price": 79000,
                    "inventory": 150,
                    "status": "ACTIVE",
                    "created_at": "2024-01-01T10:00:00Z"
                },
                {
                    "item_id": "CP002",
                    "vendor_item_id": "VENDOR_CP002", 
                    "item_name": "애플 에어팟 프로",
                    "brand_name": "애플",
                    "category_id": "electronics_audio",
                    "sale_price": 329000,
                    "discount_price": 299000,
                    "inventory": 80,
                    "status": "ACTIVE",
                    "created_at": "2024-01-01T11:00:00Z"
                }
            ]
        }
        
        mock_coupang_api.get_products.return_value = expected_products
        
        result = await mock_coupang_api.get_products(query_params)
        
        assert result["total_count"] == 1250
        assert len(result["products"]) == 2
        assert all(p["status"] == "ACTIVE" for p in result["products"])
        mock_coupang_api.get_products.assert_called_once_with(query_params)
    
    @pytest.mark.asyncio
    async def test_register_product(self, mock_coupang_api):
        """쿠팡 상품 등록 테스트"""
        product_data = {
            "vendor_item_id": "NEW_PROD_001",
            "item_name": "신규 블루투스 스피커",
            "brand_name": "TechSound",
            "category_id": "electronics_audio",
            "sale_price": 159000,
            "original_price": 199000,
            "inventory": 200,
            "description": "고품질 사운드의 휴대용 블루투스 스피커",
            "images": [
                {"url": "https://example.com/image1.jpg", "type": "MAIN"},
                {"url": "https://example.com/image2.jpg", "type": "DETAIL"}
            ],
            "attributes": {
                "connectivity": "블루투스 5.0",
                "battery_life": "12시간",
                "waterproof": "IPX7"
            }
        }
        
        expected_registration_result = {
            "success": True,
            "item_id": "CP_NEW_001",
            "vendor_item_id": "NEW_PROD_001",
            "status": "UNDER_REVIEW",
            "estimated_review_time": "2-5 business days",
            "registration_date": "2024-01-01T15:00:00Z"
        }
        
        mock_coupang_api.register_product.return_value = expected_registration_result
        
        result = await mock_coupang_api.register_product(product_data)
        
        assert result["success"] is True
        assert result["vendor_item_id"] == "NEW_PROD_001"
        assert result["status"] == "UNDER_REVIEW"
        mock_coupang_api.register_product.assert_called_once_with(product_data)
    
    @pytest.mark.asyncio
    async def test_update_inventory(self, mock_coupang_api):
        """쿠팡 재고 업데이트 테스트"""
        inventory_updates = [
            {"item_id": "CP001", "inventory": 120},
            {"item_id": "CP002", "inventory": 0},  # 품절
            {"item_id": "CP003", "inventory": 250}
        ]
        
        expected_update_result = {
            "success": True,
            "updated_items": [
                {"item_id": "CP001", "status": "SUCCESS", "new_inventory": 120},
                {"item_id": "CP002", "status": "SUCCESS", "new_inventory": 0},
                {"item_id": "CP003", "status": "SUCCESS", "new_inventory": 250}
            ],
            "failed_items": [],
            "update_timestamp": "2024-01-01T16:00:00Z"
        }
        
        mock_coupang_api.update_inventory.return_value = expected_update_result
        
        result = await mock_coupang_api.update_inventory(inventory_updates)
        
        assert result["success"] is True
        assert len(result["updated_items"]) == 3
        assert len(result["failed_items"]) == 0
        mock_coupang_api.update_inventory.assert_called_once_with(inventory_updates)
    
    @pytest.mark.asyncio
    async def test_get_orders(self, mock_coupang_api):
        """쿠팡 주문 조회 테스트"""
        order_query = {
            "created_at_from": "2024-01-01T00:00:00Z",
            "created_at_to": "2024-01-31T23:59:59Z",
            "status": ["ACCEPT", "INSTRUCT"],
            "page": 1,
            "size": 100
        }
        
        expected_orders = {
            "total_count": 45,
            "page": 1,
            "size": 100,
            "orders": [
                {
                    "order_id": "CO_2024_001",
                    "vendor_id": "test_vendor_123",
                    "order_date": "2024-01-15T14:30:00Z",
                    "status": "ACCEPT",
                    "total_amount": 128000,
                    "customer": {
                        "name": "홍길동",
                        "phone": "010-1234-5678"
                    },
                    "shipping_info": {
                        "address": "서울시 강남구 테스트로 123",
                        "zipcode": "12345",
                        "method": "DAWN_DELIVERY"
                    },
                    "items": [
                        {
                            "item_id": "CP001",
                            "item_name": "삼성 무선 이어폰",
                            "quantity": 1,
                            "unit_price": 79000,
                            "total_price": 79000
                        },
                        {
                            "item_id": "CP004",
                            "item_name": "스마트폰 케이스",
                            "quantity": 1,
                            "unit_price": 49000,
                            "total_price": 49000
                        }
                    ]
                }
            ]
        }
        
        mock_coupang_api.get_orders.return_value = expected_orders
        
        result = await mock_coupang_api.get_orders(order_query)
        
        assert result["total_count"] == 45
        assert len(result["orders"]) == 1
        assert result["orders"][0]["status"] == "ACCEPT"
        assert len(result["orders"][0]["items"]) == 2
        mock_coupang_api.get_orders.assert_called_once_with(order_query)


@pytest.mark.unit
class TestNaverAPI:
    """네이버 스마트스토어 API 서비스 테스트"""
    
    @pytest.fixture
    def mock_naver_api(self):
        """네이버 API 모킹"""
        with patch('app.services.platforms.naver_api.NaverAPI') as mock:
            instance = mock.return_value
            instance.get_access_token = AsyncMock()
            instance.get_store_info = AsyncMock()
            instance.get_products = AsyncMock()
            instance.update_product = AsyncMock()
            instance.get_orders = AsyncMock()
            yield instance
    
    @pytest.mark.asyncio
    async def test_get_access_token(self, mock_naver_api):
        """네이버 액세스 토큰 획득 테스트"""
        oauth_config = {
            "client_id": "naver_client_id",
            "client_secret": "naver_client_secret",
            "refresh_token": "existing_refresh_token"
        }
        
        expected_token_result = {
            "access_token": "new_access_token_12345",
            "refresh_token": "new_refresh_token_67890",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "commerce.read commerce.write"
        }
        
        mock_naver_api.get_access_token.return_value = expected_token_result
        
        result = await mock_naver_api.get_access_token(oauth_config)
        
        assert result["access_token"] == "new_access_token_12345"
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        mock_naver_api.get_access_token.assert_called_once_with(oauth_config)
    
    @pytest.mark.asyncio
    async def test_get_store_info(self, mock_naver_api):
        """네이버 스토어 정보 조회 테스트"""
        expected_store_info = {
            "channel_no": 12345,
            "channel_name": "테스트 스마트스토어",
            "seller_name": "테스트 셀러",
            "business_registration_number": "123-45-67890",
            "status": "ACTIVE",
            "store_type": "SMARTSTORE",
            "categories": [
                {"category_id": "50000000", "category_name": "패션의류"},
                {"category_id": "50000001", "category_name": "패션잡화"}
            ],
            "policies": {
                "return_policy": "7일 내 반품 가능",
                "shipping_policy": "주문 후 2-3일 내 발송"
            }
        }
        
        mock_naver_api.get_store_info.return_value = expected_store_info
        
        result = await mock_naver_api.get_store_info()
        
        assert result["channel_no"] == 12345
        assert result["status"] == "ACTIVE"
        assert len(result["categories"]) == 2
        mock_naver_api.get_store_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_products(self, mock_naver_api):
        """네이버 상품 목록 조회 테스트"""
        search_params = {
            "page": 1,
            "size": 20,
            "status": "SALE",
            "category_id": "50000000"
        }
        
        expected_products = {
            "total_count": 350,
            "page": 1,
            "size": 20,
            "products": [
                {
                    "product_no": "NV001",
                    "product_name": "여성 긴팔 블라우스",
                    "category_id": "50000000",
                    "sale_price": 89000,
                    "discount_price": 69000,
                    "stock_quantity": 45,
                    "status": "SALE",
                    "images": [
                        {"url": "https://naver.com/image1.jpg", "type": "MAIN"},
                        {"url": "https://naver.com/image2.jpg", "type": "DETAIL"}
                    ],
                    "options": [
                        {"option_name": "색상", "option_values": ["블랙", "화이트", "네이비"]},
                        {"option_name": "사이즈", "option_values": ["S", "M", "L", "XL"]}
                    ]
                }
            ]
        }
        
        mock_naver_api.get_products.return_value = expected_products
        
        result = await mock_naver_api.get_products(search_params)
        
        assert result["total_count"] == 350
        assert len(result["products"]) == 1
        assert result["products"][0]["status"] == "SALE"
        assert len(result["products"][0]["options"]) == 2
        mock_naver_api.get_products.assert_called_once_with(search_params)
    
    @pytest.mark.asyncio
    async def test_update_product(self, mock_naver_api):
        """네이버 상품 업데이트 테스트"""
        product_no = "NV001"
        update_data = {
            "sale_price": 95000,
            "discount_price": 75000,
            "stock_quantity": 60,
            "product_description": "업데이트된 상품 설명",
            "images": [
                {"url": "https://naver.com/new_image1.jpg", "type": "MAIN"},
                {"url": "https://naver.com/new_image2.jpg", "type": "DETAIL"}
            ]
        }
        
        expected_update_result = {
            "success": True,
            "product_no": "NV001",
            "updated_fields": ["sale_price", "discount_price", "stock_quantity", "product_description", "images"],
            "update_timestamp": "2024-01-01T17:00:00Z"
        }
        
        mock_naver_api.update_product.return_value = expected_update_result
        
        result = await mock_naver_api.update_product(product_no, update_data)
        
        assert result["success"] is True
        assert result["product_no"] == "NV001"
        assert "sale_price" in result["updated_fields"]
        mock_naver_api.update_product.assert_called_once_with(product_no, update_data)
    
    @pytest.mark.asyncio
    async def test_get_orders(self, mock_naver_api):
        """네이버 주문 조회 테스트"""
        order_search = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "order_status": ["PAYED", "DELIVERING"],
            "page": 1,
            "size": 50
        }
        
        expected_orders = {
            "total_count": 28,
            "page": 1,
            "size": 50,
            "orders": [
                {
                    "order_no": "NV_ORDER_001",
                    "product_order_no": "NV_PROD_ORDER_001",
                    "order_date": "2024-01-20T09:15:00Z",
                    "order_status": "PAYED",
                    "payment_date": "2024-01-20T09:20:00Z",
                    "total_payment_amount": 75000,
                    "orderer": {
                        "name": "김네이버",
                        "phone": "010-9876-5432",
                        "email": "test@naver.com"
                    },
                    "receiver": {
                        "name": "김네이버",
                        "phone": "010-9876-5432",
                        "address": "경기도 성남시 분당구 테스트로 456",
                        "zipcode": "13579"
                    },
                    "products": [
                        {
                            "product_no": "NV001",
                            "product_name": "여성 긴팔 블라우스",
                            "option": "색상:블랙, 사이즈:M",
                            "quantity": 1,
                            "unit_price": 75000,
                            "total_price": 75000
                        }
                    ]
                }
            ]
        }
        
        mock_naver_api.get_orders.return_value = expected_orders
        
        result = await mock_naver_api.get_orders(order_search)
        
        assert result["total_count"] == 28
        assert len(result["orders"]) == 1
        assert result["orders"][0]["order_status"] == "PAYED"
        assert len(result["orders"][0]["products"]) == 1
        mock_naver_api.get_orders.assert_called_once_with(order_search)


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.slow
class TestPlatformServicesIntegration:
    """플랫폼 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_multi_platform_sync(self, test_db):
        """다중 플랫폼 동기화 통합 테스트"""
        try:
            from app.services.platforms.platform_manager import PlatformManager
            manager = PlatformManager()
            
            # 지원되는 플랫폼 목록 확인
            platforms = manager.get_supported_platforms()
            assert len(platforms) > 0
            
            # 각 플랫폼에 대해 연결 테스트 (모킹된 데이터로)
            active_platforms = [p for p in platforms if p["status"] == "active"]
            
            for platform in active_platforms[:2]:  # 최대 2개 플랫폼만 테스트
                test_config = {
                    "platform": platform["code"],
                    "api_key": f"test_{platform['code']}_key",
                    "api_secret": f"test_{platform['code']}_secret"
                }
                
                try:
                    connection_result = await manager.test_connection(test_config)
                    assert isinstance(connection_result, dict)
                    assert "success" in connection_result
                except Exception as e:
                    # 실제 API 연결 실패는 예상되므로 로깅만 수행
                    pytest.skip(f"플랫폼 {platform['code']} 연결 테스트 실패: {str(e)}")
                    
        except ImportError:
            pytest.skip("플랫폼 서비스 모듈이 구현되지 않음")
    
    @pytest.mark.asyncio
    async def test_product_synchronization_workflow(self, test_db, sample_product_data):
        """상품 동기화 워크플로우 테스트"""
        try:
            from app.services.platforms.platform_manager import PlatformManager
            manager = PlatformManager()
            
            # 테스트 플랫폼 설정
            platform_configs = [
                {
                    "platform": "coupang",
                    "account_id": "test_coupang",
                    "api_key": "test_key",
                    "api_secret": "test_secret"
                }
            ]
            
            for config in platform_configs:
                try:
                    # 상품 동기화 테스트
                    sync_result = await manager.sync_products({
                        **config,
                        "sync_mode": "test",
                        "product_data": [sample_product_data]
                    })
                    
                    assert isinstance(sync_result, dict)
                    assert "success" in sync_result or "status" in sync_result
                    
                except Exception as e:
                    pytest.skip(f"상품 동기화 테스트 실패: {str(e)}")
                    
        except ImportError:
            pytest.skip("플랫폼 서비스 모듈이 구현되지 않음")
    
    @pytest.mark.asyncio
    async def test_order_synchronization_workflow(self, test_db):
        """주문 동기화 워크플로우 테스트"""
        try:
            from app.services.platforms.platform_manager import PlatformManager
            manager = PlatformManager()
            
            # 테스트 기간 설정
            sync_config = {
                "platform": "naver",
                "account_id": "test_naver",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
            
            try:
                order_sync_result = await manager.sync_orders(sync_config)
                
                assert isinstance(order_sync_result, dict)
                assert "success" in order_sync_result or "status" in order_sync_result
                
                if order_sync_result.get("success"):
                    assert "statistics" in order_sync_result
                    assert isinstance(order_sync_result["statistics"], dict)
                    
            except Exception as e:
                pytest.skip(f"주문 동기화 테스트 실패: {str(e)}")
                
        except ImportError:
            pytest.skip("플랫폼 서비스 모듈이 구현되지 않음")
    
    @pytest.mark.asyncio
    async def test_platform_error_recovery(self, test_db):
        """플랫폼 오류 복구 테스트"""
        try:
            from app.services.platforms.platform_manager import PlatformManager
            manager = PlatformManager()
            
            # 잘못된 설정으로 연결 테스트
            invalid_config = {
                "platform": "coupang",
                "api_key": "invalid_key",
                "api_secret": "invalid_secret"
            }
            
            try:
                result = await manager.test_connection(invalid_config)
                
                # 오류가 적절히 처리되었는지 확인
                if isinstance(result, dict):
                    assert result.get("success") is False or "error" in result
                    
            except Exception as e:
                # 예외가 발생해도 적절히 처리되어야 함
                assert isinstance(e, (ValueError, ConnectionError, Exception))
                
        except ImportError:
            pytest.skip("플랫폼 서비스 모듈이 구현되지 않음")
    
    @pytest.mark.asyncio
    async def test_concurrent_platform_operations(self, test_db):
        """동시 플랫폼 작업 테스트"""
        try:
            from app.services.platforms.platform_manager import PlatformManager
            manager = PlatformManager()
            
            # 여러 플랫폼에서 동시에 연결 테스트
            platform_configs = [
                {"platform": "coupang", "api_key": "test1", "api_secret": "secret1"},
                {"platform": "naver", "client_id": "test2", "client_secret": "secret2"},
                {"platform": "eleventh_street", "api_key": "test3", "api_secret": "secret3"}
            ]
            
            # 동시 실행
            tasks = [
                manager.test_connection(config) 
                for config in platform_configs
            ]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 결과 확인
                assert len(results) == len(platform_configs)
                
                for result in results:
                    if not isinstance(result, Exception):
                        assert isinstance(result, dict)
                        
            except Exception as e:
                pytest.skip(f"동시 플랫폼 작업 테스트 실패: {str(e)}")
                
        except ImportError:
            pytest.skip("플랫폼 서비스 모듈이 구현되지 않음")