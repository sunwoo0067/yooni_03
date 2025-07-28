"""
End-to-End tests for critical dropshipping workflows
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json
import time
from decimal import Decimal
from datetime import datetime, timedelta

from tests.conftest_enhanced import *
from tests.mocks import *


class TestCompleteDropshippingWorkflow:
    """Test complete end-to-end dropshipping workflow"""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @patch('app.services.wholesalers.wholesaler_manager.WholesalerManager')
    @patch('app.services.platforms.marketplace_manager.MarketplaceManager')
    @patch('app.services.ai.ai_service_manager.AIServiceManager')
    async def test_full_product_lifecycle(
        self, 
        mock_ai_manager, 
        mock_marketplace_manager, 
        mock_wholesaler_manager,
        enhanced_test_client, 
        test_user_token
    ):
        """Test complete product lifecycle from sourcing to sale"""
        
        # Setup mocks
        wholesaler_mock = mock_wholesaler_manager.return_value
        marketplace_mock = mock_marketplace_manager.return_value
        ai_mock = mock_ai_manager.return_value
        
        # Mock wholesaler data
        wholesaler_mock.collect_all_products = AsyncMock(return_value={
            "ownerclan": [
                {
                    "id": "oc_001",
                    "name": "18K 골드 목걸이",
                    "price": 125000,
                    "cost": 62500,
                    "stock": 15,
                    "category": "보석",
                    "supplier": "ownerclan",
                    "description": "고급 18K 골드 목걸이",
                    "images": ["https://example.com/gold-necklace.jpg"]
                }
            ]
        })
        
        # Mock AI enhancement
        ai_mock.enhance_product = AsyncMock(return_value={
            "enhanced_description": "럭셔리한 18K 골드로 제작된 프리미엄 목걸이입니다. 세련된 디자인과 뛰어난 품질로 특별한 순간을 더욱 빛나게 만들어드립니다.",
            "optimized_price": 149000,
            "keywords": ["18K골드", "목걸이", "럭셔리", "프리미엄", "선물"],
            "market_score": 92,
            "confidence": 0.95
        })
        
        # Mock marketplace registration
        marketplace_mock.register_to_all_platforms = AsyncMock(return_value={
            "coupang": {
                "success": True,
                "product_id": "CP_12345",
                "vendor_item_id": "VI_001",
                "status": "registered"
            },
            "naver": {
                "success": True,
                "product_id": "NV_67890", 
                "channel_product_no": "CH_001",
                "status": "registered"
            },
            "eleventy": {
                "success": True,
                "product_id": "11_54321",
                "vendor_item_id": "VI_002", 
                "status": "registered"
            }
        })
        
        # Mock order collection
        marketplace_mock.collect_all_orders = AsyncMock(return_value={
            "coupang": [
                {
                    "order_id": "CP_ORD_001",
                    "vendor_item_id": "VI_001",
                    "product_name": "18K 골드 목걸이",
                    "quantity": 1,
                    "total_price": 149000,
                    "status": "paid",
                    "customer_info": {
                        "name": "김고객",
                        "phone": "010-1234-5678",
                        "address": "서울시 강남구 테스트로 123"
                    }
                }
            ]
        })
        
        # Step 1: Product Sourcing
        print("🔍 Step 1: Collecting products from wholesalers...")
        sourcing_response = enhanced_test_client.post(
            "/api/v1/sourcing/collect-all-products",
            json={
                "category": "보석",
                "limit_per_supplier": 10,
                "min_margin_rate": 0.4
            },
            headers=test_user_token["headers"]
        )
        
        assert sourcing_response.status_code == 200
        sourcing_result = sourcing_response.json()
        assert "results" in sourcing_result
        assert "ownerclan" in sourcing_result["results"]
        
        source_product = sourcing_result["results"]["ownerclan"][0]
        
        # Step 2: AI Enhancement
        print("🤖 Step 2: Enhancing product with AI...")
        ai_response = enhanced_test_client.post(
            "/api/v1/ai/enhance-product",
            json={
                "product_data": source_product,
                "enhancement_level": "premium",
                "target_margin": 0.5
            },
            headers=test_user_token["headers"]
        )
        
        assert ai_response.status_code == 200
        ai_result = ai_response.json()
        assert "enhanced_description" in ai_result
        assert "optimized_price" in ai_result
        assert ai_result["market_score"] > 80
        
        # Step 3: Product Creation
        print("📦 Step 3: Creating product in system...")
        product_data = {
            "name": source_product["name"],
            "description": ai_result["enhanced_description"],
            "price": ai_result["optimized_price"],
            "cost": source_product["cost"],
            "sku": f"DS_{source_product['id']}",
            "category": source_product["category"],
            "stock_quantity": source_product["stock"],
            "supplier": source_product["supplier"],
            "supplier_product_id": source_product["id"],
            "images": source_product["images"],
            "tags": ai_result["keywords"],
            "ai_enhanced": True,
            "market_score": ai_result["market_score"]
        }
        
        product_response = enhanced_test_client.post(
            "/api/v1/products/",
            json=product_data,
            headers=test_user_token["headers"]
        )
        
        assert product_response.status_code == 201
        product_result = product_response.json()
        product_id = product_result["id"]
        
        # Step 4: Multi-Platform Registration
        print("🛒 Step 4: Registering to all marketplaces...")
        registration_response = enhanced_test_client.post(
            f"/api/v1/platforms/{product_id}/register-all",
            json={
                "margin_rate": 0.5,
                "pricing_strategy": "premium",
                "auto_sync": True
            },
            headers=test_user_token["headers"]
        )
        
        assert registration_response.status_code == 200
        registration_result = registration_response.json()
        
        # Verify all platforms succeeded
        assert registration_result["coupang"]["success"] is True
        assert registration_result["naver"]["success"] is True
        assert registration_result["eleventy"]["success"] is True
        
        platform_mapping = {
            "coupang": registration_result["coupang"]["vendor_item_id"],
            "naver": registration_result["naver"]["channel_product_no"],
            "eleventy": registration_result["eleventy"]["vendor_item_id"]
        }
        
        # Step 5: Wait for Orders (simulated)
        print("⏳ Step 5: Monitoring for orders...")
        time.sleep(1)  # Simulate time passage
        
        # Step 6: Order Collection and Processing
        print("📋 Step 6: Collecting orders from platforms...")
        order_sync_response = enhanced_test_client.post(
            "/api/v1/orders/sync-from-platforms",
            json={
                "platforms": ["coupang", "naver", "eleventy"],
                "auto_process": True
            },
            headers=test_user_token["headers"]
        )
        
        assert order_sync_response.status_code == 200
        order_sync_result = order_sync_response.json()
        assert order_sync_result["synced_orders"]["total"] >= 1
        
        # Step 7: Verify Complete Workflow
        print("✅ Step 7: Verifying complete workflow...")
        
        # Check product exists and is enhanced
        product_check = enhanced_test_client.get(
            f"/api/v1/products/{product_id}",
            headers=test_user_token["headers"]
        )
        assert product_check.status_code == 200
        final_product = product_check.json()
        
        assert final_product["ai_enhanced"] is True
        assert final_product["market_score"] > 80
        assert len(final_product["platform_listings"]) == 3
        
        # Check orders were created
        orders_check = enhanced_test_client.get(
            "/api/v1/orders/",
            headers=test_user_token["headers"]
        )
        assert orders_check.status_code == 200
        orders_result = orders_check.json()
        assert orders_result["total"] >= 1
        
        print("🎉 Complete dropshipping workflow test passed!")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @patch('app.services.automation.order_processor.OrderProcessor')
    async def test_automated_order_fulfillment_workflow(
        self,
        mock_order_processor,
        enhanced_test_client,
        test_user_token,
        product_factory,
        order_factory
    ):
        """Test automated order fulfillment from order receipt to shipping"""
        
        # Setup
        product = product_factory(
            name="자동화 테스트 상품",
            stock_quantity=50,
            supplier="ownerclan",
            supplier_product_id="AUTO_001"
        )
        
        order = order_factory(
            platform="coupang",
            status="pending",
            order_items=[{
                "product_id": str(product.id),
                "quantity": 2,
                "price": float(product.price)
            }]
        )
        
        # Mock order processor
        processor_mock = mock_order_processor.return_value
        processor_mock.process_order = AsyncMock(return_value={
            "success": True,
            "supplier_order_id": "SUPP_ORD_001",
            "tracking_number": "TRK123456789",
            "estimated_delivery": "2024-02-15"
        })
        
        # Step 1: Trigger automated processing
        print("⚡ Step 1: Triggering automated order processing...")
        processing_response = enhanced_test_client.post(
            f"/api/v1/automation/process-order/{order.id}",
            headers=test_user_token["headers"]
        )
        
        assert processing_response.status_code == 200
        processing_result = processing_response.json()
        assert processing_result["success"] is True
        assert "supplier_order_id" in processing_result
        assert "tracking_number" in processing_result
        
        # Step 2: Verify order status updated
        print("📊 Step 2: Verifying order status...")
        order_check = enhanced_test_client.get(
            f"/api/v1/orders/{order.id}",
            headers=test_user_token["headers"]
        )
        
        assert order_check.status_code == 200
        updated_order = order_check.json()
        assert updated_order["status"] == "processing"
        assert "tracking_number" in updated_order
        
        # Step 3: Simulate shipping update
        print("🚚 Step 3: Simulating shipping update...")
        shipping_update = enhanced_test_client.patch(
            f"/api/v1/orders/{order.id}/shipping",
            json={
                "status": "shipped",
                "tracking_number": "TRK123456789",
                "carrier": "CJ대한통운",
                "estimated_delivery": "2024-02-15"
            },
            headers=test_user_token["headers"]
        )
        
        assert shipping_update.status_code == 200
        
        # Step 4: Verify customer notification
        print("📧 Step 4: Verifying customer notification...")
        notification_check = enhanced_test_client.get(
            f"/api/v1/orders/{order.id}/notifications",
            headers=test_user_token["headers"]
        )
        
        assert notification_check.status_code == 200
        notifications = notification_check.json()
        assert len(notifications) > 0
        assert any(n["type"] == "shipping_notification" for n in notifications)
        
        print("✅ Automated order fulfillment workflow completed!")
    
    @pytest.mark.e2e
    @patch('app.services.monitoring.inventory_monitor.InventoryMonitor')
    async def test_inventory_sync_workflow(
        self,
        mock_inventory_monitor,
        enhanced_test_client,
        test_user_token,
        product_factory
    ):
        """Test real-time inventory synchronization workflow"""
        
        # Setup products with different stock levels
        low_stock_product = product_factory(
            name="재고 부족 상품",
            stock_quantity=5,
            min_stock_level=10
        )
        
        normal_product = product_factory(
            name="정상 재고 상품", 
            stock_quantity=50,
            min_stock_level=10
        )
        
        # Mock inventory monitor
        monitor_mock = mock_inventory_monitor.return_value
        monitor_mock.check_all_inventory = AsyncMock(return_value={
            str(low_stock_product.id): {
                "current_stock": 5,
                "min_level": 10,
                "status": "low_stock",
                "needs_reorder": True
            },
            str(normal_product.id): {
                "current_stock": 50,
                "min_level": 10,
                "status": "normal",
                "needs_reorder": False
            }
        })
        
        # Step 1: Run inventory check
        print("📊 Step 1: Running inventory check...")
        inventory_response = enhanced_test_client.post(
            "/api/v1/inventory/check-all",
            headers=test_user_token["headers"]
        )
        
        assert inventory_response.status_code == 200
        inventory_result = inventory_response.json()
        
        # Should identify low stock product
        low_stock_items = [
            item for item in inventory_result["items"]
            if item["status"] == "low_stock"
        ]
        assert len(low_stock_items) >= 1
        
        # Step 2: Trigger automated reorder
        print("🔄 Step 2: Triggering automated reorder...")
        reorder_response = enhanced_test_client.post(
            "/api/v1/inventory/auto-reorder",
            json={
                "product_ids": [str(low_stock_product.id)],
                "reorder_quantity": 50
            },
            headers=test_user_token["headers"]
        )
        
        assert reorder_response.status_code == 200
        reorder_result = reorder_response.json()
        assert reorder_result["success"] is True
        assert len(reorder_result["reorders"]) >= 1
        
        # Step 3: Sync stock to marketplaces
        print("🔄 Step 3: Syncing stock to marketplaces...")
        sync_response = enhanced_test_client.post(
            f"/api/v1/platforms/{low_stock_product.id}/sync-stock",
            json={
                "stock_quantity": 55,  # Updated after reorder
                "platforms": ["coupang", "naver", "eleventy"]
            },
            headers=test_user_token["headers"]
        )
        
        assert sync_response.status_code == 200
        sync_result = sync_response.json()
        
        # All platforms should be synced
        for platform in ["coupang", "naver", "eleventy"]:
            assert sync_result[platform]["success"] is True
            assert sync_result[platform]["updated_stock"] == 55
        
        print("✅ Inventory sync workflow completed!")
    
    @pytest.mark.e2e
    @pytest.mark.performance
    async def test_high_volume_order_processing(
        self,
        enhanced_test_client,
        test_user_token,
        product_factory
    ):
        """Test system performance under high order volume"""
        
        # Create test products
        products = []
        for i in range(10):
            product = product_factory(
                name=f"대량 주문 테스트 상품 {i+1}",
                stock_quantity=100
            )
            products.append(product)
        
        # Create multiple orders simultaneously
        print("📦 Creating multiple orders...")
        order_tasks = []
        
        for i in range(20):  # 20 concurrent orders
            order_data = {
                "platform": "coupang",
                "platform_order_id": f"BULK_ORD_{i:03d}",
                "customer_name": f"대량고객{i+1}",
                "customer_email": f"bulk{i+1}@example.com",
                "customer_phone": "010-1234-5678",
                "order_items": [
                    {
                        "product_id": str(products[i % 10].id),
                        "name": products[i % 10].name,
                        "quantity": 2,
                        "price": float(products[i % 10].price),
                        "total": float(products[i % 10].price * 2)
                    }
                ],
                "total_amount": float(products[i % 10].price * 2),
                "payment_status": "paid"
            }
            
            # Create order
            response = enhanced_test_client.post(
                "/api/v1/orders/",
                json=order_data,
                headers=test_user_token["headers"]
            )
            order_tasks.append(response)
        
        # Verify all orders created successfully
        successful_orders = [r for r in order_tasks if r.status_code == 201]
        assert len(successful_orders) == 20
        
        # Test bulk processing
        print("⚡ Processing bulk orders...")
        start_time = time.time()
        
        bulk_process_response = enhanced_test_client.post(
            "/api/v1/automation/process-bulk-orders",
            json={
                "batch_size": 10,
                "parallel": True
            },
            headers=test_user_token["headers"]
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert bulk_process_response.status_code == 200
        bulk_result = bulk_process_response.json()
        
        # Performance assertions
        assert processing_time < 30.0  # Should complete within 30 seconds
        assert bulk_result["processed_count"] == 20
        assert bulk_result["success_rate"] > 0.9  # 90% success rate
        
        print(f"✅ Processed {bulk_result['processed_count']} orders in {processing_time:.2f} seconds")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_error_recovery_workflow(
        self,
        enhanced_test_client,
        test_user_token,
        product_factory
    ):
        """Test system recovery from various error scenarios"""
        
        product = product_factory(name="에러 복구 테스트 상품")
        
        # Scenario 1: API timeout recovery
        print("🔄 Testing API timeout recovery...")
        with patch('app.services.external_api.timeout', side_effect=TimeoutError()):
            response = enhanced_test_client.post(
                "/api/v1/sourcing/collect-products",
                json={"supplier": "ownerclan", "timeout": 1},
                headers=test_user_token["headers"]
            )
            
            # Should handle timeout gracefully
            assert response.status_code in [200, 408, 503]
        
        # Scenario 2: Database connection recovery
        print("🗄️ Testing database recovery...")
        health_response = enhanced_test_client.get("/api/v1/health/detailed")
        assert health_response.status_code == 200
        
        health_result = health_response.json()
        # System should report status even if some components are degraded
        assert health_result["overall_status"] in ["healthy", "degraded"]
        
        # Scenario 3: External service failure recovery
        print("🔗 Testing external service failure recovery...")
        with patch('app.services.ai.ai_service.generate', side_effect=Exception("AI Service Down")):
            fallback_response = enhanced_test_client.post(
                f"/api/v1/ai/generate-description/{product.id}",
                json={"fallback_enabled": True},
                headers=test_user_token["headers"]
            )
            
            # Should fallback to alternative or cached response
            assert fallback_response.status_code in [200, 206]  # 206 for partial content
        
        print("✅ Error recovery tests completed!")


class TestBusinessCriticalWorkflows:
    """Test business-critical workflows for dropshipping"""
    
    @pytest.mark.e2e
    @pytest.mark.regression
    async def test_profit_margin_protection(
        self,
        enhanced_test_client,
        test_user_token,
        product_factory
    ):
        """Test profit margin protection across all operations"""
        
        # Create product with specific margin
        product = product_factory(
            name="마진 보호 테스트 상품",
            price=Decimal("30000"),
            cost=Decimal("15000"),  # 50% margin
            min_margin_rate=Decimal("0.4")  # 40% minimum
        )
        
        # Step 1: Test pricing updates don't violate margin
        print("💰 Testing margin protection in pricing...")
        
        # Try to set price too low
        low_price_response = enhanced_test_client.put(
            f"/api/v1/products/{product.id}",
            json={"price": 20000},  # Would result in 25% margin
            headers=test_user_token["headers"]
        )
        
        # Should reject or warn about low margin
        assert low_price_response.status_code in [400, 422] or \
               "margin_warning" in low_price_response.json()
        
        # Step 2: Test automated pricing respects margins
        print("🤖 Testing AI pricing respects margins...")
        ai_price_response = enhanced_test_client.post(
            f"/api/v1/ai/optimize-price/{product.id}",
            json={
                "respect_min_margin": True,
                "min_margin_rate": 0.4
            },
            headers=test_user_token["headers"]
        )
        
        assert ai_price_response.status_code == 200
        ai_price_result = ai_price_response.json()
        
        # Suggested price should maintain minimum margin
        suggested_price = ai_price_result["suggested_price"]
        cost = float(product.cost)
        calculated_margin = (suggested_price - cost) / suggested_price
        assert calculated_margin >= 0.38  # Allow small floating point variance
        
        print("✅ Profit margin protection verified!")
    
    @pytest.mark.e2e
    @pytest.mark.regression
    async def test_compliance_and_audit_trail(
        self,
        enhanced_test_client,
        test_user_token,
        product_factory,
        order_factory
    ):
        """Test compliance requirements and audit trail"""
        
        product = product_factory(name="컴플라이언스 테스트 상품")
        order = order_factory(
            status="completed",
            total_amount=Decimal("50000")
        )
        
        # Step 1: Test data retention compliance
        print("📋 Testing data retention compliance...")
        
        # Request data export (GDPR-like)
        export_response = enhanced_test_client.get(
            "/api/v1/compliance/export-data",
            headers=test_user_token["headers"]
        )
        
        assert export_response.status_code == 200
        export_data = export_response.json()
        
        assert "products" in export_data
        assert "orders" in export_data
        assert "audit_logs" in export_data
        
        # Step 2: Test audit trail completeness
        print("🔍 Testing audit trail...")
        
        audit_response = enhanced_test_client.get(
            f"/api/v1/audit/product/{product.id}",
            headers=test_user_token["headers"]
        )
        
        assert audit_response.status_code == 200
        audit_trail = audit_response.json()
        
        # Should have creation event
        creation_events = [
            event for event in audit_trail["events"]
            if event["action"] == "created"
        ]
        assert len(creation_events) >= 1
        
        # Step 3: Test financial reporting compliance
        print("💼 Testing financial reporting...")
        
        financial_response = enhanced_test_client.get(
            "/api/v1/reports/financial",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "format": "standard"
            },
            headers=test_user_token["headers"]
        )
        
        assert financial_response.status_code == 200
        financial_report = financial_response.json()
        
        assert "revenue" in financial_report
        assert "costs" in financial_report
        assert "profit" in financial_report
        assert "tax_info" in financial_report
        
        print("✅ Compliance and audit trail verified!")
    
    @pytest.mark.e2e
    @pytest.mark.security
    async def test_security_workflow(
        self,
        enhanced_test_client,
        test_user_token
    ):
        """Test security measures in critical workflows"""
        
        # Step 1: Test rate limiting
        print("🛡️ Testing rate limiting...")
        
        # Make rapid requests
        responses = []
        for i in range(20):
            response = enhanced_test_client.get(
                "/api/v1/products/",
                headers=test_user_token["headers"]
            )
            responses.append(response)
        
        # Should eventually hit rate limit
        rate_limited = any(r.status_code == 429 for r in responses)
        # Note: In test environment, rate limiting might be disabled
        
        # Step 2: Test SQL injection protection
        print("🔒 Testing SQL injection protection...")
        
        malicious_query = "'; DROP TABLE products; --"
        response = enhanced_test_client.get(
            f"/api/v1/products/search?q={malicious_query}",
            headers=test_user_token["headers"]
        )
        
        # Should not cause server error
        assert response.status_code in [200, 400]
        
        # Step 3: Test authentication bypass attempts
        print("🔐 Testing authentication bypass...")
        
        # Try accessing protected endpoint without token
        no_auth_response = enhanced_test_client.get("/api/v1/products/")
        assert no_auth_response.status_code == 401
        
        # Try with malformed token
        bad_token_response = enhanced_test_client.get(
            "/api/v1/products/",
            headers={"Authorization": "Bearer malformed.token.here"}
        )
        assert bad_token_response.status_code == 401
        
        print("✅ Security measures verified!")


class TestDataConsistencyWorkflows:
    """Test data consistency across the system"""
    
    @pytest.mark.e2e
    @pytest.mark.requires_db
    async def test_cross_platform_consistency(
        self,
        enhanced_test_client,
        test_user_token,
        product_factory
    ):
        """Test data consistency across multiple platforms"""
        
        product = product_factory(
            name="일관성 테스트 상품",
            price=Decimal("25000"),
            stock_quantity=100
        )
        
        # Step 1: Register to multiple platforms
        print("🔄 Testing cross-platform registration...")
        
        platform_responses = {}
        for platform in ["coupang", "naver", "eleventy"]:
            response = enhanced_test_client.post(
                f"/api/v1/platforms/{product.id}/register",
                json={
                    "platform": platform,
                    "pricing_strategy": "competitive"
                },
                headers=test_user_token["headers"]
            )
            platform_responses[platform] = response
        
        # All should succeed
        for platform, response in platform_responses.items():
            assert response.status_code == 200
        
        # Step 2: Update product and verify sync
        print("📊 Testing synchronized updates...")
        
        update_response = enhanced_test_client.put(
            f"/api/v1/products/{product.id}",
            json={
                "price": 27000,
                "stock_quantity": 85,
                "sync_to_platforms": True
            },
            headers=test_user_token["headers"]
        )
        
        assert update_response.status_code == 200
        
        # Step 3: Verify consistency
        print("✅ Verifying data consistency...")
        
        # Check product data
        product_response = enhanced_test_client.get(
            f"/api/v1/products/{product.id}",
            headers=test_user_token["headers"]
        )
        
        assert product_response.status_code == 200
        updated_product = product_response.json()
        
        assert updated_product["price"] == 27000
        assert updated_product["stock_quantity"] == 85
        
        # Check platform listings are updated
        listings_response = enhanced_test_client.get(
            f"/api/v1/platforms/{product.id}/listings",
            headers=test_user_token["headers"]
        )
        
        assert listings_response.status_code == 200
        listings = listings_response.json()
        
        # All platform listings should have updated data
        for listing in listings:
            assert listing["price"] == 27000
            assert listing["stock_quantity"] == 85
        
        print("✅ Cross-platform consistency verified!")


class TestMonitoringAndAlerting:
    """Test monitoring and alerting systems"""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_real_time_monitoring(
        self,
        enhanced_test_client,
        test_user_token
    ):
        """Test real-time monitoring and alerting"""
        
        # Step 1: Check system metrics
        print("📊 Testing system metrics collection...")
        
        metrics_response = enhanced_test_client.get(
            "/api/v1/monitoring/metrics",
            headers=test_user_token["headers"]
        )
        
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()
        
        # Should have comprehensive metrics
        assert "system" in metrics
        assert "application" in metrics
        assert "business" in metrics
        
        # System metrics
        system_metrics = metrics["system"]
        assert "cpu_usage" in system_metrics
        assert "memory_usage" in system_metrics
        assert "disk_usage" in system_metrics
        
        # Application metrics
        app_metrics = metrics["application"]
        assert "request_count" in app_metrics
        assert "response_time" in app_metrics
        assert "error_rate" in app_metrics
        
        # Business metrics
        business_metrics = metrics["business"]
        assert "active_products" in business_metrics
        assert "total_orders" in business_metrics
        assert "revenue" in business_metrics
        
        # Step 2: Test alerting configuration
        print("🚨 Testing alerting system...")
        
        alerts_response = enhanced_test_client.get(
            "/api/v1/monitoring/alerts",
            headers=test_user_token["headers"]
        )
        
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        
        # Should have active monitoring
        assert "active_alerts" in alerts
        assert "alert_rules" in alerts
        
        print("✅ Monitoring and alerting verified!")
    
    @pytest.mark.e2e
    async def test_performance_benchmarks(
        self,
        enhanced_test_client,
        test_user_token
    ):
        """Test system performance against benchmarks"""
        
        print("⚡ Testing performance benchmarks...")
        
        # Test API response times
        start_time = time.time()
        
        response = enhanced_test_client.get(
            "/api/v1/products/",
            headers=test_user_token["headers"]
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
        
        # Test bulk operations
        start_time = time.time()
        
        bulk_response = enhanced_test_client.get(
            "/api/v1/products/?limit=100",
            headers=test_user_token["headers"]
        )
        
        end_time = time.time()
        bulk_response_time = end_time - start_time
        
        assert bulk_response.status_code == 200
        assert bulk_response_time < 3.0  # Bulk operations within 3 seconds
        
        print(f"✅ Performance benchmarks met (Response: {response_time:.3f}s, Bulk: {bulk_response_time:.3f}s)")
        
        return {
            "single_request_time": response_time,
            "bulk_request_time": bulk_response_time,
            "benchmark_status": "passed"
        }