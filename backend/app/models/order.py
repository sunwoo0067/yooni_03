"""
Order management models
"""
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from .base import BaseModel


class OrderStatus(enum.Enum):
    """Order status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    RETURNED = "returned"
    # 드롭쉬핑 특화 상태
    SUPPLIER_ORDER_PENDING = "supplier_order_pending"
    SUPPLIER_ORDER_CONFIRMED = "supplier_order_confirmed"
    SUPPLIER_ORDER_FAILED = "supplier_order_failed"
    OUT_OF_STOCK = "out_of_stock"
    MARGIN_PROTECTED = "margin_protected"


class PaymentStatus(enum.Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    FAILED = "failed"
    REFUNDED = "refunded"


class ShippingStatus(enum.Enum):
    """Shipping status enumeration"""
    PENDING = "pending"
    PREPARING = "preparing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"


class Order(BaseModel):
    """Order information"""
    __tablename__ = "orders"
    
    # Platform Information
    platform_account_id = Column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False, index=True)
    platform_order_id = Column(String(100), nullable=False, index=True)  # Platform-specific order ID
    
    # Order Details
    order_number = Column(String(50), unique=True, nullable=False, index=True)  # Internal order number
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Customer Information
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_id = Column(String(100), nullable=True, index=True)  # Platform customer ID
    
    # Shipping Address
    shipping_name = Column(String(100), nullable=True)
    shipping_company = Column(String(100), nullable=True)
    shipping_address1 = Column(String(200), nullable=False)
    shipping_address2 = Column(String(200), nullable=True)
    shipping_city = Column(String(100), nullable=False)
    shipping_state = Column(String(100), nullable=True)
    shipping_postal_code = Column(String(20), nullable=True)
    shipping_country = Column(String(2), default="KR", nullable=False)
    
    # Billing Address (if different)
    billing_name = Column(String(100), nullable=True)
    billing_address1 = Column(String(200), nullable=True)
    billing_address2 = Column(String(200), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(100), nullable=True)
    billing_postal_code = Column(String(20), nullable=True)
    billing_country = Column(String(2), nullable=True)
    
    # Financial Information
    currency = Column(String(3), default="KRW", nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)  # Before tax and shipping
    tax_amount = Column(Numeric(12, 2), default=0, nullable=False)
    shipping_cost = Column(Numeric(12, 2), default=0, nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Status Information
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    shipping_status = Column(SQLEnum(ShippingStatus), default=ShippingStatus.PENDING, nullable=False, index=True)
    
    # Shipping Information
    shipping_method = Column(String(100), nullable=True)
    shipping_carrier = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True, index=True)
    shipped_at = Column(DateTime, nullable=True, index=True)
    delivered_at = Column(DateTime, nullable=True, index=True)
    
    # Special Instructions
    customer_notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    gift_message = Column(Text, nullable=True)
    
    # Platform-specific data
    platform_data = Column(JSONB, nullable=True)
    
    # Processing Information
    processed_by = Column(String(100), nullable=True)  # User who processed the order
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    platform_account = relationship("PlatformAccount", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan")
    shipments = relationship("OrderShipment", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(order_number={self.order_number}, status={self.status.value})>"
    
    @property
    def is_paid(self) -> bool:
        """Check if order is fully paid"""
        return self.payment_status == PaymentStatus.PAID
    
    @property
    def is_shipped(self) -> bool:
        """Check if order is shipped"""
        return self.shipping_status in [ShippingStatus.SHIPPED, ShippingStatus.IN_TRANSIT, ShippingStatus.DELIVERED]
    
    @property
    def can_cancel(self) -> bool:
        """Check if order can be cancelled"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PAID] and not self.is_shipped


