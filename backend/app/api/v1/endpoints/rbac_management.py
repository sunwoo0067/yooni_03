"""
RBAC Management API Endpoints
Provides comprehensive role and permission management for administrators
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.api.v1.dependencies.database import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.core.rbac_security import (
    require_role_read, require_role_create, require_role_update, require_role_delete,
    require_user_read, require_user_update, require_super_admin
)
from app.models.user import User, UserRole
from app.models.rbac import (
    Permission, Role, PermissionCategory, PermissionAction, ResourceScope,
    UserPermissionAudit, AccessRequest, PermissionDelegation,
    DROPSHIPPING_PERMISSIONS, DROPSHIPPING_ROLES,
    role_permission_association, user_permission_override
)
from app.services.rbac import get_permission_service, PermissionContext
from app.schemas.rbac import (
    PermissionResponse, RoleResponse, RoleCreate, RoleUpdate,
    UserPermissionResponse, PermissionGrantRequest, PermissionDelegationRequest,
    AccessRequestResponse, AccessRequestCreate, AuditLogResponse
)

router = APIRouter()


# Permission Management Endpoints

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    category: Optional[PermissionCategory] = Query(None, description="필터링할 권한 카테고리"),
    action: Optional[PermissionAction] = Query(None, description="필터링할 권한 액션"),
    active_only: bool = Query(True, description="활성 권한만 조회"),
    search: Optional[str] = Query(None, description="권한명 검색"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 개수"),
    current_user: User = Depends(require_role_read),
    db: Session = Depends(get_db)
):
    """권한 목록 조회"""
    query = db.query(Permission)
    
    # Apply filters
    if category:
        query = query.filter(Permission.category == category)
    if action:
        query = query.filter(Permission.action == action)
    if active_only:
        query = query.filter(Permission.is_active == True)
    if search:
        query = query.filter(Permission.name.ilike(f"%{search}%"))
    
    # Apply pagination
    permissions = query.order_by(Permission.category, Permission.name).offset(skip).limit(limit).all()
    
    return [PermissionResponse.from_orm(perm) for perm in permissions]


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: str = Path(..., description="권한 ID"),
    current_user: User = Depends(require_role_read),
    db: Session = Depends(get_db)
):
    """특정 권한 상세 조회"""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="권한을 찾을 수 없습니다"
        )
    
    return PermissionResponse.from_orm(permission)


# Role Management Endpoints

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    active_only: bool = Query(True, description="활성 역할만 조회"),
    include_system: bool = Query(False, description="시스템 역할 포함"),
    search: Optional[str] = Query(None, description="역할명 검색"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(100, ge=1, le=500, description="조회할 개수"),
    current_user: User = Depends(require_role_read),
    db: Session = Depends(get_db)
):
    """역할 목록 조회"""
    query = db.query(Role)
    
    # Apply filters
    if active_only:
        query = query.filter(Role.is_active == True)
    if not include_system:
        query = query.filter(Role.is_system_role == False)
    if search:
        query = query.filter(Role.name.ilike(f"%{search}%"))
    
    # Apply pagination
    roles = query.order_by(desc(Role.level), Role.name).offset(skip).limit(limit).all()
    
    return [RoleResponse.from_orm(role) for role in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str = Path(..., description="역할 ID"),
    include_permissions: bool = Query(True, description="권한 정보 포함"),
    current_user: User = Depends(require_role_read),
    db: Session = Depends(get_db)
):
    """특정 역할 상세 조회"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="역할을 찾을 수 없습니다"
        )
    
    role_data = RoleResponse.from_orm(role)
    
    if include_permissions:
        role_data.permissions = [PermissionResponse.from_orm(perm) for perm in role.get_all_permissions()]
    
    return role_data


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_role_create),
    db: Session = Depends(get_db)
):
    """새 역할 생성"""
    # Check if role name already exists
    existing = db.query(Role).filter(Role.name == role_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 역할명입니다"
        )
    
    # Create new role
    new_role = Role(
        name=role_data.name,
        display_name=role_data.display_name,
        description=role_data.description,
        level=role_data.level,
        max_users=role_data.max_users,
        parent_role_id=role_data.parent_role_id
    )
    
    db.add(new_role)
    db.flush()  # Get the ID
    
    # Add permissions if provided
    if role_data.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        new_role.permissions = permissions
    
    db.commit()
    db.refresh(new_role)
    
    return RoleResponse.from_orm(new_role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str = Path(..., description="역할 ID"),
    role_data: RoleUpdate = Body(...),
    current_user: User = Depends(require_role_update),
    db: Session = Depends(get_db)
):
    """역할 정보 수정"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="역할을 찾을 수 없습니다"
        )
    
    # Prevent modification of system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="시스템 역할은 수정할 수 없습니다"
        )
    
    # Update fields
    update_data = role_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field != "permission_ids":
            setattr(role, field, value)
    
    # Update permissions if provided
    if role_data.permission_ids is not None:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        role.permissions = permissions
    
    db.commit()
    db.refresh(role)
    
    return RoleResponse.from_orm(role)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str = Path(..., description="역할 ID"),
    current_user: User = Depends(require_role_delete),
    db: Session = Depends(get_db)
):
    """역할 삭제"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="역할을 찾을 수 없습니다"
        )
    
    # Prevent deletion of system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="시스템 역할은 삭제할 수 없습니다"
        )
    
    # Check if role is in use
    users_count = db.query(User).filter(User.role == UserRole(role.name)).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이 역할을 사용하는 사용자가 {users_count}명 있어 삭제할 수 없습니다"
        )
    
    db.delete(role)
    db.commit()
    
    return {"message": "역할이 성공적으로 삭제되었습니다"}


