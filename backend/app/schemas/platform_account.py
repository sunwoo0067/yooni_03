"""
플랫폼 계정 관련 Pydantic 스키마
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class PlatformEnum(str, Enum):
    """지원하는 플랫폼"""
    COUPANG = "coupang"
    NAVER = "naver"
    ELEVEN_STREET = "11st"
    GMARKET = "gmarket"
    AUCTION = "auction"
    INTERPARK = "interpark"


class AccountStatusEnum(str, Enum):
    """계정 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    ERROR = "error"


class PlatformInfo(BaseModel):
    """플랫폼 정보"""
    platform: PlatformEnum
    display_name: str
    description: Optional[str] = None
    features: List[str] = []
    required_credentials: List[str] = []


class PlatformCredentials(BaseModel):
    """플랫폼 인증 정보"""
    platform: PlatformEnum
    credentials: Dict[str, str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "platform": "coupang",
                "credentials": {
                    "access_key": "your-access-key",
                    "secret_key": "your-secret-key",
                    "vendor_id": "your-vendor-id"
                }
            }
        }


class PlatformAccountBase(BaseModel):
    """플랫폼 계정 기본 스키마"""
    platform: PlatformEnum
    account_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    api_credentials: Optional[Dict[str, Any]] = Field(default_factory=dict)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PlatformAccountCreate(PlatformAccountBase):
    """플랫폼 계정 생성 스키마"""
    pass


class PlatformAccountUpdate(BaseModel):
    """플랫폼 계정 업데이트 스키마"""
    account_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    api_credentials: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None


class PlatformAccountResponse(PlatformAccountBase):
    """플랫폼 계정 응답 스키마"""
    id: int
    uuid: UUID
    status: AccountStatusEnum
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    sync_status: Optional[str] = None
    
    class Config:
        from_attributes = True


class PlatformAccountSummary(BaseModel):
    """플랫폼 계정 요약 정보"""
    id: int
    uuid: UUID
    platform: PlatformEnum
    account_name: str
    status: AccountStatusEnum
    is_active: bool
    last_sync_at: Optional[datetime]
    product_count: int = 0
    order_count: int = 0
    
    class Config:
        from_attributes = True


class PlatformAccountConnectionTest(BaseModel):
    """플랫폼 연결 테스트 결과"""
    platform: PlatformEnum
    account_id: int
    success: bool
    message: str
    response_time_ms: float
    tested_at: datetime
    details: Optional[Dict[str, Any]] = None


class PlatformAccountStats(BaseModel):
    """플랫폼 계정 통계"""
    account_id: int
    account_name: str
    platform: PlatformEnum
    total_products: int = 0
    active_products: int = 0
    total_orders: int = 0
    pending_orders: int = 0
    total_revenue: float = 0.0
    total_profit: float = 0.0
    sync_success_rate: float = 100.0
    last_7_days_orders: int = 0
    last_30_days_orders: int = 0
    
    class Config:
        from_attributes = True


class BulkOperationRequest(BaseModel):
    """대량 작업 요청"""
    account_ids: List[int] = Field(..., min_items=1)
    operation: str = Field(..., pattern="^(activate|deactivate|sync|delete)$")


class BulkOperationResponse(BaseModel):
    """대량 작업 응답"""
    total: int
    success: int
    failed: int
    results: List[Dict[str, Any]]


class PlatformSyncLogResponse(BaseModel):
    """동기화 로그 응답"""
    id: int
    account_id: int
    sync_type: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    records_processed: int
    records_success: int
    records_failed: int
    error_message: Optional[str]
    details: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True