"""
수집된 상품의 가격 및 재고 변동 이력 추적 모델
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Integer, Numeric, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel
from .collected_product import WholesalerSource


class ChangeType(enum.Enum):
    """변경 유형"""
    PRICE_CHANGE = "price_change"          # 가격 변경
    STOCK_CHANGE = "stock_change"          # 재고 변경
    STATUS_CHANGE = "status_change"        # 상태 변경
    INFO_UPDATE = "info_update"            # 정보 업데이트
    NEW_COLLECTION = "new_collection"      # 신규 수집


class CollectedProductHistory(BaseModel):
    """수집된 상품 변경 이력"""
    __tablename__ = "collected_product_histories"
    
    # 관계
    collected_product_id = Column(UUID(as_uuid=True), ForeignKey("collected_products.id", ondelete="CASCADE"), nullable=False, index=True)
    collected_product = relationship("CollectedProduct", backref="change_history")
    
    # 도매처 정보
    source = Column(SQLEnum(WholesalerSource), nullable=False, index=True)
    supplier_id = Column(String(100), nullable=False, index=True)
    
    # 변경 정보
    change_type = Column(SQLEnum(ChangeType), nullable=False, index=True)
    change_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 가격 변경 정보
    old_price = Column(Numeric(12, 2), nullable=True)
    new_price = Column(Numeric(12, 2), nullable=True)
    price_change_amount = Column(Numeric(12, 2), nullable=True)  # 가격 변화량
    price_change_percentage = Column(Numeric(5, 2), nullable=True)  # 가격 변화율 (%)
    
    # 재고 변경 정보
    old_stock_quantity = Column(Integer, nullable=True)
    new_stock_quantity = Column(Integer, nullable=True)
    old_stock_status = Column(String(50), nullable=True)
    new_stock_status = Column(String(50), nullable=True)
    
    # 상태 변경 정보
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    
    # 추가 변경 정보
    changes_summary = Column(JSONB, nullable=True)  # 모든 변경사항 요약
    batch_id = Column(String(100), nullable=True, index=True)  # 수집 배치 ID
    
    def __repr__(self):
        return f"<CollectedProductHistory(id={self.id}, type={self.change_type.value}, product={self.supplier_id})>"
    
    @property
    def is_significant_price_change(self) -> bool:
        """중요한 가격 변경인지 확인 (5% 이상)"""
        if self.price_change_percentage and abs(self.price_change_percentage) >= 5:
            return True
        return False
    
    @property
    def is_out_of_stock(self) -> bool:
        """재고 소진 변경인지 확인"""
        return (self.old_stock_status == "available" and 
                self.new_stock_status == "out_of_stock")
    
    @property
    def is_back_in_stock(self) -> bool:
        """재입고 변경인지 확인"""
        return (self.old_stock_status == "out_of_stock" and 
                self.new_stock_status == "available")


class PriceAlert(BaseModel):
    """가격 알림 설정"""
    __tablename__ = "price_alerts"
    
    # 사용자 관계
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", backref="price_alerts")
    
    # 수집된 상품 관계
    collected_product_id = Column(UUID(as_uuid=True), ForeignKey("collected_products.id", ondelete="CASCADE"), nullable=False, index=True)
    collected_product = relationship("CollectedProduct", backref="price_alerts")
    
    # 알림 조건
    alert_type = Column(String(50), nullable=False)  # price_drop, price_increase, back_in_stock
    threshold_percentage = Column(Numeric(5, 2), nullable=True)  # 가격 변동 임계값 (%)
    threshold_amount = Column(Numeric(12, 2), nullable=True)  # 가격 변동 임계값 (금액)
    target_price = Column(Numeric(12, 2), nullable=True)  # 목표 가격
    
    # 알림 설정
    is_active = Column(Boolean, default=True, nullable=False)
    notification_method = Column(String(50), default="email", nullable=False)  # email, push, sms
    
    # 알림 이력
    last_alerted_at = Column(DateTime, nullable=True)
    alert_count = Column(Integer, default=0, nullable=False)
    
    # 메타데이터
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # 알림 만료일
    
    def __repr__(self):
        return f"<PriceAlert(id={self.id}, type={self.alert_type}, product={self.collected_product_id})>"
    
    @property
    def is_expired(self) -> bool:
        """알림이 만료되었는지 확인"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False