"""
Product registration models for multi-platform dropshipping
"""
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import (
    Boolean, Column, String, Text, DateTime, Integer, 
    ForeignKey, Enum as SQLEnum, Numeric, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import enum
import uuid

from .base import BaseModel


class RegistrationStatus(enum.Enum):
    """Product registration status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"
    RETRY_SCHEDULED = "retry_scheduled"


class RegistrationPriority(enum.Enum):
    """Registration priority levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    URGENT = "urgent"


class ImageProcessingStatus(enum.Enum):
    """Image processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProductRegistrationBatch(BaseModel):
    """Batch registration management"""
    __tablename__ = "product_registration_batches"
    
    # Basic Information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    batch_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Batch Configuration
    target_platforms = Column(ARRAY(String), nullable=False)  # List of platform types
    priority = Column(SQLEnum(RegistrationPriority), default=RegistrationPriority.MEDIUM, nullable=False)
    
    # Status Tracking
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False, index=True)
    total_products = Column(Integer, default=0, nullable=False)
    completed_products = Column(Integer, default=0, nullable=False)
    failed_products = Column(Integer, default=0, nullable=False)
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=True, index=True)
    started_at = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    
    # Configuration
    batch_settings = Column(JSONB, nullable=True)  # Batch-specific settings
    auto_retry_enabled = Column(Boolean, default=True, nullable=False)
    max_retry_attempts = Column(Integer, default=3, nullable=False)
    retry_delay_minutes = Column(Integer, default=30, nullable=False)
    
    # Progress Tracking
    progress_percentage = Column(Numeric(5, 2), default=0.0, nullable=False)
    estimated_completion_time = Column(DateTime, nullable=True)
    
    # Error Handling
    error_summary = Column(JSONB, nullable=True)
    last_error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="registration_batches")
    product_registrations = relationship("ProductRegistration", back_populates="batch", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProductRegistrationBatch(name={self.batch_name}, status={self.status.value})>"
    
    def calculate_progress(self):
        """Calculate and update progress percentage"""
        if self.total_products == 0:
            self.progress_percentage = 0.0
        else:
            completed = self.completed_products + self.failed_products
            self.progress_percentage = (completed / self.total_products) * 100
    
    def is_completed(self) -> bool:
        """Check if batch is completed"""
        return self.status in [RegistrationStatus.COMPLETED, RegistrationStatus.PARTIALLY_COMPLETED]
    
    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_products == 0:
            return 0.0
        return (self.completed_products / self.total_products) * 100


class ProductRegistration(BaseModel):
    """Individual product registration record"""
    __tablename__ = "product_registrations"
    
    # Basic Information
    batch_id = Column(UUID(as_uuid=True), ForeignKey("product_registration_batches.id"), nullable=False, index=True)
    source_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True)
    
    # Product Data
    product_name = Column(String(500), nullable=False)
    product_description = Column(Text, nullable=True)
    category_id = Column(String(100), nullable=True)
    brand = Column(String(200), nullable=True)
    
    # Pricing
    original_price = Column(Numeric(12, 2), nullable=True)
    sale_price = Column(Numeric(12, 2), nullable=False)
    cost_price = Column(Numeric(12, 2), nullable=True)
    
    # Inventory
    stock_quantity = Column(Integer, default=0, nullable=False)
    weight = Column(Numeric(8, 3), nullable=True)
    dimensions = Column(JSONB, nullable=True)  # {length, width, height}
    
    # Media
    main_image_url = Column(String(1000), nullable=True)
    additional_images = Column(ARRAY(String), nullable=True)
    image_processing_status = Column(SQLEnum(ImageProcessingStatus), default=ImageProcessingStatus.PENDING, nullable=False)
    processed_images = Column(JSONB, nullable=True)  # Platform-specific processed images
    
    # Product Details
    attributes = Column(JSONB, nullable=True)  # Product attributes
    keywords = Column(ARRAY(String), nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # Registration Status
    overall_status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False, index=True)
    platform_statuses = Column(JSONB, nullable=True)  # Status per platform
    
    # Timing
    scheduled_at = Column(DateTime, nullable=True, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    platform_product_ids = Column(JSONB, nullable=True)  # Mapping of platform -> product_id
    registration_results = Column(JSONB, nullable=True)  # Detailed results per platform
    
    # Error Handling
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime, nullable=True)
    error_details = Column(JSONB, nullable=True)
    
    # Relationships
    batch = relationship("ProductRegistrationBatch", back_populates="product_registrations")
    source_product = relationship("Product", foreign_keys=[source_product_id])
    platform_registrations = relationship("PlatformProductRegistration", back_populates="product_registration", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProductRegistration(name={self.product_name}, status={self.overall_status.value})>"
    
    def can_retry(self, max_attempts: int = 3) -> bool:
        """Check if registration can be retried"""
        return (
            self.overall_status == RegistrationStatus.FAILED and
            self.retry_count < max_attempts
        )
    
    def get_platform_status(self, platform: str) -> str:
        """Get status for specific platform"""
        if not self.platform_statuses:
            return RegistrationStatus.PENDING.value
        return self.platform_statuses.get(platform, RegistrationStatus.PENDING.value)
    
    def update_platform_status(self, platform: str, status: str, result: dict = None):
        """Update status for specific platform"""
        if not self.platform_statuses:
            self.platform_statuses = {}
        if not self.registration_results:
            self.registration_results = {}
            
        self.platform_statuses[platform] = status
        if result:
            self.registration_results[platform] = result
        
        # Update overall status based on platform statuses
        self._update_overall_status()
    
    def _update_overall_status(self):
        """Update overall status based on platform statuses"""
        if not self.platform_statuses:
            return
        
        statuses = list(self.platform_statuses.values())
        
        if all(s == RegistrationStatus.COMPLETED.value for s in statuses):
            self.overall_status = RegistrationStatus.COMPLETED
        elif all(s == RegistrationStatus.FAILED.value for s in statuses):
            self.overall_status = RegistrationStatus.FAILED
        elif any(s == RegistrationStatus.IN_PROGRESS.value for s in statuses):
            self.overall_status = RegistrationStatus.IN_PROGRESS
        elif any(s == RegistrationStatus.COMPLETED.value for s in statuses):
            self.overall_status = RegistrationStatus.PARTIALLY_COMPLETED
        else:
            self.overall_status = RegistrationStatus.PENDING


class PlatformProductRegistration(BaseModel):
    """Platform-specific registration details"""
    __tablename__ = "platform_product_registrations"
    
    # References
    product_registration_id = Column(UUID(as_uuid=True), ForeignKey("product_registrations.id"), nullable=False, index=True)
    platform_account_id = Column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False, index=True)
    platform_type = Column(String(50), nullable=False, index=True)
    
    # Platform-specific Data
    platform_product_data = Column(JSONB, nullable=False)  # Transformed product data for platform
    platform_product_id = Column(String(200), nullable=True, index=True)
    platform_sku = Column(String(200), nullable=True, index=True)
    platform_url = Column(String(1000), nullable=True)
    
    # Status
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False, index=True)
    
    # Timing
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # API Details
    api_request_data = Column(JSONB, nullable=True)
    api_response_data = Column(JSONB, nullable=True)
    api_call_count = Column(Integer, default=0, nullable=False)
    
    # Error Handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime, nullable=True)
    
    # Validation
    validation_errors = Column(JSONB, nullable=True)
    validation_warnings = Column(JSONB, nullable=True)
    
    # Relationships
    product_registration = relationship("ProductRegistration", back_populates="platform_registrations")
    platform_account = relationship("PlatformAccount")
    
    def __repr__(self):
        return f"<PlatformProductRegistration(platform={self.platform_type}, status={self.status.value})>"


class RegistrationQueue(BaseModel):
    """Queue management for product registrations"""
    __tablename__ = "registration_queue"
    
    # Queue Information
    queue_name = Column(String(100), nullable=False, index=True)
    priority = Column(SQLEnum(RegistrationPriority), default=RegistrationPriority.MEDIUM, nullable=False, index=True)
    
    # Task Details
    task_type = Column(String(50), nullable=False, index=True)  # batch_registration, single_registration, retry
    task_data = Column(JSONB, nullable=False)
    
    # References
    batch_id = Column(UUID(as_uuid=True), ForeignKey("product_registration_batches.id"), nullable=True, index=True)
    product_registration_id = Column(UUID(as_uuid=True), ForeignKey("product_registrations.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Status
    status = Column(String(20), default="queued", nullable=False, index=True)  # queued, processing, completed, failed
    
    # Timing
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Processing
    worker_id = Column(String(100), nullable=True)
    processing_time_seconds = Column(Integer, nullable=True)
    
    # Results
    result_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Retry Management
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Relationships
    batch = relationship("ProductRegistrationBatch")
    product_registration = relationship("ProductRegistration")
    user = relationship("User")
    
    def __repr__(self):
        return f"<RegistrationQueue(task_type={self.task_type}, status={self.status})>"
    
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.retry_count < self.max_retries and self.status == "failed"


class ImageProcessingJob(BaseModel):
    """Image processing job tracking"""
    __tablename__ = "image_processing_jobs"
    
    # References
    product_registration_id = Column(UUID(as_uuid=True), ForeignKey("product_registrations.id"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("product_registration_batches.id"), nullable=True, index=True)
    
    # Image Information
    source_image_url = Column(String(1000), nullable=False)
    image_type = Column(String(20), nullable=False)  # main, additional
    image_index = Column(Integer, default=0, nullable=False)
    
    # Processing Configuration
    target_platforms = Column(ARRAY(String), nullable=False)
    processing_rules = Column(JSONB, nullable=True)  # Platform-specific rules
    
    # Status
    status = Column(SQLEnum(ImageProcessingStatus), default=ImageProcessingStatus.PENDING, nullable=False, index=True)
    
    # Timing
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    processed_images = Column(JSONB, nullable=True)  # Platform -> processed image URLs
    supabase_urls = Column(JSONB, nullable=True)  # Supabase storage URLs
    processing_details = Column(JSONB, nullable=True)
    
    # Error Handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    product_registration = relationship("ProductRegistration")
    batch = relationship("ProductRegistrationBatch")
    
    def __repr__(self):
        return f"<ImageProcessingJob(image_type={self.image_type}, status={self.status.value})>"


class PlatformRegistrationTemplate(BaseModel):
    """Templates for platform-specific registration"""
    __tablename__ = "platform_registration_templates"
    
    # Basic Information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    template_name = Column(String(200), nullable=False)
    platform_type = Column(String(50), nullable=False, index=True)
    
    # Template Configuration
    category_id = Column(String(100), nullable=True)
    default_attributes = Column(JSONB, nullable=True)
    pricing_rules = Column(JSONB, nullable=True)
    image_rules = Column(JSONB, nullable=True)
    
    # Mapping Rules
    field_mappings = Column(JSONB, nullable=True)  # Source field -> Platform field mappings
    transformation_rules = Column(JSONB, nullable=True)
    validation_rules = Column(JSONB, nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Usage Statistics
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<PlatformRegistrationTemplate(name={self.template_name}, platform={self.platform_type})>"