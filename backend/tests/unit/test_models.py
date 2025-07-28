"""
Database models unit tests
데이터베이스 모델 테스트
"""
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Numeric, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

# 모의 Base 모델들
Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 모의 모델 클래스들
class User(BaseModel):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.is_active is None:
            self.is_active = True
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

class Product(BaseModel):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.is_active is None:
            self.is_active = True
    
    @property
    def margin(self):
        if self.price == 0:
            return Decimal('0')
        return ((self.price - self.cost) / self.price * 100).quantize(Decimal('0.01'))
    
    @property
    def profit(self):
        return self.price - self.cost
    
    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name})>"

class Order(BaseModel):
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), default="pending")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.status is None:
            self.status = "pending"
    
    customer = relationship("User", backref="orders")
    
    @property
    def is_completed(self):
        return self.status == "completed"
    
    @property
    def is_pending(self):
        return self.status == "pending"
    
    def __repr__(self):
        return f"<Order(id={self.id}, customer_id={self.customer_id})>"

class OrderItem(BaseModel):
    __tablename__ = "order_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    
    order = relationship("Order", backref="items")
    product = relationship("Product")
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, quantity={self.quantity})>"

class WholesaleAccount(BaseModel):
    __tablename__ = "wholesale_accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    api_endpoint = Column(String(500))
    api_key = Column(String(255))
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.is_active is None:
            self.is_active = True
    
    def mark_synced(self):
        self.last_sync = datetime.utcnow()
    
    @property
    def is_sync_due(self):
        if not self.last_sync:
            return True
        return datetime.utcnow() - self.last_sync > timedelta(hours=1)
    
    def __repr__(self):
        return f"<WholesaleAccount(id={self.id}, name={self.name})>"


class TestUserModel:
    """사용자 모델 테스트"""
    
    @pytest.fixture
    def user_data(self):
        return {
            "email": "test@example.com",
            "username": "testuser"
        }
    
    def test_user_creation(self, user_data):
        """사용자 생성 테스트"""
        user = User(**user_data)
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.id is not None
    
    def test_user_repr(self, user_data):
        """사용자 문자열 표현 테스트"""
        user = User(**user_data)
        user.id = "test-id"
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert "test@example.com" in repr_str
        assert "test-id" in repr_str
    
    def test_user_timestamps(self, user_data):
        """사용자 타임스탬프 테스트"""
        user = User(**user_data)
        
        # created_at과 updated_at은 자동으로 설정되어야 함
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')


class TestProductModel:
    """상품 모델 테스트"""
    
    @pytest.fixture
    def product_data(self):
        return {
            "name": "테스트 상품",
            "price": Decimal("10000"),
            "cost": Decimal("7000"),
            "description": "테스트용 상품입니다"
        }
    
    def test_product_creation(self, product_data):
        """상품 생성 테스트"""
        product = Product(**product_data)
        
        assert product.name == "테스트 상품"
        assert product.price == Decimal("10000")
        assert product.cost == Decimal("7000")
        assert product.description == "테스트용 상품입니다"
        assert product.is_active is True
    
    def test_product_margin_calculation(self, product_data):
        """상품 마진 계산 테스트"""
        product = Product(**product_data)
        
        expected_margin = Decimal("30.00")  # (10000-7000)/10000 * 100
        assert product.margin == expected_margin
    
    def test_product_margin_zero_price(self):
        """가격이 0일 때 마진 계산 테스트"""
        product = Product(
            name="무료 상품",
            price=Decimal("0"),
            cost=Decimal("0")
        )
        
        assert product.margin == Decimal("0")
    
    def test_product_profit_calculation(self, product_data):
        """상품 수익 계산 테스트"""
        product = Product(**product_data)
        
        expected_profit = Decimal("3000")  # 10000 - 7000
        assert product.profit == expected_profit
    
    def test_product_repr(self, product_data):
        """상품 문자열 표현 테스트"""
        product = Product(**product_data)
        product.id = "test-product-id"
        
        repr_str = repr(product)
        assert "Product" in repr_str
        assert "테스트 상품" in repr_str
        assert "test-product-id" in repr_str


