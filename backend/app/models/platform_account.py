"""
Platform account models for multi-marketplace management
"""
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from .base import BaseModel, get_json_type


class PlatformType(enum.Enum):
    """Platform type enumeration"""
    COUPANG = "coupang"
    NAVER = "naver"
    ELEVEN_ST = "11st"
    GMARKET = "gmarket"
    AUCTION = "auction"
    TMON = "tmon"
    WE_MAKE_PRICE = "wemakeprice"
    INTERPARK = "interpark"
    
    # Wholesale platforms
    TOPTEN = "topten"
    ICOOP = "icoop"
    DONGWON = "dongwon"


class AccountStatus(enum.Enum):
    """Account status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"
    ERROR = "error"


class PlatformAccount(BaseModel):
    """Platform account information"""
    __tablename__ = "platform_accounts"
    
    # Basic Information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    platform_type = Column(SQLEnum(PlatformType), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    account_id = Column(String(100), nullable=False)  # Platform-specific account ID
    
    # Authentication
    api_key = Column(Text, nullable=True)  # Encrypted
    api_secret = Column(Text, nullable=True)  # Encrypted
    access_token = Column(Text, nullable=True)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_expires_at = Column(DateTime, nullable=True)
    
    # Account Details
    seller_id = Column(String(100), nullable=True, index=True)
    store_name = Column(String(200), nullable=True)
    store_url = Column(String(500), nullable=True)
    
    # Status and Health
    status = Column(SQLEnum(AccountStatus), default=AccountStatus.PENDING_APPROVAL, nullable=False, index=True)
    last_sync_at = Column(DateTime, nullable=True, index=True)
    last_health_check_at = Column(DateTime, nullable=True)
    health_status = Column(String(50), default="unknown", nullable=False)  # healthy, warning, error
    
    # Configuration
    sync_enabled = Column(Boolean, default=True, nullable=False)
    auto_pricing_enabled = Column(Boolean, default=False, nullable=False)
    auto_inventory_sync = Column(Boolean, default=True, nullable=False)
    
    # Platform-specific settings
    platform_settings = Column(get_json_type(), nullable=True)
    
    # Rate limiting and quotas
    daily_api_quota = Column(Integer, nullable=True)
    daily_api_used = Column(Integer, default=0, nullable=False)
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    
    # Financial information
    commission_rate = Column(Numeric(5, 4), nullable=True)  # Platform commission rate
    monthly_fee = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="KRW", nullable=False)
    
    # Error tracking
    last_error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    consecutive_errors = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="platform_accounts")
    products = relationship("Product", back_populates="platform_account", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="platform_account", cascade="all, delete-orphan")
    sync_logs = relationship("PlatformSyncLog", back_populates="platform_account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PlatformAccount(platform={self.platform_type.value}, account_name={self.account_name})>"
    
    def is_token_expired(self) -> bool:
        """Check if access token is expired"""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at
    
    def needs_health_check(self, interval_minutes: int = 30) -> bool:
        """Check if health check is needed"""
        if not self.last_health_check_at:
            return True
        time_diff = datetime.utcnow() - self.last_health_check_at
        return time_diff.total_seconds() > (interval_minutes * 60)
    
    def increment_error_count(self):
        """Increment error counters"""
        self.error_count += 1
        self.consecutive_errors += 1
        
        # Auto-disable if too many consecutive errors
        if self.consecutive_errors >= 10:
            self.status = AccountStatus.ERROR
            self.sync_enabled = False
    
    def reset_error_count(self):
        """Reset error counters on successful operation"""
        self.consecutive_errors = 0


class PlatformSyncLog(BaseModel):
    """Platform synchronization logs"""
    __tablename__ = "platform_sync_logs"
    
    platform_account_id = Column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False, index=True)
    sync_type = Column(String(50), nullable=False, index=True)  # products, orders, inventory, etc.
    
    # Sync details
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), default="running", nullable=False, index=True)  # running, completed, failed
    
    # Results
    total_items = Column(Integer, default=0, nullable=False)
    processed_items = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    
    # Details
    error_message = Column(Text, nullable=True)
    sync_details = Column(get_json_type(), nullable=True)  # Detailed sync information
    
    # Performance metrics
    processing_time_seconds = Column(Integer, nullable=True)
    api_calls_made = Column(Integer, default=0, nullable=False)
    
    # Relationships
    platform_account = relationship("PlatformAccount", back_populates="sync_logs")
    
    def __repr__(self):
        return f"<PlatformSyncLog(type={self.sync_type}, status={self.status})>"
    
    def calculate_success_rate(self) -> float:
        """Calculate sync success rate"""
        if self.total_items == 0:
            return 0.0
        return (self.success_count / self.total_items) * 100


class WholesaleAccount(BaseModel):
    """Wholesale/supplier account information"""
    __tablename__ = "wholesale_accounts"
    
    # Basic Information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    supplier_name = Column(String(200), nullable=False)
    supplier_code = Column(String(50), nullable=True, index=True)
    
    # Contact Information
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    
    # Business Information
    business_number = Column(String(20), nullable=True, index=True)  # 사업자등록번호
    tax_type = Column(String(20), default="vat", nullable=False)  # vat, tax_free
    
    # Authentication (if API-based)
    api_endpoint = Column(String(500), nullable=True)
    api_key = Column(Text, nullable=True)  # Encrypted
    username = Column(String(100), nullable=True)
    password_hash = Column(Text, nullable=True)  # Encrypted
    
    # Status
    status = Column(SQLEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False, index=True)
    is_preferred = Column(Boolean, default=False, nullable=False)
    
    # Terms and conditions
    payment_terms = Column(String(100), nullable=True)  # 결제조건
    delivery_terms = Column(String(100), nullable=True)  # 배송조건
    minimum_order_amount = Column(Numeric(12, 2), nullable=True)
    
    # Performance metrics
    reliability_score = Column(Numeric(3, 2), default=5.0, nullable=False)  # 1.0 to 5.0
    average_delivery_days = Column(Integer, nullable=True)
    total_orders = Column(Integer, default=0, nullable=False)
    
    # Settings
    auto_sync_enabled = Column(Boolean, default=False, nullable=False)
    sync_interval_hours = Column(Integer, default=24, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    products = relationship("Product", back_populates="wholesale_account")
    
    def __repr__(self):
        return f"<WholesaleAccount(supplier_name={self.supplier_name})>"