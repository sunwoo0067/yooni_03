"""
Mock implementations for wholesaler APIs
"""
import asyncio
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, Mock
from decimal import Decimal
from datetime import datetime
import json


class MockOwnerClanAPI:
    """Mock OwnerClan API for testing"""
    
    def __init__(self):
        self.base_url = "https://api.ownerclan.com"
        self.token = "mock_jwt_token"
        self.session = AsyncMock()
        
    async def authenticate(self) -> Dict[str, Any]:
        """Mock authentication"""
        return {
            "success": True,
            "token": self.token,
            "expires_in": 3600
        }
    
    async def collect_products(self, category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Mock product collection"""
        mock_products = [
            {
                "id": "oc_001",
                "name": "18K 골드 목걸이",
                "description": "고급 18K 골드로 제작된 세련된 목걸이",
                "price": 125000,
                "cost": 62500,
                "stock": 15,
                "category": "보석",
                "subcategory": "목걸이",
                "brand": "OwnerClan Premium",
                "sku": "OC-GOLD-001",
                "weight": "15g",
                "material": "18K 골드",
                "images": [
                    "https://mock-images.ownerclan.com/gold-necklace-1.jpg",
                    "https://mock-images.ownerclan.com/gold-necklace-2.jpg"
                ],
                "specifications": {
                    "length": "45cm",
                    "clasp": "스프링 클래스프",
                    "chain_type": "벤치안 체인"
                },
                "supplier": "ownerclan",
                "supplier_product_id": "OC-PREMIUM-001",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": "oc_002",
                "name": "실버 925 반지",
                "description": "순은 925로 제작된 심플한 디자인의 반지",
                "price": 45000,
                "cost": 22500,
                "stock": 25,
                "category": "보석",
                "subcategory": "반지",
                "brand": "OwnerClan Silver",
                "sku": "OC-SILVER-002",
                "weight": "8g",
                "material": "실버 925",
                "images": [
                    "https://mock-images.ownerclan.com/silver-ring-1.jpg"
                ],
                "specifications": {
                    "sizes": ["13호", "14호", "15호", "16호"],
                    "width": "3mm",
                    "thickness": "1.5mm"
                },
                "supplier": "ownerclan",
                "supplier_product_id": "OC-SILVER-002",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": "oc_003",
                "name": "진주 귀걸이",
                "description": "천연 담수진주로 제작된 우아한 귀걸이",
                "price": 89000,
                "cost": 44500,
                "stock": 12,
                "category": "보석",
                "subcategory": "귀걸이",
                "brand": "OwnerClan Pearl",
                "sku": "OC-PEARL-003",
                "weight": "6g",
                "material": "천연 담수진주, 실버 925",
                "images": [
                    "https://mock-images.ownerclan.com/pearl-earring-1.jpg",
                    "https://mock-images.ownerclan.com/pearl-earring-2.jpg"
                ],
                "specifications": {
                    "pearl_size": "8-9mm",
                    "pearl_type": "담수진주",
                    "setting": "실버 925 포스트"
                },
                "supplier": "ownerclan",
                "supplier_product_id": "OC-PEARL-003",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        
        # Filter by category if specified
        if category:
            mock_products = [p for p in mock_products if p["category"].lower() == category.lower()]
        
        # Apply limit
        return mock_products[:limit]
    
    async def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """Mock get single product details"""
        products = await self.collect_products()
        for product in products:
            if product["id"] == product_id:
                return product
        
        raise ValueError(f"Product {product_id} not found")
    
    async def check_stock(self, product_id: str) -> Dict[str, Any]:
        """Mock stock check"""
        return {
            "product_id": product_id,
            "stock": 20,
            "status": "available",
            "last_updated": datetime.utcnow().isoformat()
        }


class MockZentradeAPI:
    """Mock Zentrade API for testing"""
    
    def __init__(self):
        self.base_url = "https://api.zentrade.com"
        self.session = AsyncMock()
        
    async def collect_products(self, category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Mock product collection from XML API"""
        mock_products = [
            {
                "id": "zt_001",
                "name": "스테인리스 주방칼 세트",
                "description": "프리미엄 스테인리스 스틸로 제작된 전문가용 주방칼 5종 세트",
                "price": 89000,
                "cost": 44500,
                "stock": 50,
                "category": "주방용품",
                "subcategory": "조리도구",
                "brand": "Zentrade Kitchen",
                "sku": "ZT-KNIFE-001",
                "weight": "1.2kg",
                "material": "스테인리스 스틸",
                "images": [
                    "https://mock-images.zentrade.com/knife-set-1.jpg",
                    "https://mock-images.zentrade.com/knife-set-2.jpg"
                ],
                "specifications": {
                    "set_contents": ["식칼", "과도", "빵칼", "유틸리티 나이프", "파링 나이프"],
                    "blade_material": "독일산 스테인리스 스틸",
                    "handle_material": "에르고노믹 플라스틱"
                },
                "supplier": "zentrade",
                "supplier_product_id": "ZT-KITCHEN-001",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": "zt_002",
                "name": "논스틱 후라이팬 세트",
                "description": "고급 세라믹 코팅이 적용된 논스틱 후라이팬 3종 세트",
                "price": 67000,
                "cost": 33500,
                "stock": 75,
                "category": "주방용품",
                "subcategory": "조리기구",
                "brand": "Zentrade Ceramic",
                "sku": "ZT-PAN-002",
                "weight": "2.1kg",
                "material": "알루미늄 + 세라믹 코팅",
                "images": [
                    "https://mock-images.zentrade.com/pan-set-1.jpg"
                ],
                "specifications": {
                    "sizes": ["20cm", "24cm", "28cm"],
                    "coating": "세라믹 논스틱",
                    "bottom": "인덕션 호환"
                },
                "supplier": "zentrade",
                "supplier_product_id": "ZT-PAN-002",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        
        if category:
            mock_products = [p for p in mock_products if p["category"].lower() == category.lower()]
        
        return mock_products[:limit]
    
    async def parse_xml_response(self, xml_content: str) -> List[Dict[str, Any]]:
        """Mock XML parsing"""
        # Simulate XML parsing
        return await self.collect_products()


class MockDomeggookAPI:
    """Mock Domeggook API for testing"""
    
    def __init__(self):
        self.base_url = "https://api.domeggook.com"
        self.session = AsyncMock()
        
    async def collect_products(self, category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Mock product collection"""
        mock_products = [
            {
                "id": "dg_001",
                "name": "다기능 청소 도구 세트",
                "description": "일상 청소를 위한 다양한 도구가 포함된 올인원 청소 세트",
                "price": 35000,
                "cost": 17500,
                "stock": 100,
                "category": "생활용품",
                "subcategory": "청소용품",
                "brand": "Domeggook Clean",
                "sku": "DG-CLEAN-001",
                "weight": "800g",
                "material": "플라스틱, 마이크로파이버",
                "images": [
                    "https://mock-images.domeggook.com/clean-set-1.jpg"
                ],
                "specifications": {
                    "contents": ["걸레", "스프레이", "브러시", "클리너"],
                    "package_size": "30x20x15cm"
                },
                "supplier": "domeggook",
                "supplier_product_id": "DG-CLEAN-001",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": "dg_002",
                "name": "수납 정리함 세트",
                "description": "다양한 크기의 투명 수납함으로 깔끔한 정리 정돈",
                "price": 28000,
                "cost": 14000,
                "stock": 80,
                "category": "생활용품",
                "subcategory": "수납용품",
                "brand": "Domeggook Storage",
                "sku": "DG-STORAGE-002",
                "weight": "1.5kg",
                "material": "투명 PP 플라스틱",
                "images": [
                    "https://mock-images.domeggook.com/storage-set-1.jpg",
                    "https://mock-images.domeggook.com/storage-set-2.jpg"
                ],
                "specifications": {
                    "sizes": ["소형 4개", "중형 2개", "대형 1개"],
                    "material": "BPA Free PP",
                    "stackable": True
                },
                "supplier": "domeggook",
                "supplier_product_id": "DG-STORAGE-002",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        
        if category:
            mock_products = [p for p in mock_products if p["category"].lower() == category.lower()]
        
        return mock_products[:limit]


class MockWholesalerManager:
    """Mock wholesaler manager for coordinating all wholesaler APIs"""
    
    def __init__(self):
        self.ownerclan = MockOwnerClanAPI()
        self.zentrade = MockZentradeAPI()
        self.domeggook = MockDomeggookAPI()
        
    async def collect_all_products(self, category: Optional[str] = None, limit_per_supplier: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """Collect products from all wholesalers"""
        results = {}
        
        try:
            results['ownerclan'] = await self.ownerclan.collect_products(category, limit_per_supplier)
        except Exception as e:
            results['ownerclan'] = []
            
        try:
            results['zentrade'] = await self.zentrade.collect_products(category, limit_per_supplier)
        except Exception as e:
            results['zentrade'] = []
            
        try:
            results['domeggook'] = await self.domeggook.collect_products(category, limit_per_supplier)
        except Exception as e:
            results['domeggook'] = []
            
        return results
    
    async def get_product_by_supplier(self, supplier: str, product_id: str) -> Dict[str, Any]:
        """Get specific product from supplier"""
        if supplier == "ownerclan":
            return await self.ownerclan.get_product_details(product_id)
        elif supplier == "zentrade":
            products = await self.zentrade.collect_products()
            for product in products:
                if product["id"] == product_id:
                    return product
        elif supplier == "domeggook":
            products = await self.domeggook.collect_products()
            for product in products:
                if product["id"] == product_id:
                    return product
        
        raise ValueError(f"Product {product_id} not found in {supplier}")
    
    async def check_all_stock(self, products: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Check stock for all products"""
        stock_results = {}
        
        for product in products:
            supplier = product.get("supplier")
            product_id = product.get("id")
            
            if supplier == "ownerclan":
                stock_results[product_id] = await self.ownerclan.check_stock(product_id)
            else:
                # Mock stock check for other suppliers
                stock_results[product_id] = {
                    "product_id": product_id,
                    "stock": 25,
                    "status": "available",
                    "last_updated": datetime.utcnow().isoformat()
                }
        
        return stock_results