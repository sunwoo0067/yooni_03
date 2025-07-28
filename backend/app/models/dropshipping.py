"""
드롭쉬핑 관련 데이터베이스 모델

품절 관리, 공급업체 신뢰도, 재입고 감지, 수익 보호, 예측 등
드롭쉬핑 운영에 필요한 모든 데이터 모델
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum

from .base import BaseModel, get_json_type


class OutOfStockHistory(BaseModel):
    """품절 이력"""
    __tablename__ = "outofstock_history"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    # wholesaler_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False)  # TEMPORARILY DISABLED
    
    # 품절 정보
    out_of_stock_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    restock_time = Column(DateTime, nullable=True)
    duration_hours = Column(Numeric(8, 2), nullable=True)
    
    # 처리 정보
    action_taken = Column(String(50), nullable=True)  # deactivate, hide, delete, replace
    alternative_suggested = Column(Boolean, default=False)
    estimated_lost_sales = Column(Numeric(12, 2), default=0.0)
    
    # 관계
    # product = relationship("Product", back_populates="outofstock_history")  # TEMPORARILY DISABLED - Product model doesn't have this relationship yet
    # wholesaler = relationship("Wholesaler", back_populates="outofstock_history")  # TEMPORARILY DISABLED


class SupplierReliability(BaseModel):
    """공급업체 신뢰도"""
    __tablename__ = "supplier_reliability"

    # supplier_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False, unique=True, index=True)  # TEMPORARILY DISABLED
    
    # 신뢰도 지표
    outofstock_rate = Column(Numeric(5, 2), default=0.0)  # 품절률 (%)
    avg_outofstock_duration = Column(Numeric(8, 2), default=0.0)  # 평균 품절 지속시간 (시간)
    response_time_avg = Column(Numeric(10, 2), default=0.0)  # 평균 응답시간 (ms)
    restock_speed_avg = Column(Numeric(8, 2), default=0.0)  # 평균 재입고 속도 (시간)
    price_stability = Column(Numeric(5, 2), default=100.0)  # 가격 안정성 (%)
    
    # 종합 점수
    reliability_score = Column(Numeric(5, 2), default=0.0)  # 신뢰도 점수 (0-100)
    grade = Column(String(20), default="unknown")  # excellent, good, average, poor, very_poor
    risk_level = Column(String(20), default="unknown")  # 위험 수준
    
    # 분석 정보
    last_analyzed = Column(DateTime, default=datetime.utcnow)
    analysis_period_days = Column(Numeric(3, 0), default=90)
    
    # 관계
    # supplier = relationship("Wholesaler", back_populates="reliability")  # TEMPORARILY DISABLED


class RestockHistory(BaseModel):
    """재입고 이력"""
    __tablename__ = "restock_history"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 재고 정보
    previous_stock = Column(Numeric(10, 0), default=0)
    current_stock = Column(Numeric(10, 0), nullable=False)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 가격 정보
    wholesale_price_before = Column(Numeric(12, 2), nullable=True)
    wholesale_price_after = Column(Numeric(12, 2), nullable=True)
    price_change_rate = Column(Numeric(6, 4), default=0.0)
    
    # 결정 정보
    decision = Column(String(50), nullable=False)  # auto_reactivate, manual_review, price_changed, etc.
    auto_reactivated = Column(Boolean, default=False)
    review_required = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)
    
    # 관계
    product = relationship("Product", back_populates="restock_history")


class StockCheckLog(BaseModel):
    """재고 체크 로그"""
    __tablename__ = "stock_check_log"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    # wholesaler_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False)  # TEMPORARILY DISABLED
    
    # 체크 결과
    previous_stock = Column(Numeric(10, 0), default=0)
    current_stock = Column(Numeric(10, 0), nullable=False)
    status = Column(String(20), nullable=False)  # in_stock, low_stock, out_of_stock, unknown
    status_changed = Column(Boolean, default=False)
    
    # 성능 정보
    check_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    response_time_ms = Column(Numeric(8, 2), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 관계
    product = relationship("Product", back_populates="stock_check_logs")
    # wholesaler = relationship("Wholesaler", back_populates="stock_check_logs")  # TEMPORARILY DISABLED


class PriceHistory(BaseModel):
    """가격 변동 이력"""
    __tablename__ = "price_history"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    # wholesaler_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False)  # TEMPORARILY DISABLED
    
    # 가격 정보
    price = Column(Numeric(12, 2), nullable=False)
    price_type = Column(String(20), default="wholesale")  # wholesale, selling
    previous_price = Column(Numeric(12, 2), nullable=True)
    change_rate = Column(Numeric(6, 4), default=0.0)
    
    # 메타데이터
    recorded_at = Column(DateTime, default=datetime.utcnow)
    recorded_by = Column(String(50), default="system")  # system, manual, api
    
    # 관계
    product = relationship("Product", back_populates="price_history")
    # wholesaler = relationship("Wholesaler", back_populates="price_history")  # TEMPORARILY DISABLED


class ProfitProtectionLog(BaseModel):
    """수익 보호 로그"""
    __tablename__ = "profit_protection_log"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 수익 분석 결과
    current_margin = Column(Numeric(6, 4), nullable=False)
    target_margin = Column(Numeric(6, 4), nullable=False)
    margin_gap = Column(Numeric(6, 4), default=0.0)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # 시장 정보
    competitor_price_avg = Column(Numeric(12, 2), nullable=True)
    market_position = Column(String(20), nullable=True)  # 저가, 경쟁적, 고가
    
    # 조치 정보
    recommended_action = Column(Text, nullable=True)
    action_taken = Column(Boolean, default=False)
    estimated_loss_per_day = Column(Numeric(12, 2), default=0.0)
    
    # 메타데이터
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    product = relationship("Product", back_populates="profit_protection_logs")


class StockoutPredictionHistory(BaseModel):
    """품절 예측 이력"""
    __tablename__ = "stockout_prediction_history"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 현재 상태
    current_stock = Column(Numeric(10, 0), nullable=False)
    
    # 예측 결과
    predicted_stockout_date = Column(DateTime, nullable=True)
    days_until_stockout = Column(Numeric(5, 0), nullable=True)
    confidence_level = Column(String(20), nullable=False)  # very_high, high, medium, low, very_low
    confidence_score = Column(Numeric(5, 4), default=0.0)
    
    # 예측 정보
    predicted_by = Column(String(100), nullable=False)  # 예측 모델명
    risk_level = Column(String(20), nullable=True)  # 위험 수준
    factors = Column(get_json_type(), nullable=True)  # JSON 형태의 영향 요인
    recommendations = Column(get_json_type(), nullable=True)  # JSON 형태의 권장사항
    
    # 메타데이터
    predicted_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    product = relationship("Product", back_populates="stockout_predictions")


class DemandAnalysisHistory(BaseModel):
    """수요 분석 이력"""
    __tablename__ = "demand_analysis_history"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 수요 분석 결과
    demand_score = Column(Numeric(5, 2), default=0.0)  # 현재 수요 점수 (0-100)
    trend = Column(String(20), nullable=False)  # increasing, stable, decreasing, volatile
    
    # 패턴 분석
    weekly_pattern = Column(get_json_type(), nullable=True)  # JSON 형태의 요일별 패턴
    monthly_pattern = Column(get_json_type(), nullable=True)  # JSON 형태의 월별 패턴
    seasonal_index = Column(Numeric(5, 4), default=1.0)  # 계절성 지수
    
    # 탄력성 및 변동성
    price_elasticity = Column(Numeric(6, 4), default=-1.0)  # 가격 탄력성
    demand_volatility = Column(Numeric(6, 4), default=0.0)  # 수요 변동성
    growth_rate = Column(Numeric(6, 4), default=0.0)  # 수요 성장률 (%)
    
    # 분석 결과
    peak_demand_period = Column(String(50), nullable=True)  # 피크 수요 시기
    recommendations = Column(get_json_type(), nullable=True)  # JSON 형태의 권장사항
    
    # 메타데이터
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_period_days = Column(Numeric(3, 0), default=90)
    
    # 관계
    product = relationship("Product", back_populates="demand_analyses")


class AutomationRule(BaseModel):
    """자동화 규칙"""
    __tablename__ = "automation_rules"

    # 규칙 정보
    rule_id = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 조건 및 액션
    condition = Column(Text, nullable=False)  # 조건식
    action = Column(String(50), nullable=False)  # activate, deactivate, update_price, etc.
    parameters = Column(get_json_type(), nullable=True)  # 액션 파라미터
    
    # 설정
    is_active = Column(Boolean, default=True)
    priority = Column(Numeric(2, 0), default=5)  # 우선순위 (1이 가장 높음)
    
    # 통계
    execution_count = Column(Numeric(10, 0), default=0)
    success_count = Column(Numeric(10, 0), default=0)
    last_executed = Column(DateTime, nullable=True)
    
    # 메타데이터
    created_by = Column(String(50), default="system")


class AutomationExecution(BaseModel):
    """자동화 실행 이력"""
    __tablename__ = "automation_executions"

    rule_id = Column(String(50), ForeignKey("automation_rules.rule_id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 실행 정보
    action_taken = Column(String(50), nullable=False)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    # 실행 결과
    before_state = Column(get_json_type(), nullable=True)  # 실행 전 상태
    after_state = Column(get_json_type(), nullable=True)   # 실행 후 상태
    
    # 메타데이터
    executed_at = Column(DateTime, default=datetime.utcnow)
    execution_time_ms = Column(Numeric(8, 2), nullable=True)
    
    # 관계
    automation_rule = relationship("AutomationRule")
    product = relationship("Product", back_populates="automation_executions")


class AlternativeRecommendation(BaseModel):
    """대체 상품 추천 이력"""
    __tablename__ = "alternative_recommendations"

    original_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    alternative_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 추천 정보
    similarity_score = Column(Numeric(5, 4), default=0.0)
    alternative_type = Column(String(30), nullable=False)  # same_supplier, different_supplier, etc.
    recommendation_reason = Column(Text, nullable=True)
    
    # 성과 정보
    click_count = Column(Numeric(10, 0), default=0)
    conversion_count = Column(Numeric(10, 0), default=0)
    conversion_rate = Column(Numeric(5, 4), default=0.0)
    
    # 메타데이터
    recommended_at = Column(DateTime, default=datetime.utcnow)
    last_clicked = Column(DateTime, nullable=True)
    
    # 관계
    original_product = relationship("Product", foreign_keys=[original_product_id])
    alternative_product = relationship("Product", foreign_keys=[alternative_product_id])


class DropshippingSettings(BaseModel):
    """드롭쉬핑 설정"""
    __tablename__ = "dropshipping_settings"

    # 모니터링 설정
    monitoring_enabled = Column(Boolean, default=True)
    check_interval_seconds = Column(Numeric(8, 0), default=600)  # 10분
    low_stock_threshold = Column(Numeric(6, 0), default=10)
    
    # 자동화 설정
    automation_enabled = Column(Boolean, default=True)
    auto_deactivate_on_stockout = Column(Boolean, default=True)
    auto_reactivate_on_restock = Column(Boolean, default=True)
    price_change_threshold = Column(Numeric(5, 4), default=0.05)  # 5%
    
    # 수익 보호 설정
    profit_protection_enabled = Column(Boolean, default=True)
    min_margin_rate = Column(Numeric(5, 4), default=0.15)  # 15%
    target_margin_rate = Column(Numeric(5, 4), default=0.25)  # 25%
    max_price_adjustment = Column(Numeric(5, 4), default=0.10)  # 10%
    
    # 예측 설정
    prediction_enabled = Column(Boolean, default=True)
    prediction_horizon_days = Column(Numeric(3, 0), default=30)
    high_risk_threshold_days = Column(Numeric(2, 0), default=7)
    
    # 알림 설정
    notification_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    slack_notifications = Column(Boolean, default=False)
    critical_alerts_only = Column(Boolean, default=False)
    
    # 메타데이터
    updated_by = Column(String(50), default="system")


class DuplicateProductGroup(BaseModel):
    """중복 상품 그룹"""
    __tablename__ = "duplicate_product_groups"

    # 그룹 정보
    group_id = Column(String(50), nullable=False, unique=True, index=True)
    representative_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    product_count = Column(Numeric(6, 0), default=1)
    
    # 분석 정보
    similarity_threshold = Column(Numeric(5, 4), default=0.8)
    analysis_method = Column(String(50), default="tfidf")
    
    # 가격 정보
    min_price = Column(Numeric(12, 2), nullable=True)
    max_price = Column(Numeric(12, 2), nullable=True)
    best_deal_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    potential_savings = Column(Numeric(12, 2), default=0.0)
    
    # 관계
    representative_product = relationship("Product", foreign_keys=[representative_product_id])
    best_deal_product = relationship("Product", foreign_keys=[best_deal_product_id])
    duplicate_products = relationship("DuplicateProduct", back_populates="group")


class DuplicateProduct(BaseModel):
    """중복 상품"""
    __tablename__ = "duplicate_products"

    group_id = Column(String(50), ForeignKey("duplicate_product_groups.group_id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # 유사도 정보
    similarity_score = Column(Numeric(5, 4), default=0.0)
    match_type = Column(String(30), default="name")  # name, keywords, model, sku
    
    # 가격 비교
    price_difference = Column(Numeric(12, 2), default=0.0)
    is_best_deal = Column(Boolean, default=False)
    savings_amount = Column(Numeric(12, 2), default=0.0)
    
    # 메타데이터
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    group = relationship("DuplicateProductGroup", back_populates="duplicate_products")
    product = relationship("Product")


# Product 모델에 새로운 관계 추가를 위한 백레퍼런스 정의
# (실제 Product 모델에 이 관계들을 추가해야 함)
"""
Product 모델에 추가해야 할 관계:

# 드롭쉬핑 관련 관계
outofstock_history = relationship("OutOfStockHistory", back_populates="product")
restock_history = relationship("RestockHistory", back_populates="product")
stock_check_logs = relationship("StockCheckLog", back_populates="product")
price_history = relationship("PriceHistory", back_populates="product")
profit_protection_logs = relationship("ProfitProtectionLog", back_populates="product")
stockout_predictions = relationship("StockoutPredictionHistory", back_populates="product")
demand_analyses = relationship("DemandAnalysisHistory", back_populates="product")
automation_executions = relationship("AutomationExecution", back_populates="product")
"""

# Wholesaler 모델에 새로운 관계 추가를 위한 백레퍼런스 정의
# (실제 Wholesaler 모델에 이 관계들을 추가해야 함)
"""
Wholesaler 모델에 추가해야 할 관계:

# 드롭쉬핑 관련 관계
outofstock_history = relationship("OutOfStockHistory", back_populates="wholesaler")
reliability = relationship("SupplierReliability", back_populates="supplier", uselist=False)
stock_check_logs = relationship("StockCheckLog", back_populates="wholesaler")
price_history = relationship("PriceHistory", back_populates="wholesaler")
"""