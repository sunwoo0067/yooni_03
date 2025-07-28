"""
Security audit and token management models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, Base, get_json_type


class SecurityAuditLog(BaseModel):
    """Security audit log for tracking authentication and security events"""
    __tablename__ = "security_audit_logs"
    
    # User information (nullable for failed logins or anonymous actions)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Action information
    action = Column(String(100), nullable=False, index=True)  # login_success, login_failure, password_change, etc.
    resource = Column(String(100), nullable=True, index=True)  # API endpoint or resource accessed
    
    # Request information
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, etc.
    request_path = Column(String(500), nullable=True)
    
    # Result information
    success = Column(Boolean, nullable=False, index=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional details as JSON
    details = Column(get_json_type(), nullable=True)
    
    # Location information (optional)
    country = Column(String(2), nullable=True)  # ISO country code
    city = Column(String(100), nullable=True)
    
    # Session information
    session_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_security_audit_user_action', 'user_id', 'action'),
        Index('idx_security_audit_time_action', 'created_at', 'action'),
        Index('idx_security_audit_ip_time', 'ip_address', 'created_at'),
        Index('idx_security_audit_success_time', 'success', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SecurityAuditLog(action={self.action}, user_id={self.user_id}, success={self.success})>"


class TokenBlacklist(BaseModel):
    """JWT token blacklist for token revocation"""
    __tablename__ = "token_blacklist"
    
    # Token information
    jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID
    token_type = Column(String(20), nullable=False, index=True)  # access, refresh
    
    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Token metadata
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoke_reason = Column(String(100), nullable=True)  # logout, password_change, admin_revoke, etc.
    
    # Request information when revoked
    revoke_ip = Column(String(45), nullable=True)
    revoke_user_agent = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_token_blacklist_expires', 'expires_at'),
        Index('idx_token_blacklist_user_type', 'user_id', 'token_type'),
        Index('idx_token_blacklist_revoked', 'revoked_at'),
    )
    
    def is_expired(self) -> bool:
        """Check if the blacklisted token has expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<TokenBlacklist(jti={self.jti}, user_id={self.user_id}, token_type={self.token_type})>"


class LoginAttempt(BaseModel):
    """Track login attempts for rate limiting and security monitoring"""
    __tablename__ = "login_attempts"
    
    # Attempt information
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    
    # Result
    success = Column(Boolean, nullable=False, index=True)
    failure_reason = Column(String(100), nullable=True)  # invalid_password, user_not_found, account_locked, etc.
    
    # User ID if login was successful
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Location information (optional)
    country = Column(String(2), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes for performance and rate limiting
    __table_args__ = (
        Index('idx_login_attempts_email_ip', 'email', 'ip_address'),
        Index('idx_login_attempts_ip_time', 'ip_address', 'created_at'),
        Index('idx_login_attempts_email_time', 'email', 'created_at'),
        Index('idx_login_attempts_success_time', 'success', 'created_at'),
    )
    
    def __repr__(self):
        return f"<LoginAttempt(email={self.email}, ip={self.ip_address}, success={self.success})>"


class PasswordResetToken(BaseModel):
    """Password reset tokens"""
    __tablename__ = "password_reset_tokens"
    
    # Token information
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Expiration and usage
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False, nullable=False, index=True)
    
    # Request information
    request_ip = Column(String(45), nullable=True)
    request_user_agent = Column(Text, nullable=True)
    
    # Usage information
    used_ip = Column(String(45), nullable=True)
    used_user_agent = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_password_reset_user_expires', 'user_id', 'expires_at'),
        Index('idx_password_reset_expires_used', 'expires_at', 'is_used'),
    )
    
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()
    
    def mark_used(self, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Mark token as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.used_ip = ip_address
        self.used_user_agent = user_agent
    
    def __repr__(self):
        return f"<PasswordResetToken(user_id={self.user_id}, is_used={self.is_used}, expires_at={self.expires_at})>"