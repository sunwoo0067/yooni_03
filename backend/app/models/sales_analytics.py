"""
Sales analytics and performance tracking models
"""
from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Text, DateTime, Date, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel


class MarketplaceType(str, Enum):
    """Supported marketplaces"""
    COUPANG = "coupang"
    NAVER = "naver"
    ELEVENTH_STREET = "11st"
    GMARKET = "gmarket"
    AUCTION = "auction"
    INTERPARK = "interpark"
    WE_MAKE_PRICE = "wemakeprice"
    TMON = "tmon"


class DataCollectionStatus(str, Enum):
    """Data collection status"""
    PENDING = "pending"
    COLLECTING = "collecting"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SalesAnalytics(BaseModel):
    """Sales performance data from marketplaces"""
    __tablename__ = "sales_analytics"
    
    # Product identification
    product_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_code = Column(String(100), nullable=True)
    product_name = Column(String(500), nullable=True)
    
    # Platform information
    marketplace = Column(String(50), nullable=False, index=True)
    platform_account_id = Column(UUID(as_uuid=True), nullable=True)
    platform_product_id = Column(String(100), nullable=True)
    
    # Date tracking
    collection_date = Column(Date, nullable=False, index=True)
    data_period_start = Column(Date, nullable=False)
    data_period_end = Column(Date, nullable=False)
    
    # Sales metrics
    sales_volume = Column(Integer, default=0)  # Units sold
    revenue = Column(Numeric(12, 2), default=0.00)  # Total revenue
    profit = Column(Numeric(12, 2), default=0.00)  # Net profit
    cost = Column(Numeric(12, 2), default=0.00)  # Total cost
    
    # Traffic metrics
    page_views = Column(Integer, default=0)
    unique_visitors = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    impression_count = Column(Integer, default=0)
    
    # Conversion metrics
    conversion_rate = Column(Numeric(5, 4), default=0.0000)  # Click to purchase
    view_to_cart_rate = Column(Numeric(5, 4), default=0.0000)
    cart_to_purchase_rate = Column(Numeric(5, 4), default=0.0000)
    
    # Engagement metrics
    wishlist_adds = Column(Integer, default=0)
    reviews_count = Column(Integer, default=0)
    questions_count = Column(Integer, default=0)
    average_rating = Column(Numeric(3, 2), default=0.00)
    
    # Search and discovery
    search_ranking_avg = Column(Numeric(8, 2), default=0.00)
    search_keywords = Column(JSONB, nullable=True)  # Top keywords
    traffic_sources = Column(JSONB, nullable=True)  # Source breakdown
    
    # Competitive data
    competitor_data = Column(JSONB, nullable=True)
    market_share = Column(Numeric(5, 4), default=0.0000)
    
    # Pricing analytics
    price_history = Column(JSONB, nullable=True)
    competitor_prices = Column(JSONB, nullable=True)
    price_competitiveness = Column(Numeric(5, 2), default=0.00)
    
    # Additional metrics
    return_rate = Column(Numeric(5, 4), default=0.0000)
    refund_amount = Column(Numeric(10, 2), default=0.00)
    customer_acquisition_cost = Column(Numeric(8, 2), default=0.00)
    lifetime_value = Column(Numeric(10, 2), default=0.00)
    
    # Data quality
    data_completeness = Column(Numeric(5, 2), default=0.00)  # Percentage
    collection_method = Column(String(50), nullable=True)  # api, scraping, manual
    
    def calculate_roi(self) -> float:
        """Calculate return on investment"""
        if self.cost <= 0:
            return 0.0
        return float((self.profit / self.cost) * 100)
    
    def calculate_margin(self) -> float:
        """Calculate profit margin"""
        if self.revenue <= 0:
            return 0.0
        return float((self.profit / self.revenue) * 100)


