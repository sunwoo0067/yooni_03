"""
Order automation and processing models
주문 처리 자동화 관련 모델들
"""
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from .base import BaseModel


class WholesaleOrderStatus(enum.Enum):
    """도매 주문 상태"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"
    OUT_OF_STOCK = "out_of_stock"
    PARTIAL_SHIPPED = "partial_shipped"


class ShippingTrackingStatus(enum.Enum):
    """배송 추적 상태"""
    PENDING = "pending"
    COLLECTED = "collected"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    RETURNED = "returned"
    EXCEPTION = "exception"


class SettlementStatus(enum.Enum):
    """정산 상태"""
    PENDING = "pending"
    CALCULATED = "calculated"
    APPROVED = "approved"
    COMPLETED = "completed"
    DISPUTED = "disputed"


class WholesaleOrder(BaseModel):
    """도매 발주 정보"""
    __tablename__ = "wholesale_orders"
    
    # 원본 주문 참조
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=True, index=True)
    
    # 도매업체 정보
    wholesaler_id = Column(UUID(as_uuid=True), ForeignKey("wholesalers.id"), nullable=False, index=True)
    wholesaler_order_id = Column(String(100), nullable=True, index=True)  # 도매업체 주문 ID
    
    # 주문 정보
    product_sku = Column(String(100), nullable=False, index=True)
    product_name = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # 상태 및 처리 정보
    status = Column(SQLEnum(WholesaleOrderStatus), default=WholesaleOrderStatus.PENDING, nullable=False, index=True)
    auto_order_enabled = Column(Boolean, default=True, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retry_count = Column(Integer, default=3, nullable=False)
    
    # 시간 정보
    ordered_at = Column(DateTime, nullable=True, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    estimated_delivery_date = Column(DateTime, nullable=True)
    
    # 배송 정보
    tracking_number = Column(String(100), nullable=True, index=True)
    carrier = Column(String(100), nullable=True)
    shipping_method = Column(String(100), nullable=True)
    
    # 오류 처리
    last_error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    is_manual_hold = Column(Boolean, default=False, nullable=False)
    hold_reason = Column(Text, nullable=True)
    
    # 추가 데이터
    wholesaler_response = Column(JSONB, nullable=True)
    processing_notes = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order")
    order_item = relationship("OrderItem")
    wholesaler = relationship("Wholesaler")
    tracking_history = relationship("ShippingTracking", back_populates="wholesale_order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WholesaleOrder(wholesaler_order_id={self.wholesaler_order_id}, status={self.status.value})>"
    
    @property
    def can_retry(self) -> bool:
        """재시도 가능 여부"""
        return (self.retry_count < self.max_retry_count and 
                not self.is_manual_hold and 
                self.status in [WholesaleOrderStatus.PENDING, WholesaleOrderStatus.FAILED])


class ShippingTracking(BaseModel):
    """배송 추적 정보"""
    __tablename__ = "shipping_tracking"
    
    # 도매 주문 참조
    wholesale_order_id = Column(UUID(as_uuid=True), ForeignKey("wholesale_orders.id"), nullable=False, index=True)
    
    # 추적 정보
    tracking_number = Column(String(100), nullable=False, index=True)
    carrier = Column(String(100), nullable=False)
    service_type = Column(String(50), nullable=True)
    
    # 상태 정보
    status = Column(SQLEnum(ShippingTrackingStatus), nullable=False, index=True)
    current_location = Column(String(200), nullable=True)
    last_scan_time = Column(DateTime, nullable=True, index=True)
    
    # 배송 정보
    origin_address = Column(JSONB, nullable=True)
    destination_address = Column(JSONB, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    actual_delivery = Column(DateTime, nullable=True, index=True)
    
    # 추적 이벤트 히스토리
    tracking_history = Column(JSONB, nullable=True)  # Array of tracking events
    
    # 업데이트 정보
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    update_frequency_minutes = Column(Integer, default=60, nullable=False)  # 업데이트 주기
    
    # 알림 정보
    customer_notified = Column(Boolean, default=False, nullable=False)
    notification_sent_at = Column(DateTime, nullable=True)
    
    # API 관련 정보
    tracking_api_response = Column(JSONB, nullable=True)
    api_error_count = Column(Integer, default=0, nullable=False)
    last_api_error = Column(Text, nullable=True)
    
    # Relationships
    wholesale_order = relationship("WholesaleOrder", back_populates="tracking_history")
    
    def __repr__(self):
        return f"<ShippingTracking(tracking_number={self.tracking_number}, status={self.status.value})>"
    
    @property
    def is_delivered(self) -> bool:
        """배송 완료 여부"""
        return self.status == ShippingTrackingStatus.DELIVERED
    
    @property
    def needs_update(self) -> bool:
        """업데이트 필요 여부"""
        if self.is_delivered:
            return False
        
        if not self.last_updated:
            return True
            
        time_diff = datetime.utcnow() - self.last_updated
        return time_diff.total_seconds() > (self.update_frequency_minutes * 60)


class Settlement(BaseModel):
    """정산 정보"""
    __tablename__ = "settlements"
    
    # 주문 참조
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True, unique=True)
    wholesale_order_id = Column(UUID(as_uuid=True), ForeignKey("wholesale_orders.id"), nullable=True, index=True)
    
    # 매출 정보
    customer_payment = Column(Numeric(12, 2), nullable=False)  # 고객 결제 금액
    marketplace_fee = Column(Numeric(12, 2), default=0, nullable=False)  # 마켓플레이스 수수료
    payment_gateway_fee = Column(Numeric(12, 2), default=0, nullable=False)  # 결제 수수료
    
    # 비용 정보
    wholesale_cost = Column(Numeric(12, 2), nullable=False)  # 도매 구매 비용
    shipping_cost = Column(Numeric(12, 2), default=0, nullable=False)  # 배송비
    packaging_cost = Column(Numeric(12, 2), default=0, nullable=False)  # 포장비
    other_costs = Column(Numeric(12, 2), default=0, nullable=False)  # 기타 비용
    
    # 수익 계산
    gross_revenue = Column(Numeric(12, 2), nullable=False)  # 총 매출
    total_costs = Column(Numeric(12, 2), nullable=False)    # 총 비용
    net_profit = Column(Numeric(12, 2), nullable=False)     # 순이익
    profit_margin = Column(Numeric(5, 2), nullable=False)   # 이익률 (%)
    
    # 세금 정보
    vat_amount = Column(Numeric(12, 2), default=0, nullable=False)  # 부가세
    income_tax = Column(Numeric(12, 2), default=0, nullable=False)  # 소득세
    
    # 정산 상태
    status = Column(SQLEnum(SettlementStatus), default=SettlementStatus.PENDING, nullable=False, index=True)
    settlement_date = Column(DateTime, nullable=True, index=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # 계산 상세 정보
    calculation_details = Column(JSONB, nullable=True)  # 상세 계산 내역
    cost_breakdown = Column(JSONB, nullable=True)       # 비용 세부 내역
    
    # 분쟁 및 조정
    dispute_reason = Column(Text, nullable=True)
    adjustment_amount = Column(Numeric(12, 2), default=0, nullable=False)
    adjustment_reason = Column(Text, nullable=True)
    
    # 시간 정보
    calculation_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    
    # Relationships
    order = relationship("Order")
    wholesale_order = relationship("WholesaleOrder")
    
    def __repr__(self):
        return f"<Settlement(order_id={self.order_id}, net_profit={self.net_profit})>"
    
    @property
    def is_profitable(self) -> bool:
        """수익성 여부"""
        return self.net_profit > 0
    
    @property
    def roi_percentage(self) -> float:
        """투자 수익률 (ROI) 계산"""
        if self.total_costs == 0:
            return 0.0
        return float((self.net_profit / self.total_costs) * 100)


class OrderProcessingRule(BaseModel):
    """주문 처리 규칙"""
    __tablename__ = "order_processing_rules"
    
    # 규칙 기본 정보
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(50), nullable=False)  # auto_order, margin_protection, inventory_check
    
    # 적용 범위
    marketplace = Column(String(50), nullable=True)  # 특정 마켓플레이스
    wholesaler_id = Column(UUID(as_uuid=True), ForeignKey("wholesalers.id"), nullable=True, index=True)
    product_category = Column(String(100), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True)
    
    # 조건 설정
    conditions = Column(JSONB, nullable=False)  # 규칙 적용 조건
    actions = Column(JSONB, nullable=False)     # 실행할 액션
    
    # 우선순위 및 활성화
    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 실행 통계
    execution_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    last_executed_at = Column(DateTime, nullable=True)
    
    # 유효 기간
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    
    # Relationships
    wholesaler = relationship("Wholesaler")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<OrderProcessingRule(name={self.name}, rule_type={self.rule_type})>"
    
    @property
    def is_valid(self) -> bool:
        """규칙 유효성 확인"""
        now = datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return self.is_active
    
    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100


class OrderProcessingLog(BaseModel):
    """주문 처리 로그"""
    __tablename__ = "order_processing_logs"
    
    # 주문 및 처리 정보
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    wholesale_order_id = Column(UUID(as_uuid=True), ForeignKey("wholesale_orders.id"), nullable=True, index=True)
    processing_rule_id = Column(UUID(as_uuid=True), ForeignKey("order_processing_rules.id"), nullable=True, index=True)
    
    # 처리 단계
    processing_step = Column(String(50), nullable=False, index=True)  # order_received, validation, auto_order, tracking, settlement
    action = Column(String(100), nullable=False)  # 수행된 액션
    
    # 결과 정보
    success = Column(Boolean, nullable=False, index=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 처리 시간
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # 입력/출력 데이터
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    
    # 시스템 정보
    processor_name = Column(String(100), nullable=True)  # 처리한 서비스/모듈명
    user_id = Column(String(100), nullable=True)  # 처리한 사용자 (수동 처리시)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(200), nullable=True)
    
    # Relationships
    order = relationship("Order")
    wholesale_order = relationship("WholesaleOrder")
    processing_rule = relationship("OrderProcessingRule")
    
    def __repr__(self):
        return f"<OrderProcessingLog(order_id={self.order_id}, action={self.action}, success={self.success})>"
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """처리 시간 (초)"""
        if self.processing_time_ms:
            return self.processing_time_ms / 1000
        return None


class ExceptionCase(BaseModel):
    """예외 상황 처리"""
    __tablename__ = "exception_cases"
    
    # 관련 주문
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    wholesale_order_id = Column(UUID(as_uuid=True), ForeignKey("wholesale_orders.id"), nullable=True, index=True)
    
    # 예외 정보
    exception_type = Column(String(50), nullable=False, index=True)  # out_of_stock, price_change, delivery_issue
    severity = Column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # 상태 정보
    status = Column(String(30), default="open", nullable=False, index=True)  # open, in_progress, resolved, closed
    assigned_to = Column(String(100), nullable=True)  # 담당자
    
    # 해결 정보
    resolution_action = Column(String(100), nullable=True)  # 해결 액션
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True, index=True)
    resolved_by = Column(String(100), nullable=True)
    
    # 자동 처리 시도
    auto_resolution_attempted = Column(Boolean, default=False, nullable=False)
    auto_resolution_success = Column(Boolean, default=False, nullable=False)
    auto_resolution_notes = Column(Text, nullable=True)
    
    # 고객 영향
    customer_notified = Column(Boolean, default=False, nullable=False)
    customer_notification_sent_at = Column(DateTime, nullable=True)
    customer_compensation_amount = Column(Numeric(12, 2), nullable=True)
    
    # 관련 데이터
    exception_data = Column(JSONB, nullable=True)  # 예외 상황 관련 데이터
    
    # 우선순위 (높을수록 우선)
    priority_score = Column(Integer, default=0, nullable=False, index=True)
    
    # Relationships
    order = relationship("Order")
    wholesale_order = relationship("WholesaleOrder")
    
    def __repr__(self):
        return f"<ExceptionCase(exception_type={self.exception_type}, status={self.status})>"
    
    @property
    def is_critical(self) -> bool:
        """긴급 처리 필요 여부"""
        return self.severity == "critical" or self.priority_score >= 90
    
    @property
    def days_open(self) -> int:
        """미해결 일수"""
        if self.resolved_at:
            return 0
        return (datetime.utcnow() - self.created_at).days