"""
주문 관련 Pydantic 스키마
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID

from app.models.order_core import OrderStatus


class OrderItemBase(BaseModel):
    """주문 아이템 기본 스키마"""
    product_id: int
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=0)


class OrderItemCreate(OrderItemBase):
    """주문 아이템 생성 스키마"""
    pass


class OrderItemUpdate(BaseModel):
    """주문 아이템 수정 스키마"""
    quantity: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, gt=0)


class OrderItemResponse(OrderItemBase):
    """주문 아이템 응답 스키마"""
    id: int
    product_name: str
    product_sku: Optional[str]
    subtotal: Decimal
    
    class Config:
        from_attributes = True


class CustomerInfo(BaseModel):
    """고객 정보 스키마"""
    name: str
    phone: str
    email: Optional[str] = None
    address: str
    memo: Optional[str] = None


class OrderBase(BaseModel):
    """주문 기본 스키마"""
    platform_type: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    shipping_address: str
    customer_memo: Optional[str] = None
    shipping_fee: Decimal = Decimal("0")


class OrderCreate(OrderBase):
    """주문 생성 스키마"""
    items: List[OrderItemCreate]
    platform_order_id: str


class OrderUpdate(BaseModel):
    """주문 수정 스키마"""
    status: Optional[OrderStatus] = None
    tracking_number: Optional[str] = None
    courier: Optional[str] = None
    internal_memo: Optional[str] = None


class OrderResponse(OrderBase):
    """주문 응답 스키마"""
    id: int
    order_number: str
    status: str
    customer: CustomerInfo
    items: List[OrderItemResponse]
    total_amount: Decimal
    tracking_number: Optional[str] = None
    wholesaler_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    internal_memo: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    """주문 목록 아이템 스키마"""
    id: int
    order_number: str
    platform: str
    customer_name: str
    customer_phone: str
    total_amount: Decimal
    status: str
    tracking_number: Optional[str] = None
    created_at: str
    items_count: int


class OrderListResponse(BaseModel):
    """주문 목록 응답 스키마"""
    items: List[OrderListItem]
    total: int
    page: int
    page_size: int
    pages: int


class OrderSyncResult(BaseModel):
    """주문 동기화 결과 스키마"""
    synced_count: int
    errors: List[Dict[str, Any]]
    started_at: datetime
    completed_at: datetime


class OrderProcessingResult(BaseModel):
    """주문 처리 결과 스키마"""
    order_id: int
    status: str
    wholesaler_order_id: Optional[str] = None
    error_message: Optional[str] = None