class MarketplaceSession(BaseModel):
    """Marketplace scraping session tracking"""
    __tablename__ = "marketplace_sessions"
    
    marketplace = Column(String(50), nullable=False)
    account_identifier = Column(String(100), nullable=False)
    session_type = Column(String(50), nullable=False)  # analytics, products, orders
    
    # Session details
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(20), default=DataCollectionStatus.PENDING)
    
    # Collection scope
    target_date_start = Column(Date, nullable=False)
    target_date_end = Column(Date, nullable=False)
    target_products = Column(JSONB, nullable=True)  # Product IDs to collect
    
    # Results
    total_items_target = Column(Integer, default=0)
    total_items_collected = Column(Integer, default=0)
    total_items_failed = Column(Integer, default=0)
    
    # Technical details
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    proxy_used = Column(String(100), nullable=True)
    
    # Performance
    request_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    rate_limit_hits = Column(Integer, default=0)
    avg_response_time = Column(Numeric(8, 3), default=0.000)
    
    # Session data
    session_cookies = Column(Text, nullable=True)  # Encrypted
    session_config = Column(JSONB, nullable=True)
    error_log = Column(Text, nullable=True)
    
    def calculate_success_rate(self) -> float:
        """Calculate collection success rate"""
        if self.total_items_target == 0:
            return 0.0
        return (self.total_items_collected / self.total_items_target) * 100


class TrafficSource(BaseModel):
    """Traffic source analysis"""
    __tablename__ = "traffic_sources"
    
    analytics_id = Column(UUID(as_uuid=True), ForeignKey("sales_analytics.id"), nullable=False)
    
    source_type = Column(String(50), nullable=False)  # organic, paid, direct, referral
    source_name = Column(String(100), nullable=False)  # google, naver, facebook, etc.
    medium = Column(String(50), nullable=True)  # cpc, banner, email, etc.
    campaign = Column(String(100), nullable=True)
    
    # Metrics
    sessions = Column(Integer, default=0)
    users = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    bounces = Column(Integer, default=0)
    transactions = Column(Integer, default=0)
    revenue = Column(Numeric(10, 2), default=0.00)
    
    # Calculated metrics
    bounce_rate = Column(Numeric(5, 4), default=0.0000)
    conversion_rate = Column(Numeric(5, 4), default=0.0000)
    avg_session_value = Column(Numeric(8, 2), default=0.00)
    
    # Relationships
    analytics = relationship("SalesAnalytics")


class SearchKeyword(BaseModel):
    """Search keyword performance"""
    __tablename__ = "search_keywords"
    
    analytics_id = Column(UUID(as_uuid=True), ForeignKey("sales_analytics.id"), nullable=False)
    
    keyword = Column(String(200), nullable=False)
    search_volume = Column(Integer, default=0)
    ranking_position = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    impression_count = Column(Integer, default=0)
    
    # Performance metrics
    click_through_rate = Column(Numeric(5, 4), default=0.0000)
    conversion_count = Column(Integer, default=0)
    conversion_rate = Column(Numeric(5, 4), default=0.0000)
    revenue = Column(Numeric(10, 2), default=0.00)
    
    # Keyword analysis
    keyword_type = Column(String(50), nullable=True)  # brand, generic, competitor
    intent_type = Column(String(50), nullable=True)  # informational, commercial, transactional
    competition_level = Column(String(20), nullable=True)  # low, medium, high
    
    # Relationships
    analytics = relationship("SalesAnalytics")


class CompetitorAnalysis(BaseModel):
    """Competitor product analysis"""
    __tablename__ = "competitor_analysis"
    
    analytics_id = Column(UUID(as_uuid=True), ForeignKey("sales_analytics.id"), nullable=False)
    
    competitor_name = Column(String(200), nullable=False)
    competitor_product_id = Column(String(100), nullable=True)
    competitor_product_url = Column(String(1000), nullable=True)
    
    # Product comparison
    price = Column(Numeric(10, 2), nullable=True)
    discount_rate = Column(Numeric(5, 2), default=0.00)
    rating = Column(Numeric(3, 2), nullable=True)
    review_count = Column(Integer, default=0)
    
    # Performance metrics
    estimated_sales = Column(Integer, default=0)
    ranking_position = Column(Integer, default=0)
    availability_status = Column(String(50), nullable=True)
    
    # Feature comparison
    feature_comparison = Column(JSONB, nullable=True)
    content_quality_score = Column(Numeric(5, 2), default=0.00)
    
    # Market positioning
    price_competitiveness = Column(Numeric(5, 2), default=0.00)
    feature_competitiveness = Column(Numeric(5, 2), default=0.00)
    overall_competitiveness = Column(Numeric(5, 2), default=0.00)
    
    # Relationships
    analytics = relationship("SalesAnalytics")


