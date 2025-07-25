"""
트렌드 분석 모델
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, JSON, Boolean
from datetime import datetime

from .base import Base


class TrendKeyword(Base):
    """트렌드 키워드 모델"""
    __tablename__ = "trend_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    trend_score = Column(Float, default=0.0)  # 트렌드 점수 (0-100)
    trend_direction = Column(String(20), default="stable")  # rising, falling, stable
    platform = Column(String(50), nullable=False, index=True)  # google, naver, etc
    
    # 검색 데이터
    search_volume = Column(Integer, default=0)
    competition_level = Column(String(20), default="medium")  # low, medium, high
    cpc_min = Column(Integer, default=0)  # 최소 클릭당 비용
    cpc_max = Column(Integer, default=0)  # 최대 클릭당 비용
    
    # 분석 데이터
    rise_percentage = Column(Float, default=0.0)  # 상승률
    interest_over_time = Column(JSON, nullable=True)  # 시간별 관심도 데이터
    related_queries = Column(JSON, nullable=True)  # 연관 검색어
    demographic_data = Column(JSON, nullable=True)  # 인구통계 데이터
    
    # 추가 메타데이터
    trend_metadata = Column(JSON, nullable=True)  # 기타 플랫폼별 데이터
    is_seasonal = Column(Boolean, default=False)  # 계절성 여부
    peak_months = Column(String(100), nullable=True)  # 피크 월들 (JSON array로 저장)
    
    # 타임스탬프
    analyzed_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_keyword_platform_date', 'keyword', 'platform', 'analyzed_at'),
        Index('idx_trend_score_direction', 'trend_score', 'trend_direction'),
        Index('idx_category_platform', 'category', 'platform'),
    )
    
    def __repr__(self):
        return f"<TrendKeyword(keyword={self.keyword}, score={self.trend_score}, direction={self.trend_direction})>"


class TrendData(Base):
    """트렌드 원시 데이터"""
    __tablename__ = "trend_data"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    data_type = Column(String(50), nullable=False)  # interest_over_time, related_queries, etc
    
    # 원시 데이터
    raw_data = Column(JSON, nullable=False)  # 플랫폼에서 받은 원본 데이터
    processed_data = Column(JSON, nullable=True)  # 가공된 데이터
    
    # 데이터 품질
    data_quality_score = Column(Float, default=1.0)  # 데이터 품질 점수 (0-1)
    completeness = Column(Float, default=1.0)  # 완전성 점수 (0-1)
    
    # 수집 정보
    collection_date = Column(DateTime, default=datetime.utcnow, index=True)
    timeframe = Column(String(50), nullable=True)  # 수집 기간 (e.g., "today 3-m")
    geo_location = Column(String(10), default="KR")  # 지역 코드
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_keyword_platform_type', 'keyword', 'platform', 'data_type'),
        Index('idx_collection_date', 'collection_date'),
    )
    
    def __repr__(self):
        return f"<TrendData(keyword={self.keyword}, platform={self.platform}, type={self.data_type})>"


class KeywordAnalysis(Base):
    """키워드 종합 분석 결과"""
    __tablename__ = "keyword_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    
    # 종합 분석 점수
    overall_score = Column(Float, default=0.0)  # 종합 점수 (0-100)
    potential_score = Column(Float, default=0.0)  # 잠재력 점수 (0-100)
    risk_score = Column(Float, default=0.0)  # 리스크 점수 (0-100)
    competition_score = Column(Float, default=0.0)  # 경쟁 점수 (0-100)
    
    # 세부 분석
    search_trend_analysis = Column(JSON, nullable=True)  # 검색 트렌드 분석
    seasonal_analysis = Column(JSON, nullable=True)  # 계절성 분석
    competitive_analysis = Column(JSON, nullable=True)  # 경쟁 분석
    demographic_analysis = Column(JSON, nullable=True)  # 인구통계 분석
    
    # 예측 데이터
    predicted_growth = Column(Float, default=0.0)  # 예상 성장률
    market_size_estimate = Column(Integer, default=0)  # 시장 규모 추정
    entry_timing = Column(String(50), nullable=True)  # 진입 타이밍
    
    # AI 추천
    ai_recommendation = Column(String(20), default="HOLD")  # BUY, SELL, HOLD, AVOID
    confidence_level = Column(Float, default=0.0)  # 신뢰도 (0-1)
    recommendation_reasons = Column(JSON, nullable=True)  # 추천 이유들
    action_items = Column(JSON, nullable=True)  # 실행 항목들
    
    # 모니터링
    monitoring_alerts = Column(JSON, nullable=True)  # 모니터링 알림 설정
    next_review_date = Column(DateTime, nullable=True)  # 다음 리뷰 날짜
    
    # 타임스탬프
    analyzed_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_keyword_analyzed', 'keyword', 'analyzed_at'),
        Index('idx_overall_score', 'overall_score'),
        Index('idx_recommendation', 'ai_recommendation', 'confidence_level'),
    )
    
    def __repr__(self):
        return f"<KeywordAnalysis(keyword={self.keyword}, score={self.overall_score}, recommendation={self.ai_recommendation})>"


class TrendAlert(Base):
    """트렌드 알림 모델"""
    __tablename__ = "trend_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # spike, drop, threshold, etc
    threshold_value = Column(Float, nullable=True)  # 임계값
    current_value = Column(Float, nullable=False)  # 현재값
    
    # 알림 내용
    alert_title = Column(String(255), nullable=False)
    alert_message = Column(Text, nullable=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    
    # 처리 상태
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    
    # 메타데이터
    alert_data = Column(JSON, nullable=True)  # 추가 알림 데이터
    
    # 타임스탬프
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 복합 인덱스
    __table_args__ = (
        Index('idx_keyword_triggered', 'keyword', 'triggered_at'),
        Index('idx_alert_status', 'is_read', 'is_resolved'),
        Index('idx_severity_triggered', 'severity', 'triggered_at'),
    )
    
    def __repr__(self):
        return f"<TrendAlert(keyword={self.keyword}, type={self.alert_type}, severity={self.severity})>"