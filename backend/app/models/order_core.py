"""
Core order models for Phase 1 - Essential functionality only
All dropshipping and advanced features will be added in Phase 2
"""
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import BaseModel, get_json_type


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
    platform_order_id = Column(String(100), nullable=False, index=True)
    
    # Order Details
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Customer Information
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_id = Column(String(100), nullable=True, index=True)
    
    # Shipping Address
    shipping_name = Column(String(100), nullable=True)
    shipping_address1 = Column(String(200), nullable=False)
    shipping_address2 = Column(String(200), nullable=True)
    shipping_city = Column(String(100), nullable=False)
    shipping_state = Column(String(100), nullable=True)
    shipping_postal_code = Column(String(20), nullable=True)
    shipping_country = Column(String(2), default="KR", nullable=False)
    
    # Financial Information
    currency = Column(String(3), default="KRW", nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0, nullable=False)
    shipping_cost = Column(Numeric(12, 2), default=0, nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Status Information
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    shipping_status = Column(SQLEnum(ShippingStatus), default=ShippingStatus.PENDING, nullable=False, index=True)
    
    # Platform-specific data
    platform_data = Column(get_json_type(), nullable=True)
    
    # Relationships
    platform_account = relationship("PlatformAccount", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(order_number={self.order_number}, status={self.status.value})>"


class OrderItem(BaseModel):
    """Order item information"""
    __tablename__ = "order_items"
    
    # References
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True)
    
    # Product Information
    sku = Column(String(100), nullable=False, index=True)
    product_name = Column(String(500), nullable=False)
    
    # Pricing
    unit_price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    
    # Status
    status = Column(String(50), default="pending", nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(sku={self.sku}, quantity={self.quantity})>"


class OrderPayment(BaseModel):
    """Order payment information"""
    __tablename__ = "order_payments"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Payment Details
    payment_method = Column(String(50), nullable=False)
    transaction_id = Column(String(100), nullable=True, index=True)
    
    # Amounts
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="KRW", nullable=False)
    
    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    payment_date = Column(DateTime, nullable=True)
    
    # Relationships
    order = relationship("Order")
    
    def __repr__(self):
        return f"<OrderPayment(transaction_id={self.transaction_id}, amount={self.amount})>"


class OrderShipment(BaseModel):
    """Order shipment information"""
    __tablename__ = "order_shipments"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Shipment Details
    shipment_number = Column(String(50), unique=True, nullable=False, index=True)
    carrier = Column(String(100), nullable=False)
    tracking_number = Column(String(100), nullable=True, index=True)
    
    # Status
    status = Column(SQLEnum(ShippingStatus), default=ShippingStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    shipped_at = Column(DateTime, nullable=True, index=True)
    delivered_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    order = relationship("Order")
    
    def __repr__(self):
        return f"<OrderShipment(shipment_number={self.shipment_number}, status={self.status.value})>"


class OrderShipmentItem(BaseModel):
    """Items included in a shipment"""
    __tablename__ = "order_shipment_items"
    
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("order_shipments.id"), nullable=False, index=True)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    shipment = relationship("OrderShipment")
    order_item = relationship("OrderItem")


class OrderStatusHistory(BaseModel):
    """Order status change history"""
    __tablename__ = "order_status_history"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    changed_by = Column(String(100), nullable=True)
    
    # Relationships
    order = relationship("Order")
    
    def __repr__(self):
        return f"<OrderStatusHistory(order_id={self.order_id}, to_status={self.to_status})>"