"""Database models for the Dropship Market AI System"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, 
    Text, JSON, DECIMAL, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

Base = declarative_base()


class MarketRawData(Base):
    """Store raw API data from marketplaces"""
    __tablename__ = 'market_raw_data'
    
    id = Column(Integer, primary_key=True)
    marketplace = Column(String(50), nullable=False, index=True)
    api_endpoint = Column(String(200), nullable=False)
    raw_data = Column(JSONB, nullable=False)
    collected_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed = Column(Boolean, default=False, index=True)
    processing_error = Column(Text)
    
    __table_args__ = (
        Index('idx_marketplace_endpoint', 'marketplace', 'api_endpoint'),
        Index('idx_collected_processed', 'collected_at', 'processed'),
    )


class Product(Base):
    """Product master table"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    product_code = Column(String(100), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    category = Column(String(200))
    brand = Column(String(100))
    cost_price = Column(DECIMAL(12, 2))
    target_margin = Column(Float, default=0.3)
    status = Column(String(20), default='active', index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    marketplace_products = relationship("MarketplaceProduct", back_populates="product")
    performances = relationship("ProductPerformance", back_populates="product")
    predictions = relationship("AIPrediction", back_populates="product")
    rotations = relationship("RotationHistory", back_populates="product")


class MarketplaceProduct(Base):
    """Product listings on different marketplaces"""
    __tablename__ = 'marketplace_products'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    marketplace = Column(String(50), nullable=False)
    marketplace_product_id = Column(String(100), nullable=False)
    listing_url = Column(String(500))
    current_price = Column(DECIMAL(12, 2))
    listing_status = Column(String(20), default='active')
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="marketplace_products")
    
    __table_args__ = (
        UniqueConstraint('marketplace', 'marketplace_product_id'),
        Index('idx_product_marketplace', 'product_id', 'marketplace'),
    )


class ProductPerformance(Base):
    """Daily product performance metrics"""
    __tablename__ = 'product_performance'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    marketplace = Column(String(50), nullable=False)
    date = Column(Date, nullable=False, index=True)
    
    # Traffic metrics
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    wish_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    # Sales metrics
    conversions = Column(Integer, default=0)
    sales_volume = Column(Integer, default=0)
    revenue = Column(DECIMAL(12, 2), default=0)
    profit = Column(DECIMAL(12, 2), default=0)
    
    # Ranking metrics
    category_ranking = Column(Integer)
    search_ranking = Column(JSONB)  # {"keyword": ranking}
    
    # Competition metrics
    competitor_count = Column(Integer)
    price_position = Column(Float)  # Percentile in category
    
    # Relationships
    product = relationship("Product", back_populates="performances")
    
    __table_args__ = (
        UniqueConstraint('product_id', 'marketplace', 'date'),
        Index('idx_performance_date', 'date'),
        Index('idx_product_marketplace_date', 'product_id', 'marketplace', 'date'),
    )


class Review(Base):
    """Product reviews from marketplaces"""
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    marketplace = Column(String(50), nullable=False)
    review_id = Column(String(100), nullable=False)
    rating = Column(Integer, nullable=False)
    title = Column(String(500))
    content = Column(Text)
    reviewer_name = Column(String(100))
    verified_purchase = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)
    images_count = Column(Integer, default=0)
    created_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analytics = relationship("ReviewAnalytics", back_populates="review", uselist=False)
    
    __table_args__ = (
        UniqueConstraint('marketplace', 'review_id'),
        Index('idx_product_rating', 'product_id', 'rating'),
        Index('idx_created_at', 'created_at'),
    )


class ReviewAnalytics(Base):
    """AI-analyzed review data"""
    __tablename__ = 'review_analytics'
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey('reviews.id'), unique=True, nullable=False)
    
    # Sentiment analysis
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_label = Column(String(20))  # positive, negative, neutral
    
    # Extracted information
    key_phrases = Column(JSONB)  # ["품질 좋음", "배송 빠름"]
    product_aspects = Column(JSONB)  # {"quality": 0.8, "shipping": 0.9}
    mentioned_features = Column(JSONB)  # ["size", "color", "material"]
    improvement_suggestions = Column(JSONB)  # ["포장 개선 필요"]
    
    # Classification
    customer_type = Column(String(50))  # new, repeat, vip
    review_category = Column(String(50))  # complaint, praise, suggestion
    
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    review = relationship("Review", back_populates="analytics")


