"""
User related schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

from app.schemas.auth import UserRole, UserStatus


# ==================
# Request Schemas
# ==================

class UserCreate(BaseModel):
    """User creation schema for admin use"""
    username: str = Field(..., min_length=3, max_length=50, description="고유 사용자명")
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=8, max_length=100, description="비밀번호")
    full_name: str = Field(..., min_length=1, max_length=100, description="전체 이름")
    phone: Optional[str] = Field(None, max_length=20, description="전화번호")
    department: Optional[str] = Field(None, max_length=50, description="부서")
    role: UserRole = Field(default=UserRole.OPERATOR, description="사용자 역할")
    status: UserStatus = Field(default=UserStatus.PENDING, description="계정 상태")
    is_active: bool = Field(default=True, description="계정 활성화 여부")
    is_verified: bool = Field(default=False, description="이메일 인증 여부")
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
                "role": "operator",
                "status": "active",
                "is_active": True,
                "is_verified": False,
                "timezone": "Asia/Seoul",
                "language": "ko"
            }
        }


class UserUpdate(BaseModel):
    """User update schema"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="고유 사용자명")
    email: Optional[EmailStr] = Field(None, description="이메일 주소")
    full_name: Optional[str] = Field(None, min_length=1, max_length=100, description="전체 이름")
    phone: Optional[str] = Field(None, max_length=20, description="전화번호")
    department: Optional[str] = Field(None, max_length=50, description="부서")
    timezone: Optional[str] = Field(None, description="시간대")
    language: Optional[str] = Field(None, description="언어 설정")
    preferences: Optional[Dict[str, Any]] = Field(None, description="사용자 설정")
    notification_settings: Optional[Dict[str, Any]] = Field(None, description="알림 설정")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
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
                "full_name": "홍길동",
                "phone": "010-1234-5678",
                "department": "마케팅팀",
                "timezone": "Asia/Seoul",
                "language": "ko",
                "preferences": {
                    "theme": "dark",
                    "notifications_enabled": True
                },
                "notification_settings": {
                    "email_notifications": True,
                    "sms_notifications": False,
                    "push_notifications": True
                }
            }
        }


class UserAdminUpdate(UserUpdate):
    """Admin user update schema with additional fields"""
    role: Optional[UserRole] = Field(None, description="사용자 역할")
    status: Optional[UserStatus] = Field(None, description="계정 상태")
    is_active: Optional[bool] = Field(None, description="계정 활성화 여부")
    is_verified: Optional[bool] = Field(None, description="이메일 인증 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "홍길동",
                "phone": "010-1234-5678",
                "department": "마케팅팀",
                "role": "manager",
                "status": "active",
                "is_active": True,
                "is_verified": True,
                "timezone": "Asia/Seoul",
                "language": "ko"
            }
        }


class UserBulkAction(BaseModel):
    """Bulk user action schema"""
    user_ids: List[str] = Field(..., description="사용자 ID 목록")
    action: str = Field(..., description="수행할 액션")
    parameters: Optional[Dict[str, Any]] = Field(None, description="액션 파라미터")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['activate', 'deactivate', 'delete', 'change_role', 'change_status']
        if v not in allowed_actions:
            raise ValueError(f'허용되지 않은 액션입니다. 허용된 액션: {", ".join(allowed_actions)}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": ["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"],
                "action": "activate",
                "parameters": {}
            }
        }


# ==================
# Response Schemas
# ==================

class UserResponse(BaseModel):
    """User response schema"""
    id: str = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자명")
    email: str = Field(..., description="이메일 주소")
    full_name: str = Field(..., description="전체 이름")
    phone: Optional[str] = Field(None, description="전화번호")
    department: Optional[str] = Field(None, description="부서")
    role: UserRole = Field(..., description="사용자 역할")
    status: UserStatus = Field(..., description="계정 상태")
    is_active: bool = Field(..., description="계정 활성화 여부")
    is_verified: bool = Field(..., description="이메일 인증 여부")
    timezone: str = Field(..., description="시간대")
    language: str = Field(..., description="언어 설정")
    last_login_at: Optional[datetime] = Field(None, description="마지막 로그인 시간")
    created_at: datetime = Field(..., description="계정 생성 시간")
    updated_at: datetime = Field(..., description="계정 수정 시간")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "홍길동",
                "phone": "010-1234-5678",
                "department": "영업팀",
                "role": "operator",
                "status": "active",
                "is_active": True,
                "is_verified": True,
                "timezone": "Asia/Seoul",
                "language": "ko",
                "last_login_at": "2024-01-01T10:00:00Z",
                "created_at": "2024-01-01T09:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z"
            }
        }


