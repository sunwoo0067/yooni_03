"""
Pydantic schemas for product registration API
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum


class RegistrationPriorityEnum(str, Enum):
    """Registration priority options"""
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class RegistrationStatusEnum(str, Enum):
    """Registration status options"""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    partially_completed = "partially_completed"
    cancelled = "cancelled"
    retry_scheduled = "retry_scheduled"


class PlatformTypeEnum(str, Enum):
    """Supported platform types"""
    coupang = "coupang"
    naver = "naver"
    eleven_st = "11st"
    gmarket = "gmarket"
    auction = "auction"
    tmon = "tmon"
    wemakeprice = "wemakeprice"
    interpark = "interpark"


class ProductDimensions(BaseModel):
    """Product dimensions"""
    length: Optional[float] = Field(None, ge=0, description="Length in cm")
    width: Optional[float] = Field(None, ge=0, description="Width in cm")
    height: Optional[float] = Field(None, ge=0, description="Height in cm")


class ProductData(BaseModel):
    """Product data for registration"""
    name: str = Field(..., min_length=1, max_length=500, description="Product name")
    description: Optional[str] = Field(None, max_length=5000, description="Product description")
    category_id: Optional[str] = Field(None, max_length=100, description="Category ID")
    brand: Optional[str] = Field(None, max_length=200, description="Brand name")
    
    # Pricing
    price: Decimal = Field(..., gt=0, description="Sale price")
    original_price: Optional[Decimal] = Field(None, gt=0, description="Original price")
    cost_price: Optional[Decimal] = Field(None, ge=0, description="Cost price")
    
    # Inventory
    stock_quantity: int = Field(0, ge=0, description="Stock quantity")
    weight: Optional[float] = Field(None, ge=0, description="Weight in kg")
    dimensions: Optional[ProductDimensions] = Field(None, description="Product dimensions")
    
    # Media
    main_image_url: Optional[str] = Field(None, description="Main product image URL")
    additional_images: Optional[List[str]] = Field([], description="Additional image URLs")
    
    # Metadata
    attributes: Optional[Dict[str, Any]] = Field({}, description="Product attributes")
    keywords: Optional[List[str]] = Field([], description="Search keywords")
    tags: Optional[List[str]] = Field([], description="Product tags")
    
    # Source reference
    source_product_id: Optional[str] = Field(None, description="Source product ID")
    
    @validator('additional_images')
    def validate_additional_images(cls, v):
        """Validate additional images list"""
        if v and len(v) > 10:
            raise ValueError("Maximum 10 additional images allowed")
        return v
    
    @validator('keywords')
    def validate_keywords(cls, v):
        """Validate keywords list"""
        if v and len(v) > 20:
            raise ValueError("Maximum 20 keywords allowed")
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags list"""
        if v and len(v) > 15:
            raise ValueError("Maximum 15 tags allowed")
        return v


class BatchSettings(BaseModel):
    """Batch-specific settings"""
    auto_retry_enabled: bool = Field(True, description="Enable automatic retry")
    max_retry_attempts: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_minutes: int = Field(30, ge=1, le=1440, description="Retry delay in minutes")
    concurrent_registrations: int = Field(5, ge=1, le=20, description="Concurrent registrations")
    image_processing_enabled: bool = Field(True, description="Enable image processing")
    image_processing_rules: Optional[Dict[str, Any]] = Field({}, description="Image processing rules")


class BatchRegistrationRequest(BaseModel):
    """Request for batch product registration"""
    batch_name: str = Field(..., min_length=1, max_length=200, description="Batch name")
    description: Optional[str] = Field(None, max_length=1000, description="Batch description")
    products: List[ProductData] = Field(..., min_items=1, max_items=1000, description="Products to register")
    target_platforms: List[PlatformTypeEnum] = Field(..., min_items=1, description="Target platforms")
    priority: RegistrationPriorityEnum = Field(RegistrationPriorityEnum.medium, description="Registration priority")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled registration time")
    batch_settings: Optional[BatchSettings] = Field(None, description="Batch-specific settings")
    
    @validator('target_platforms')
    def validate_target_platforms(cls, v):
        """Validate target platforms"""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate platforms not allowed")
        return v