# User Permission Management

@router.get("/users/{user_id}/permissions", response_model=UserPermissionResponse)
async def get_user_permissions(
    user_id: str = Path(..., description="사용자 ID"),
    include_inherited: bool = Query(True, description="상속된 권한 포함"),
    current_user: User = Depends(require_user_read),
    db: Session = Depends(get_db)
):
    """사용자 권한 조회"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    permission_service = get_permission_service(db)
    permissions = await permission_service.get_user_permissions(user, include_inherited)
    
    # Get role permissions
    role_permissions = []
    if user.role:
        role = db.query(Role).filter(Role.name == user.role.value).first()
        if role:
            if include_inherited:
                role_permissions = role.get_all_permissions()
            else:
                role_permissions = role.permissions
    
    # Get user-specific overrides
    overrides = db.query(user_permission_override).join(Permission).filter(
        and_(
            user_permission_override.c.user_id == user.id,
            or_(
                user_permission_override.c.expires_at.is_(None),
                user_permission_override.c.expires_at > datetime.utcnow()
            )
        )
    ).all()
    
    override_permissions = []
    for override in overrides:
        permission = db.query(Permission).filter(Permission.id == override.permission_id).first()
        if permission:
            override_permissions.append({
                "permission": PermissionResponse.from_orm(permission),
                "granted": override.is_granted,
                "expires_at": override.expires_at,
                "reason": override.reason
            })
    
    # Get delegated permissions
    delegated = db.query(PermissionDelegation).join(Permission).filter(
        and_(
            PermissionDelegation.delegate_id == user.id,
            PermissionDelegation.is_active == True,
            PermissionDelegation.valid_from <= datetime.utcnow(),
            or_(
                PermissionDelegation.valid_until.is_(None),
                PermissionDelegation.valid_until > datetime.utcnow()
            )
        )
    ).all()
    
    delegated_permissions = []
    for delegation in delegated:
        if delegation.is_valid():
            delegated_permissions.append({
                "permission": PermissionResponse.from_orm(delegation.permission),
                "delegator_id": str(delegation.delegator_id),
                "expires_at": delegation.valid_until,
                "conditions": delegation.conditions
            })
    
    return UserPermissionResponse(
        user_id=str(user.id),
        role_name=user.role.value if user.role else None,
        role_permissions=[PermissionResponse.from_orm(p) for p in role_permissions],
        override_permissions=override_permissions,
        delegated_permissions=delegated_permissions,
        effective_permissions=[PermissionResponse.from_orm(p) for p in permissions]
    )


@router.post("/users/{user_id}/permissions/grant")
async def grant_user_permission(
    user_id: str = Path(..., description="사용자 ID"),
    grant_request: PermissionGrantRequest = Body(...),
    current_user: User = Depends(require_user_update),
    db: Session = Depends(get_db)
):
    """사용자에게 권한 부여"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    permission_service = get_permission_service(db)
    
    success = await permission_service.grant_permission(
        user=user,
        permission_name=grant_request.permission_name,
        granted_by=current_user,
        expires_at=grant_request.expires_at,
        reason=grant_request.reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="권한 부여에 실패했습니다"
        )
    
    return {"message": "권한이 성공적으로 부여되었습니다"}


