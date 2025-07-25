"""
상품가공 시스템을 위한 데이터베이스 모델

이 모듈은 상품가공 프로세스에 필요한 모든 데이터 모델을 정의합니다.
- 상품가공 이력 관리
- 베스트셀러 패턴 분석
- 이미지 가공 이력
- 마켓별 가이드라인
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, JSON, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class ProductProcessingHistory(Base):
    """상품가공 이력 테이블"""
    __tablename__ = "product_processing_history"

    id = Column(Integer, primary_key=True, index=True)
    original_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    processed_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    processing_type = Column(String(50), nullable=False)  # name_change, image_process, purpose_change
    original_data = Column(JSON, nullable=False)
    processed_data = Column(JSON, nullable=False)
    ai_model_used = Column(String(100), nullable=False)
    processing_cost = Column(DECIMAL(10, 4), nullable=False, default=0.0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    original_product = relationship("Product", foreign_keys=[original_product_id])
    processed_product = relationship("Product", foreign_keys=[processed_product_id])


class BestsellerPattern(Base):
    """베스트셀러 패턴 분석 테이블"""
    __tablename__ = "bestseller_patterns"

    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(50), nullable=False)  # coupang, naver, 11st
    category = Column(String(100), nullable=False)
    pattern_type = Column(String(50), nullable=False)  # name_structure, keyword_usage, etc
    pattern_data = Column(JSON, nullable=False)
    effectiveness_score = Column(Float, nullable=False, default=0.0)
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    last_analyzed = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ImageProcessingHistory(Base):
    """이미지 가공 이력 테이블"""
    __tablename__ = "image_processing_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    original_image_url = Column(Text, nullable=False)
    processed_image_url = Column(Text, nullable=True)
    processing_steps = Column(JSON, nullable=False)
    market_specifications = Column(JSON, nullable=False)
    supabase_path = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    image_quality_score = Column(Float, nullable=True)
    compression_ratio = Column(Float, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="image_processing_history")


class MarketGuideline(Base):
    """마켓별 가이드라인 테이블"""
    __tablename__ = "market_guidelines"

    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(50), nullable=False, unique=True)
    image_specs = Column(JSON, nullable=False)  # 이미지 규격
    naming_rules = Column(JSON, nullable=False)  # 상품명 규칙
    description_rules = Column(JSON, nullable=False)  # 설명 규칙
    prohibited_keywords = Column(JSON, nullable=True)  # 금지 키워드
    required_fields = Column(JSON, nullable=True)  # 필수 필드
    guidelines_version = Column(String(20), nullable=False, default="1.0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProductNameGeneration(Base):
    """상품명 생성 이력 테이블"""
    __tablename__ = "product_name_generation"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    original_name = Column(Text, nullable=False)
    generated_names = Column(JSON, nullable=False)  # 생성된 후보 상품명들
    selected_name = Column(Text, nullable=True)
    marketplace = Column(String(50), nullable=False)
    generation_strategy = Column(String(100), nullable=False)  # bestseller_pattern, ai_creative, etc
    ai_model_used = Column(String(100), nullable=False)
    generation_cost = Column(DECIMAL(10, 4), nullable=False, default=0.0)
    effectiveness_score = Column(Float, nullable=True)  # 실제 성과 분석 결과
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="name_generations")


class ProductPurposeAnalysis(Base):
    """상품 용도 분석 테이블"""
    __tablename__ = "product_purpose_analysis"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    original_purpose = Column(Text, nullable=False)
    alternative_purposes = Column(JSON, nullable=False)  # 대체 용도들
    selected_purpose = Column(Text, nullable=True)
    target_audience = Column(JSON, nullable=True)  # 타겟 고객층
    market_opportunity = Column(JSON, nullable=True)  # 시장 기회 분석
    competition_level = Column(String(20), nullable=True)  # low, medium, high
    ai_model_used = Column(String(100), nullable=False)
    analysis_cost = Column(DECIMAL(10, 4), nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="purpose_analyses")


class ProcessingCostTracking(Base):
    """가공 비용 추적 테이블"""
    __tablename__ = "processing_cost_tracking"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    processing_type = Column(String(50), nullable=False)
    ai_model = Column(String(100), nullable=False)
    total_requests = Column(Integer, nullable=False, default=0)
    total_cost = Column(DECIMAL(10, 4), nullable=False, default=0.0)
    average_cost_per_request = Column(DECIMAL(10, 4), nullable=False, default=0.0)
    cost_optimization_used = Column(Boolean, default=False)  # 야간 로컬 모델 사용 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorAnalysis(Base):
    """경쟁사 분석 테이블"""
    __tablename__ = "competitor_analysis"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    marketplace = Column(String(50), nullable=False)
    competitor_products = Column(JSON, nullable=False)  # 경쟁 상품 정보
    price_analysis = Column(JSON, nullable=True)  # 가격 분석
    naming_patterns = Column(JSON, nullable=True)  # 네이밍 패턴 분석
    image_strategies = Column(JSON, nullable=True)  # 이미지 전략 분석
    market_gap_opportunities = Column(JSON, nullable=True)  # 시장 틈새 기회
    competitive_advantage = Column(JSON, nullable=True)  # 경쟁 우위 요소
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="competitor_analyses")