class RotationHistory(Base):
    """Product rotation history"""
    __tablename__ = 'rotation_history'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    marketplace = Column(String(50), nullable=False)
    rotation_strategy = Column(String(50), nullable=False)
    
    # Rotation metrics
    previous_rank = Column(Integer)
    new_rank = Column(Integer)
    previous_sales_7d = Column(Integer)
    new_sales_7d = Column(Integer)
    performance_change = Column(Float)  # Percentage
    
    # Rotation details
    old_listing_id = Column(String(100))
    new_listing_id = Column(String(100))
    changes_made = Column(JSONB)  # {"title": true, "images": true, "price": false}
    
    rotated_at = Column(DateTime, default=datetime.utcnow)
    evaluated_at = Column(DateTime)
    
    # Relationships
    product = relationship("Product", back_populates="rotations")
    
    __table_args__ = (
        Index('idx_rotation_product_date', 'product_id', 'rotated_at'),
    )


class AIPrediction(Base):
    """AI model predictions"""
    __tablename__ = 'ai_predictions'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    prediction_type = Column(String(50), nullable=False)  # sales, price, inventory
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20))
    
    # Prediction data
    predictions = Column(JSONB, nullable=False)
    confidence_score = Column(Float)
    feature_importance = Column(JSONB)
    
    # Temporal info
    prediction_date = Column(Date, nullable=False)
    prediction_horizon_days = Column(Integer)
    predicted_at = Column(DateTime, default=datetime.utcnow)
    
    # Evaluation
    actual_values = Column(JSONB)
    evaluation_metrics = Column(JSONB)  # {"mae": 0.1, "rmse": 0.2}
    evaluated_at = Column(DateTime)
    
    # Relationships
    product = relationship("Product", back_populates="predictions")
    
    __table_args__ = (
        Index('idx_prediction_type_date', 'prediction_type', 'prediction_date'),
        Index('idx_product_type_date', 'product_id', 'prediction_type', 'prediction_date'),
    )


class MarketOptimization(Base):
    """A/B testing and optimization history"""
    __tablename__ = 'market_optimizations'
    
    id = Column(Integer, primary_key=True)
    optimization_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    marketplace = Column(String(50), nullable=False)
    optimization_type = Column(String(50), nullable=False)  # title, price, image, keyword
    
    # Test configuration
    test_name = Column(String(200))
    control_variant = Column(JSONB)
    test_variants = Column(JSONB)  # [{"name": "A", "changes": {...}}]
    
    # Test results
    status = Column(String(20), default='running')  # running, completed, cancelled
    winner_variant = Column(String(50))
    metrics = Column(JSONB)  # {"conversion_rate": {"control": 0.02, "A": 0.03}}
    statistical_significance = Column(Float)
    
    # Temporal info
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_optimization_status', 'status'),
        Index('idx_product_type', 'product_id', 'optimization_type'),
    )


class Alert(Base):
    """System alerts and notifications"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)  # sales_drop, review_alert, inventory_low
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Alert details
    product_id = Column(Integer, ForeignKey('products.id'))
    marketplace = Column(String(50))
    message = Column(Text, nullable=False)
    details = Column(JSONB)
    
    # Status tracking
    status = Column(String(20), default='active')  # active, acknowledged, resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # Notification tracking
    notifications_sent = Column(JSONB)  # {"email": true, "slack": true}
    
    __table_args__ = (
        Index('idx_alert_status_type', 'status', 'alert_type'),
        Index('idx_created_at_severity', 'created_at', 'severity'),
    )


class DashboardMetrics(Base):
    """Pre-calculated metrics for dashboard performance"""
    __tablename__ = 'dashboard_metrics'
    
    id = Column(Integer, primary_key=True)
    metric_date = Column(Date, nullable=False)
    metric_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    
    # Aggregated metrics
    total_revenue = Column(DECIMAL(12, 2))
    total_profit = Column(DECIMAL(12, 2))
    total_orders = Column(Integer)
    average_order_value = Column(DECIMAL(12, 2))
    
    # Performance metrics
    conversion_rate = Column(Float)
    return_rate = Column(Float)
    average_rating = Column(Float)
    
    # Marketplace breakdown
    marketplace_metrics = Column(JSONB)
    category_metrics = Column(JSONB)
    top_products = Column(JSONB)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('metric_date', 'metric_type'),
        Index('idx_metrics_date_type', 'metric_date', 'metric_type'),
    )