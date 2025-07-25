"""
벤치마크 데이터 모델
중앙 집중식 시장 데이터 관리
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Boolean, Index, Text
from sqlalchemy.sql import func
from app.core.database import Base


class BenchmarkProduct(Base):
    """벤치마크 상품 정보"""
    __tablename__ = "benchmark_products"
    
    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)
    market_product_id = Column(String(100), index=True)  # 마켓별 상품 ID
    market_type = Column(String(50), index=True)  # coupang, naver, 11st
    
    # 상품 기본 정보
    product_name = Column(String(500))
    brand = Column(String(200))
    category_path = Column(String(500))  # 카테고리 경로
    main_category = Column(String(100), index=True)
    sub_category = Column(String(100), index=True)
    
    # 가격 정보
    original_price = Column(Integer)
    sale_price = Column(Integer)
    discount_rate = Column(Float)
    delivery_fee = Column(Integer)
    
    # 판매 실적
    monthly_sales = Column(Integer)  # 월 판매량
    review_count = Column(Integer)
    rating = Column(Float)
    
    # 순위 정보
    bestseller_rank = Column(Integer)  # 베스트셀러 순위
    category_rank = Column(Integer)  # 카테고리 순위
    
    # 판매자 정보
    seller_name = Column(String(200))
    seller_grade = Column(String(50))
    is_power_seller = Column(Boolean, default=False)
    
    # 상품 속성
    options = Column(JSON)  # 옵션 정보
    keywords = Column(JSON)  # 키워드 리스트
    attributes = Column(JSON)  # 상품 속성
    
    # 수집 정보
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 인덱스
    __table_args__ = (
        Index('idx_market_category', 'market_type', 'main_category'),
        Index('idx_bestseller', 'market_type', 'bestseller_rank'),
        Index('idx_sales', 'monthly_sales'),
    )


class BenchmarkPriceHistory(Base):
    """가격 변동 이력"""
    __tablename__ = "benchmark_price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    market_product_id = Column(String(100), index=True)
    market_type = Column(String(50))
    
    original_price = Column(Integer)
    sale_price = Column(Integer)
    discount_rate = Column(Float)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 인덱스
    __table_args__ = (
        Index('idx_product_time', 'market_product_id', 'recorded_at'),
    )


class BenchmarkKeyword(Base):
    """키워드 트렌드 데이터"""
    __tablename__ = "benchmark_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(100), unique=True, index=True)
    
    # 검색량 데이터
    search_volume = Column(Integer)  # 월간 검색량
    competition = Column(String(20))  # 경쟁도 (high/medium/low)
    
    # 트렌드 점수
    trend_score = Column(Float)  # 트렌드 점수 (0-100)
    growth_rate = Column(Float)  # 성장률 (%)
    
    # 연관 데이터
    related_keywords = Column(JSON)
    category_distribution = Column(JSON)  # 카테고리별 분포
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BenchmarkReview(Base):
    """리뷰 분석 데이터"""
    __tablename__ = "benchmark_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    market_product_id = Column(String(100), index=True)
    market_type = Column(String(50))
    
    # 리뷰 통계
    total_reviews = Column(Integer)
    positive_count = Column(Integer)
    neutral_count = Column(Integer)
    negative_count = Column(Integer)
    
    # 감성 분석
    sentiment_score = Column(Float)  # -1 ~ 1
    
    # 주요 키워드
    positive_keywords = Column(JSON)
    negative_keywords = Column(JSON)
    improvement_suggestions = Column(JSON)
    
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())


class BenchmarkCompetitor(Base):
    """경쟁사 분석 데이터"""
    __tablename__ = "benchmark_competitors"
    
    id = Column(Integer, primary_key=True, index=True)
    competitor_name = Column(String(200), unique=True, index=True)
    
    # 판매자 정보
    market_share = Column(Float)  # 시장 점유율 (%)
    total_products = Column(Integer)
    average_rating = Column(Float)
    
    # 가격 전략
    avg_price = Column(Integer)
    price_range_min = Column(Integer)
    price_range_max = Column(Integer)
    
    # 주력 카테고리
    main_categories = Column(JSON)
    bestseller_products = Column(JSON)
    
    # 성과 지표
    monthly_revenue_estimate = Column(Integer)
    growth_trend = Column(String(20))  # up/stable/down
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BenchmarkMarketTrend(Base):
    """시장 트렌드 데이터"""
    __tablename__ = "benchmark_market_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), index=True)
    period = Column(String(20))  # daily/weekly/monthly
    
    # 시장 규모
    market_size = Column(Integer)  # 추정 시장 규모
    transaction_volume = Column(Integer)  # 거래량
    
    # 트렌드 지표
    growth_rate = Column(Float)
    seasonality_index = Column(Float)
    
    # 주요 인사이트
    top_keywords = Column(JSON)
    emerging_brands = Column(JSON)
    price_trends = Column(JSON)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class BenchmarkAlert(Base):
    """벤치마크 알림 설정"""
    __tablename__ = "benchmark_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50))  # price_drop, new_competitor, trend_change
    
    # 알림 조건
    target_product_id = Column(String(100))
    target_keyword = Column(String(100))
    threshold_value = Column(Float)
    
    # 알림 상태
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime(timezone=True))
    trigger_count = Column(Integer, default=0)
    
    # 알림 내용
    message_template = Column(Text)
    notification_channels = Column(JSON)  # ['slack', 'email', 'sms']
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())