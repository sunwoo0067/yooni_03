"""
API endpoints unit tests
API 엔드포인트 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from decimal import Decimal
import json

# 모의 FastAPI 앱과 엔드포인트 구현
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

# 모의 모델들
class ProductCreate(BaseModel):
    name: str
    price: Decimal
    cost: Decimal
    description: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    name: str
    price: Decimal
    cost: Decimal
    margin: Decimal
    description: Optional[str] = None

class OrderCreate(BaseModel):
    customer_id: str
    items: List[dict]
    shipping_address: dict

class OrderResponse(BaseModel):
    id: str
    customer_id: str
    total_amount: Decimal
    status: str

# 모의 서비스 클래스들
class MockProductService:
    def __init__(self):
        self.products = {}
        self.next_id = 1
    
    async def create_product(self, product_data: dict) -> dict:
        product_id = str(self.next_id)
        self.next_id += 1
        
        margin = ((product_data["price"] - product_data["cost"]) / product_data["price"] * 100) if product_data["price"] > 0 else 0
        
        product = {
            "id": product_id,
            "name": product_data["name"],
            "price": product_data["price"],
            "cost": product_data["cost"],
            "margin": margin,
            "description": product_data.get("description")
        }
        
        self.products[product_id] = product
        return product
    
    async def get_product(self, product_id: str) -> Optional[dict]:
        return self.products.get(product_id)
    
    async def get_products(self, skip: int = 0, limit: int = 100) -> List[dict]:
        products = list(self.products.values())
        return products[skip:skip + limit]
    
    async def update_product(self, product_id: str, update_data: dict) -> Optional[dict]:
        if product_id not in self.products:
            return None
        
        product = self.products[product_id]
        product.update(update_data)
        
        if "price" in update_data or "cost" in update_data:
            product["margin"] = ((product["price"] - product["cost"]) / product["price"] * 100) if product["price"] > 0 else 0
        
        return product
    
    async def delete_product(self, product_id: str) -> bool:
        if product_id in self.products:
            del self.products[product_id]
            return True
        return False

class MockOrderService:
    def __init__(self):
        self.orders = {}
        self.next_id = 1
    
    async def create_order(self, order_data: dict) -> dict:
        order_id = str(self.next_id)
        self.next_id += 1
        
        total_amount = sum(item["price"] * item["quantity"] for item in order_data["items"])
        
        order = {
            "id": order_id,
            "customer_id": order_data["customer_id"],
            "items": order_data["items"],
            "total_amount": total_amount,
            "status": "pending",
            "shipping_address": order_data["shipping_address"]
        }
        
        self.orders[order_id] = order
        return order
    
    async def get_order(self, order_id: str) -> Optional[dict]:
        return self.orders.get(order_id)
    
    async def get_orders(self, skip: int = 0, limit: int = 100) -> List[dict]:
        orders = list(self.orders.values())
        return orders[skip:skip + limit]
    
    async def update_order_status(self, order_id: str, status: str) -> Optional[dict]:
        if order_id not in self.orders:
            return None
        
        self.orders[order_id]["status"] = status
        return self.orders[order_id]

# 모의 FastAPI 앱 생성
def create_test_app():
    app = FastAPI()
    
    product_service = MockProductService()
    order_service = MockOrderService()
    
    @app.post("/api/v1/products", response_model=ProductResponse)
    async def create_product(product: ProductCreate):
        try:
            created_product = await product_service.create_product(product.dict())
            return ProductResponse(**created_product)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/v1/products/{product_id}", response_model=ProductResponse)
    async def get_product(product_id: str):
        product = await product_service.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return ProductResponse(**product)
    
    @app.get("/api/v1/products", response_model=List[ProductResponse])
    async def get_products(skip: int = 0, limit: int = 100):
        products = await product_service.get_products(skip, limit)
        return [ProductResponse(**product) for product in products]
    
    @app.put("/api/v1/products/{product_id}", response_model=ProductResponse)
    async def update_product(product_id: str, product_update: dict):
        updated_product = await product_service.update_product(product_id, product_update)
        if not updated_product:
            raise HTTPException(status_code=404, detail="Product not found")
        return ProductResponse(**updated_product)
    
    @app.delete("/api/v1/products/{product_id}")
    async def delete_product(product_id: str):
        deleted = await product_service.delete_product(product_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"message": "Product deleted successfully"}
    
    @app.post("/api/v1/orders", response_model=OrderResponse)
    async def create_order(order: OrderCreate):
        try:
            created_order = await order_service.create_order(order.dict())
            return OrderResponse(**created_order)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/v1/orders/{order_id}", response_model=OrderResponse)
    async def get_order(order_id: str):
        order = await order_service.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderResponse(**order)
    
    @app.get("/api/v1/orders", response_model=List[OrderResponse])
    async def get_orders(skip: int = 0, limit: int = 100):
        orders = await order_service.get_orders(skip, limit)
        return [OrderResponse(**order) for order in orders]
    
    @app.put("/api/v1/orders/{order_id}/status")
    async def update_order_status(order_id: str, status_data: dict):
        updated_order = await order_service.update_order_status(order_id, status_data["status"])
        if not updated_order:
            raise HTTPException(status_code=404, detail="Order not found")
        return {"message": "Order status updated successfully"}
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "message": "API is running"}
    
    return app

class TestProductAPI:
    """상품 API 테스트"""
    
    @pytest.fixture
    def client(self):
        app = create_test_app()
        return TestClient(app)
    
    def test_create_product(self, client):
        """상품 생성 API 테스트"""
        product_data = {
            "name": "테스트 상품",
            "price": 10000,
            "cost": 7000,
            "description": "테스트용 상품입니다"
        }
        
        response = client.post("/api/v1/products", json=product_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "테스트 상품"
        assert float(data["price"]) == 10000
        assert float(data["cost"]) == 7000
        assert float(data["margin"]) == 30.0
    
    def test_create_product_invalid_data(self, client):
        """잘못된 데이터로 상품 생성 API 테스트"""
        product_data = {
            # 상품명 누락
            "price": -1000,  # 음수 가격
            "cost": 7000
        }
        
        response = client.post("/api/v1/products", json=product_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_get_product(self, client):
        """상품 조회 API 테스트"""
        # 먼저 상품 생성
        product_data = {
            "name": "조회용 상품",
            "price": 15000,
            "cost": 10000
        }
        create_response = client.post("/api/v1/products", json=product_data)
        created_product = create_response.json()
        
        # 상품 조회
        response = client.get(f"/api/v1/products/{created_product['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "조회용 상품"
        assert data["id"] == created_product["id"]
    
    def test_get_product_not_found(self, client):
        """존재하지 않는 상품 조회 API 테스트"""
        response = client.get("/api/v1/products/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_products_list(self, client):
        """상품 목록 조회 API 테스트"""
        # 여러 상품 생성
        products = [
            {"name": "상품1", "price": 10000, "cost": 7000},
            {"name": "상품2", "price": 20000, "cost": 15000},
            {"name": "상품3", "price": 30000, "cost": 20000}
        ]
        
        for product in products:
            client.post("/api/v1/products", json=product)
        
        # 상품 목록 조회
        response = client.get("/api/v1/products")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all("name" in product for product in data)
    
    def test_update_product(self, client):
        """상품 수정 API 테스트"""
        # 상품 생성
        product_data = {"name": "수정전 상품", "price": 10000, "cost": 7000}
        create_response = client.post("/api/v1/products", json=product_data)
        created_product = create_response.json()
        
        # 상품 수정
        update_data = {"name": "수정후 상품", "price": 12000}
        response = client.put(f"/api/v1/products/{created_product['id']}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정후 상품"
        assert float(data["price"]) == 12000
    
    def test_delete_product(self, client):
        """상품 삭제 API 테스트"""
        # 상품 생성
        product_data = {"name": "삭제용 상품", "price": 10000, "cost": 7000}
        create_response = client.post("/api/v1/products", json=product_data)
        created_product = create_response.json()
        
        # 상품 삭제
        response = client.delete(f"/api/v1/products/{created_product['id']}")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # 삭제 확인
        get_response = client.get(f"/api/v1/products/{created_product['id']}")
        assert get_response.status_code == 404


class TestOrderAPI:
    """주문 API 테스트"""
    
    @pytest.fixture
    def client(self):
        app = create_test_app()
        return TestClient(app)
    
    @pytest.fixture
    def sample_order_data(self):
        return {
            "customer_id": "customer123",
            "items": [
                {"product_id": "prod1", "quantity": 2, "price": 10000},
                {"product_id": "prod2", "quantity": 1, "price": 5000}
            ],
            "shipping_address": {
                "name": "홍길동",
                "phone": "010-1234-5678",
                "address": "서울시 강남구"
            }
        }
    
    def test_create_order(self, client, sample_order_data):
        """주문 생성 API 테스트"""
        response = client.post("/api/v1/orders", json=sample_order_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "customer123"
        assert float(data["total_amount"]) == 25000  # (10000*2) + (5000*1)
        assert data["status"] == "pending"
    
    def test_create_order_invalid_data(self, client):
        """잘못된 데이터로 주문 생성 API 테스트"""
        invalid_order = {
            "customer_id": "",  # 빈 고객 ID
            "items": []  # 빈 아이템 목록
        }
        
        response = client.post("/api/v1/orders", json=invalid_order)
        
        assert response.status_code == 422  # Validation error
    
    def test_get_order(self, client, sample_order_data):
        """주문 조회 API 테스트"""
        # 주문 생성
        create_response = client.post("/api/v1/orders", json=sample_order_data)
        created_order = create_response.json()
        
        # 주문 조회
        response = client.get(f"/api/v1/orders/{created_order['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_order["id"]
        assert data["customer_id"] == "customer123"
    
    def test_get_orders_list(self, client, sample_order_data):
        """주문 목록 조회 API 테스트"""
        # 여러 주문 생성
        for i in range(3):
            order_data = sample_order_data.copy()
            order_data["customer_id"] = f"customer{i}"
            client.post("/api/v1/orders", json=order_data)
        
        # 주문 목록 조회
        response = client.get("/api/v1/orders")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all("customer_id" in order for order in data)
    
    def test_update_order_status(self, client, sample_order_data):
        """주문 상태 업데이트 API 테스트"""
        # 주문 생성
        create_response = client.post("/api/v1/orders", json=sample_order_data)
        created_order = create_response.json()
        
        # 주문 상태 업데이트
        status_data = {"status": "processing"}
        response = client.put(f"/api/v1/orders/{created_order['id']}/status", json=status_data)
        
        assert response.status_code == 200
        assert "updated successfully" in response.json()["message"]


class TestHealthAPI:
    """헬스체크 API 테스트"""
    
    @pytest.fixture
    def client(self):
        app = create_test_app()
        return TestClient(app)
    
    def test_health_check(self, client):
        """헬스체크 API 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "API is running" in data["message"]


