"""
드롭쉬핑 CRM 시스템을 위한 데이터베이스 모델
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import uuid
from .base import Base


class CustomerLifecycleStage(PyEnum):
    """고객 생애주기 단계"""
    NEW = "new"                     # 신규 고객
    ACTIVE = "active"               # 활성 고객
    ENGAGED = "engaged"             # 참여 고객
    AT_RISK = "at_risk"            # 이탈 위험
    DORMANT = "dormant"            # 휴면 고객
    CHURNED = "churned"            # 이탈 고객
    VIP = "vip"                    # VIP 고객


class CustomerSegment(PyEnum):
    """RFM 기반 고객 세그먼트"""
    CHAMPIONS = "champions"                 # 우수 고객
    LOYAL_CUSTOMERS = "loyal_customers"     # 충성 고객
    POTENTIAL_LOYALISTS = "potential_loyalists"  # 잠재 충성 고객
    NEW_CUSTOMERS = "new_customers"         # 신규 고객
    PROMISING = "promising"                 # 유망 고객
    NEED_ATTENTION = "need_attention"       # 관심 필요
    ABOUT_TO_SLEEP = "about_to_sleep"      # 잠재 휴면
    AT_RISK = "at_risk"                    # 이탈 위험
    CANNOT_LOSE_THEM = "cannot_lose_them"  # 중요 고객
    HIBERNATING = "hibernating"            # 휴면 고객
    LOST = "lost"                          # 이탈 고객


class Customer(Base):
    """고객 기본 정보"""
    __tablename__ = "crm_customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # 기본 정보
    name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(20))
    gender = Column(String(10))
    age = Column(Integer)
    birth_date = Column(DateTime)
    
    # 주소 정보
    address = Column(Text)
    city = Column(String(100))
    postal_code = Column(String(20))
    
    # 계정 정보
    registration_date = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # 고객 분류
    lifecycle_stage = Column(Enum(CustomerLifecycleStage), default=CustomerLifecycleStage.NEW)
    segment = Column(Enum(CustomerSegment))
    customer_value_tier = Column(String(20))  # bronze, silver, gold, platinum
    
    # RFM 점수
    recency_score = Column(Integer)         # 1-5
    frequency_score = Column(Integer)       # 1-5
    monetary_score = Column(Integer)        # 1-5
    rfm_score = Column(String(3))          # 예: "543"
    
    # 고객 지표
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    average_order_value = Column(Float, default=0.0)
    lifetime_value = Column(Float, default=0.0)
    predicted_ltv = Column(Float)
    
    # 구매 패턴
    first_purchase_date = Column(DateTime)
    last_purchase_date = Column(DateTime)
    purchase_frequency = Column(Float)      # 월 평균 구매 횟수
    preferred_categories = Column(JSON)     # 선호 카테고리 목록
    preferred_brands = Column(JSON)         # 선호 브랜드 목록
    preferred_price_range = Column(JSON)    # {"min": 10000, "max": 50000}
    
    # 플랫폼 정보
    acquisition_channel = Column(String(50))  # 고객 유입 채널
    preferred_platform = Column(String(50))   # 주로 이용하는 플랫폼
    mobile_usage_rate = Column(Float)         # 모바일 이용률
    
    # 커뮤니케이션 선호도
    email_marketing_consent = Column(Boolean, default=True)
    sms_marketing_consent = Column(Boolean, default=True)
    push_notification_consent = Column(Boolean, default=True)
    preferred_contact_time = Column(String(20))  # morning, afternoon, evening
    
    # 만족도 지표
    nps_score = Column(Integer)             # Net Promoter Score
    satisfaction_score = Column(Float)       # 평균 만족도
    complaint_count = Column(Integer, default=0)
    compliment_count = Column(Integer, default=0)
    
    # 이탈 관련
    churn_probability = Column(Float)        # 이탈 확률 (0-1)
    churn_risk_factors = Column(JSON)        # 이탈 위험 요소들
    last_engagement_date = Column(DateTime)  # 마지막 상호작용 날짜
    
    # 메타데이터
    tags = Column(JSON)                      # 고객 태그
    notes = Column(Text)                     # 고객 메모
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계 설정
    behaviors = relationship("CustomerBehavior", back_populates="customer")
    rfm_analyses = relationship("RFMAnalysis", back_populates="customer")
    interactions = relationship("CustomerInteraction", back_populates="customer")
    recommendations = relationship("CustomerRecommendation", back_populates="customer")
    campaigns = relationship("CustomerCampaign", back_populates="customer")


class CustomerBehavior(Base):
    """고객 행동 로그"""
    __tablename__ = "crm_customer_behaviors"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), index=True)
    
    # 행동 정보
    action_type = Column(String(50))        # view, click, add_to_cart, purchase, return
    action_details = Column(JSON)           # 상세 행동 데이터
    
    # 상품 관련
    product_id = Column(String(100))
    product_category = Column(String(100))
    product_price = Column(Float)
    
    # 세션 정보
    session_id = Column(String(100))
    page_url = Column(String(500))
    referrer = Column(String(500))
    device_type = Column(String(20))        # mobile, desktop, tablet
    platform = Column(String(50))          # 플랫폼 정보
    
    # 시간 정보
    timestamp = Column(DateTime, default=func.now())
    duration = Column(Integer)              # 체류 시간 (초)
    
    # 위치 정보
    ip_address = Column(String(50))
    location = Column(JSON)                 # {"city": "Seoul", "country": "KR"}
    
    customer = relationship("Customer", back_populates="behaviors")


class RFMAnalysis(Base):
    """RFM 분석 결과"""
    __tablename__ = "crm_rfm_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), index=True)
    
    # 분석 기간
    analysis_date = Column(DateTime, default=func.now())
    analysis_period_start = Column(DateTime)
    analysis_period_end = Column(DateTime)
    
    # RFM 원시 값
    recency_days = Column(Integer)          # 마지막 구매 후 경과일
    frequency_count = Column(Integer)        # 구매 횟수
    monetary_value = Column(Float)          # 총 구매 금액
    
    # RFM 점수 (1-5)
    recency_score = Column(Integer)
    frequency_score = Column(Integer)
    monetary_score = Column(Integer)
    rfm_score = Column(String(3))
    
    # 세그먼트
    segment = Column(Enum(CustomerSegment))
    segment_description = Column(String(200))
    
    # 추가 지표
    average_order_value = Column(Float)
    purchase_interval_avg = Column(Float)   # 평균 구매 간격 (일)
    trend_indicator = Column(String(20))    # improving, stable, declining
    
    customer = relationship("Customer", back_populates="rfm_analyses")


class CustomerInteraction(Base):
    """고객 상호작용 이력"""
    __tablename__ = "crm_customer_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), index=True)
    
    # 상호작용 정보
    interaction_type = Column(String(50))   # email, sms, call, chat, review, complaint
    channel = Column(String(50))           # platform, email, phone, social
    direction = Column(String(20))         # inbound, outbound
    
    # 내용
    subject = Column(String(200))
    content = Column(Text)
    sentiment = Column(String(20))         # positive, neutral, negative
    
    # 상태
    status = Column(String(20))            # pending, completed, cancelled
    priority = Column(String(20))          # low, medium, high, urgent
    
    # 담당자
    agent_id = Column(String(50))
    department = Column(String(50))
    
    # 결과
    resolution = Column(Text)
    satisfaction_rating = Column(Integer)   # 1-5
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(DateTime)
    
    # 시간 정보
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime)
    response_time_minutes = Column(Integer)
    
    customer = relationship("Customer", back_populates="interactions")


class CustomerRecommendation(Base):
    """고객 추천 로그"""
    __tablename__ = "crm_customer_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), index=True)
    
    # 추천 정보
    recommendation_type = Column(String(50))  # product, category, brand, promotion
    algorithm_used = Column(String(50))       # collaborative, content_based, hybrid
    
    # 추천 상품/내용
    recommended_items = Column(JSON)          # 추천된 상품들
    recommendation_score = Column(Float)      # 추천 점수
    
    # 개인화 요소
    personalization_factors = Column(JSON)    # 개인화에 사용된 요소들
    context = Column(JSON)                    # 추천 당시 상황 정보
    
    # 성과 지표
    impression_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)
    revenue_generated = Column(Float, default=0.0)
    
    # 시간 정보
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)
    last_shown_at = Column(DateTime)
    
    customer = relationship("Customer", back_populates="recommendations")


class CustomerCampaign(Base):
    """고객 마케팅 캠페인 참여 이력"""
    __tablename__ = "crm_customer_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), index=True)
    
    # 캠페인 정보
    campaign_id = Column(String(100))
    campaign_name = Column(String(200))
    campaign_type = Column(String(50))      # email, sms, push, social, retargeting
    
    # 개인화 정보
    personalized_content = Column(JSON)     # 개인화된 콘텐츠
    segment_targeted = Column(String(50))   # 타겟 세그먼트
    
    # 발송 정보
    sent_at = Column(DateTime)
    delivery_status = Column(String(20))    # sent, delivered, failed, bounced
    
    # 반응 정보
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    converted_at = Column(DateTime)
    unsubscribed_at = Column(DateTime)
    
    # 성과 지표
    open_rate = Column(Float)
    click_rate = Column(Float)
    conversion_rate = Column(Float)
    revenue_attributed = Column(Float)
    
    # 피드백
    feedback_rating = Column(Integer)       # 1-5
    feedback_comment = Column(Text)
    
    customer = relationship("Customer", back_populates="campaigns")


class CustomerLifecycleEvent(Base):
    """고객 생애주기 이벤트"""
    __tablename__ = "crm_lifecycle_events"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"))
    
    # 이벤트 정보
    event_type = Column(String(50))         # registration, first_purchase, milestone, churn_risk
    event_description = Column(String(200))
    
    # 단계 변화
    previous_stage = Column(Enum(CustomerLifecycleStage))
    current_stage = Column(Enum(CustomerLifecycleStage))
    
    # 트리거 정보
    trigger_factor = Column(String(100))    # 단계 변화를 유발한 요인
    trigger_data = Column(JSON)            # 상세 데이터
    
    # 액션 필요성
    action_required = Column(Boolean, default=False)
    recommended_actions = Column(JSON)      # 권장 액션들
    
    # 시간 정보
    event_date = Column(DateTime, default=func.now())
    
    customer = relationship("Customer")


class CustomerPreference(Base):
    """고객 선호도 정보"""
    __tablename__ = "crm_customer_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"))
    
    # 상품 선호도
    preferred_categories = Column(JSON)     # 카테고리별 선호도 점수
    preferred_brands = Column(JSON)         # 브랜드별 선호도 점수
    preferred_price_ranges = Column(JSON)   # 가격대별 선호도
    
    # 구매 패턴 선호도
    preferred_day_of_week = Column(JSON)    # 요일별 구매 선호도
    preferred_time_of_day = Column(JSON)    # 시간대별 구매 선호도
    seasonal_preferences = Column(JSON)     # 계절별 선호도
    
    # 서비스 선호도
    preferred_delivery_method = Column(String(50))
    preferred_payment_method = Column(String(50))
    preferred_communication_channel = Column(String(50))
    
    # 할인 선호도
    discount_sensitivity = Column(Float)     # 할인 민감도 (0-1)
    preferred_promotion_types = Column(JSON) # 선호하는 프로모션 유형
    
    # 학습 데이터
    confidence_score = Column(Float)        # 선호도 예측 신뢰도
    last_updated = Column(DateTime, default=func.now())
    data_points_count = Column(Integer)     # 학습에 사용된 데이터 포인트 수
    
    customer = relationship("Customer")