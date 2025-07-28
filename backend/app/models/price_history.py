"""
가격 이력 모델
상품의 가격 변경 이력을 추적
"""
from sqlalchemy import Column, Integer, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class PriceHistory(BaseModel):
    """가격 이력 모델"""
    __tablename__ = "price_histories"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    previous_price = Column(Numeric(10, 2))
    change_reason = Column(String(200))
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    product = relationship("Product", backref="price_history")
    user = relationship("User")