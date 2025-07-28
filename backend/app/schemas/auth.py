"""
Authentication related schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration for API responses"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """User status enumeration for API responses"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


# ==================
# Request Schemas
# ==================

class UserRegister(BaseModel):
    """User registration request schema"""
    username: str = Field(..., min_length=3, max_length=50, description="고유 사용자명")
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=8, max_length=100, description="비밀번호")
    full_name: str = Field(..., min_length=1, max_length=100, description="전체 이름")
    phone: Optional[str] = Field(None, max_length=20, description="전화번호")
    department: Optional[str] = Field(None, max_length=50, description="부서")
    timezone: str = Field(default="Asia/Seoul", description="시간대")
    language: str = Field(default="ko", description="언어 설정")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('사용자명은 영문, 숫자, 언더스코어, 하이픈만 사용 가능합니다')
        return v
    
    @validator('phone')
    def phone_format(cls, v):
        if v and not v.replace('-', '').replace(' ', '').replace('+', '').isdigit():
            raise ValueError('올바른 전화번호 형식이 아닙니다')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "full_name": "홍길동",
                "phone": "010-1234-5678",
                "department": "영업팀",
                "timezone": "Asia/Seoul",
                "language": "ko"
            }
        }


class UserLogin(BaseModel):
    """User login request schema"""
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., description="비밀번호")
    remember_me: Optional[bool] = Field(default=False, description="로그인 유지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123!",
                "remember_me": False
            }
        }


class PasswordChange(BaseModel):
    """Password change request schema"""
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=100, description="새 비밀번호")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewPass123!"
            }
        }


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr = Field(..., description="비밀번호를 재설정할 이메일 주소")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com"
            }
        }


class PasswordReset(BaseModel):
    """Password reset schema"""
    token: str = Field(..., description="비밀번호 재설정 토큰")
    new_password: str = Field(..., min_length=8, max_length=100, description="새 비밀번호")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset_token_here",
                "new_password": "NewPass123!"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str = Field(..., description="리프레시 토큰")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }


# ==================
# Response Schemas
# ==================

class Token(BaseModel):
    """Token response schema"""
    access_token: str = Field(..., description="액세스 토큰")
    refresh_token: str = Field(..., description="리프레시 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="토큰 만료 시간 (초)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class TokenPayload(BaseModel):
    """JWT token payload schema"""
    sub: Optional[str] = None  # Subject (user ID)
    email: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None  # Expiration time
    iat: Optional[int] = None  # Issued at
    jti: Optional[str] = None  # JWT ID
    type: Optional[str] = None  # Token type (access/refresh)


class LoginResponse(BaseModel):
    """Login response schema"""
    user: "UserResponse"
    token: Token
    login_info: dict = Field(..., description="로그인 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "full_name": "홍길동",
                    "role": "operator",
                    "status": "active",
                    "is_active": True,
                    "is_verified": True
                },
                "token": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600
                },
                "login_info": {
                    "login_time": "2024-01-01T10:00:00Z",
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0..."
                }
            }
        }


class SecurityAuditResponse(BaseModel):
    """Security audit log response schema"""
    id: str
    user_id: Optional[str]
    action: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    details: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "action": "login_success",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "success": True,
                "details": {"method": "email_password"},
                "created_at": "2024-01-01T10:00:00Z"
            }
        }


class SessionResponse(BaseModel):
    """User session response schema"""
    id: str
    user_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    expires_at: datetime
    is_active: bool
    country: Optional[str]
    city: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "ip_address": "192.168.1.1",  
                "user_agent": "Mozilla/5.0...",
                "expires_at": "2024-01-02T10:00:00Z",
                "is_active": True,
                "country": "KR",
                "city": "Seoul",
                "created_at": "2024-01-01T10:00:00Z"
            }
        }


# ==================
# Generic Response Schemas
# ==================

class MessageResponse(BaseModel):
    """Generic message response schema"""
    message: str = Field(..., description="응답 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "작업이 완료되었습니다"
            }
        }


class SuccessResponse(BaseModel):
    """Generic success response schema"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[dict] = Field(None, description="추가 데이터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "작업이 완료되었습니다",
                "data": None
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response schema"""
    success: bool = Field(default=False, description="성공 여부")
    error: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[dict] = Field(None, description="에러 세부사항")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "입력 데이터가 올바르지 않습니다",
                "details": {
                    "field": "email",
                    "issue": "Invalid email format"
                }
            }
        }


# Import here to avoid circular imports
from app.schemas.user import UserResponse
LoginResponse.model_rebuild()