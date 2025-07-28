"""
User and authentication models
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from .base import BaseModel, Base, get_json_type


class UserRole(enum.Enum):
    """User role enumeration"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class UserStatus(enum.Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(BaseModel):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    # Basic Information
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Role and Status
    role = Column(SQLEnum(UserRole), default=UserRole.OPERATOR, nullable=False, index=True)
    status = Column(SQLEnum(UserStatus), default=UserStatus.PENDING, nullable=False, index=True)
    
    # Contact Information
    phone = Column(String(20), nullable=True)
    department = Column(String(50), nullable=True)
    
    # Security
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    password_changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Settings
    preferences = Column(get_json_type(), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="ko", nullable=False)
    
    # Notification settings
    notification_settings = Column(get_json_type(), nullable=True)
    
    # RBAC Relationships
    role_ref = relationship("Role", foreign_keys="User.role", uselist=False)
    
    # Relationships
    platform_accounts = relationship("PlatformAccount", back_populates="user", cascade="all, delete-orphan")
    ai_logs = relationship("AILog", back_populates="user", cascade="all, delete-orphan")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    # notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")  # Temporarily disabled - model not implemented
    wholesaler_accounts = relationship("WholesalerAccount", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username={self.username}, email={self.email})>"
    
    @property
    def is_superuser(self) -> bool:
        """Check if user is a superuser"""
        return self.role == UserRole.SUPER_ADMIN
    
    def has_permission(self, permission: str) -> bool:
        """
        Legacy permission check - maintained for backward compatibility
        Use the new RBAC service for granular permission checking
        """
        # Super admin has all permissions
        if self.role == UserRole.SUPER_ADMIN:
            return True
            
        # Basic role-based permissions (legacy)
        role_permissions = {
            UserRole.ADMIN: [
                "users.read", "users.create", "users.update",
                "products.read.all", "products.manage.all", "products.bulk_update",
                "orders.read.all", "orders.process", "orders.approve", 
                "inventory.read", "inventory.update", "inventory.sync",
                "reports.read", "reports.create", "analytics.read",
                "marketplaces.read", "marketplaces.configure", "marketplaces.sync",
                "wholesalers.read", "wholesalers.configure", "wholesalers.sync",
                "pricing.read", "pricing.update", "pricing.manage",
                "ai_services.read", "ai_services.use", "ai_services.configure"
            ],
            UserRole.MANAGER: [
                "products.read.all", "products.update.own", "products.create.own",
                "orders.read.all", "orders.process", "orders.approve",
                "inventory.read", "inventory.update",
                "reports.read", "reports.create", "analytics.read",
                "marketplaces.read", "marketplaces.sync",
                "wholesalers.read", "wholesalers.sync",
                "pricing.read", "pricing.update",
                "ai_services.read", "ai_services.use"
            ],
            UserRole.OPERATOR: [
                "products.read.own", "products.update.own", "products.create.own",
                "orders.read.own", "orders.create",
                "inventory.read", "reports.read", "analytics.read",
                "marketplaces.read", "wholesalers.read",
                "pricing.read", "ai_services.read", "ai_services.use"
            ],
            UserRole.VIEWER: [
                "products.read.own", "orders.read.own", "inventory.read",
                "reports.read", "analytics.read", "marketplaces.read",
                "wholesalers.read", "pricing.read", "ai_services.read"
            ]
        }
        
        user_permissions = role_permissions.get(self.role, [])
        return permission in user_permissions


class UserSession(BaseModel):
    """User session tracking"""
    __tablename__ = "user_sessions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Location tracking
    country = Column(String(2), nullable=True)  # ISO country code
    city = Column(String(100), nullable=True)
    
    # Session data
    session_data = Column(get_json_type(), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_sessions")
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, expires_at={self.expires_at})>"


class UserAPIKey(BaseModel):
    """API key management for users"""
    __tablename__ = "user_api_keys"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # Key name/description
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    
    # Permissions and restrictions
    permissions = Column(get_json_type(), nullable=True)  # Specific permissions for this key
    rate_limit = Column(Integer, default=1000, nullable=False)  # Requests per hour
    allowed_ips = Column(get_json_type(), nullable=True)  # Whitelist of IPs
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    user = relationship("User")
    
    def is_expired(self) -> bool:
        """Check if API key is expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<UserAPIKey(name={self.name}, user_id={self.user_id})>"