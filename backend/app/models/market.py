"""
마켓플레이스 및 시장 트렌드 모델
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class MarketTrend(Base):
    """시장 트렌드 모델"""
    __tablename__ = "market_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    platform = Column(String(50), nullable=True)
    search_volume = Column(Integer, default=0)
    growth_rate = Column(Float, default=0.0)  # 성장률 (%)
    competition_level = Column(String(20), default="medium")  # low, medium, high
    relevance_score = Column(Float, default=0.0)  # 관련성 점수 (0-1)
    trend_type = Column(String(50), default="general")  # general, seasonal, emerging
    data_source = Column(String(100), nullable=True)
    trend_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_trend_category_date', 'category', 'created_at'),
        Index('idx_trend_keyword_platform', 'keyword', 'platform'),
    )
    
    def __repr__(self):
        return f"<MarketTrend(keyword={self.keyword}, growth_rate={self.growth_rate})>"


class MarketProduct(Base):
    """마켓플레이스 상품 모델"""
    __tablename__ = "market_products"
    
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(50), nullable=False, index=True)  # coupang, naver, 11st
    product_id = Column(String(255), nullable=True, index=True)  # 마켓별 상품 ID
    category = Column(String(100), nullable=True, index=True)
    rank = Column(Integer, nullable=True, index=True)  # 베스트셀러 순위
    product_name = Column(Text, nullable=False)
    price = Column(Integer, default=0)
    original_price = Column(Integer, default=0)
    discount_rate = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    
    # 마켓별 추가 정보
    is_rocket = Column(Boolean, default=False)  # 쿠팡 로켓배송
    mall_count = Column(Integer, default=0)  # 네이버 판매처 수
    purchase_count = Column(Integer, default=0)  # 구매 수
    brand = Column(String(255), nullable=True)
    maker = Column(String(255), nullable=True)
    seller_grade = Column(String(50), nullable=True)
    delivery_type = Column(String(50), nullable=True)
    
    # 메타데이터
    raw_data = Column(JSON, nullable=True)  # 원본 데이터
    collected_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    sales_data = relationship("MarketSalesData", back_populates="market_product")
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_marketplace_category', 'marketplace', 'category'),
        Index('idx_marketplace_rank', 'marketplace', 'rank'),
        Index('idx_product_collected', 'product_id', 'collected_at'),
    )
    
    def __repr__(self):
        return f"<MarketProduct(marketplace={self.marketplace}, name={self.product_name[:50]})>"


class MarketSalesData(Base):
    """마켓 상품 판매 데이터 추적"""
    __tablename__ = "market_sales_data"
    
    id = Column(Integer, primary_key=True, index=True)
    market_product_id = Column(Integer, ForeignKey("market_products.id"), nullable=False, index=True)
    
    # 판매 지표
    estimated_monthly_sales = Column(Integer, default=0)
    price = Column(Integer, default=0)
    discount_rate = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    rank = Column(Integer, nullable=True)
    
    # 추적 데이터
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    market_product = relationship("MarketProduct", back_populates="sales_data")
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_product_recorded', 'market_product_id', 'recorded_at'),
    )
    
    def __repr__(self):
        return f"<MarketSalesData(product_id={self.market_product_id}, sales={self.estimated_monthly_sales})>"


class MarketCategory(Base):
    """마켓 카테고리 분석 데이터"""
    __tablename__ = "market_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(50), nullable=False, index=True)
    category_name = Column(String(100), nullable=False, index=True)
    category_id = Column(String(100), nullable=True)
    parent_category = Column(String(100), nullable=True)
    
    # 카테고리 통계
    total_products = Column(Integer, default=0)
    avg_price = Column(Float, default=0.0)
    avg_review_count = Column(Float, default=0.0)
    avg_rating = Column(Float, default=0.0)
    total_sales_volume = Column(Integer, default=0)
    
    # 시장 분석
    competition_level = Column(String(20), default="medium")  # low, medium, high
    growth_rate = Column(Float, default=0.0)  # 성장률 (%)
    market_saturation = Column(Float, default=0.0)  # 포화도 (0-1)
    entry_barrier = Column(String(20), default="medium")  # low, medium, high
    
    # 메타데이터
    analysis_data = Column(JSON, nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_marketplace_category_name', 'marketplace', 'category_name'),
        Index('idx_category_analyzed', 'category_name', 'analyzed_at'),
    )
    
    def __repr__(self):
        return f"<MarketCategory(marketplace={self.marketplace}, category={self.category_name})>"