class PerformanceReport(BaseModel):
    """Aggregated performance reports"""
    __tablename__ = "performance_reports"
    
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly, quarterly
    report_date = Column(Date, nullable=False, index=True)
    
    # Scope
    marketplace = Column(String(50), nullable=True)
    product_category = Column(String(100), nullable=True)
    product_ids = Column(JSONB, nullable=True)  # Products included
    
    # Performance metrics
    total_products = Column(Integer, default=0)
    active_products = Column(Integer, default=0)
    
    # Sales performance
    total_revenue = Column(Numeric(15, 2), default=0.00)
    total_profit = Column(Numeric(15, 2), default=0.00)
    total_cost = Column(Numeric(15, 2), default=0.00)
    total_sales_volume = Column(Integer, default=0)
    
    # Operational metrics
    sourcing_accuracy = Column(Numeric(5, 2), default=0.00)
    processing_effectiveness = Column(Numeric(5, 2), default=0.00)
    registration_success_rate = Column(Numeric(5, 2), default=0.00)
    
    # AI performance
    ai_prediction_accuracy = Column(Numeric(5, 2), default=0.00)
    ai_processing_time_avg = Column(Numeric(8, 2), default=0.00)
    ai_cost_per_product = Column(Numeric(6, 4), default=0.0000)
    
    # Trends and insights
    growth_rate = Column(Numeric(8, 4), default=0.0000)
    trend_direction = Column(String(20), nullable=True)  # up, down, stable
    
    # Cost analysis
    cost_analysis = Column(JSONB, nullable=True)
    profit_analysis = Column(JSONB, nullable=True)
    
    # Recommendations
    recommendations = Column(JSONB, nullable=True)
    action_items = Column(JSONB, nullable=True)
    
    # Report metadata
    generated_by = Column(String(100), nullable=True)
    generation_time_seconds = Column(Integer, default=0)
    data_sources = Column(JSONB, nullable=True)
    
    def calculate_roi(self) -> float:
        """Calculate overall ROI"""
        if self.total_cost <= 0:
            return 0.0
        return float((self.total_profit / self.total_cost) * 100)
    
    def calculate_margin(self) -> float:
        """Calculate overall profit margin"""
        if self.total_revenue <= 0:
            return 0.0
        return float((self.total_profit / self.total_revenue) * 100)


class DataCollectionLog(BaseModel):
    """Log of data collection activities"""
    __tablename__ = "data_collection_logs"
    
    session_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_sessions.id"), nullable=False)
    
    # Collection details
    target_url = Column(String(1000), nullable=False)
    method = Column(String(20), nullable=False)  # GET, POST
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Request details
    request_headers = Column(JSONB, nullable=True)
    request_data = Column(Text, nullable=True)
    
    # Response details
    response_size_bytes = Column(Integer, nullable=True)
    response_headers = Column(JSONB, nullable=True)
    
    # Collection result
    success = Column(Boolean, default=False)
    data_extracted = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    # Anti-detection measures
    captcha_encountered = Column(Boolean, default=False)
    rate_limited = Column(Boolean, default=False)
    ip_blocked = Column(Boolean, default=False)
    
    # Extracted data summary
    data_points_extracted = Column(Integer, default=0)
    data_quality_score = Column(Numeric(5, 2), default=0.00)
    
    # Relationships
    session = relationship("MarketplaceSession")