class SingleRegistrationRequest(BaseModel):
    """Request for single product registration"""
    product: ProductData = Field(..., description="Product to register")
    target_platforms: List[PlatformTypeEnum] = Field(..., min_items=1, description="Target platforms")
    priority: RegistrationPriorityEnum = Field(RegistrationPriorityEnum.high, description="Registration priority")
    
    @validator('target_platforms')
    def validate_target_platforms(cls, v):
        """Validate target platforms"""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate platforms not allowed")
        return v


class PlatformResult(BaseModel):
    """Platform-specific registration result"""
    platform: str = Field(..., description="Platform name")
    success: bool = Field(..., description="Registration success")
    product_id: Optional[str] = Field(None, description="Platform product ID")
    platform_url: Optional[str] = Field(None, description="Product URL on platform")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")


class RegistrationResponse(BaseModel):
    """Generic registration response"""
    success: bool = Field(..., description="Overall success")
    message: str = Field(..., description="Response message")
    target_platforms: List[str] = Field([], description="Target platforms")
    priority: Optional[str] = Field(None, description="Registration priority")
    platform_results: Optional[List[PlatformResult]] = Field([], description="Platform-specific results")
    errors: Optional[List[str]] = Field([], description="Error messages")
    warnings: Optional[List[str]] = Field([], description="Warning messages")


class BatchResponse(BaseModel):
    """Batch registration response"""
    batch_id: str = Field(..., description="Batch ID")
    batch_name: str = Field(..., description="Batch name")
    status: RegistrationStatusEnum = Field(..., description="Batch status")
    total_products: int = Field(..., description="Total products in batch")
    completed_products: int = Field(0, description="Successfully completed products")
    failed_products: int = Field(0, description="Failed products")
    target_platforms: List[str] = Field(..., description="Target platforms")
    priority: RegistrationPriorityEnum = Field(..., description="Batch priority")
    progress_percentage: float = Field(0.0, ge=0, le=100, description="Progress percentage")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled time")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    created_at: datetime = Field(..., description="Creation time")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion")
    message: Optional[str] = Field(None, description="Additional message")


class PlatformSummary(BaseModel):
    """Platform-specific summary"""
    platform: str = Field(..., description="Platform name")
    total: int = Field(..., description="Total registrations")
    completed: int = Field(..., description="Completed registrations")
    failed: int = Field(..., description="Failed registrations")
    in_progress: int = Field(..., description="In-progress registrations")
    success_rate: float = Field(0.0, ge=0, le=100, description="Success rate percentage")


class BatchStatusResponse(BaseModel):
    """Detailed batch status response"""
    batch_id: str = Field(..., description="Batch ID")
    batch_name: str = Field(..., description="Batch name")
    status: RegistrationStatusEnum = Field(..., description="Batch status")
    total_products: int = Field(..., description="Total products")
    completed_products: int = Field(..., description="Completed products")
    failed_products: int = Field(..., description="Failed products")
    progress_percentage: float = Field(..., description="Progress percentage")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    platform_summary: Dict[str, Dict[str, int]] = Field(..., description="Platform-wise summary")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion")


class QueueInfo(BaseModel):
    """Queue information"""
    pending: int = Field(..., description="Pending items")
    scheduled: Optional[int] = Field(None, description="Scheduled items")
    total: Optional[int] = Field(None, description="Total items")


class WorkerInfo(BaseModel):
    """Worker information"""
    active: int = Field(..., description="Active workers")
    total: int = Field(..., description="Total workers")


class QueueStatsResponse(BaseModel):
    """Queue statistics response"""
    status: str = Field(..., description="System status")
    queues: Dict[str, QueueInfo] = Field(..., description="Queue information")
    workers: WorkerInfo = Field(..., description="Worker information")
    processing_rate: Optional[float] = Field(None, description="Items processed per minute")
    average_processing_time: Optional[float] = Field(None, description="Average processing time")


class ImageProcessingRequest(BaseModel):
    """Image processing request"""
    product_registration_id: str = Field(..., description="Product registration ID")
    main_image_url: str = Field(..., description="Main image URL")
    additional_images: List[str] = Field([], description="Additional image URLs")
    target_platforms: List[PlatformTypeEnum] = Field(..., description="Target platforms")
    processing_rules: Optional[Dict[str, Any]] = Field({}, description="Custom processing rules")


