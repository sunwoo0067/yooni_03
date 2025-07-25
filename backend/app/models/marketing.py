"""
마케팅 자동화 시스템을 위한 데이터베이스 모델
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean, Text, ForeignKey, Enum, Table, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import uuid
from .base import Base


class CampaignType(PyEnum):
    """캠페인 유형"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    SOCIAL = "social"
    RETARGETING = "retargeting"
    PROMOTION = "promotion"
    ABANDONED_CART = "abandoned_cart"
    WELCOME = "welcome"
    REACTIVATION = "reactivation"
    LOYALTY = "loyalty"
    SEASONAL = "seasonal"
    FLASH_SALE = "flash_sale"


class CampaignStatus(PyEnum):
    """캠페인 상태"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TriggerType(PyEnum):
    """트리거 유형"""
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    BEHAVIOR_BASED = "behavior_based"
    LIFECYCLE_BASED = "lifecycle_based"
    CONDITION_BASED = "condition_based"


class MessageStatus(PyEnum):
    """메시지 상태"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    CONVERTED = "converted"
    FAILED = "failed"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


# 다대다 관계 테이블
campaign_segments = Table(
    'marketing_campaign_segments',
    Base.metadata,
    Column('campaign_id', Integer, ForeignKey('marketing_campaigns.id')),
    Column('segment_id', Integer, ForeignKey('marketing_segments.id'))
)


class MarketingCampaign(Base):
    """마케팅 캠페인"""
    __tablename__ = "marketing_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # 기본 정보
    name = Column(String(200), nullable=False)
    description = Column(Text)
    campaign_type = Column(Enum(CampaignType), nullable=False)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    
    # 타겟팅
    target_segments = relationship("MarketingSegment", secondary=campaign_segments, back_populates="campaigns")
    target_conditions = Column(JSON)  # 추가 타겟팅 조건
    expected_recipients = Column(Integer)
    
    # 일정
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    schedule_type = Column(String(50))  # immediate, scheduled, recurring
    schedule_config = Column(JSON)  # 반복 일정 설정
    
    # 콘텐츠
    subject = Column(String(200))
    preview_text = Column(String(200))
    content_template = Column(Text)  # HTML/텍스트 템플릿
    personalization_tags = Column(JSON)  # 개인화 태그
    
    # A/B 테스팅
    is_ab_test = Column(Boolean, default=False)
    ab_test_config = Column(JSON)  # A/B 테스트 설정
    control_group_size = Column(Float)  # 대조군 비율
    
    # 예산 및 목표
    budget = Column(Float)
    spent_amount = Column(Float, default=0.0)
    goal_type = Column(String(50))  # revenue, conversion, engagement
    goal_value = Column(Float)
    
    # 성과 지표
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    converted_count = Column(Integer, default=0)
    unsubscribed_count = Column(Integer, default=0)
    
    # 성과율
    delivery_rate = Column(Float)
    open_rate = Column(Float)
    click_rate = Column(Float)
    conversion_rate = Column(Float)
    roi = Column(Float)  # Return on Investment
    
    # 수익
    revenue_generated = Column(Float, default=0.0)
    average_order_value = Column(Float)
    
    # 메타데이터
    created_by = Column(String(100))
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계
    messages = relationship("MarketingMessage", back_populates="campaign")
    ab_variants = relationship("ABTestVariant", back_populates="campaign")
    automation_triggers = relationship("AutomationTrigger", back_populates="campaign")


class MarketingSegment(Base):
    """마케팅 세그먼트"""
    __tablename__ = "marketing_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 기본 정보
    name = Column(String(100), nullable=False)
    description = Column(Text)
    segment_type = Column(String(50))  # dynamic, static, smart
    
    # 세그먼트 규칙
    rules = Column(JSON)  # 세그먼트 생성 규칙
    sql_query = Column(Text)  # 동적 세그먼트용 SQL
    
    # 고객 수
    customer_count = Column(Integer, default=0)
    last_calculated = Column(DateTime)
    
    # 세그먼트 특성
    average_ltv = Column(Float)
    average_order_value = Column(Float)
    churn_rate = Column(Float)
    engagement_score = Column(Float)
    
    # 상태
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # 시스템 정의 세그먼트
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계
    campaigns = relationship("MarketingCampaign", secondary=campaign_segments, back_populates="target_segments")


