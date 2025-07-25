"""
드롭쉬핑 관련 데이터베이스 모델

품절 관리, 공급업체 신뢰도, 재입고 감지, 수익 보호, 예측 등
드롭쉬핑 운영에 필요한 모든 데이터 모델
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base


class OutOfStockHistory(Base):
    """품절 이력"""
    __tablename__ = "outofstock_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    wholesaler_id = Column(Integer, ForeignKey("wholesalers.id"), nullable=False)
    
    # 품절 정보
    out_of_stock_time = Column(DateTime, nullable=False, default=datetime.now)
    restock_time = Column(DateTime, nullable=True)
    duration_hours = Column(Float, nullable=True)
    
    # 처리 정보
    action_taken = Column(String(50), nullable=True)  # deactivate, hide, delete, replace
    alternative_suggested = Column(Boolean, default=False)
    estimated_lost_sales = Column(Float, default=0.0)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계
    product = relationship("Product", back_populates="outofstock_history")
    wholesaler = relationship("Wholesaler", back_populates="outofstock_history")


class SupplierReliability(Base):
    """공급업체 신뢰도"""
    __tablename__ = "supplier_reliability"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("wholesalers.id"), nullable=False, unique=True, index=True)
    
    # 신뢰도 지표
    outofstock_rate = Column(Float, default=0.0)  # 품절률 (%)
    avg_outofstock_duration = Column(Float, default=0.0)  # 평균 품절 지속시간 (시간)
    response_time_avg = Column(Float, default=0.0)  # 평균 응답시간 (ms)
    restock_speed_avg = Column(Float, default=0.0)  # 평균 재입고 속도 (시간)
    price_stability = Column(Float, default=100.0)  # 가격 안정성 (%)
    
    # 종합 점수
    reliability_score = Column(Float, default=0.0)  # 신뢰도 점수 (0-100)
    grade = Column(String(20), default="unknown")  # excellent, good, average, poor, very_poor
    risk_level = Column(String(20), default="unknown")  # 위험 수준
    
    # 분석 정보
    last_analyzed = Column(DateTime, default=datetime.now)
    analysis_period_days = Column(Integer, default=90)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계
    supplier = relationship("Wholesaler", back_populates="reliability")


class RestockHistory(Base):
    """재입고 이력"""
    __tablename__ = "restock_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 재고 정보
    previous_stock = Column(Integer, default=0)
    current_stock = Column(Integer, nullable=False)
    detected_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # 가격 정보
    wholesale_price_before = Column(Float, nullable=True)
    wholesale_price_after = Column(Float, nullable=True)
    price_change_rate = Column(Float, default=0.0)
    
    # 결정 정보
    decision = Column(String(50), nullable=False)  # auto_reactivate, manual_review, price_changed, etc.
    auto_reactivated = Column(Boolean, default=False)
    review_required = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계
    product = relationship("Product", back_populates="restock_history")


class StockCheckLog(Base):
    """재고 체크 로그"""
    __tablename__ = "stock_check_log"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    wholesaler_id = Column(Integer, ForeignKey("wholesalers.id"), nullable=False)
    
    # 체크 결과
    previous_stock = Column(Integer, default=0)
    current_stock = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # in_stock, low_stock, out_of_stock, unknown
    status_changed = Column(Boolean, default=False)
    
    # 성능 정보
    check_time = Column(DateTime, nullable=False, default=datetime.now)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 관계
    product = relationship("Product", back_populates="stock_check_logs")
    wholesaler = relationship("Wholesaler", back_populates="stock_check_logs")


class PriceHistory(Base):
    """가격 변동 이력"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    wholesaler_id = Column(Integer, ForeignKey("wholesalers.id"), nullable=False)
    
    # 가격 정보
    price = Column(Float, nullable=False)
    price_type = Column(String(20), default="wholesale")  # wholesale, selling
    previous_price = Column(Float, nullable=True)
    change_rate = Column(Float, default=0.0)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now)
    recorded_by = Column(String(50), default="system")  # system, manual, api
    
    # 관계
    product = relationship("Product", back_populates="price_history")
    wholesaler = relationship("Wholesaler", back_populates="price_history")