class UserDetailResponse(UserResponse):
    """Detailed user response schema with additional information"""
    failed_login_attempts: int = Field(..., description="로그인 실패 횟수")
    password_changed_at: datetime = Field(..., description="비밀번호 변경 시간")
    preferences: Optional[Dict[str, Any]] = Field(None, description="사용자 설정")
    notification_settings: Optional[Dict[str, Any]] = Field(None, description="알림 설정")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "홍길동",
                "phone": "010-1234-5678",
                "department": "영업팀",
                "role": "operator",
                "status": "active",
                "is_active": True,
                "is_verified": True,
                "timezone": "Asia/Seoul",
                "language": "ko",
                "last_login_at": "2024-01-01T10:00:00Z",
                "created_at": "2024-01-01T09:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z",
                "failed_login_attempts": 0,
                "password_changed_at": "2024-01-01T09:00:00Z",
                "preferences": {
                    "theme": "light",
                    "notifications_enabled": True
                },
                "notification_settings": {
                    "email_notifications": True,
                    "sms_notifications": False,
                    "push_notifications": True
                }
            }
        }


class UserListResponse(BaseModel):
    """User list response schema with pagination"""
    users: List[UserResponse] = Field(..., description="사용자 목록")
    total: int = Field(..., description="전체 사용자 수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    total_pages: int = Field(..., description="전체 페이지 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "username": "john_doe",
                        "email": "john@example.com",
                        "full_name": "홍길동",
                        "role": "operator",
                        "status": "active",
                        "is_active": True,
                        "is_verified": True,
                        "created_at": "2024-01-01T09:00:00Z"
                    }
                ],
                "total": 100,
                "page": 1,
                "size": 20,
                "total_pages": 5
            }
        }


class UserStatsResponse(BaseModel):
    """User statistics response schema"""
    total_users: int = Field(..., description="전체 사용자 수")
    active_users: int = Field(..., description="활성 사용자 수")
    verified_users: int = Field(..., description="인증된 사용자 수")
    users_by_role: Dict[str, int] = Field(..., description="역할별 사용자 수")
    users_by_status: Dict[str, int] = Field(..., description="상태별 사용자 수")
    recent_registrations: int = Field(..., description="최근 7일 신규 가입자 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_users": 150,
                "active_users": 120,
                "verified_users": 100,
                "users_by_role": {
                    "super_admin": 1,
                    "admin": 3,
                    "manager": 10,
                    "operator": 100,
                    "viewer": 36
                },
                "users_by_status": {
                    "active": 120,
                    "inactive": 15,
                    "suspended": 5,
                    "pending": 10
                },
                "recent_registrations": 8
            }
        }


class UserActivityResponse(BaseModel):
    """User activity response schema"""
    user_id: str = Field(..., description="사용자 ID")
    activity_type: str = Field(..., description="활동 유형")
    activity_data: Dict[str, Any] = Field(..., description="활동 데이터")
    ip_address: Optional[str] = Field(None, description="IP 주소")
    user_agent: Optional[str] = Field(None, description="사용자 에이전트")
    created_at: datetime = Field(..., description="활동 시간")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "activity_type": "login",
                "activity_data": {
                    "method": "email_password",
                    "success": True
                },
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "created_at": "2024-01-01T10:00:00Z"
            }
        }


class UserPermissionResponse(BaseModel):
    """User permission response schema"""
    user_id: str = Field(..., description="사용자 ID")
    role: UserRole = Field(..., description="사용자 역할")
    permissions: List[str] = Field(..., description="사용자 권한 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "operator",
                "permissions": [
                    "product_edit",
                    "order_edit",
                    "inventory_edit"
                ]
            }
        }


class UserBulkActionResponse(BaseModel):
    """Bulk action response schema"""
    success_count: int = Field(..., description="성공한 작업 수")
    fail_count: int = Field(..., description="실패한 작업 수")
    failed_user_ids: List[str] = Field(..., description="실패한 사용자 ID 목록")
    errors: List[str] = Field(..., description="에러 메시지 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success_count": 8,
                "fail_count": 2,
                "failed_user_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                "errors": ["사용자를 찾을 수 없습니다"]
            }
        }