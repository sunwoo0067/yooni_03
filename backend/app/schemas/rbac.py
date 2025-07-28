"""
RBAC Pydantic schemas for request/response models
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.rbac import PermissionCategory, PermissionAction, ResourceScope


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        use_enum_values = True


# Permission schemas
class PermissionBase(BaseSchema):
    name: str = Field(..., description="권한명")
    display_name: str = Field(..., description="표시명")
    description: Optional[str] = Field(None, description="설명")
    category: PermissionCategory = Field(..., description="권한 카테고리")
    action: PermissionAction = Field(..., description="권한 액션")
    resource_type: Optional[str] = Field(None, description="리소스 타입")
    scope: ResourceScope = Field(ResourceScope.OWN, description="접근 범위")


class PermissionCreate(PermissionBase):
    conditions: Optional[Dict[str, Any]] = Field(None, description="조건부 권한 설정")
    parent_id: Optional[str] = Field(None, description="상위 권한 ID")
    priority: int = Field(0, description="우선순위")


class PermissionUpdate(BaseSchema):
    display_name: Optional[str] = Field(None, description="표시명")
    description: Optional[str] = Field(None, description="설명")
    is_active: Optional[bool] = Field(None, description="활성 상태")
    conditions: Optional[Dict[str, Any]] = Field(None, description="조건부 권한 설정")
    priority: Optional[int] = Field(None, description="우선순위")


class PermissionResponse(PermissionBase):
    id: str = Field(..., description="권한 ID")
    is_active: bool = Field(..., description="활성 상태")
    is_system_permission: bool = Field(..., description="시스템 권한 여부")
    priority: int = Field(..., description="우선순위")
    conditions: Optional[Dict[str, Any]] = Field(None, description="조건부 권한 설정")
    parent_id: Optional[str] = Field(None, description="상위 권한 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")


# Role schemas
class RoleBase(BaseSchema):
    name: str = Field(..., description="역할명")
    display_name: str = Field(..., description="표시명")
    description: Optional[str] = Field(None, description="설명")
    level: int = Field(0, description="계층 레벨")


class RoleCreate(RoleBase):
    max_users: Optional[int] = Field(None, description="최대 사용자 수")
    parent_role_id: Optional[str] = Field(None, description="상위 역할 ID")
    permission_ids: Optional[List[str]] = Field(None, description="권한 ID 목록")
    auto_grant_conditions: Optional[Dict[str, Any]] = Field(None, description="자동 부여 조건")


class RoleUpdate(BaseSchema):
    display_name: Optional[str] = Field(None, description="표시명")
    description: Optional[str] = Field(None, description="설명")
    level: Optional[int] = Field(None, description="계층 레벨")
    is_active: Optional[bool] = Field(None, description="활성 상태")
    max_users: Optional[int] = Field(None, description="최대 사용자 수")
    permission_ids: Optional[List[str]] = Field(None, description="권한 ID 목록")
    auto_grant_conditions: Optional[Dict[str, Any]] = Field(None, description="자동 부여 조건")


class RoleResponse(RoleBase):
    id: str = Field(..., description="역할 ID")
    is_active: bool = Field(..., description="활성 상태")
    is_system_role: bool = Field(..., description="시스템 역할 여부")
    max_users: Optional[int] = Field(None, description="최대 사용자 수")
    parent_role_id: Optional[str] = Field(None, description="상위 역할 ID")
    auto_grant_conditions: Optional[Dict[str, Any]] = Field(None, description="자동 부여 조건")
    permissions: Optional[List[PermissionResponse]] = Field(None, description="권한 목록")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")


# User permission schemas
class UserPermissionOverride(BaseSchema):
    permission: PermissionResponse = Field(..., description="권한 정보")
    granted: bool = Field(..., description="부여 여부")
    expires_at: Optional[datetime] = Field(None, description="만료일시")
    reason: Optional[str] = Field(None, description="부여/취소 사유")


class UserDelegatedPermission(BaseSchema):
    permission: PermissionResponse = Field(..., description="권한 정보")
    delegator_id: str = Field(..., description="위임자 ID")
    expires_at: Optional[datetime] = Field(None, description="만료일시")
    conditions: Optional[Dict[str, Any]] = Field(None, description="위임 조건")


class UserPermissionResponse(BaseSchema):
    user_id: str = Field(..., description="사용자 ID")
    role_name: Optional[str] = Field(None, description="역할명")
    role_permissions: List[PermissionResponse] = Field([], description="역할 권한 목록")
    override_permissions: List[UserPermissionOverride] = Field([], description="개별 권한 설정")
    delegated_permissions: List[UserDelegatedPermission] = Field([], description="위임받은 권한")
    effective_permissions: List[PermissionResponse] = Field([], description="유효 권한 목록")


class PermissionGrantRequest(BaseSchema):
    permission_name: str = Field(..., description="부여할 권한명")
    expires_at: Optional[datetime] = Field(None, description="만료일시")
    reason: Optional[str] = Field(None, description="부여 사유")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError("만료일시는 현재 시각보다 미래여야 합니다")
        return v


class PermissionDelegationRequest(BaseSchema):
    permission_name: str = Field(..., description="위임할 권한명")
    valid_until: Optional[datetime] = Field(None, description="위임 만료일시")
    can_redelegate: bool = Field(False, description="재위임 가능 여부")
    conditions: Optional[Dict[str, Any]] = Field(None, description="위임 조건")

    @validator('valid_until')
    def validate_valid_until(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError("위임 만료일시는 현재 시각보다 미래여야 합니다")
        return v


# Access request schemas
class AccessRequestCreate(BaseSchema):
    permission_name: Optional[str] = Field(None, description="요청할 권한명")
    role_name: Optional[str] = Field(None, description="요청할 역할명")
    justification: str = Field(..., description="요청 사유", min_length=10)
    requested_duration: Optional[int] = Field(None, description="요청 기간(일)", gt=0, le=365)

    @validator('permission_name', 'role_name')
    def validate_request_type(cls, v, values):
        permission_name = values.get('permission_name')
        role_name = values.get('role_name')
        
        if not permission_name and not role_name:
            raise ValueError("권한명 또는 역할명 중 하나는 필수입니다")
        if permission_name and role_name:
            raise ValueError("권한명과 역할명을 동시에 요청할 수 없습니다")
        
        return v


class AccessRequestResponse(BaseSchema):
    id: str = Field(..., description="요청 ID")
    user_id: str = Field(..., description="요청자 ID")
    permission_id: Optional[str] = Field(None, description="권한 ID")
    role_id: Optional[str] = Field(None, description="역할 ID")
    request_type: str = Field(..., description="요청 유형 (PERMISSION/ROLE)")
    justification: str = Field(..., description="요청 사유")
    requested_duration: Optional[int] = Field(None, description="요청 기간(일)")
    status: str = Field(..., description="상태 (PENDING/APPROVED/REJECTED)")
    reviewed_by: Optional[str] = Field(None, description="검토자 ID")
    reviewed_at: Optional[datetime] = Field(None, description="검토일시")
    review_comments: Optional[str] = Field(None, description="검토 의견")
    auto_approved: bool = Field(..., description="자동 승인 여부")
    approval_expires_at: Optional[datetime] = Field(None, description="승인 만료일시")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")


# Audit log schemas
class AuditLogResponse(BaseSchema):
    id: str = Field(..., description="로그 ID")
    user_id: str = Field(..., description="대상 사용자 ID")
    permission_id: Optional[str] = Field(None, description="권한 ID")
    role_id: Optional[str] = Field(None, description="역할 ID")
    action: str = Field(..., description="액션 (GRANT/REVOKE/MODIFY)")
    changed_by: str = Field(..., description="변경자 ID")
    reason: Optional[str] = Field(None, description="변경 사유")
    old_value: Optional[Dict[str, Any]] = Field(None, description="이전 값")
    new_value: Optional[Dict[str, Any]] = Field(None, description="새 값")
    ip_address: Optional[str] = Field(None, description="IP 주소")
    user_agent: Optional[str] = Field(None, description="User Agent")
    session_id: Optional[str] = Field(None, description="세션 ID")
    created_at: datetime = Field(..., description="생성일시")


# Permission evaluation schemas
class PermissionCheckRequest(BaseSchema):
    permission_name: str = Field(..., description="확인할 권한명")
    resource_id: Optional[str] = Field(None, description="리소스 ID")
    resource_type: Optional[str] = Field(None, description="리소스 타입")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="추가 컨텍스트")


class PermissionCheckResponse(BaseSchema):
    granted: bool = Field(..., description="권한 부여 여부")
    reason: str = Field(..., description="판정 사유")
    conditions_met: List[str] = Field([], description="충족된 조건들")
    conditions_failed: List[str] = Field([], description="실패한 조건들")
    delegated: bool = Field(False, description="위임된 권한 여부")
    expires_at: Optional[datetime] = Field(None, description="권한 만료일시")


# Bulk operation schemas
class BulkPermissionGrantRequest(BaseSchema):
    user_ids: List[str] = Field(..., description="대상 사용자 ID 목록", min_items=1)
    permission_name: str = Field(..., description="부여할 권한명")
    expires_at: Optional[datetime] = Field(None, description="만료일시")
    reason: Optional[str] = Field(None, description="부여 사유")


class BulkPermissionRevokeRequest(BaseSchema):
    user_ids: List[str] = Field(..., description="대상 사용자 ID 목록", min_items=1)
    permission_name: str = Field(..., description="취소할 권한명")
    reason: Optional[str] = Field(None, description="취소 사유")


class BulkOperationResponse(BaseSchema):
    total_requested: int = Field(..., description="요청된 총 개수")
    successful: int = Field(..., description="성공한 개수")
    failed: int = Field(..., description="실패한 개수")
    errors: List[Dict[str, str]] = Field([], description="오류 목록")


# Permission template schemas
class PermissionTemplate(BaseSchema):
    name: str = Field(..., description="템플릿명")
    description: str = Field(..., description="템플릿 설명")
    permissions: List[str] = Field(..., description="권한명 목록")
    conditions: Optional[Dict[str, Any]] = Field(None, description="적용 조건")


class PermissionTemplateResponse(PermissionTemplate):
    id: str = Field(..., description="템플릿 ID")
    created_by: str = Field(..., description="생성자 ID")
    is_active: bool = Field(..., description="활성 상태")
    usage_count: int = Field(0, description="사용 횟수")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")


# System statistics schemas
class PermissionStatistics(BaseSchema):
    total_permissions: int = Field(..., description="총 권한 수")
    active_permissions: int = Field(..., description="활성 권한 수")
    permissions_by_category: Dict[str, int] = Field(..., description="카테고리별 권한 수")
    most_used_permissions: List[Dict[str, Union[str, int]]] = Field([], description="가장 많이 사용된 권한")


class RoleStatistics(BaseSchema):
    total_roles: int = Field(..., description="총 역할 수")
    active_roles: int = Field(..., description="활성 역할 수")
    users_by_role: Dict[str, int] = Field(..., description="역할별 사용자 수")
    role_permission_count: Dict[str, int] = Field(..., description="역할별 권한 수")


class SystemStatistics(BaseSchema):
    permission_stats: PermissionStatistics = Field(..., description="권한 통계")
    role_stats: RoleStatistics = Field(..., description="역할 통계")
    total_users: int = Field(..., description="총 사용자 수")
    active_users: int = Field(..., description="활성 사용자 수")
    pending_access_requests: int = Field(..., description="대기 중인 접근 요청 수")
    active_delegations: int = Field(..., description="활성 권한 위임 수")
    last_updated: datetime = Field(..., description="통계 업데이트 시각")


# Configuration schemas
class RBACConfiguration(BaseSchema):
    enable_permission_caching: bool = Field(True, description="권한 캐싱 활성화")
    cache_ttl_seconds: int = Field(300, description="캐시 TTL(초)")
    enable_audit_logging: bool = Field(True, description="감사 로깅 활성화")
    enable_auto_cleanup: bool = Field(True, description="자동 정리 활성화")
    cleanup_interval_days: int = Field(30, description="정리 주기(일)")
    max_delegation_depth: int = Field(3, description="최대 위임 깊이")
    default_permission_duration_days: int = Field(90, description="기본 권한 기간(일)")
    require_justification: bool = Field(True, description="사유 필수 입력")
    enable_ip_restrictions: bool = Field(False, description="IP 제한 활성화")
    enable_time_restrictions: bool = Field(False, description="시간 제한 활성화")


class RBACConfigurationResponse(RBACConfiguration):
    id: str = Field(..., description="설정 ID")
    updated_by: str = Field(..., description="수정자 ID")
    updated_at: datetime = Field(..., description="수정일시")