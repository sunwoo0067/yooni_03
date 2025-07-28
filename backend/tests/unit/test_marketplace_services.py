"""
Unit tests for marketplace services
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from decimal import Decimal
from datetime import datetime, timedelta
import json

from tests.mocks.marketplace_mocks import (
    MockCoupangAPI, MockNaverAPI, MockEleventyAPI, MockMarketplaceManager
)


class TestCoupangAPI:
    """Test Coupang Partners API integration"""
    
    @pytest.fixture
    def coupang_api(self):
        return MockCoupangAPI()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_success(self, coupang_api):
        """Test successful authentication"""
        result = await coupang_api.authenticate()
        
        assert result["success"] is True
        assert result["vendor_id"] == "test_vendor"
        assert "access_token" in result
        assert result["expires_in"] == 7200
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_product_success(self, coupang_api):
        """Test successful product creation"""
        product_data = {
            "name": "테스트 상품",
            "price": 25000,
            "category": "테스트 카테고리",
            "brand": "테스트 브랜드"
        }
        
        result = await coupang_api.create_product(product_data)
        
        assert result["success"] is True
        assert result["code"] == "SUCCESS"
        assert "vendor_item_id" in result["data"]
        assert "product_id" in result["data"]
        assert result["data"]["status"] == "registered"
        assert result["data"]["approval_status"] == "pending"
        assert result["data"]["item_details"]["name"] == product_data["name"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_product_success(self, coupang_api):
        """Test successful product update"""
        vendor_item_id = "VI_TEST123"
        update_data = {
            "price": 30000,
            "stock": 50
        }
        
        result = await coupang_api.update_product(vendor_item_id, update_data)
        
        assert result["success"] is True
        assert result["code"] == "SUCCESS"
        assert result["data"]["vendor_item_id"] == vendor_item_id
        assert result["data"]["updated_fields"] == ["price", "stock"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_orders_success(self, coupang_api):
        """Test order retrieval"""
        orders = await coupang_api.get_orders()
        
        assert len(orders) == 2
        
        for order in orders:
            assert "order_id" in order
            assert "vendor_item_id" in order
            assert "product_name" in order
            assert "quantity" in order
            assert "total_price" in order
            assert "status" in order
            assert "delivery_info" in order
            assert "customer_info" in order
            assert "payment_info" in order
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_orders_with_date_range(self, coupang_api):
        """Test order retrieval with date range"""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        orders = await coupang_api.get_orders(start_date, end_date)
        
        assert isinstance(orders, list)
        # Mock returns same data regardless of date range
        assert len(orders) == 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_stock_success(self, coupang_api):
        """Test stock update"""
        vendor_item_id = "VI_TEST123"
        stock_quantity = 75
        
        result = await coupang_api.update_stock(vendor_item_id, stock_quantity)
        
        assert result["success"] is True
        assert result["code"] == "SUCCESS"
        assert result["data"]["vendor_item_id"] == vendor_item_id
        assert result["data"]["updated_stock"] == stock_quantity
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_product_performance(self, coupang_api):
        """Test product performance data retrieval"""
        vendor_item_id = "VI_TEST123"
        
        performance = await coupang_api.get_product_performance(vendor_item_id)
        
        assert performance["vendor_item_id"] == vendor_item_id
        assert "views" in performance
        assert "clicks" in performance
        assert "orders" in performance
        assert "revenue" in performance
        assert "conversion_rate" in performance
        assert "average_rating" in performance
        assert "review_count" in performance
        assert performance["period"] == "last_30_days"


class TestNaverAPI:
    """Test Naver Smart Store API integration"""
    
    @pytest.fixture
    def naver_api(self):
        return MockNaverAPI()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_access_token_success(self, naver_api):
        """Test OAuth token retrieval"""
        result = await naver_api.get_access_token()
        
        assert "access_token" in result
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert "commerce.product" in result["scope"]
        assert "commerce.order" in result["scope"]
        assert naver_api.access_token is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_product_success(self, naver_api):
        """Test product creation"""
        product_data = {
            "name": "네이버 테스트 상품",
            "price": 35000,
            "category": "생활용품"
        }
        
        result = await naver_api.create_product(product_data)
        
        assert result["success"] is True
        assert result["code"] == "SUCCESS"
        assert "product_id" in result["data"]
        assert "channel_product_no" in result["data"]
        assert result["data"]["status"] == "registered"
        assert result["data"]["approval_status"] == "reviewing"
        assert result["data"]["product_info"]["name"] == product_data["name"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_orders_success(self, naver_api):
        """Test order retrieval"""
        orders = await naver_api.get_orders()
        
        assert len(orders) == 1
        
        order = orders[0]
        assert "order_id" in order
        assert "product_order_id" in order
        assert "channel_product_no" in order
        assert "product_name" in order
        assert "delivery_info" in order
        assert "customer_info" in order
        assert "payment_info" in order
        assert order["payment_info"]["payment_commission"] == 840  # 3% of 28000
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_stock_success(self, naver_api):
        """Test stock update"""
        channel_product_no = "CH_TEST123"
        stock_quantity = 60
        
        result = await naver_api.update_stock(channel_product_no, stock_quantity)
        
        assert result["success"] is True
        assert result["code"] == "SUCCESS"
        assert result["data"]["channel_product_no"] == channel_product_no
        assert result["data"]["updated_stock"] == stock_quantity
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_channel_info(self, naver_api):
        """Test channel information retrieval"""
        channel_info = await naver_api.get_channel_info()
        
        assert channel_info["channel_id"] == "test_smart_store"
        assert channel_info["channel_name"] == "테스트 스마트스토어"
        assert channel_info["status"] == "active"
        assert channel_info["commission_rate"] == 0.03
        assert channel_info["settlement_cycle"] == "weekly"


class TestEleventyAPI:
    """Test 11st Open Market API integration"""
    
    @pytest.fixture
    def eleventy_api(self):
        return MockEleventyAPI()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_success(self, eleventy_api):
        """Test authentication"""
        result = await eleventy_api.authenticate()
        
        assert result["success"] is True
        assert result["api_key"] == "test_11st_api_key"
        assert result["vendor_code"] == "TEST_VENDOR_11ST"
        assert result["access_granted"] is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_product_success(self, eleventy_api):
        """Test product creation"""
        product_data = {
            "name": "11번가 테스트 상품",
            "price": 22000,
            "category_code": "ELECTRONICS",
            "brand": "테스트브랜드"
        }
        
        result = await eleventy_api.create_product(product_data)
        
        assert result["success"] is True
        assert result["resultCode"] == "SUCCESS"
        assert "product_id" in result["data"]
        assert "vendor_item_id" in result["data"]
        assert result["data"]["display_status"] == "registered"
        assert result["data"]["approval_status"] == "waiting"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_orders_success(self, eleventy_api):
        """Test order retrieval"""
        orders = await eleventy_api.get_orders()
        
        assert len(orders) == 1
        
        order = orders[0]
        assert "order_id" in order
        assert "order_detail_id" in order
        assert "vendor_item_id" in order
        assert "status" in order
        assert order["status"] == "payment_complete"
        assert "delivery_info" in order
        assert "customer_info" in order
        assert "payment_info" in order
        assert order["payment_info"]["commission_rate"] == 0.035
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_inventory_success(self, eleventy_api):
        """Test inventory update"""
        vendor_item_id = "VI_TEST123"
        inventory_data = {
            "stock_quantity": 40,
            "price": 23000
        }
        
        result = await eleventy_api.update_inventory(vendor_item_id, inventory_data)
        
        assert result["success"] is True
        assert result["resultCode"] == "SUCCESS"
        assert result["data"]["vendor_item_id"] == vendor_item_id
        assert result["data"]["updated_fields"] == inventory_data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_settlement_info(self, eleventy_api):
        """Test settlement information"""
        settlement = await eleventy_api.get_settlement_info("monthly")
        
        assert settlement["period"] == "monthly"
        assert "total_sales" in settlement
        assert "commission" in settlement
        assert "net_amount" in settlement
        assert "settlement_date" in settlement
        assert "orders_count" in settlement
        assert settlement["total_sales"] > settlement["net_amount"]  # Commission deducted


class TestMarketplaceManager:
    """Test marketplace manager coordination"""
    
    @pytest.fixture
    def marketplace_manager(self):
        return MockMarketplaceManager()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_register_product_to_all_platforms(self, marketplace_manager):
        """Test product registration across all platforms"""
        product_data = {
            "name": "통합 테스트 상품",
            "price": 30000,
            "category": "테스트",
            "brand": "테스트브랜드"
        }
        
        results = await marketplace_manager.register_product_to_all_platforms(product_data)
        
        assert "coupang" in results
        assert "naver" in results
        assert "eleventy" in results
        
        # All should succeed in mock environment
        assert results["coupang"]["success"] is True
        assert results["naver"]["success"] is True
        assert results["eleventy"]["success"] is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_stock_across_platforms(self, marketplace_manager):
        """Test stock synchronization across platforms"""
        product_mapping = {
            "coupang": {"vendor_item_id": "VI_COUP123"},
            "naver": {"channel_product_no": "CH_NAVER123"},
            "eleventy": {"vendor_item_id": "VI_11ST123"}
        }
        stock_quantity = 85
        
        results = await marketplace_manager.sync_stock_across_platforms(product_mapping, stock_quantity)
        
        assert "coupang" in results
        assert "naver" in results
        assert "eleventy" in results
        
        # Verify stock updates
        assert results["coupang"]["data"]["updated_stock"] == stock_quantity
        assert results["naver"]["data"]["updated_stock"] == stock_quantity
        assert results["eleventy"]["data"]["updated_fields"]["stock_quantity"] == stock_quantity
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_all_orders(self, marketplace_manager):
        """Test order collection from all platforms"""
        results = await marketplace_manager.collect_all_orders()
        
        assert "coupang" in results
        assert "naver" in results
        assert "eleventy" in results
        
        assert len(results["coupang"]) == 2
        assert len(results["naver"]) == 1
        assert len(results["eleventy"]) == 1
        
        # Verify order structure
        for platform, orders in results.items():
            for order in orders:
                assert "order_id" in order
                assert "product_name" in order
                assert "quantity" in order
                assert "total_price" in order
                assert "status" in order
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_platform_performance_coupang(self, marketplace_manager):
        """Test performance data from Coupang"""
        performance = await marketplace_manager.get_platform_performance("coupang", "VI_TEST123")
        
        assert "vendor_item_id" in performance
        assert "views" in performance
        assert "conversion_rate" in performance
        assert "revenue" in performance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_platform_performance_naver(self, marketplace_manager):
        """Test performance data from Naver"""
        performance = await marketplace_manager.get_platform_performance("naver", "CH_TEST123")
        
        assert "channel_id" in performance
        assert "commission_rate" in performance
        assert "settlement_cycle" in performance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_platform_performance_eleventy(self, marketplace_manager):
        """Test performance data from 11st"""
        performance = await marketplace_manager.get_platform_performance("eleventy", "VI_TEST123")
        
        assert "total_sales" in performance
        assert "commission" in performance
        assert "net_amount" in performance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_platform_performance_invalid_platform(self, marketplace_manager):
        """Test error handling for invalid platform"""
        with pytest.raises(ValueError, match="Unsupported platform"):
            await marketplace_manager.get_platform_performance("invalid", "any_id")


class TestMarketplaceIntegration:
    """Integration tests for marketplace services"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_product_registration_workflow(self):
        """Test complete product registration workflow"""
        manager = MockMarketplaceManager()
        
        # Step 1: Prepare product data
        product_data = {
            "name": "드롭쉬핑 테스트 상품",
            "description": "고품질 테스트 상품입니다",
            "price": 45000,
            "cost": 22500,
            "category": "생활용품",
            "brand": "프리미엄브랜드",
            "images": ["https://example.com/image1.jpg"],
            "weight": "500g",
            "dimensions": {"length": 20, "width": 15, "height": 10}
        }
        
        # Step 2: Register to all platforms
        registration_results = await manager.register_product_to_all_platforms(product_data)
        
        # Verify all registrations succeeded
        for platform, result in registration_results.items():
            assert result["success"] is True
        
        # Step 3: Extract platform-specific IDs
        product_mapping = {
            "coupang": {"vendor_item_id": registration_results["coupang"]["data"]["vendor_item_id"]},
            "naver": {"channel_product_no": registration_results["naver"]["data"]["channel_product_no"]},
            "eleventy": {"vendor_item_id": registration_results["eleventy"]["data"]["vendor_item_id"]}
        }
        
        # Step 4: Set initial stock
        initial_stock = 100
        stock_results = await manager.sync_stock_across_platforms(product_mapping, initial_stock)
        
        # Verify stock synchronization
        for platform, result in stock_results.items():
            assert result["success"] is True
        
        # Step 5: Monitor orders
        order_results = await manager.collect_all_orders()
        
        # Verify order collection
        total_orders = sum(len(orders) for orders in order_results.values())
        assert total_orders > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('tests.mocks.marketplace_mocks.MockCoupangAPI.create_product')
    async def test_partial_registration_failure(self, mock_coupang_create):
        """Test handling of partial platform registration failure"""
        # Make Coupang fail
        mock_coupang_create.side_effect = Exception("Coupang API Error")
        
        manager = MockMarketplaceManager()
        product_data = {"name": "Test Product", "price": 25000}
        
        results = await manager.register_product_to_all_platforms(product_data)
        
        # Coupang should fail, others should succeed
        assert results["coupang"]["success"] is False
        assert "error" in results["coupang"]
        assert results["naver"]["success"] is True
        assert results["eleventy"]["success"] is True
    
    # @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_bulk_order_collection_performance(self):
        """Test performance of bulk order collection"""
        manager = MockMarketplaceManager()
        
        start_time = datetime.now()
        
        # Collect orders multiple times (simulate bulk operation)
        tasks = []
        for _ in range(10):
            tasks.append(manager.collect_all_orders())
        
        # Execute all tasks concurrently
        import asyncio
        results_list = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time
        assert execution_time < 5.0  # 5 seconds for 10 concurrent operations
        assert len(results_list) == 10
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_order_processing_integration(self):
        """Test integration between order collection and processing"""
        manager = MockMarketplaceManager()
        
        # Collect orders from all platforms
        all_orders = await manager.collect_all_orders()
        
        # Process orders for fulfillment
        processed_orders = []
        for platform, orders in all_orders.items():
            for order in orders:
                processed_order = {
                    "platform": platform,
                    "platform_order_id": order["order_id"],
                    "product_name": order["product_name"],
                    "quantity": order["quantity"],
                    "total_amount": Decimal(str(order["total_price"])),
                    "customer_name": order["customer_info"]["name"],
                    "customer_phone": order["customer_info"]["phone"],
                    "shipping_address": order["customer_info"]["address"],
                    "status": "pending_fulfillment",
                    "created_at": datetime.utcnow()
                }
                processed_orders.append(processed_order)
        
        # Verify processed orders
        assert len(processed_orders) == 4  # 2 + 1 + 1
        
        for order in processed_orders:
            assert "platform" in order
            assert "platform_order_id" in order
            assert isinstance(order["total_amount"], Decimal)
            assert order["status"] == "pending_fulfillment"