@router.post("/users/{user_id}/permissions/revoke")
async def revoke_user_permission(
    user_id: str = Path(..., description="사용자 ID"),
    permission_name: str = Body(..., embed=True),
    reason: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(require_user_update),
    db: Session = Depends(get_db)
):
    """사용자 권한 취소"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    permission_service = get_permission_service(db)
    
    success = await permission_service.revoke_permission(
        user=user,
        permission_name=permission_name,
        revoked_by=current_user,
        reason=reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="권한 취소에 실패했습니다"
        )
    
    return {"message": "권한이 성공적으로 취소되었습니다"}


@router.post("/users/{user_id}/permissions/delegate")
async def delegate_permission(
    user_id: str = Path(..., description="위임받을 사용자 ID"),
    delegation_request: PermissionDelegationRequest = Body(...),
    current_user: User = Depends(require_user_update),
    db: Session = Depends(get_db)
):
    """권한 위임"""
    delegate_user = db.query(User).filter(User.id == user_id).first()
    if not delegate_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="위임받을 사용자를 찾을 수 없습니다"
        )
    
    permission_service = get_permission_service(db)
    
    success = await permission_service.delegate_permission(
        delegator=current_user,
        delegate=delegate_user,
        permission_name=delegation_request.permission_name,
        valid_until=delegation_request.valid_until,
        can_redelegate=delegation_request.can_redelegate,
        conditions=delegation_request.conditions
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="권한 위임에 실패했습니다"
        )
    
    return {"message": "권한이 성공적으로 위임되었습니다"}


# Access Request Management

@router.get("/access-requests", response_model=List[AccessRequestResponse])
async def list_access_requests(
    status_filter: Optional[str] = Query(None, description="상태 필터 (PENDING, APPROVED, REJECTED)"),
    user_id: Optional[str] = Query(None, description="특정 사용자의 요청만 조회"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_user_read),
    db: Session = Depends(get_db)
):
    """접근 권한 요청 목록 조회"""
    query = db.query(AccessRequest)
    
    if status_filter:
        query = query.filter(AccessRequest.status == status_filter)
    if user_id:
        query = query.filter(AccessRequest.user_id == user_id)
    
    requests = query.order_by(desc(AccessRequest.created_at)).offset(skip).limit(limit).all()
    
    return [AccessRequestResponse.from_orm(req) for req in requests]


@router.post("/access-requests", response_model=AccessRequestResponse)
async def create_access_request(
    request_data: AccessRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 접근 권한 요청 생성"""
    # Check if user already has an active request for the same permission/role
    existing = db.query(AccessRequest).filter(
        and_(
            AccessRequest.user_id == current_user.id,
            AccessRequest.status == "PENDING",
            or_(
                and_(
                    AccessRequest.permission_id.isnot(None),
                    AccessRequest.permission_id == db.query(Permission).filter(
                        Permission.name == request_data.permission_name
                    ).first().id if request_data.permission_name else None
                ),
                and_(
                    AccessRequest.role_id.isnot(None),
                    AccessRequest.role_id == db.query(Role).filter(
                        Role.name == request_data.role_name
                    ).first().id if request_data.role_name else None
                )
            )
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="동일한 권한/역할에 대한 대기 중인 요청이 이미 있습니다"
        )
    
    # Create new request
    new_request = AccessRequest(
        user_id=current_user.id,
        request_type="PERMISSION" if request_data.permission_name else "ROLE",
        justification=request_data.justification,
        requested_duration=request_data.requested_duration
    )
    
    if request_data.permission_name:
        permission = db.query(Permission).filter(Permission.name == request_data.permission_name).first()
        if permission:
            new_request.permission_id = permission.id
    
    if request_data.role_name:
        role = db.query(Role).filter(Role.name == request_data.role_name).first()
        if role:
            new_request.role_id = role.id
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return AccessRequestResponse.from_orm(new_request)


@router.put("/access-requests/{request_id}/review")
async def review_access_request(
    request_id: str = Path(..., description="요청 ID"),
    action: str = Body(..., description="APPROVE 또는 REJECT"),
    comments: Optional[str] = Body(None, description="검토 의견"),
    current_user: User = Depends(require_user_update),
    db: Session = Depends(get_db)
):
    """접근 권한 요청 검토"""
    if action not in ["APPROVE", "REJECT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action은 APPROVE 또는 REJECT이어야 합니다"
        )
    
    request_obj = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청을 찾을 수 없습니다"
        )
    
    if request_obj.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리된 요청입니다"
        )
    
    # Update request status
    request_obj.status = action + "D"  # APPROVED or REJECTED
    request_obj.reviewed_by = current_user.id
    request_obj.reviewed_at = datetime.utcnow()
    request_obj.review_comments = comments
    
    # If approved, grant the permission/role
    if action == "APPROVE":
        user = db.query(User).filter(User.id == request_obj.user_id).first()
        if user:
            permission_service = get_permission_service(db)
            
            if request_obj.permission_id:
                permission = db.query(Permission).filter(Permission.id == request_obj.permission_id).first()
                if permission:
                    expires_at = None
                    if request_obj.requested_duration:
                        expires_at = datetime.utcnow() + timedelta(days=request_obj.requested_duration)
                    
                    await permission_service.grant_permission(
                        user=user,
                        permission_name=permission.name,
                        granted_by=current_user,
                        expires_at=expires_at,
                        reason=f"Access request approved: {request_obj.justification}"
                    )
    
    db.commit()
    
    return {"message": f"요청이 성공적으로 {action.lower()}되었습니다"}