class TestAPIErrorHandling:
    """API 에러 처리 테스트"""
    
    @pytest.fixture
    def client(self):
        app = create_test_app()
        return TestClient(app)
    
    def test_404_not_found(self, client):
        """존재하지 않는 엔드포인트 테스트"""
        response = client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
    
    def test_405_method_not_allowed(self, client):
        """허용되지 않는 HTTP 메서드 테스트"""
        response = client.patch("/health")  # PATCH는 지원하지 않음
        
        assert response.status_code == 405


class TestAPIIntegration:
    """API 통합 테스트"""
    
    @pytest.fixture
    def client(self):
        app = create_test_app()
        return TestClient(app)
    
    def test_product_order_workflow(self, client):
        """상품 생성 → 주문 생성 워크플로우 테스트"""
        # 1. 상품 생성
        product_data = {"name": "워크플로우 상품", "price": 15000, "cost": 10000}
        product_response = client.post("/api/v1/products", json=product_data)
        created_product = product_response.json()
        
        # 2. 주문 생성
        order_data = {
            "customer_id": "workflow_customer",
            "items": [
                {"product_id": created_product["id"], "quantity": 2, "price": 15000}
            ],
            "shipping_address": {
                "name": "워크플로우 고객",
                "phone": "010-9999-9999",
                "address": "서울시 테스트구"
            }
        }
        order_response = client.post("/api/v1/orders", json=order_data)
        created_order = order_response.json()
        
        # 3. 검증
        assert product_response.status_code == 200
        assert order_response.status_code == 200
        assert float(created_order["total_amount"]) == 30000  # 15000 * 2
        
        # 4. 주문 상태 업데이트
        status_response = client.put(
            f"/api/v1/orders/{created_order['id']}/status", 
            json={"status": "completed"}
        )
        assert status_response.status_code == 200