class ProfitProtectionLog(Base):
    """수익 보호 로그"""
    __tablename__ = "profit_protection_log"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 수익 분석 결과
    current_margin = Column(Float, nullable=False)
    target_margin = Column(Float, nullable=False)
    margin_gap = Column(Float, default=0.0)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # 시장 정보
    competitor_price_avg = Column(Float, nullable=True)
    market_position = Column(String(20), nullable=True)  # 저가, 경쟁적, 고가
    
    # 조치 정보
    recommended_action = Column(Text, nullable=True)
    action_taken = Column(Boolean, default=False)
    estimated_loss_per_day = Column(Float, default=0.0)
    
    # 메타데이터
    analyzed_at = Column(DateTime, default=datetime.now)
    
    # 관계
    product = relationship("Product", back_populates="profit_protection_logs")


class StockoutPredictionHistory(Base):
    """품절 예측 이력"""
    __tablename__ = "stockout_prediction_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 현재 상태
    current_stock = Column(Integer, nullable=False)
    
    # 예측 결과
    predicted_stockout_date = Column(DateTime, nullable=True)
    days_until_stockout = Column(Integer, nullable=True)
    confidence_level = Column(String(20), nullable=False)  # very_high, high, medium, low, very_low
    confidence_score = Column(Float, default=0.0)
    
    # 예측 정보
    predicted_by = Column(String(100), nullable=False)  # 예측 모델명
    risk_level = Column(String(20), nullable=True)  # 위험 수준
    factors = Column(Text, nullable=True)  # JSON 형태의 영향 요인
    recommendations = Column(Text, nullable=True)  # JSON 형태의 권장사항
    
    # 메타데이터
    predicted_at = Column(DateTime, default=datetime.now)
    
    # 관계
    product = relationship("Product", back_populates="stockout_predictions")


class DemandAnalysisHistory(Base):
    """수요 분석 이력"""
    __tablename__ = "demand_analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 수요 분석 결과
    demand_score = Column(Float, default=0.0)  # 현재 수요 점수 (0-100)
    trend = Column(String(20), nullable=False)  # increasing, stable, decreasing, volatile
    
    # 패턴 분석
    weekly_pattern = Column(Text, nullable=True)  # JSON 형태의 요일별 패턴
    monthly_pattern = Column(Text, nullable=True)  # JSON 형태의 월별 패턴
    seasonal_index = Column(Float, default=1.0)  # 계절성 지수
    
    # 탄력성 및 변동성
    price_elasticity = Column(Float, default=-1.0)  # 가격 탄력성
    demand_volatility = Column(Float, default=0.0)  # 수요 변동성
    growth_rate = Column(Float, default=0.0)  # 수요 성장률 (%)
    
    # 분석 결과
    peak_demand_period = Column(String(50), nullable=True)  # 피크 수요 시기
    recommendations = Column(Text, nullable=True)  # JSON 형태의 권장사항
    
    # 메타데이터
    analyzed_at = Column(DateTime, default=datetime.now)
    analysis_period_days = Column(Integer, default=90)
    
    # 관계
    product = relationship("Product", back_populates="demand_analyses")


class AutomationRule(Base):
    """자동화 규칙"""
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    # 규칙 정보
    rule_id = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 조건 및 액션
    condition = Column(Text, nullable=False)  # 조건식
    action = Column(String(50), nullable=False)  # activate, deactivate, update_price, etc.
    parameters = Column(JSON, nullable=True)  # 액션 파라미터
    
    # 설정
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=5)  # 우선순위 (1이 가장 높음)
    
    # 통계
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    last_executed = Column(DateTime, nullable=True)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String(50), default="system")


