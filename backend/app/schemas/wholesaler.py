from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from ..models.wholesaler import WholesalerType, ConnectionStatus, CollectionStatus


# Base Schemas
class WholesalerTypeEnum(str, Enum):
    DOMEGGOOK = "domeggook"
    OWNERCLAN = "ownerclan"
    ZENTRADE = "zentrade"


class ConnectionStatusEnum(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TESTING = "testing"


class CollectionStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Wholesaler Account Schemas
class WholesalerAccountBase(BaseModel):
    wholesaler_type: WholesalerTypeEnum
    account_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    auto_collect_enabled: bool = False
    collect_interval_hours: int = Field(default=24, ge=1, le=168)  # 1시간~1주일
    collect_categories: Optional[List[str]] = None
    collect_recent_days: int = Field(default=7, ge=1, le=365)
    max_products_per_collection: int = Field(default=1000, ge=1, le=10000)


class WholesalerAccountCreate(WholesalerAccountBase):
    api_credentials: Dict[str, Any] = Field(..., description="API 인증 정보")


class WholesalerAccountUpdate(BaseModel):
    account_name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    auto_collect_enabled: Optional[bool] = None
    collect_interval_hours: Optional[int] = Field(None, ge=1, le=168)
    collect_categories: Optional[List[str]] = None
    collect_recent_days: Optional[int] = Field(None, ge=1, le=365)
    max_products_per_collection: Optional[int] = Field(None, ge=1, le=10000)


class WholesalerAccountResponse(WholesalerAccountBase):
    id: int
    user_id: int
    connection_status: ConnectionStatusEnum
    last_connected_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # API 인증 정보는 보안상 제외
    # 대신 연결 상태만 제공
    
    class Config:
        from_attributes = True


# Collection Request Schemas  
class CollectionRequest(BaseModel):
    collection_type: str = Field(..., description="수집 유형: all, recent, category")
    filters: Optional[Dict[str, Any]] = Field(None, description="수집 조건")
    max_products: Optional[int] = Field(1000, ge=1, le=10000)


class RecentCollectionRequest(BaseModel):
    days: int = Field(7, ge=1, le=30, description="최근 N일 상품 수집")
    categories: Optional[List[str]] = None
    max_products: Optional[int] = Field(1000, ge=1, le=10000)


class CategoryCollectionRequest(BaseModel):
    categories: List[str] = Field(..., min_items=1, description="수집할 카테고리 목록")
    include_subcategories: bool = Field(True, description="하위 카테고리 포함 여부")
    max_products: Optional[int] = Field(1000, ge=1, le=10000)


# Collection Log Schemas
class CollectionLogResponse(BaseModel):
    id: int
    wholesaler_account_id: int
    collection_type: str
    status: CollectionStatusEnum
    filters: Optional[Dict[str, Any]] = None
    total_products_found: int
    products_collected: int
    products_updated: int
    products_failed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    collection_summary: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# Scheduled Collection Schemas
class ScheduledCollectionBase(BaseModel):
    schedule_name: str = Field(..., min_length=1, max_length=100)
    collection_type: str
    cron_expression: str = Field(..., description="크론 표현식 (예: 0 2 * * *)")
    timezone: str = Field(default="Asia/Seoul")
    filters: Optional[Dict[str, Any]] = None
    max_products: int = Field(default=1000, ge=1, le=10000)
    is_active: bool = True


class ScheduledCollectionCreate(ScheduledCollectionBase):
    pass


class ScheduledCollectionUpdate(BaseModel):
    schedule_name: Optional[str] = Field(None, min_length=1, max_length=100)
    collection_type: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    max_products: Optional[int] = Field(None, ge=1, le=10000)
    is_active: Optional[bool] = None


class ScheduledCollectionResponse(ScheduledCollectionBase):
    id: int
    wholesaler_account_id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    total_runs: int
    successful_runs: int
    failed_runs: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Wholesaler Product Schemas
class WholesalerProductBase(BaseModel):
    wholesaler_product_id: str
    wholesaler_sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    category_path: Optional[str] = None
    wholesale_price: int
    retail_price: Optional[int] = None
    discount_rate: Optional[int] = None
    stock_quantity: int = 0
    is_in_stock: bool = True
    main_image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    shipping_info: Optional[Dict[str, Any]] = None


class WholesalerProductCreate(WholesalerProductBase):
    wholesaler_account_id: int


class WholesalerProductUpdate(BaseModel):
    wholesaler_sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category_path: Optional[str] = None
    wholesale_price: Optional[int] = None
    retail_price: Optional[int] = None
    discount_rate: Optional[int] = None
    stock_quantity: Optional[int] = None
    is_in_stock: Optional[bool] = None
    main_image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    shipping_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WholesalerProductResponse(WholesalerProductBase):
    id: int
    wholesaler_account_id: int
    is_active: bool
    is_collected: bool
    first_collected_at: datetime
    last_updated_at: datetime
    
    class Config:
        from_attributes = True


# Excel Upload Schemas
class ExcelUploadRequest(BaseModel):
    wholesaler_account_id: int
    mapping_config: Optional[Dict[str, str]] = Field(None, description="컬럼 매핑 설정")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="데이터 검증 규칙")


class ExcelUploadResponse(BaseModel):
    upload_id: int
    filename: str
    status: CollectionStatusEnum
    total_rows: int
    processed_rows: int
    success_rows: int
    failed_rows: int
    uploaded_at: datetime
    processing_log: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# API Test Schemas
class ConnectionTestRequest(BaseModel):
    api_credentials: Dict[str, Any] = Field(..., description="테스트할 API 인증 정보")


class ConnectionTestResponse(BaseModel):
    success: bool
    connection_status: ConnectionStatusEnum
    message: str
    response_time_ms: Optional[int] = None
    api_info: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None


# Common Response Schemas
class MessageResponse(BaseModel):
    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


# Wholesaler-specific API Credential Schemas
class DomeggookCredentials(BaseModel):
    api_key: str = Field(..., min_length=1, description="도매매 API 키")
    user_id: Optional[str] = Field(None, description="사용자 ID (선택)")


class OwnerClanCredentials(BaseModel):
    username: str = Field(..., min_length=1, description="오너클랜 사용자명")
    password: str = Field(..., min_length=1, description="오너클랜 비밀번호")
    api_url: Optional[str] = Field(None, description="API URL (기본값 사용 시 생략)")


class ZentradeCredentials(BaseModel):
    api_key: str = Field(..., min_length=1, description="젠트레이드 API 키")
    api_id: str = Field(..., min_length=1, description="젠트레이드 API ID")
    base_url: Optional[str] = Field(None, description="API 베이스 URL (기본값 사용 시 생략)")


# Collection Statistics
class CollectionStats(BaseModel):
    total_accounts: int
    active_accounts: int
    connected_accounts: int
    total_products: int
    products_this_month: int
    last_collection_date: Optional[datetime] = None
    avg_collection_time_minutes: Optional[float] = None


class WholesalerStats(BaseModel):
    wholesaler_type: WholesalerTypeEnum
    account_count: int
    active_accounts: int
    total_products: int
    last_collection: Optional[datetime] = None
    success_rate: float  # 성공한 수집 비율