class MarketingMessage(Base):
    """마케팅 메시지"""
    __tablename__ = "marketing_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), index=True)
    customer_id = Column(Integer, ForeignKey("crm_customers.id"), index=True)
    
    # 메시지 정보
    message_type = Column(String(50))  # email, sms, push
    channel = Column(String(50))
    
    # 개인화된 콘텐츠
    personalized_subject = Column(String(200))
    personalized_content = Column(Text)
    personalization_data = Column(JSON)
    
    # 발송 정보
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    
    # 상태
    status = Column(Enum(MessageStatus), default=MessageStatus.PENDING)
    error_message = Column(Text)
    
    # 상호작용
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    converted_at = Column(DateTime)
    unsubscribed_at = Column(DateTime)
    
    # 클릭 추적
    click_count = Column(Integer, default=0)
    clicked_links = Column(JSON)  # 클릭한 링크들
    
    # 전환 추적
    conversion_value = Column(Float)
    attributed_revenue = Column(Float)
    
    # A/B 테스트
    variant_id = Column(String(50))  # A/B 테스트 변형
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    
    # 관계
    campaign = relationship("MarketingCampaign", back_populates="messages")


class AutomationWorkflow(Base):
    """자동화 워크플로우"""
    __tablename__ = "marketing_automation_workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # 기본 정보
    name = Column(String(200), nullable=False)
    description = Column(Text)
    workflow_type = Column(String(50))  # welcome, abandoned_cart, win_back, etc.
    
    # 상태
    is_active = Column(Boolean, default=True)
    is_paused = Column(Boolean, default=False)
    
    # 워크플로우 정의
    workflow_definition = Column(JSON)  # 노드와 연결 정의
    entry_conditions = Column(JSON)  # 진입 조건
    exit_conditions = Column(JSON)  # 종료 조건
    
    # 실행 설정
    max_entries_per_customer = Column(Integer, default=1)
    cooldown_period_days = Column(Integer)  # 재진입 대기 기간
    
    # 성과
    total_entries = Column(Integer, default=0)
    active_entries = Column(Integer, default=0)
    completed_entries = Column(Integer, default=0)
    conversion_rate = Column(Float)
    average_revenue = Column(Float)
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계
    nodes = relationship("WorkflowNode", back_populates="workflow")
    executions = relationship("WorkflowExecution", back_populates="workflow")


class WorkflowNode(Base):
    """워크플로우 노드"""
    __tablename__ = "marketing_workflow_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("marketing_automation_workflows.id"))
    
    # 노드 정보
    node_type = Column(String(50))  # trigger, action, condition, wait, split
    node_name = Column(String(100))
    position = Column(JSON)  # UI에서의 위치
    
    # 설정
    config = Column(JSON)  # 노드별 설정
    
    # 연결
    next_nodes = Column(JSON)  # 다음 노드들의 ID
    previous_nodes = Column(JSON)  # 이전 노드들의 ID
    
    # 조건
    conditions = Column(JSON)  # 분기 조건
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    
    # 관계
    workflow = relationship("AutomationWorkflow", back_populates="nodes")


class WorkflowExecution(Base):
    """워크플로우 실행 로그"""
    __tablename__ = "marketing_workflow_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("marketing_automation_workflows.id"))
    customer_id = Column(Integer, ForeignKey("crm_customers.id"))
    
    # 실행 정보
    execution_id = Column(String(100), unique=True, index=True)
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    
    # 상태
    status = Column(String(50))  # active, completed, failed, cancelled
    current_node_id = Column(Integer)
    
    # 실행 경로
    execution_path = Column(JSON)  # 거친 노드들
    node_results = Column(JSON)  # 각 노드의 실행 결과
    
    # 결과
    converted = Column(Boolean, default=False)
    conversion_value = Column(Float)
    error_message = Column(Text)
    
    # 관계
    workflow = relationship("AutomationWorkflow", back_populates="executions")


class AutomationTrigger(Base):
    """자동화 트리거"""
    __tablename__ = "marketing_automation_triggers"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=True)
    workflow_id = Column(Integer, ForeignKey("marketing_automation_workflows.id"), nullable=True)
    
    # 트리거 정보
    trigger_name = Column(String(100))
    trigger_type = Column(Enum(TriggerType))
    
    # 트리거 조건
    event_name = Column(String(100))  # purchase, cart_abandon, birthday, etc.
    conditions = Column(JSON)  # 상세 조건
    
    # 실행 설정
    delay_minutes = Column(Integer, default=0)  # 지연 시간
    priority = Column(Integer, default=5)  # 우선순위 (1-10)
    
    # 상태
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    
    # 관계
    campaign = relationship("MarketingCampaign", back_populates="automation_triggers")