class OrderItem(BaseModel):
    """Order item information"""
    __tablename__ = "order_items"
    
    # References
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=True, index=True)
    
    # Product Information (snapshot at time of order)
    sku = Column(String(100), nullable=False, index=True)
    product_name = Column(String(500), nullable=False)
    variant_name = Column(String(200), nullable=True)
    
    # Pricing
    unit_price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    
    # Platform-specific information
    platform_item_id = Column(String(100), nullable=True, index=True)
    platform_sku = Column(String(100), nullable=True)
    
    # Product attributes at time of order
    product_attributes = Column(JSONB, nullable=True)
    
    # Status
    status = Column(String(50), default="pending", nullable=False)
    cancelled_quantity = Column(Integer, default=0, nullable=False)
    refunded_quantity = Column(Integer, default=0, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    variant = relationship("ProductVariant")
    
    def __repr__(self):
        return f"<OrderItem(sku={self.sku}, quantity={self.quantity})>"
    
    @property
    def fulfilled_quantity(self) -> int:
        """Calculate fulfilled quantity"""
        return self.quantity - self.cancelled_quantity - self.refunded_quantity


class OrderPayment(BaseModel):
    """Order payment information"""
    __tablename__ = "order_payments"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Payment Details
    payment_method = Column(String(50), nullable=False)  # card, bank_transfer, etc.
    payment_gateway = Column(String(50), nullable=True)  # PayPal, Stripe, etc.
    transaction_id = Column(String(100), nullable=True, index=True)
    
    # Amounts
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="KRW", nullable=False)
    
    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    payment_date = Column(DateTime, nullable=True)
    authorized_at = Column(DateTime, nullable=True)
    captured_at = Column(DateTime, nullable=True)
    
    # Additional Information
    gateway_response = Column(JSONB, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="payments")
    
    def __repr__(self):
        return f"<OrderPayment(transaction_id={self.transaction_id}, amount={self.amount})>"


class OrderShipment(BaseModel):
    """Order shipment information"""
    __tablename__ = "order_shipments"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Shipment Details
    shipment_number = Column(String(50), unique=True, nullable=False, index=True)
    carrier = Column(String(100), nullable=False)
    service_type = Column(String(100), nullable=True)  # Express, Standard, etc.
    tracking_number = Column(String(100), nullable=True, index=True)
    
    # Status
    status = Column(SQLEnum(ShippingStatus), default=ShippingStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    shipped_at = Column(DateTime, nullable=True, index=True)
    estimated_delivery = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True, index=True)
    
    # Costs
    shipping_cost = Column(Numeric(10, 2), nullable=True)
    insurance_cost = Column(Numeric(10, 2), nullable=True)
    
    # Package Information
    weight = Column(Numeric(8, 3), nullable=True)
    dimensions = Column(JSONB, nullable=True)  # length, width, height
    package_count = Column(Integer, default=1, nullable=False)
    
    # Tracking Information
    tracking_events = Column(JSONB, nullable=True)  # Array of tracking events
    
    # Relationships
    order = relationship("Order", back_populates="shipments")
    shipment_items = relationship("OrderShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OrderShipment(shipment_number={self.shipment_number}, status={self.status.value})>"


class OrderShipmentItem(BaseModel):
    """Items included in a shipment"""
    __tablename__ = "order_shipment_items"
    
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("order_shipments.id"), nullable=False, index=True)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    shipment = relationship("OrderShipment", back_populates="shipment_items")
    order_item = relationship("OrderItem")
    
    def __repr__(self):
        return f"<OrderShipmentItem(shipment_id={self.shipment_id}, quantity={self.quantity})>"


class OrderStatusHistory(BaseModel):
    """Order status change history"""
    __tablename__ = "order_status_history"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Status Information
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    status_type = Column(String(20), nullable=False)  # order, payment, shipping
    
    # Change Information
    changed_by = Column(String(100), nullable=True)  # User who made the change
    change_reason = Column(Text, nullable=True)
    
    # Additional data
    status_data = Column(JSONB, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="status_history")
    
    def __repr__(self):
        return f"<OrderStatusHistory(order_id={self.order_id}, to_status={self.to_status})>"