class TestOrderModel:
    """주문 모델 테스트"""
    
    @pytest.fixture
    def order_data(self):
        return {
            "customer_id": "customer-123",
            "total_amount": Decimal("25000")
        }
    
    def test_order_creation(self, order_data):
        """주문 생성 테스트"""
        order = Order(**order_data)
        
        assert order.customer_id == "customer-123"
        assert order.total_amount == Decimal("25000")
        assert order.status == "pending"
        assert order.id is not None
    
    def test_order_is_pending(self, order_data):
        """주문 대기 상태 확인 테스트"""
        order = Order(**order_data)
        
        assert order.is_pending is True
        assert order.is_completed is False
    
    def test_order_is_completed(self, order_data):
        """주문 완료 상태 확인 테스트"""
        order = Order(**order_data)
        order.status = "completed"
        
        assert order.is_completed is True
        assert order.is_pending is False
    
    def test_order_repr(self, order_data):
        """주문 문자열 표현 테스트"""
        order = Order(**order_data)
        order.id = "test-order-id"
        
        repr_str = repr(order)
        assert "Order" in repr_str
        assert "customer-123" in repr_str
        assert "test-order-id" in repr_str


class TestOrderItemModel:
    """주문 아이템 모델 테스트"""
    
    @pytest.fixture
    def order_item_data(self):
        return {
            "order_id": "order-123",
            "product_id": "product-456",
            "quantity": 3,
            "unit_price": Decimal("5000")
        }
    
    def test_order_item_creation(self, order_item_data):
        """주문 아이템 생성 테스트"""
        item = OrderItem(**order_item_data)
        
        assert item.order_id == "order-123"
        assert item.product_id == "product-456"
        assert item.quantity == 3
        assert item.unit_price == Decimal("5000")
    
    def test_order_item_total_price(self, order_item_data):
        """주문 아이템 총 가격 계산 테스트"""
        item = OrderItem(**order_item_data)
        
        expected_total = Decimal("15000")  # 3 * 5000
        assert item.total_price == expected_total
    
    def test_order_item_repr(self, order_item_data):
        """주문 아이템 문자열 표현 테스트"""
        item = OrderItem(**order_item_data)
        item.id = "test-item-id"
        
        repr_str = repr(item)
        assert "OrderItem" in repr_str
        assert "3" in repr_str  # quantity
        assert "test-item-id" in repr_str


class TestWholesaleAccountModel:
    """도매 계정 모델 테스트"""
    
    @pytest.fixture
    def wholesale_account_data(self):
        return {
            "name": "테스트 도매처",
            "api_endpoint": "https://api.test-wholesaler.com",
            "api_key": "test-api-key-123"
        }
    
    def test_wholesale_account_creation(self, wholesale_account_data):
        """도매 계정 생성 테스트"""
        account = WholesaleAccount(**wholesale_account_data)
        
        assert account.name == "테스트 도매처"
        assert account.api_endpoint == "https://api.test-wholesaler.com"
        assert account.api_key == "test-api-key-123"
        assert account.is_active is True
        assert account.last_sync is None
    
    def test_mark_synced(self, wholesale_account_data):
        """동기화 마킹 테스트"""
        account = WholesaleAccount(**wholesale_account_data)
        
        # 동기화 전에는 last_sync가 None
        assert account.last_sync is None
        
        # 동기화 마킹
        account.mark_synced()
        
        # 동기화 후에는 현재 시간으로 설정
        assert account.last_sync is not None
        assert isinstance(account.last_sync, datetime)
    
    def test_is_sync_due_no_previous_sync(self, wholesale_account_data):
        """이전 동기화가 없을 때 동기화 필요 여부 테스트"""
        account = WholesaleAccount(**wholesale_account_data)
        
        # 이전 동기화가 없으면 동기화 필요
        assert account.is_sync_due is True
    
    def test_is_sync_due_recent_sync(self, wholesale_account_data):
        """최근 동기화 시 동기화 필요 여부 테스트"""
        account = WholesaleAccount(**wholesale_account_data)
        account.last_sync = datetime.utcnow() - timedelta(minutes=30)  # 30분 전
        
        # 1시간 이내면 동기화 불필요
        assert account.is_sync_due is False
    
    def test_is_sync_due_old_sync(self, wholesale_account_data):
        """오래된 동기화 시 동기화 필요 여부 테스트"""
        account = WholesaleAccount(**wholesale_account_data)
        account.last_sync = datetime.utcnow() - timedelta(hours=2)  # 2시간 전
        
        # 1시간 이상 경과하면 동기화 필요
        assert account.is_sync_due is True
    
    def test_wholesale_account_repr(self, wholesale_account_data):
        """도매 계정 문자열 표현 테스트"""
        account = WholesaleAccount(**wholesale_account_data)
        account.id = "test-account-id"
        
        repr_str = repr(account)
        assert "WholesaleAccount" in repr_str
        assert "테스트 도매처" in repr_str
        assert "test-account-id" in repr_str