class ABTestVariant(Base):
    """A/B 테스트 변형"""
    __tablename__ = "marketing_ab_test_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"))
    
    # 변형 정보
    variant_name = Column(String(50))  # A, B, C...
    variant_type = Column(String(50))  # subject, content, cta, timing
    
    # 변형 내용
    subject = Column(String(200))
    content = Column(Text)
    cta_text = Column(String(100))
    send_time = Column(String(50))
    
    # 할당
    traffic_allocation = Column(Float)  # 트래픽 할당 비율
    assigned_count = Column(Integer, default=0)
    
    # 성과
    sent_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    converted_count = Column(Integer, default=0)
    
    # 성과율
    open_rate = Column(Float)
    click_rate = Column(Float)
    conversion_rate = Column(Float)
    
    # 통계
    confidence_level = Column(Float)  # 통계적 신뢰도
    is_winner = Column(Boolean, default=False)
    
    # 관계
    campaign = relationship("MarketingCampaign", back_populates="ab_variants")


class PromotionCode(Base):
    """프로모션 코드"""
    __tablename__ = "marketing_promotion_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=True)
    
    # 코드 정보
    code = Column(String(50), unique=True, index=True)
    code_type = Column(String(50))  # percentage, fixed, free_shipping, bogo
    
    # 할인 정보
    discount_value = Column(Float)  # 할인 금액/퍼센트
    minimum_purchase = Column(Float)  # 최소 구매 금액
    maximum_discount = Column(Float)  # 최대 할인 금액
    
    # 적용 범위
    applicable_products = Column(JSON)  # 적용 가능 상품
    applicable_categories = Column(JSON)  # 적용 가능 카테고리
    excluded_products = Column(JSON)  # 제외 상품
    
    # 사용 제한
    usage_limit = Column(Integer)  # 전체 사용 한도
    usage_per_customer = Column(Integer, default=1)  # 고객당 사용 한도
    current_usage = Column(Integer, default=0)
    
    # 유효 기간
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    
    # 타겟팅
    target_segment_id = Column(Integer, ForeignKey("marketing_segments.id"), nullable=True)
    target_customers = Column(JSON)  # 특정 고객 ID들
    
    # 상태
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)  # 공개 여부
    
    # 성과
    redemption_count = Column(Integer, default=0)
    revenue_generated = Column(Float, default=0.0)
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SocialMediaPost(Base):
    """소셜미디어 게시물"""
    __tablename__ = "marketing_social_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=True)
    
    # 게시물 정보
    platform = Column(String(50))  # facebook, instagram, twitter, etc.
    post_type = Column(String(50))  # text, image, video, story
    
    # 콘텐츠
    content = Column(Text)
    media_urls = Column(JSON)  # 이미지/비디오 URL들
    hashtags = Column(JSON)
    mentions = Column(JSON)
    
    # 일정
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    
    # 상태
    status = Column(String(50))  # draft, scheduled, published, failed
    platform_post_id = Column(String(100))  # 플랫폼에서의 게시물 ID
    
    # 참여 지표
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    reach_count = Column(Integer, default=0)
    engagement_rate = Column(Float)
    
    # 전환 추적
    click_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)
    revenue_attributed = Column(Float, default=0.0)
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class MarketingAnalytics(Base):
    """마케팅 분석 데이터"""
    __tablename__ = "marketing_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 분석 대상
    analytics_type = Column(String(50))  # campaign, channel, segment, product
    entity_id = Column(String(100))  # 대상 엔티티 ID
    entity_name = Column(String(200))
    
    # 기간
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    granularity = Column(String(20))  # hourly, daily, weekly, monthly
    
    # 기본 지표
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    
    # 비율 지표
    ctr = Column(Float)  # Click-through rate
    conversion_rate = Column(Float)
    bounce_rate = Column(Float)
    
    # 비용 지표
    cost = Column(Float, default=0.0)
    cpc = Column(Float)  # Cost per click
    cpa = Column(Float)  # Cost per acquisition
    roi = Column(Float)  # Return on investment
    roas = Column(Float)  # Return on ad spend
    
    # 고객 지표
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)
    customer_lifetime_value = Column(Float)
    
    # 참여 지표
    engagement_score = Column(Float)
    avg_session_duration = Column(Float)
    pages_per_session = Column(Float)
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    
    # 인덱스 설정을 위한 복합 인덱스
    __table_args__ = (
        Index('idx_analytics_type_entity', 'analytics_type', 'entity_id'),
        Index('idx_analytics_period', 'period_start', 'period_end'),
    )