class SupplierOrderStatus(enum.Enum):
    """공급업체 주문 상태"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"
    OUT_OF_STOCK = "out_of_stock"


class DropshippingOrder(BaseModel):
    """드롭쉬핑 주문 정보"""
    __tablename__ = "dropshipping_orders"
    
    # 원본 고객 주문 참조
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True, unique=True)
    
    # 공급업체 정보
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("wholesalers.id"), nullable=False, index=True)
    supplier_order_id = Column(String(100), nullable=True, index=True)  # 공급업체에서 발급한 주문 ID
    
    # 마진 정보
    customer_price = Column(Numeric(12, 2), nullable=False)  # 고객 판매가
    supplier_price = Column(Numeric(12, 2), nullable=False)  # 공급업체 구매가
    margin_amount = Column(Numeric(12, 2), nullable=False)   # 마진 금액
    margin_rate = Column(Numeric(5, 2), nullable=False)      # 마진율 (%)
    minimum_margin_rate = Column(Numeric(5, 2), nullable=False, default=10.0)  # 최소 마진율
    
    # 자동 처리 설정
    auto_order_enabled = Column(Boolean, default=True, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retry_count = Column(Integer, default=3, nullable=False)
    
    # 상태 및 시간 정보
    status = Column(SQLEnum(SupplierOrderStatus), default=SupplierOrderStatus.PENDING, nullable=False, index=True)
    supplier_order_date = Column(DateTime, nullable=True)
    supplier_confirmed_at = Column(DateTime, nullable=True)
    supplier_shipped_at = Column(DateTime, nullable=True)
    
    # 배송 정보
    supplier_tracking_number = Column(String(100), nullable=True, index=True)
    supplier_carrier = Column(String(100), nullable=True)
    estimated_delivery_date = Column(DateTime, nullable=True)
    
    # 오류 및 예외 처리
    last_error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)  # 수동 처리 필요
    blocked_reason = Column(Text, nullable=True)
    
    # 추가 정보
    supplier_response_data = Column(JSONB, nullable=True)  # 공급업체 API 응답 데이터
    processing_notes = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order", backref="dropshipping_order")
    supplier = relationship("Wholesaler")
    processing_logs = relationship("DropshippingOrderLog", back_populates="dropshipping_order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DropshippingOrder(order_id={self.order_id}, status={self.status.value})>"
    
    @property
    def is_profitable(self) -> bool:
        """최소 마진율 충족 확인"""
        return self.margin_rate >= self.minimum_margin_rate
    
    @property
    def can_retry(self) -> bool:
        """재시도 가능 여부 확인"""
        return self.retry_count < self.max_retry_count and not self.is_blocked


class DropshippingOrderLog(BaseModel):
    """드롭쉬핑 주문 처리 로그"""
    __tablename__ = "dropshipping_order_logs"
    
    dropshipping_order_id = Column(UUID(as_uuid=True), ForeignKey("dropshipping_orders.id"), nullable=False, index=True)
    
    # 로그 정보
    action = Column(String(50), nullable=False)  # submit_order, check_status, etc.
    status_before = Column(String(50), nullable=True)
    status_after = Column(String(50), nullable=True)
    
    # 결과 정보
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSONB, nullable=True)
    
    # 처리 시간
    processing_time_ms = Column(Integer, nullable=True)
    
    # 추가 정보
    user_agent = Column(String(200), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationships
    dropshipping_order = relationship("DropshippingOrder", back_populates="processing_logs")
    
    def __repr__(self):
        return f"<DropshippingOrderLog(action={self.action}, success={self.success})>"


class MarginProtectionRule(BaseModel):
    """마진 보호 규칙"""
    __tablename__ = "margin_protection_rules"
    
    # 규칙 정보
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 적용 범위
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("wholesalers.id"), nullable=True, index=True)
    product_category = Column(String(100), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True)
    
    # 마진 규칙
    minimum_margin_rate = Column(Numeric(5, 2), nullable=False)  # 최소 마진율
    maximum_margin_rate = Column(Numeric(5, 2), nullable=True)   # 최대 마진율
    
    # 가격 변동 대응
    max_price_increase_rate = Column(Numeric(5, 2), default=5.0, nullable=False)  # 허용 가격 인상률
    auto_adjust_price = Column(Boolean, default=False, nullable=False)  # 자동 가격 조정
    
    # 활성화 상태
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)  # 규칙 우선순위
    
    # 적용 조건
    min_order_amount = Column(Numeric(12, 2), nullable=True)
    max_order_amount = Column(Numeric(12, 2), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    
    # Relationships
    supplier = relationship("Wholesaler")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<MarginProtectionRule(name={self.name}, minimum_margin_rate={self.minimum_margin_rate})>"