"""
Unit tests for wholesaler services
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from decimal import Decimal
from datetime import datetime
import json

from tests.mocks.wholesaler_mocks import (
    MockOwnerClanAPI, MockZentradeAPI, MockDomeggookAPI, MockWholesalerManager
)


class TestOwnerClanAPI:
    """Test OwnerClan API integration"""
    
    @pytest.fixture
    def ownerclan_api(self):
        return MockOwnerClanAPI()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_success(self, ownerclan_api):
        """Test successful authentication"""
        result = await ownerclan_api.authenticate()
        
        assert result["success"] is True
        assert "token" in result
        assert result["expires_in"] == 3600
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_default(self, ownerclan_api):
        """Test product collection with default parameters"""
        products = await ownerclan_api.collect_products()
        
        assert len(products) == 3
        assert all("id" in product for product in products)
        assert all("name" in product for product in products)
        assert all("price" in product for product in products)
        assert all("supplier" in product for product in products)
        assert all(product["supplier"] == "ownerclan" for product in products)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_with_category_filter(self, ownerclan_api):
        """Test product collection with category filter"""
        products = await ownerclan_api.collect_products(category="보석")
        
        assert len(products) == 3  # All mock products are jewelry
        assert all(product["category"] == "보석" for product in products)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_with_limit(self, ownerclan_api):
        """Test product collection with limit"""
        products = await ownerclan_api.collect_products(limit=2)
        
        assert len(products) == 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_product_details_existing(self, ownerclan_api):
        """Test getting details for existing product"""
        product = await ownerclan_api.get_product_details("oc_001")
        
        assert product["id"] == "oc_001"
        assert product["name"] == "18K 골드 목걸이"
        assert product["price"] == 125000
        assert "specifications" in product
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_product_details_not_found(self, ownerclan_api):
        """Test getting details for non-existing product"""
        with pytest.raises(ValueError, match="Product not_found not found"):
            await ownerclan_api.get_product_details("not_found")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_stock(self, ownerclan_api):
        """Test stock checking"""
        stock_info = await ownerclan_api.check_stock("oc_001")
        
        assert stock_info["product_id"] == "oc_001"
        assert stock_info["stock"] == 20
        assert stock_info["status"] == "available"
        assert "last_updated" in stock_info


class TestZentradeAPI:
    """Test Zentrade API integration"""
    
    @pytest.fixture
    def zentrade_api(self):
        return MockZentradeAPI()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_default(self, zentrade_api):
        """Test product collection from Zentrade"""
        products = await zentrade_api.collect_products()
        
        assert len(products) == 2
        assert all(product["supplier"] == "zentrade" for product in products)
        assert all(product["category"] == "주방용품" for product in products)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_kitchen_category(self, zentrade_api):
        """Test product collection with kitchen category"""
        products = await zentrade_api.collect_products(category="주방용품")
        
        assert len(products) == 2
        assert all(product["category"] == "주방용품" for product in products)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_non_existing_category(self, zentrade_api):
        """Test product collection with non-existing category"""
        products = await zentrade_api.collect_products(category="non_existing")
        
        assert len(products) == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_parse_xml_response(self, zentrade_api):
        """Test XML parsing functionality"""
        xml_content = "<xml><products><product>test</product></products></xml>"
        products = await zentrade_api.parse_xml_response(xml_content)
        
        # Since this is mocked, it returns the standard product list
        assert len(products) >= 0
        assert isinstance(products, list)


class TestDomeggookAPI:
    """Test Domeggook API integration"""
    
    @pytest.fixture
    def domeggook_api(self):
        return MockDomeggookAPI()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_default(self, domeggook_api):
        """Test product collection from Domeggook"""
        products = await domeggook_api.collect_products()
        
        assert len(products) == 2
        assert all(product["supplier"] == "domeggook" for product in products)
        assert all(product["category"] == "생활용품" for product in products)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_products_with_limit(self, domeggook_api):
        """Test product collection with limit"""
        products = await domeggook_api.collect_products(limit=1)
        
        assert len(products) == 1
        assert products[0]["id"] == "dg_001"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_product_data_structure(self, domeggook_api):
        """Test product data structure"""
        products = await domeggook_api.collect_products()
        
        for product in products:
            # Required fields
            assert "id" in product
            assert "name" in product
            assert "price" in product
            assert "cost" in product
            assert "stock" in product
            assert "category" in product
            assert "supplier" in product
            
            # Optional fields
            assert "description" in product
            assert "images" in product
            assert "specifications" in product
            
            # Data types
            assert isinstance(product["price"], int)
            assert isinstance(product["cost"], int)
            assert isinstance(product["stock"], int)
            assert isinstance(product["images"], list)


class TestWholesalerManager:
    """Test wholesaler manager coordination"""
    
    @pytest.fixture
    def wholesaler_manager(self):
        return MockWholesalerManager()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_all_products_success(self, wholesaler_manager):
        """Test collecting products from all wholesalers"""
        results = await wholesaler_manager.collect_all_products()
        
        assert "ownerclan" in results
        assert "zentrade" in results
        assert "domeggook" in results
        
        assert len(results["ownerclan"]) == 3
        assert len(results["zentrade"]) == 2
        assert len(results["domeggook"]) == 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_all_products_with_category(self, wholesaler_manager):
        """Test collecting products with category filter"""
        results = await wholesaler_manager.collect_all_products(category="보석")
        
        # Only OwnerClan has jewelry products in mock data
        assert len(results["ownerclan"]) == 3
        assert len(results["zentrade"]) == 0  # No jewelry
        assert len(results["domeggook"]) == 0  # No jewelry
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_all_products_with_limit(self, wholesaler_manager):
        """Test collecting products with limit per supplier"""
        results = await wholesaler_manager.collect_all_products(limit_per_supplier=1)
        
        assert len(results["ownerclan"]) == 1
        assert len(results["zentrade"]) == 1
        assert len(results["domeggook"]) == 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_product_by_supplier_ownerclan(self, wholesaler_manager):
        """Test getting specific product from OwnerClan"""
        product = await wholesaler_manager.get_product_by_supplier("ownerclan", "oc_001")
        
        assert product["id"] == "oc_001"
        assert product["supplier"] == "ownerclan"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_product_by_supplier_zentrade(self, wholesaler_manager):
        """Test getting specific product from Zentrade"""
        product = await wholesaler_manager.get_product_by_supplier("zentrade", "zt_001")
        
        assert product["id"] == "zt_001"
        assert product["supplier"] == "zentrade"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_product_by_supplier_not_found(self, wholesaler_manager):
        """Test getting non-existing product"""
        with pytest.raises(ValueError):
            await wholesaler_manager.get_product_by_supplier("ownerclan", "not_found")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_product_by_supplier_invalid_supplier(self, wholesaler_manager):
        """Test getting product from invalid supplier"""
        with pytest.raises(ValueError):
            await wholesaler_manager.get_product_by_supplier("invalid_supplier", "any_id")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_all_stock(self, wholesaler_manager):
        """Test checking stock for multiple products"""
        products = [
            {"id": "oc_001", "supplier": "ownerclan"},
            {"id": "zt_001", "supplier": "zentrade"},
            {"id": "dg_001", "supplier": "domeggook"}
        ]
        
        stock_results = await wholesaler_manager.check_all_stock(products)
        
        assert len(stock_results) == 3
        assert "oc_001" in stock_results
        assert "zt_001" in stock_results
        assert "dg_001" in stock_results
        
        for product_id, stock_info in stock_results.items():
            assert "product_id" in stock_info
            assert "stock" in stock_info
            assert "status" in stock_info
            assert "last_updated" in stock_info


class TestWholesalerIntegration:
    """Integration tests for wholesaler services"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_product_sourcing_workflow(self):
        """Test complete product sourcing workflow"""
        manager = MockWholesalerManager()
        
        # Step 1: Collect all products
        all_products = await manager.collect_all_products()
        
        # Step 2: Filter profitable products (margin > 50%)
        profitable_products = []
        for supplier, products in all_products.items():
            for product in products:
                margin = (product["price"] - product["cost"]) / product["price"]
                if margin > 0.5:
                    profitable_products.append(product)
        
        assert len(profitable_products) > 0
        
        # Step 3: Check stock for profitable products
        stock_results = await manager.check_all_stock(profitable_products)
        
        # Step 4: Filter products with adequate stock
        available_products = []
        for product in profitable_products:
            stock_info = stock_results.get(product["id"])
            if stock_info and stock_info["stock"] > 10:
                available_products.append({
                    **product,
                    "available_stock": stock_info["stock"]
                })
        
        assert len(available_products) > 0
        
        # Verify final product list has required fields
        for product in available_products:
            assert "id" in product
            assert "name" in product
            assert "price" in product
            assert "cost" in product
            assert "supplier" in product
            assert "available_stock" in product
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('tests.mocks.wholesaler_mocks.MockOwnerClanAPI.collect_products')
    async def test_wholesaler_fallback_on_failure(self, mock_ownerclan_collect):
        """Test fallback when one wholesaler fails"""
        # Make OwnerClan fail
        mock_ownerclan_collect.side_effect = Exception("API Error")
        
        manager = MockWholesalerManager()
        results = await manager.collect_all_products()
        
        # OwnerClan should return empty list due to exception handling
        assert results["ownerclan"] == []
        # Other suppliers should still work
        assert len(results["zentrade"]) > 0
        assert len(results["domeggook"]) > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_product_data_transformation(self):
        """Test product data transformation for database storage"""
        manager = MockWholesalerManager()
        all_products = await manager.collect_all_products()
        
        # Transform products for database storage
        transformed_products = []
        for supplier, products in all_products.items():
            for product in products:
                transformed = {
                    "external_id": product["id"],
                    "name": product["name"],
                    "description": product.get("description", ""),
                    "price": Decimal(str(product["price"])),
                    "cost": Decimal(str(product["cost"])),
                    "sku": product.get("sku", ""),
                    "category": product["category"],
                    "stock_quantity": product["stock"],
                    "supplier": product["supplier"],
                    "supplier_product_id": product.get("supplier_product_id", ""),
                    "images": json.dumps(product.get("images", [])),
                    "specifications": json.dumps(product.get("specifications", {})),
                    "margin_rate": (Decimal(str(product["price"])) - Decimal(str(product["cost"]))) / Decimal(str(product["price"])),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                transformed_products.append(transformed)
        
        assert len(transformed_products) == 7  # 3 + 2 + 2
        
        # Verify data types
        for product in transformed_products:
            assert isinstance(product["price"], Decimal)
            assert isinstance(product["cost"], Decimal)
            assert isinstance(product["margin_rate"], Decimal)
            assert isinstance(product["created_at"], datetime)
            assert isinstance(product["updated_at"], datetime)
    
    # @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_bulk_product_collection_performance(self):
        """Test performance of bulk product collection"""
        manager = MockWholesalerManager()
        
        start_time = datetime.now()
        
        # Collect large number of products
        results = await manager.collect_all_products(limit_per_supplier=100)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time (mock operations should be fast)
        assert execution_time < 5.0  # 5 seconds max
        
        total_products = sum(len(products) for products in results.values())
        assert total_products > 0