class AutomationExecution(Base):
    """자동화 실행 이력"""
    __tablename__ = "automation_executions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(50), ForeignKey("automation_rules.rule_id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 실행 정보
    action_taken = Column(String(50), nullable=False)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    # 실행 결과
    before_state = Column(JSON, nullable=True)  # 실행 전 상태
    after_state = Column(JSON, nullable=True)   # 실행 후 상태
    
    # 메타데이터
    executed_at = Column(DateTime, default=datetime.now)
    execution_time_ms = Column(Float, nullable=True)
    
    # 관계
    automation_rule = relationship("AutomationRule")
    product = relationship("Product", back_populates="automation_executions")


class AlternativeRecommendation(Base):
    """대체 상품 추천 이력"""
    __tablename__ = "alternative_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    original_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    alternative_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 추천 정보
    similarity_score = Column(Float, default=0.0)
    alternative_type = Column(String(30), nullable=False)  # same_supplier, different_supplier, etc.
    recommendation_reason = Column(Text, nullable=True)
    
    # 성과 정보
    click_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    
    # 메타데이터
    recommended_at = Column(DateTime, default=datetime.now)
    last_clicked = Column(DateTime, nullable=True)
    
    # 관계
    original_product = relationship("Product", foreign_keys=[original_product_id])
    alternative_product = relationship("Product", foreign_keys=[alternative_product_id])


class DropshippingSettings(Base):
    """드롭쉬핑 설정"""
    __tablename__ = "dropshipping_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # 모니터링 설정
    monitoring_enabled = Column(Boolean, default=True)
    check_interval_seconds = Column(Integer, default=600)  # 10분
    low_stock_threshold = Column(Integer, default=10)
    
    # 자동화 설정
    automation_enabled = Column(Boolean, default=True)
    auto_deactivate_on_stockout = Column(Boolean, default=True)
    auto_reactivate_on_restock = Column(Boolean, default=True)
    price_change_threshold = Column(Float, default=0.05)  # 5%
    
    # 수익 보호 설정
    profit_protection_enabled = Column(Boolean, default=True)
    min_margin_rate = Column(Float, default=0.15)  # 15%
    target_margin_rate = Column(Float, default=0.25)  # 25%
    max_price_adjustment = Column(Float, default=0.10)  # 10%
    
    # 예측 설정
    prediction_enabled = Column(Boolean, default=True)
    prediction_horizon_days = Column(Integer, default=30)
    high_risk_threshold_days = Column(Integer, default=7)
    
    # 알림 설정
    notification_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    slack_notifications = Column(Boolean, default=False)
    critical_alerts_only = Column(Boolean, default=False)
    
    # 메타데이터
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(String(50), default="system")


class DuplicateProductGroup(Base):
    """중복 상품 그룹"""
    __tablename__ = "duplicate_product_groups"

    id = Column(Integer, primary_key=True, index=True)
    
    # 그룹 정보
    group_id = Column(String(50), nullable=False, unique=True, index=True)
    representative_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_count = Column(Integer, default=1)
    
    # 분석 정보
    similarity_threshold = Column(Float, default=0.8)
    analysis_method = Column(String(50), default="tfidf")
    
    # 가격 정보
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    best_deal_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    potential_savings = Column(Float, default=0.0)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계
    representative_product = relationship("Product", foreign_keys=[representative_product_id])
    best_deal_product = relationship("Product", foreign_keys=[best_deal_product_id])
    duplicate_products = relationship("DuplicateProduct", back_populates="group")


class DuplicateProduct(Base):
    """중복 상품"""
    __tablename__ = "duplicate_products"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(50), ForeignKey("duplicate_product_groups.group_id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 유사도 정보
    similarity_score = Column(Float, default=0.0)
    match_type = Column(String(30), default="name")  # name, keywords, model, sku
    
    # 가격 비교
    price_difference = Column(Float, default=0.0)
    is_best_deal = Column(Boolean, default=False)
    savings_amount = Column(Float, default=0.0)
    
    # 메타데이터
    detected_at = Column(DateTime, default=datetime.now)
    
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