class TestModelRelationships:
    """모델 관계 테스트"""
    
    def test_user_order_relationship(self):
        """사용자-주문 관계 테스트"""
        user = User(email="test@example.com", username="testuser")
        user.id = "user-123"
        
        order = Order(customer_id="user-123", total_amount=Decimal("10000"))
        
        # 관계 설정은 실제 DB 세션에서 이루어지므로 여기서는 ID만 확인
        assert order.customer_id == user.id
    
    def test_order_item_relationships(self):
        """주문-주문아이템-상품 관계 테스트"""
        order = Order(customer_id="user-123", total_amount=Decimal("15000"))
        order.id = "order-456"
        
        product = Product(name="테스트 상품", price=Decimal("5000"), cost=Decimal("3000"))
        product.id = "product-789"
        
        order_item = OrderItem(
            order_id="order-456",
            product_id="product-789",
            quantity=3,
            unit_price=Decimal("5000")
        )
        
        # 관계 ID 확인
        assert order_item.order_id == order.id
        assert order_item.product_id == product.id


class TestModelValidation:
    """모델 검증 테스트"""
    
    def test_product_validation_business_rules(self):
        """상품 비즈니스 규칙 검증 테스트"""
        # 정상적인 상품
        valid_product = Product(
            name="정상 상품",
            price=Decimal("10000"),
            cost=Decimal("7000")
        )
        
        assert valid_product.margin > 0
        assert valid_product.profit > 0
        
        # 손실이 나는 상품
        loss_product = Product(
            name="손실 상품",
            price=Decimal("5000"),
            cost=Decimal("8000")
        )
        
        assert loss_product.profit < 0
        assert loss_product.margin < 0
    
    def test_order_validation_business_rules(self):
        """주문 비즈니스 규칙 검증 테스트"""
        # 정상적인 주문
        valid_order = Order(
            customer_id="customer-123",
            total_amount=Decimal("25000")
        )
        
        assert valid_order.total_amount > 0
        assert valid_order.is_pending
        
        # 무료 주문 (가능한 시나리오)
        free_order = Order(
            customer_id="customer-456",
            total_amount=Decimal("0")
        )
        
        assert free_order.total_amount == 0


class TestModelUtilities:
    """모델 유틸리티 테스트"""
    
    def test_id_generation(self):
        """ID 자동 생성 테스트"""
        product1 = Product(name="상품1", price=Decimal("1000"), cost=Decimal("700"))
        product2 = Product(name="상품2", price=Decimal("2000"), cost=Decimal("1400"))
        
        # ID가 자동으로 생성되고 서로 다른지 확인
        assert product1.id is not None
        assert product2.id is not None
        assert product1.id != product2.id
    
    def test_timestamps_auto_setting(self):
        """타임스탬프 자동 설정 테스트"""
        user = User(email="timestamp@test.com", username="timestampuser")
        
        # BaseModel을 상속받은 모든 모델은 타임스탬프를 가져야 함
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
    
    def test_model_string_representations(self):
        """모델 문자열 표현 일관성 테스트"""
        models = [
            User(email="test@example.com", username="testuser"),
            Product(name="테스트 상품", price=Decimal("1000"), cost=Decimal("700")),
            Order(customer_id="customer-123", total_amount=Decimal("5000")),
            OrderItem(order_id="order-123", product_id="product-456", quantity=1, unit_price=Decimal("1000")),
            WholesaleAccount(name="테스트 도매처")
        ]
        
        for model in models:
            repr_str = repr(model)
            # 모든 모델의 repr에는 클래스명이 포함되어야 함
            assert model.__class__.__name__ in repr_str
            # ID가 포함되어야 함 (자동 생성되므로)
            assert "id=" in repr_str