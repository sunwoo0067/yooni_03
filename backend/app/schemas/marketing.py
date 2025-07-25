"""
마케팅 자동화 Pydantic 스키마
"""

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


# Enums
class CampaignTypeEnum(str, Enum):
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


class CampaignStatusEnum(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MessageStatusEnum(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    CONVERTED = "converted"
    FAILED = "failed"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


class PromotionCodeTypeEnum(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    FREE_SHIPPING = "free_shipping"
    BOGO = "bogo"


class TriggerTypeEnum(str, Enum):
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    BEHAVIOR_BASED = "behavior_based"
    LIFECYCLE_BASED = "lifecycle_based"
    CONDITION_BASED = "condition_based"


# Base schemas
class MarketingCampaignBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    campaign_type: CampaignTypeEnum
    subject: Optional[str] = Field(None, max_length=200)
    preview_text: Optional[str] = Field(None, max_length=200)
    content_template: Optional[str] = None
    personalization_tags: Optional[List[str]] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    schedule_type: Optional[str] = "immediate"
    schedule_config: Optional[Dict[str, Any]] = {}
    budget: Optional[float] = Field(None, ge=0)
    goal_type: Optional[str] = None
    goal_value: Optional[float] = None
    is_ab_test: Optional[bool] = False
    ab_test_config: Optional[Dict[str, Any]] = {}
    control_group_size: Optional[float] = Field(None, ge=0, le=1)


class MarketingCampaignCreate(MarketingCampaignBase):
    target_segment_ids: Optional[List[int]] = []
    target_conditions: Optional[Dict[str, Any]] = {}
    created_by: str


class MarketingCampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=200)
    preview_text: Optional[str] = Field(None, max_length=200)
    content_template: Optional[str] = None
    personalization_tags: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = Field(None, ge=0)
    goal_type: Optional[str] = None
    goal_value: Optional[float] = None
    target_segment_ids: Optional[List[int]] = None


class MarketingCampaignResponse(MarketingCampaignBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    campaign_uuid: str
    status: CampaignStatusEnum
    expected_recipients: Optional[int] = 0
    sent_count: Optional[int] = 0
    delivered_count: Optional[int] = 0
    opened_count: Optional[int] = 0
    clicked_count: Optional[int] = 0
    converted_count: Optional[int] = 0
    unsubscribed_count: Optional[int] = 0
    delivery_rate: Optional[float] = 0
    open_rate: Optional[float] = 0
    click_rate: Optional[float] = 0
    conversion_rate: Optional[float] = 0
    roi: Optional[float] = 0
    revenue_generated: Optional[float] = 0
    spent_amount: Optional[float] = 0
    created_at: datetime
    updated_at: datetime


class CampaignPerformance(BaseModel):
    campaign_id: int
    campaign_name: str
    status: str
    metrics: Dict[str, int]
    rates: Dict[str, float]
    financial: Dict[str, float]
    goal: Dict[str, Any]
    ab_test_results: Optional[List[Dict[str, Any]]] = None


# Marketing Segment schemas
class MarketingSegmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    segment_type: Optional[str] = "dynamic"
    rules: Optional[Dict[str, Any]] = {}
    is_active: Optional[bool] = True


class MarketingSegmentCreate(MarketingSegmentBase):
    pass


class MarketingSegmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MarketingSegmentResponse(MarketingSegmentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    customer_count: Optional[int] = 0
    last_calculated: Optional[datetime] = None
    average_ltv: Optional[float] = 0
    average_order_value: Optional[float] = 0
    churn_rate: Optional[float] = 0
    engagement_score: Optional[float] = 0
    is_system: Optional[bool] = False
    created_at: datetime
    updated_at: datetime


# Promotion Code schemas
class PromotionCodeBase(BaseModel):
    code_type: PromotionCodeTypeEnum
    discount_value: float = Field(..., gt=0)
    minimum_purchase: Optional[float] = Field(0, ge=0)
    maximum_discount: Optional[float] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    usage_per_customer: Optional[int] = Field(1, ge=1)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = True
    is_public: Optional[bool] = True


class PromotionCodeCreate(PromotionCodeBase):
    code: Optional[str] = Field(None, max_length=50)
    code_prefix: Optional[str] = ""
    code_length: Optional[int] = Field(8, ge=4, le=20)
    campaign_id: Optional[int] = None
    applicable_products: Optional[List[str]] = []
    applicable_categories: Optional[List[str]] = []
    excluded_products: Optional[List[str]] = []
    target_segment_id: Optional[int] = None
    target_customers: Optional[List[int]] = []


class PromotionCodeUpdate(BaseModel):
    discount_value: Optional[float] = Field(None, gt=0)
    minimum_purchase: Optional[float] = Field(None, ge=0)
    maximum_discount: Optional[float] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class PromotionCodeResponse(PromotionCodeBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    code: str
    campaign_id: Optional[int] = None
    current_usage: Optional[int] = 0
    redemption_count: Optional[int] = 0
    revenue_generated: Optional[float] = 0
    created_at: datetime
    updated_at: datetime


class PromotionValidation(BaseModel):
    code: str
    customer_id: int
    order_data: Dict[str, Any]


class PromotionValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    promotion_id: Optional[int] = None
    code_type: Optional[str] = None
    discount_value: Optional[float] = None
    discount_amount: Optional[float] = None
    final_amount: Optional[float] = None


# Automation Workflow schemas
class WorkflowNodeConfig(BaseModel):
    node_type: str
    node_name: str
    position: Optional[Dict[str, float]] = {"x": 0, "y": 0}
    config: Optional[Dict[str, Any]] = {}
    conditions: Optional[Dict[str, Any]] = {}
    next_nodes: Optional[List[int]] = []
    previous_nodes: Optional[List[int]] = []


class AutomationWorkflowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    workflow_type: Optional[str] = "custom"
    workflow_definition: Dict[str, Any]
    entry_conditions: Optional[Dict[str, Any]] = {}
    exit_conditions: Optional[Dict[str, Any]] = {}
    max_entries_per_customer: Optional[int] = Field(1, ge=1)
    cooldown_period_days: Optional[int] = Field(0, ge=0)
    is_active: Optional[bool] = True


class AutomationWorkflowCreate(AutomationWorkflowBase):
    nodes: List[WorkflowNodeConfig]


class AutomationWorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    workflow_definition: Optional[Dict[str, Any]] = None
    entry_conditions: Optional[Dict[str, Any]] = None
    exit_conditions: Optional[Dict[str, Any]] = None
    max_entries_per_customer: Optional[int] = Field(None, ge=1)
    cooldown_period_days: Optional[int] = Field(None, ge=0)
    nodes: Optional[List[WorkflowNodeConfig]] = None


class AutomationWorkflowResponse(AutomationWorkflowBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    workflow_uuid: str
    is_paused: Optional[bool] = False
    total_entries: Optional[int] = 0
    active_entries: Optional[int] = 0
    completed_entries: Optional[int] = 0
    conversion_rate: Optional[float] = 0
    average_revenue: Optional[float] = 0
    created_at: datetime
    updated_at: datetime


# A/B Testing schemas
class ABTestVariantCreate(BaseModel):
    variant_name: Optional[str] = None
    variant_type: str
    subject: Optional[str] = None
    content: Optional[str] = None
    cta_text: Optional[str] = None
    send_time: Optional[str] = None
    traffic_allocation: float = Field(..., gt=0, le=100)


class ABTestVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    campaign_id: int
    variant_name: str
    variant_type: str
    traffic_allocation: float
    assigned_count: Optional[int] = 0
    sent_count: Optional[int] = 0
    opened_count: Optional[int] = 0
    clicked_count: Optional[int] = 0
    converted_count: Optional[int] = 0
    open_rate: Optional[float] = 0
    click_rate: Optional[float] = 0
    conversion_rate: Optional[float] = 0
    confidence_level: Optional[float] = 0
    is_winner: Optional[bool] = False


class ABTestAnalysis(BaseModel):
    variants: List[Dict[str, Any]]
    winner: Optional[str] = None
    confidence_level: float
    recommendations: List[str]


# Social Media schemas
class SocialMediaPostBase(BaseModel):
    platform: str
    post_type: Optional[str] = "text"
    content: str
    media_urls: Optional[List[str]] = []
    hashtags: Optional[List[str]] = []
    mentions: Optional[List[str]] = []
    scheduled_at: Optional[datetime] = None


class SocialMediaPostCreate(SocialMediaPostBase):
    campaign_id: Optional[int] = None
    optimize_content: Optional[bool] = False
    publish_now: Optional[bool] = False


class SocialMediaPostUpdate(BaseModel):
    content: Optional[str] = None
    media_urls: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None


class SocialMediaPostResponse(SocialMediaPostBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    campaign_id: Optional[int] = None
    status: str
    platform_post_id: Optional[str] = None
    published_at: Optional[datetime] = None
    likes_count: Optional[int] = 0
    comments_count: Optional[int] = 0
    shares_count: Optional[int] = 0
    reach_count: Optional[int] = 0
    engagement_rate: Optional[float] = 0
    click_count: Optional[int] = 0
    conversion_count: Optional[int] = 0
    revenue_attributed: Optional[float] = 0
    created_at: datetime
    updated_at: datetime


# Email/SMS Service schemas
class EmailSendRequest(BaseModel):
    message_ids: List[int]
    batch_size: Optional[int] = Field(50, ge=1, le=1000)


class SMSSendRequest(BaseModel):
    message_ids: List[int]
    batch_size: Optional[int] = Field(100, ge=1, le=1000)


class EmailTemplateValidation(BaseModel):
    template: str


class SMSContentValidation(BaseModel):
    content: str


# Analytics schemas
class MarketingAnalyticsRequest(BaseModel):
    campaign_id: int


class MarketingDashboardRequest(BaseModel):
    start_date: datetime
    end_date: datetime


class CustomerJourneyRequest(BaseModel):
    customer_id: int


class MarketingAnalyticsResponse(BaseModel):
    campaign_id: int
    campaign_name: str
    analysis_date: str
    basic_metrics: Dict[str, Any]
    temporal_performance: Dict[str, Any]
    segment_performance: List[Dict[str, Any]]
    conversion_funnel: Dict[str, Any]
    roi_analysis: Dict[str, Any]
    ltv_impact: Dict[str, Any]
    channel_comparison: Dict[str, Any]
    recommendations: List[Dict[str, Any]]


# Personalization schemas
class PersonalizationRequest(BaseModel):
    customer_id: int
    template: str
    context: Optional[Dict[str, Any]] = {}


class ProductRecommendationRequest(BaseModel):
    customer_id: int
    recommendation_type: Optional[str] = "collaborative"
    limit: Optional[int] = Field(10, ge=1, le=50)


class PersonalizationInsightsResponse(BaseModel):
    customer_id: int
    profile: Dict[str, Any]
    preferences: Dict[str, Any]
    behavior_patterns: Dict[str, Any]
    engagement_score: float
    personalization_opportunities: List[Dict[str, Any]]
    recommended_actions: List[Dict[str, Any]]


# Retargeting schemas
class CartAbandonmentCampaignRequest(BaseModel):
    name: Optional[str] = None
    hours_since_abandonment: Optional[int] = Field(24, ge=1, le=168)
    min_cart_value: Optional[float] = Field(0, ge=0)
    campaign_type: Optional[str] = "email"
    subject: Optional[str] = None
    schedule_type: Optional[str] = "immediate"
    created_by: Optional[str] = "system"


class BrowseAbandonmentCampaignRequest(BaseModel):
    name: Optional[str] = None
    days_since_browse: Optional[int] = Field(3, ge=1, le=30)
    min_product_views: Optional[int] = Field(3, ge=1)
    campaign_type: Optional[str] = "email"
    subject: Optional[str] = None
    schedule_type: Optional[str] = "immediate"
    created_by: Optional[str] = "system"


class CustomerWinbackCampaignRequest(BaseModel):
    name: Optional[str] = None
    days_inactive: Optional[int] = Field(90, ge=30, le=365)
    min_previous_orders: Optional[int] = Field(1, ge=1)
    campaign_type: Optional[str] = "email"
    subject: Optional[str] = None
    schedule_type: Optional[str] = "immediate"
    created_by: Optional[str] = "system"


class PostPurchaseCampaignRequest(BaseModel):
    name: Optional[str] = None
    days_since_purchase: Optional[int] = Field(7, ge=1, le=30)
    post_purchase_type: str = Field(..., pattern="^(review_request|cross_sell|repurchase)$")
    campaign_type: Optional[str] = "email"
    subject: Optional[str] = None
    schedule_type: Optional[str] = "immediate"
    created_by: Optional[str] = "system"


class RetargetingAnalysisRequest(BaseModel):
    campaign_ids: List[int]


# Bulk operation schemas
class BulkPromotionCodeRequest(BaseModel):
    count: int = Field(..., ge=1, le=10000)
    prefix: Optional[str] = ""
    base_data: PromotionCodeCreate
    individual_settings: Optional[Dict[int, Dict[str, Any]]] = {}


class BulkEmailScheduleRequest(BaseModel):
    posts_data: List[SocialMediaPostCreate]


# Trigger schemas
class AutomationTriggerCreate(BaseModel):
    trigger_name: str
    trigger_type: TriggerTypeEnum
    event_name: str
    conditions: Optional[Dict[str, Any]] = {}
    delay_minutes: Optional[int] = Field(0, ge=0)
    priority: Optional[int] = Field(5, ge=1, le=10)
    campaign_id: Optional[int] = None
    workflow_id: Optional[int] = None
    is_active: Optional[bool] = True


class AutomationTriggerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    trigger_name: str
    trigger_type: TriggerTypeEnum
    event_name: str
    conditions: Dict[str, Any]
    delay_minutes: int
    priority: int
    is_active: bool
    last_triggered: Optional[datetime] = None
    trigger_count: Optional[int] = 0
    created_at: datetime


# Event trigger schemas
class TriggerEventRequest(BaseModel):
    event_name: str
    customer_id: Optional[int] = None
    event_data: Dict[str, Any] = {}


# Workflow execution schemas
class WorkflowExecutionStart(BaseModel):
    workflow_id: int
    customer_id: int
    context: Optional[Dict[str, Any]] = {}


class WorkflowExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    workflow_id: int
    customer_id: int
    execution_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_node_id: Optional[int] = None
    execution_path: Optional[List[int]] = []
    node_results: Optional[Dict[str, Any]] = {}
    converted: Optional[bool] = False
    conversion_value: Optional[float] = 0
    error_message: Optional[str] = None