class ImageProcessingResponse(BaseModel):
    """Image processing response"""
    success: bool = Field(..., description="Processing success")
    main_image: Optional[Dict[str, Any]] = Field(None, description="Main image results")
    additional_images: List[Dict[str, Any]] = Field([], description="Additional image results")
    supabase_urls: Optional[Dict[str, str]] = Field(None, description="Supabase storage URLs")
    errors: List[str] = Field([], description="Error messages")
    warnings: List[str] = Field([], description="Warning messages")
    processing_time_seconds: float = Field(..., description="Processing time")


class PlatformAccountInfo(BaseModel):
    """Platform account information for registration"""
    account_id: str = Field(..., description="Account ID")
    platform_type: PlatformTypeEnum = Field(..., description="Platform type")
    account_name: str = Field(..., description="Account name")
    health_status: str = Field(..., description="Account health status")
    daily_quota_remaining: Optional[int] = Field(None, description="Remaining daily quota")
    rate_limit_status: str = Field(..., description="Rate limit status")


class RegistrationCapacityResponse(BaseModel):
    """Registration capacity analysis response"""
    total_products: int = Field(..., description="Total products to register")
    accounts: List[PlatformAccountInfo] = Field(..., description="Available accounts")
    estimated_time_minutes: float = Field(..., description="Estimated completion time")
    recommendations: List[str] = Field([], description="Optimization recommendations")
    capacity_warnings: List[str] = Field([], description="Capacity warnings")


class RetryRequest(BaseModel):
    """Retry registration request"""
    batch_id: Optional[str] = Field(None, description="Batch ID to retry")
    platform_filter: Optional[List[PlatformTypeEnum]] = Field(None, description="Platforms to retry")
    retry_failed_only: bool = Field(True, description="Retry only failed registrations")
    max_retry_attempts: Optional[int] = Field(None, description="Override max retry attempts")


class BulkOperationRequest(BaseModel):
    """Bulk operation request"""
    batch_ids: List[str] = Field(..., min_items=1, max_items=50, description="Batch IDs")
    operation: str = Field(..., description="Operation type (cancel, retry, delete)")
    operation_params: Optional[Dict[str, Any]] = Field({}, description="Operation parameters")


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    total_batches: int = Field(..., description="Total batches processed")
    successful_operations: int = Field(..., description="Successful operations")
    failed_operations: int = Field(..., description="Failed operations")
    results: List[Dict[str, Any]] = Field(..., description="Operation results")
    errors: List[str] = Field([], description="Error messages")


class RegistrationAnalytics(BaseModel):
    """Registration analytics"""
    period_days: int = Field(..., description="Analysis period in days")
    total_batches: int = Field(..., description="Total batches")
    total_products: int = Field(..., description="Total products registered")
    success_rate: float = Field(..., description="Overall success rate")
    platform_breakdown: Dict[str, Dict[str, Any]] = Field(..., description="Platform-wise breakdown")
    average_processing_time: float = Field(..., description="Average processing time")
    peak_usage_hours: List[int] = Field(..., description="Peak usage hours")
    failure_reasons: Dict[str, int] = Field(..., description="Common failure reasons")


class TemplateRequest(BaseModel):
    """Registration template request"""
    template_name: str = Field(..., min_length=1, max_length=200, description="Template name")
    platform_type: PlatformTypeEnum = Field(..., description="Target platform")
    category_id: Optional[str] = Field(None, description="Default category")
    default_attributes: Dict[str, Any] = Field({}, description="Default attributes")
    pricing_rules: Optional[Dict[str, Any]] = Field({}, description="Pricing rules")
    image_rules: Optional[Dict[str, Any]] = Field({}, description="Image processing rules")
    field_mappings: Optional[Dict[str, str]] = Field({}, description="Field mappings")
    is_default: bool = Field(False, description="Set as default template")


class TemplateResponse(BaseModel):
    """Registration template response"""
    template_id: str = Field(..., description="Template ID")
    template_name: str = Field(..., description="Template name")
    platform_type: str = Field(..., description="Platform type")
    is_active: bool = Field(..., description="Template is active")
    is_default: bool = Field(..., description="Is default template")
    usage_count: int = Field(..., description="Usage count")
    created_at: datetime = Field(..., description="Creation time")
    last_used_at: Optional[datetime] = Field(None, description="Last used time")