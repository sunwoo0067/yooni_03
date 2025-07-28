"""
Mock implementations for marketplace APIs
"""
import asyncio
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, Mock
from decimal import Decimal
from datetime import datetime, timedelta
import json
import uuid


class MockCoupangAPI:
    """Mock Coupang Partners API for testing"""
    
    def __init__(self):
        self.base_url = "https://api.coupang.com"
        self.vendor_id = "test_vendor"
        self.access_key = "test_access_key"
        self.secret_key = "test_secret_key"
        self.session = AsyncMock()
        
    async def authenticate(self) -> Dict[str, Any]:
        """Mock authentication"""
        return {
            "success": True,
            "vendor_id": self.vendor_id,
            "access_token": "mock_coupang_token",
            "expires_in": 7200
        }
    
    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock product creation"""
        vendor_item_id = f"VI_{uuid.uuid4().hex[:8].upper()}"
        
        return {
            "success": True,
            "code": "SUCCESS",
            "message": "상품이 성공적으로 등록되었습니다",
            "data": {
                "vendor_item_id": vendor_item_id,
                "product_id": f"CP_{uuid.uuid4().hex[:10].upper()}",
                "status": "registered",
                "approval_status": "pending",
                "registration_date": datetime.utcnow().isoformat(),
                "item_details": {
                    "name": product_data.get("name"),
                    "price": product_data.get("price"),
                    "category": product_data.get("category"),
                    "brand": product_data.get("brand", "기본 브랜드")
                }
            }
        }
    
    async def update_product(self, vendor_item_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock product update"""
        return {
            "success": True,
            "code": "SUCCESS",
            "message": "상품이 성공적으로 수정되었습니다",
            "data": {
                "vendor_item_id": vendor_item_id,
                "updated_fields": list(update_data.keys()),
                "update_date": datetime.utcnow().isoformat()
            }
        }
    
    async def get_orders(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock order retrieval"""
        mock_orders = [
            {
                "order_id": f"CP_ORD_{uuid.uuid4().hex[:10].upper()}",
                "vendor_item_id": f"VI_{uuid.uuid4().hex[:8].upper()}",
                "product_name": "테스트 상품 1",
                "quantity": 2,
                "unit_price": 25000,
                "total_price": 50000,
                "order_date": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "payment_date": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "status": "paid",
                "delivery_info": {
                    "shipping_method": "로켓배송",
                    "tracking_number": f"TRK{uuid.uuid4().hex[:12].upper()}",
                    "estimated_delivery": (datetime.utcnow() + timedelta(days=1)).isoformat()
                },
                "customer_info": {
                    "name": "홍길동",
                    "phone": "010-1234-5678",
                    "address": "서울시 강남구 테헤란로 123",
                    "zipcode": "06142"
                },
                "payment_info": {
                    "method": "신용카드",
                    "card_name": "KB국민카드",
                    "installment": "일시불"
                }
            },
            {
                "order_id": f"CP_ORD_{uuid.uuid4().hex[:10].upper()}",
                "vendor_item_id": f"VI_{uuid.uuid4().hex[:8].upper()}",
                "product_name": "테스트 상품 2",
                "quantity": 1,
                "unit_price": 35000,
                "total_price": 35000,
                "order_date": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
                "payment_date": (datetime.utcnow() - timedelta(hours=4)).isoformat(),
                "status": "shipping",
                "delivery_info": {
                    "shipping_method": "일반배송",
                    "tracking_number": f"TRK{uuid.uuid4().hex[:12].upper()}",
                    "estimated_delivery": (datetime.utcnow() + timedelta(days=2)).isoformat()
                },
                "customer_info": {
                    "name": "김영희",
                    "phone": "010-9876-5432",
                    "address": "부산시 해운대구 센텀로 456",
                    "zipcode": "48058"
                },
                "payment_info": {
                    "method": "네이버페이",
                    "installment": "일시불"
                }
            }
        ]
        
        return mock_orders
    
    async def update_stock(self, vendor_item_id: str, stock_quantity: int) -> Dict[str, Any]:
        """Mock stock update"""
        return {
            "success": True,
            "code": "SUCCESS",
            "message": "재고가 성공적으로 업데이트되었습니다",
            "data": {
                "vendor_item_id": vendor_item_id,
                "updated_stock": stock_quantity,
                "update_date": datetime.utcnow().isoformat()
            }
        }
    
    async def get_product_performance(self, vendor_item_id: str) -> Dict[str, Any]:
        """Mock product performance data"""
        return {
            "vendor_item_id": vendor_item_id,
            "views": 1250,
            "clicks": 89,
            "orders": 12,
            "revenue": 420000,
            "conversion_rate": 0.13,
            "average_rating": 4.3,
            "review_count": 8,
            "period": "last_30_days",
            "last_updated": datetime.utcnow().isoformat()
        }


class MockNaverAPI:
    """Mock Naver Smart Store API for testing"""
    
    def __init__(self):
        self.base_url = "https://api.commerce.naver.com"
        self.client_id = "test_naver_client"
        self.client_secret = "test_naver_secret"
        self.access_token = None
        self.session = AsyncMock()
        
    async def get_access_token(self) -> Dict[str, Any]:
        """Mock OAuth token retrieval"""
        self.access_token = f"naver_token_{uuid.uuid4().hex[:16]}"
        return {
            "access_token": self.access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "commerce.product commerce.order"
        }
    
    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock product creation"""
        product_id = f"NV_{uuid.uuid4().hex[:10].upper()}"
        
        return {
            "success": True,
            "code": "SUCCESS",
            "message": "상품 등록이 완료되었습니다",
            "data": {
                "product_id": product_id,
                "channel_product_no": f"CH_{uuid.uuid4().hex[:8].upper()}",
                "status": "registered",
                "approval_status": "reviewing",
                "registration_date": datetime.utcnow().isoformat(),
                "expected_approval_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "product_info": {
                    "name": product_data.get("name"),
                    "price": product_data.get("price"),
                    "category": product_data.get("category"),
                    "delivery_type": "smart_store"
                }
            }
        }
    
    async def get_orders(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock order retrieval"""
        mock_orders = [
            {
                "order_id": f"NV_ORD_{uuid.uuid4().hex[:10].upper()}",
                "product_order_id": f"PO_{uuid.uuid4().hex[:8].upper()}",
                "channel_product_no": f"CH_{uuid.uuid4().hex[:8].upper()}",
                "product_name": "네이버 테스트 상품 1",
                "quantity": 1,
                "unit_price": 28000,
                "total_price": 28000,
                "order_date": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                "payment_date": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "status": "paid",
                "delivery_info": {
                    "shipping_method": "택배배송",
                    "shipping_company": "CJ대한통운",
                    "tracking_number": f"NAVER{uuid.uuid4().hex[:10].upper()}",
                    "delivery_fee": 3000
                },
                "customer_info": {
                    "order_name": "이철수",
                    "recipient_name": "이철수",
                    "phone": "010-2345-6789",
                    "address": "대구시 수성구 동대구로 789",
                    "zipcode": "42000"
                },
                "payment_info": {
                    "method": "네이버페이",
                    "payment_commission": 840  # 3% commission
                }
            }
        ]
        
        return mock_orders
    
    async def update_stock(self, channel_product_no: str, stock_quantity: int) -> Dict[str, Any]:
        """Mock stock update"""
        return {
            "success": True,
            "code": "SUCCESS",
            "message": "재고 업데이트가 완료되었습니다",
            "data": {
                "channel_product_no": channel_product_no,
                "updated_stock": stock_quantity,
                "update_date": datetime.utcnow().isoformat()
            }
        }
    
    async def get_channel_info(self) -> Dict[str, Any]:
        """Mock channel information"""
        return {
            "channel_id": "test_smart_store",
            "channel_name": "테스트 스마트스토어",
            "status": "active",
            "commission_rate": 0.03,  # 3%
            "settlement_cycle": "weekly",
            "contact_info": {
                "email": "test@smartstore.com",
                "phone": "1588-1234"
            }
        }


class MockEleventyAPI:
    """Mock 11st Open Market API for testing"""
    
    def __init__(self):
        self.base_url = "https://api.11st.co.kr"
        self.api_key = "test_11st_api_key"
        self.session = AsyncMock()
        
    async def authenticate(self) -> Dict[str, Any]:
        """Mock authentication"""
        return {
            "success": True,
            "api_key": self.api_key,
            "vendor_code": "TEST_VENDOR_11ST",
            "access_granted": True
        }
    
    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock product creation"""
        product_id = f"11ST_{uuid.uuid4().hex[:10].upper()}"
        
        return {
            "success": True,
            "resultCode": "SUCCESS",
            "resultMessage": "상품 등록이 성공하였습니다",
            "data": {
                "product_id": product_id,
                "vendor_item_id": f"VI_{uuid.uuid4().hex[:8].upper()}",
                "display_status": "registered",
                "approval_status": "waiting",
                "registration_date": datetime.utcnow().isoformat(),
                "product_info": {
                    "name": product_data.get("name"),
                    "price": product_data.get("price"),
                    "category_code": product_data.get("category_code", "DEFAULT"),
                    "brand": product_data.get("brand", "일반브랜드")
                }
            }
        }
    
    async def get_orders(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock order retrieval"""
        mock_orders = [
            {
                "order_id": f"11ST_ORD_{uuid.uuid4().hex[:10].upper()}",
                "order_detail_id": f"OD_{uuid.uuid4().hex[:8].upper()}",
                "vendor_item_id": f"VI_{uuid.uuid4().hex[:8].upper()}",
                "product_name": "11번가 테스트 상품 1",
                "quantity": 2,
                "unit_price": 22000,
                "total_price": 44000,
                "order_date": (datetime.utcnow() - timedelta(hours=4)).isoformat(),
                "payment_date": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                "status": "payment_complete",
                "delivery_info": {
                    "shipping_method": "일반택배",
                    "shipping_company": "로젠택배",
                    "tracking_number": f"11ST{uuid.uuid4().hex[:10].upper()}",
                    "delivery_fee": 2500
                },
                "customer_info": {
                    "buyer_name": "박민수",
                    "recipient_name": "박민수",
                    "phone": "010-3456-7890",
                    "address": "인천시 부평구 부평대로 101",
                    "zipcode": "21300"
                },
                "payment_info": {
                    "method": "신용카드",
                    "commission_rate": 0.035,  # 3.5%
                    "commission_amount": 1540
                }
            }
        ]
        
        return mock_orders
    
    async def update_inventory(self, vendor_item_id: str, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock inventory update"""
        return {
            "success": True,
            "resultCode": "SUCCESS",
            "resultMessage": "재고 정보가 업데이트되었습니다",
            "data": {
                "vendor_item_id": vendor_item_id,
                "updated_fields": inventory_data,
                "update_date": datetime.utcnow().isoformat()
            }
        }
    
    async def get_settlement_info(self, period: str = "monthly") -> Dict[str, Any]:
        """Mock settlement information"""
        return {
            "period": period,
            "total_sales": 2350000,
            "commission": 82250,
            "net_amount": 2267750,
            "settlement_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "orders_count": 156,
            "returns_count": 8,
            "return_amount": 176000
        }


class MockMarketplaceManager:
    """Mock marketplace manager for coordinating all marketplace APIs"""
    
    def __init__(self):
        self.coupang = MockCoupangAPI()
        self.naver = MockNaverAPI()
        self.eleventy = MockEleventyAPI()
        
    async def register_product_to_all_platforms(self, product_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Register product to all platforms"""
        results = {}
        
        # Register to Coupang
        try:
            results['coupang'] = await self.coupang.create_product(product_data)
        except Exception as e:
            results['coupang'] = {"success": False, "error": str(e)}
        
        # Register to Naver
        try:
            # Get token first
            await self.naver.get_access_token()
            results['naver'] = await self.naver.create_product(product_data)
        except Exception as e:
            results['naver'] = {"success": False, "error": str(e)}
        
        # Register to 11st
        try:
            results['eleventy'] = await self.eleventy.create_product(product_data)
        except Exception as e:
            results['eleventy'] = {"success": False, "error": str(e)}
        
        return results
    
    async def sync_stock_across_platforms(self, product_mapping: Dict[str, Dict[str, str]], stock_quantity: int) -> Dict[str, Dict[str, Any]]:
        """Sync stock across all platforms"""
        results = {}
        
        if 'coupang' in product_mapping and 'vendor_item_id' in product_mapping['coupang']:
            results['coupang'] = await self.coupang.update_stock(
                product_mapping['coupang']['vendor_item_id'], 
                stock_quantity
            )
        
        if 'naver' in product_mapping and 'channel_product_no' in product_mapping['naver']:
            results['naver'] = await self.naver.update_stock(
                product_mapping['naver']['channel_product_no'], 
                stock_quantity
            )
        
        if 'eleventy' in product_mapping and 'vendor_item_id' in product_mapping['eleventy']:
            results['eleventy'] = await self.eleventy.update_inventory(
                product_mapping['eleventy']['vendor_item_id'],
                {"stock_quantity": stock_quantity}
            )
        
        return results
    
    async def collect_all_orders(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Collect orders from all platforms"""
        results = {}
        
        try:
            results['coupang'] = await self.coupang.get_orders(start_date, end_date)
        except Exception as e:
            results['coupang'] = []
        
        try:
            await self.naver.get_access_token()
            results['naver'] = await self.naver.get_orders(start_date, end_date)
        except Exception as e:
            results['naver'] = []
        
        try:
            results['eleventy'] = await self.eleventy.get_orders(start_date, end_date)
        except Exception as e:
            results['eleventy'] = []
        
        return results
    
    async def get_platform_performance(self, platform: str, product_id: str) -> Dict[str, Any]:
        """Get performance data from specific platform"""
        if platform == "coupang":
            return await self.coupang.get_product_performance(product_id)
        elif platform == "naver":
            return await self.naver.get_channel_info()
        elif platform == "eleventy":
            return await self.eleventy.get_settlement_info()
        else:
            raise ValueError(f"Unsupported platform: {platform}")