# Audit Trail

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    user_id: Optional[str] = Query(None, description="특정 사용자의 로그만 조회"),
    action: Optional[str] = Query(None, description="특정 액션 필터 (GRANT, REVOKE, MODIFY)"),
    start_date: Optional[datetime] = Query(None, description="시작 날짜"),
    end_date: Optional[datetime] = Query(None, description="종료 날짜"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """권한 변경 감사 로그 조회"""
    query = db.query(UserPermissionAudit)
    
    if user_id:
        query = query.filter(UserPermissionAudit.user_id == user_id)
    if action:
        query = query.filter(UserPermissionAudit.action == action)
    if start_date:
        query = query.filter(UserPermissionAudit.created_at >= start_date)
    if end_date:
        query = query.filter(UserPermissionAudit.created_at <= end_date)
    
    logs = query.order_by(desc(UserPermissionAudit.created_at)).offset(skip).limit(limit).all()
    
    return [AuditLogResponse.from_orm(log) for log in logs]


# System Management

@router.post("/initialize-default-permissions")
async def initialize_default_permissions(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """기본 권한 및 역할 초기화"""
    try:
        # Create default permissions
        created_permissions = 0
        for perm_data in DROPSHIPPING_PERMISSIONS:
            name, display_name, category, action, resource_type, scope = perm_data
            
            existing = db.query(Permission).filter(Permission.name == name).first()
            if not existing:
                permission = Permission(
                    name=name,
                    display_name=display_name,
                    category=category,
                    action=action,
                    resource_type=resource_type,
                    scope=scope,
                    is_system_permission=True
                )
                db.add(permission)
                created_permissions += 1
        
        db.flush()  # Ensure permissions are created before roles
        
        # Create default roles
        created_roles = 0
        for role_name, role_config in DROPSHIPPING_ROLES.items():
            existing = db.query(Role).filter(Role.name == role_name).first()
            if not existing:
                role = Role(
                    name=role_name,
                    display_name=role_config["display_name"],
                    description=role_config["description"],
                    level=role_config["level"],
                    is_system_role=True
                )
                
                # Add permissions to role
                if role_config["permissions"] == ["*"]:
                    # Super admin gets all permissions
                    all_permissions = db.query(Permission).all()
                    role.permissions = all_permissions
                else:
                    # Add specific permissions
                    permissions = db.query(Permission).filter(
                        Permission.name.in_(role_config["permissions"])
                    ).all()
                    role.permissions = permissions
                
                db.add(role)
                created_roles += 1
        
        db.commit()
        
        return {
            "message": "기본 권한 및 역할이 성공적으로 초기화되었습니다",
            "created_permissions": created_permissions,
            "created_roles": created_roles
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"초기화 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/system-stats")
async def get_system_stats(
    current_user: User = Depends(require_user_read),
    db: Session = Depends(get_db)
):
    """시스템 통계 정보"""
    stats = {
        "total_permissions": db.query(Permission).count(),
        "active_permissions": db.query(Permission).filter(Permission.is_active == True).count(),
        "total_roles": db.query(Role).count(),
        "active_roles": db.query(Role).filter(Role.is_active == True).count(),
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.is_active == True).count(),
        "pending_access_requests": db.query(AccessRequest).filter(
            AccessRequest.status == "PENDING"
        ).count(),
        "active_delegations": db.query(PermissionDelegation).filter(
            and_(
                PermissionDelegation.is_active == True,
                PermissionDelegation.valid_from <= datetime.utcnow(),
                or_(
                    PermissionDelegation.valid_until.is_(None),
                    PermissionDelegation.valid_until > datetime.utcnow()
                )
            )
        ).count(),
        "permission_categories": db.query(Permission.category, func.count(Permission.id)).group_by(
            Permission.category
        ).all(),
        "users_by_role": db.query(User.role, func.count(User.id)).group_by(User.role).all()
    }
    
    return stats