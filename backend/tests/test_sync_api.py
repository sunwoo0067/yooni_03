"""Tests for synchronization API endpoints."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_account import PlatformAccount, PlatformType
from app.models.product import Product
from app.models.user import User
from app.services.sync.sync_manager import SyncStatus


@pytest.fixture
async def mock_platform_accounts(db: AsyncSession, test_user: User):
    """Create mock platform accounts for testing."""
    accounts = [
        PlatformAccount(
            user_id=test_user.id,
            platform=PlatformType.COUPANG,
            name="Test Coupang",
            encrypted_credentials="encrypted_coupang_creds",
            is_active=True
        ),
        PlatformAccount(
            user_id=test_user.id,
            platform=PlatformType.NAVER,
            name="Test Naver",
            encrypted_credentials="encrypted_naver_creds",
            is_active=True
        )
    ]
    
    for account in accounts:
        db.add(account)
    await db.commit()
    
    return accounts


@pytest.fixture
async def mock_products(db: AsyncSession, test_user: User):
    """Create mock products for testing."""
    products = [
        Product(
            user_id=test_user.id,
            name="Test Product 1",
            description="Test description 1",
            price=10000,
            stock_quantity=100,
            is_active=True
        ),
        Product(
            user_id=test_user.id,
            name="Test Product 2",
            description="Test description 2",
            price=20000,
            stock_quantity=50,
            is_active=True
        )
    ]
    
    for product in products:
        db.add(product)
    await db.commit()
    
    return products


class TestSyncAPI:
    """Test synchronization API endpoints."""
    
    @pytest.mark.asyncio
    async def test_sync_products(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_platform_accounts,
        mock_products
    ):
        """Test product synchronization endpoint."""
        with patch('app.services.sync.sync_manager.SyncManager.sync_products') as mock_sync:
            mock_sync.return_value = {
                "synced_count": 2,
                "created_count": 1,
                "updated_count": 1,
                "failed_count": 0
            }
            
            response = await client.post(
                "/api/v1/sync/products",
                headers=auth_headers,
                json={}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["sync_type"] == "products"
    
    @pytest.mark.asyncio
    async def test_sync_orders(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_platform_accounts
    ):
        """Test order synchronization endpoint."""
        with patch('app.services.sync.sync_manager.SyncManager.sync_orders') as mock_sync:
            mock_sync.return_value = {
                "synced_count": 5,
                "new_orders": 3,
                "updated_orders": 2,
                "platform_results": {
                    "coupang_Test Coupang": {"count": 3, "status": "success"},
                    "naver_Test Naver": {"count": 2, "status": "success"}
                }
            }
            
            response = await client.post(
                "/api/v1/sync/orders",
                headers=auth_headers,
                json={
                    "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
                    "end_date": datetime.now().isoformat()
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["sync_type"] == "orders"
            assert "date_range" in data
    
    @pytest.mark.asyncio
    async def test_sync_inventory(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_platform_accounts,
        mock_products
    ):
        """Test inventory synchronization endpoint."""
        with patch('app.services.sync.sync_manager.SyncManager.sync_inventory') as mock_sync:
            mock_sync.return_value = {
                "synced_products": 2,
                "platform_results": {
                    "1": {
                        "unified_inventory": 100,
                        "sync_results": {"coupang": {"success": True}}
                    }
                },
                "low_stock_alerts": []
            }
            
            response = await client.post(
                "/api/v1/sync/inventory",
                headers=auth_headers,
                json={"auto_disable_out_of_stock": True}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["sync_type"] == "inventory"
    
    @pytest.mark.asyncio
    async def test_test_platform_connection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_platform_accounts
    ):
        """Test platform connection test endpoint."""
        with patch('app.services.sync.sync_manager.SyncManager.test_platform_connection') as mock_test:
            mock_test.return_value = {
                "platform": "coupang",
                "account_id": 1,
                "connected": True,
                "tested_at": datetime.now()
            }
            
            response = await client.post(
                f"/api/v1/sync/platforms/{PlatformType.COUPANG.value}/test",
                headers=auth_headers,
                json={
                    "platform": PlatformType.COUPANG.value,
                    "account_id": mock_platform_accounts[0].id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
    
    @pytest.mark.asyncio
    async def test_get_sync_status(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test sync status endpoint."""
        with patch('app.services.sync.sync_manager.SyncManager.get_sync_status') as mock_status:
            mock_status.return_value = {
                "active_syncs": {},
                "recent_history": [
                    {
                        "sync_id": "sync_12345",
                        "status": SyncStatus.COMPLETED,
                        "started_at": datetime.now() - timedelta(minutes=5),
                        "completed_at": datetime.now()
                    }
                ]
            }
            
            response = await client.get(
                "/api/v1/sync/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "sync_status" in data
    
    @pytest.mark.asyncio
    async def test_get_sync_logs(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test sync logs endpoint."""
        response = await client.get(
            "/api/v1/sync/logs",
            headers=auth_headers,
            params={
                "limit": 10,
                "platform": PlatformType.COUPANG.value
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "filters" in data
    
    @pytest.mark.asyncio
    async def test_schedule_sync(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test sync scheduling endpoint."""
        with patch('app.services.sync.sync_manager.SyncManager.schedule_sync') as mock_schedule:
            mock_schedule.return_value = {
                "user_id": 1,
                "interval_minutes": 30,
                "sync_types": ["orders", "inventory"],
                "created_at": datetime.now(),
                "next_run": datetime.now() + timedelta(minutes=30)
            }
            
            response = await client.post(
                "/api/v1/sync/schedule",
                headers=auth_headers,
                json={
                    "interval_minutes": 30,
                    "sync_types": ["orders", "inventory"],
                    "active_hours": {"start": 9, "end": 18}
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "schedule" in data
    
    @pytest.mark.asyncio
    async def test_handle_webhook(
        self,
        client: AsyncClient,
        db: AsyncSession
    ):
        """Test webhook handling endpoint."""
        with patch('app.services.sync.order_sync.OrderSyncService.process_webhooks') as mock_webhook:
            mock_webhook.return_value = {
                "success": True,
                "order_id": 123,
                "event_type": "order.created"
            }
            
            response = await client.post(
                "/api/v1/sync/webhook",
                json={
                    "platform": PlatformType.COUPANG.value,
                    "event_type": "order.created",
                    "data": {
                        "orderId": "5000000123",
                        "orderedAt": datetime.now().isoformat()
                    }
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_sync_all(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_platform_accounts
    ):
        """Test full synchronization endpoint."""
        with patch('app.services.sync.sync_manager.SyncManager.sync_all') as mock_sync_all:
            mock_sync_all.return_value = {
                "sync_id": "sync_full_12345",
                "started_at": datetime.now(),
                "status": SyncStatus.IN_PROGRESS
            }
            
            response = await client.post(
                "/api/v1/sync/all",
                headers=auth_headers,
                params={"sync_types": ["products", "orders"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
            assert "sync_types" in data


class TestPlatformAPIs:
    """Test individual platform API services."""
    
    @pytest.mark.asyncio
    async def test_coupang_api_product_operations(self):
        """Test Coupang API product operations."""
        from app.services.platforms.coupang_api import CoupangAPI
        
        mock_credentials = {
            "access_key": "test_access",
            "secret_key": "test_secret",
            "vendor_id": "A00000000"
        }
        
        api = CoupangAPI(mock_credentials)
        
        # Mock the HTTP client
        api.client = AsyncMock()
        api.client.request = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": {"sellerProductId": "12345"}}
        ))
        
        # Test create product
        result = await api.create_product({
            "displayCategoryCode": "12345",
            "sellerProductName": "Test Product"
        })
        
        assert result["data"]["sellerProductId"] == "12345"
    
    @pytest.mark.asyncio
    async def test_naver_api_order_operations(self):
        """Test Naver API order operations."""
        from app.services.platforms.naver_api import NaverAPI
        
        mock_credentials = {
            "client_id": "test_client",
            "client_secret": "test_secret",
            "access_token": "test_token",
            "refresh_token": "test_refresh"
        }
        
        api = NaverAPI(mock_credentials)
        
        # Mock the HTTP client
        api.client = AsyncMock()
        api.client.request = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": [{"productOrderId": "123"}]}
        ))
        
        # Test get orders
        result = await api.get_orders(
            datetime.now() - timedelta(days=1),
            datetime.now()
        )
        
        assert result["data"][0]["productOrderId"] == "123"
    
    @pytest.mark.asyncio
    async def test_eleventh_street_api_inventory_operations(self):
        """Test 11st API inventory operations."""
        from app.services.platforms.eleventh_street_api import EleventhStreetAPI
        
        mock_credentials = {
            "api_key": "test_api_key",
            "seller_id": "test_seller"
        }
        
        api = EleventhStreetAPI(mock_credentials)
        
        # Mock the HTTP client
        api.client = AsyncMock()
        api.client.request = AsyncMock(return_value=MagicMock(
            status_code=200,
            text='<StockList><Stock><prdNo>123</prdNo><prdSelQty>100</prdSelQty></Stock></StockList>'
        ))
        
        # Test update stock
        result = await api.update_stock("123", 100)
        
        assert result is not None