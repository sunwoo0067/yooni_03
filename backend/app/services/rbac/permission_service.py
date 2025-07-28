"""
Advanced RBAC Permission Service
Handles granular permissions, inheritance, conditional access, and resource-based permissions
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from fastapi import HTTPException, status
import json
import ipaddress
from urllib.parse import urlparse

from app.models.user import User, UserRole
from app.models.rbac import (
    Permission, Role, PermissionCategory, PermissionAction, ResourceScope,
    PermissionCondition, UserPermissionAudit, PermissionDelegation,
    role_permission_association, user_permission_override
)
from app.core.config import settings
from app.services.cache_service import cache_service


class PermissionContext:
    """Context for permission evaluation"""
    
    def __init__(
        self,
        user: User,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_owner_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_time: Optional[datetime] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        self.user = user
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.resource_owner_id = resource_owner_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_time = request_time or datetime.utcnow()
        self.additional_context = additional_context or {}


class PermissionEvaluationResult:
    """Result of permission evaluation"""
    
    def __init__(
        self,
        granted: bool,
        reason: str,
        conditions_met: List[str] = None,
        conditions_failed: List[str] = None,
        delegated: bool = False,
        expires_at: Optional[datetime] = None
    ):
        self.granted = granted
        self.reason = reason
        self.conditions_met = conditions_met or []
        self.conditions_failed = conditions_failed or []
        self.delegated = delegated
        self.expires_at = expires_at


class DropshippingPermissionService:
    """Advanced permission service for dropshipping platform"""
    
    def __init__(self, db: Session):
        self.db = db
        self._permission_cache = {}
        self._role_cache = {}
    
    async def has_permission(
        self,
        user: User,
        permission_name: str,
        context: Optional[PermissionContext] = None
    ) -> bool:
        """Check if user has specific permission"""
        result = await self.evaluate_permission(user, permission_name, context)
        return result.granted
    
    async def evaluate_permission(
        self,
        user: User,
        permission_name: str,
        context: Optional[PermissionContext] = None
    ) -> PermissionEvaluationResult:
        """Evaluate permission with detailed result"""
        if context is None:
            context = PermissionContext(user)
        
        # Check cache first
        cache_key = f"permission:{user.id}:{permission_name}:{hash(str(context.__dict__))}"
        cached_result = await self._get_cached_permission(cache_key)
        if cached_result:
            return cached_result
        
        # Super admin bypass
        if user.role == UserRole.SUPER_ADMIN:
            result = PermissionEvaluationResult(
                granted=True,
                reason="Super administrator access"
            )
            await self._cache_permission_result(cache_key, result, 300)  # 5 minutes
            return result
        
        # Get permission definition
        permission = await self._get_permission(permission_name)
        if not permission:
            result = PermissionEvaluationResult(
                granted=False,
                reason=f"Permission '{permission_name}' not found"
            )
            return result
        
        # Check if permission is active
        if not permission.is_active:
            result = PermissionEvaluationResult(
                granted=False,
                reason=f"Permission '{permission_name}' is inactive"
            )
            return result
        
        # Check user-specific permission overrides first
        override_result = await self._check_permission_override(user, permission, context)
        if override_result:
            await self._cache_permission_result(cache_key, override_result, 300)
            return override_result
        
        # Check delegated permissions
        delegation_result = await self._check_delegated_permission(user, permission, context)
        if delegation_result and delegation_result.granted:
            await self._cache_permission_result(cache_key, delegation_result, 300)
            return delegation_result
        
        # Check role-based permissions
        role_result = await self._check_role_permission(user, permission, context)
        if role_result:
            await self._cache_permission_result(cache_key, role_result, 300)
            return role_result
        
        # Default deny
        result = PermissionEvaluationResult(
            granted=False,
            reason=f"Permission '{permission_name}' not granted to user"
        )
        await self._cache_permission_result(cache_key, result, 300)
        return result
    
    async def check_resource_access(
        self,
        user: User,
        permission_name: str,
        resource_id: str,
        resource_type: str,
        resource_owner_id: Optional[str] = None
    ) -> bool:
        """Check resource-specific access"""
        context = PermissionContext(
            user=user,
            resource_id=resource_id,
            resource_type=resource_type,
            resource_owner_id=resource_owner_id
        )
        
        result = await self.evaluate_permission(user, permission_name, context)
        
        if not result.granted:
            return False
        
        # Check resource scope
        permission = await self._get_permission(permission_name)
        if not permission:
            return False
        
        return await self._check_resource_scope(user, permission, context)
    
    async def get_user_permissions(self, user: User, include_inherited: bool = True) -> List[Permission]:
        """Get all permissions for a user"""
        permissions = []
        
        # Get role-based permissions
        if user.role:
            role = await self._get_role(user.role.value)
            if role:
                if include_inherited:
                    permissions.extend(role.get_all_permissions())
                else:
                    permissions.extend(role.permissions)
        
        # Get user-specific overrides (grants)
        overrides = self.db.query(user_permission_override).filter(
            and_(
                user_permission_override.c.user_id == user.id,
                user_permission_override.c.is_granted == True,
                or_(
                    user_permission_override.c.expires_at.is_(None),
                    user_permission_override.c.expires_at > datetime.utcnow()
                )
            )
        ).all()
        
        for override in overrides:
            permission = await self._get_permission_by_id(override.permission_id)
            if permission and permission not in permissions:
                permissions.append(permission)
        
        # Get delegated permissions
        delegated = await self._get_delegated_permissions(user)
        permissions.extend(delegated)
        
        return list(set(permissions))  # Remove duplicates
    
    async def grant_permission(
        self,
        user: User,
        permission_name: str,
        granted_by: User,
        expires_at: Optional[datetime] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Grant specific permission to user"""
        permission = await self._get_permission(permission_name)
        if not permission:
            return False
        
        # Check if granter has authority
        if not await self.has_permission(granted_by, "users.update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to grant permissions"
            )
        
        # Insert or update override
        existing = self.db.query(user_permission_override).filter(
            and_(
                user_permission_override.c.user_id == user.id,
                user_permission_override.c.permission_id == permission.id
            )
        ).first()
        
        if existing:
            # Update existing override
            self.db.execute(
                user_permission_override.update().where(
                    and_(
                        user_permission_override.c.user_id == user.id,
                        user_permission_override.c.permission_id == permission.id
                    )
                ).values(
                    is_granted=True,
                    granted_at=datetime.utcnow(),
                    granted_by=granted_by.id,
                    expires_at=expires_at,
                    reason=reason
                )
            )
        else:
            # Insert new override
            self.db.execute(
                user_permission_override.insert().values(
                    user_id=user.id,
                    permission_id=permission.id,
                    is_granted=True,
                    granted_at=datetime.utcnow(),
                    granted_by=granted_by.id,
                    expires_at=expires_at,
                    reason=reason
                )
            )
        
        # Log audit trail
        await self._log_permission_audit(
            user=user,
            permission=permission,
            action="GRANT",
            changed_by=granted_by,
            reason=reason,
            new_value={"granted": True, "expires_at": expires_at.isoformat() if expires_at else None}
        )
        
        self.db.commit()
        
        # Clear cache
        await self._clear_user_permission_cache(user.id)
        
        return True
    
    async def revoke_permission(
        self,
        user: User,
        permission_name: str,
        revoked_by: User,
        reason: Optional[str] = None
    ) -> bool:
        """Revoke specific permission from user"""
        permission = await self._get_permission(permission_name)
        if not permission:
            return False
        
        # Check if revoker has authority
        if not await self.has_permission(revoked_by, "users.update"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to revoke permissions"
            )
        
        # Insert revocation override
        self.db.execute(
            user_permission_override.insert().values(
                user_id=user.id,
                permission_id=permission.id,
                is_granted=False,
                granted_at=datetime.utcnow(),
                granted_by=revoked_by.id,
                reason=reason
            )
        )
        
        # Log audit trail
        await self._log_permission_audit(
            user=user,
            permission=permission,
            action="REVOKE",
            changed_by=revoked_by,
            reason=reason,
            new_value={"granted": False}
        )
        
        self.db.commit()
        
        # Clear cache
        await self._clear_user_permission_cache(user.id)
        
        return True
    
    async def delegate_permission(
        self,
        delegator: User,
        delegate: User,
        permission_name: str,
        valid_until: Optional[datetime] = None,
        can_redelegate: bool = False,
        conditions: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Delegate permission from one user to another"""
        permission = await self._get_permission(permission_name)
        if not permission:
            return False
        
        # Check if delegator has the permission
        if not await self.has_permission(delegator, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delegate permission you don't have"
            )
        
        # Check if delegation already exists
        existing = self.db.query(PermissionDelegation).filter(
            and_(
                PermissionDelegation.delegator_id == delegator.id,
                PermissionDelegation.delegate_id == delegate.id,
                PermissionDelegation.permission_id == permission.id,
                PermissionDelegation.is_active == True
            )
        ).first()
        
        if existing:
            return False  # Already delegated
        
        # Create delegation
        delegation = PermissionDelegation(
            delegator_id=delegator.id,
            delegate_id=delegate.id,
            permission_id=permission.id,
            can_redelegate=can_redelegate,
            valid_until=valid_until,
            conditions=conditions
        )
        
        self.db.add(delegation)
        self.db.commit()
        
        # Clear cache
        await self._clear_user_permission_cache(delegate.id)
        
        return True
    
    # Private helper methods
    
    async def _get_permission(self, permission_name: str) -> Optional[Permission]:
        """Get permission by name with caching"""
        if permission_name in self._permission_cache:
            return self._permission_cache[permission_name]
        
        permission = self.db.query(Permission).filter(
            Permission.name == permission_name
        ).first()
        
        self._permission_cache[permission_name] = permission
        return permission
    
    async def _get_permission_by_id(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID"""
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    
    async def _get_role(self, role_name: str) -> Optional[Role]:
        """Get role by name with caching"""
        if role_name in self._role_cache:
            return self._role_cache[role_name]
        
        role = self.db.query(Role).filter(Role.name == role_name).first()
        self._role_cache[role_name] = role
        return role
    
    async def _check_permission_override(
        self,
        user: User,
        permission: Permission,
        context: PermissionContext
    ) -> Optional[PermissionEvaluationResult]:
        """Check user-specific permission overrides"""
        override = self.db.query(user_permission_override).filter(
            and_(
                user_permission_override.c.user_id == user.id,
                user_permission_override.c.permission_id == permission.id,
                or_(
                    user_permission_override.c.expires_at.is_(None),
                    user_permission_override.c.expires_at > datetime.utcnow()
                )
            )
        ).first()
        
        if override:
            return PermissionEvaluationResult(
                granted=override.is_granted,
                reason=f"User-specific override: {'granted' if override.is_granted else 'denied'}",
                expires_at=override.expires_at
            )
        
        return None
    
    async def _check_delegated_permission(
        self,
        user: User,
        permission: Permission,
        context: PermissionContext
    ) -> Optional[PermissionEvaluationResult]:
        """Check delegated permissions"""
        delegation = self.db.query(PermissionDelegation).filter(
            and_(
                PermissionDelegation.delegate_id == user.id,
                PermissionDelegation.permission_id == permission.id,
                PermissionDelegation.is_active == True,
                PermissionDelegation.valid_from <= datetime.utcnow(),
                or_(
                    PermissionDelegation.valid_until.is_(None),
                    PermissionDelegation.valid_until > datetime.utcnow()
                )
            )
        ).first()
        
        if delegation and delegation.is_valid():
            # Check delegation conditions
            if delegation.conditions:
                conditions_met = await self._check_conditions(delegation.conditions, context)
                if not conditions_met:
                    return PermissionEvaluationResult(
                        granted=False,
                        reason="Delegation conditions not met",
                        delegated=True
                    )
            
            # Update usage count
            delegation.usage_count += 1
            self.db.commit()
            
            return PermissionEvaluationResult(
                granted=True,
                reason=f"Permission delegated by user {delegation.delegator_id}",
                delegated=True,
                expires_at=delegation.valid_until
            )
        
        return None
    
    async def _check_role_permission(
        self,
        user: User,
        permission: Permission,
        context: PermissionContext
    ) -> Optional[PermissionEvaluationResult]:
        """Check role-based permissions"""
        if not user.role:
            return PermissionEvaluationResult(
                granted=False,
                reason="User has no role assigned"
            )
        
        role = await self._get_role(user.role.value)
        if not role:
            return PermissionEvaluationResult(
                granted=False,
                reason=f"Role '{user.role.value}' not found"
            )
        
        # Check if role has the permission (including inherited)
        all_permissions = role.get_all_permissions()
        
        if permission not in all_permissions:
            return PermissionEvaluationResult(
                granted=False,
                reason=f"Role '{role.name}' does not have permission '{permission.name}'"
            )
        
        # Check resource scope
        scope_granted = await self._check_resource_scope(user, permission, context)
        if not scope_granted:
            return PermissionEvaluationResult(
                granted=False,
                reason=f"Resource scope check failed for permission '{permission.name}'"
            )
        
        # Check conditional permissions
        if permission.conditions:
            conditions_met = await self._check_conditions(permission.conditions, context)
            if not conditions_met:
                return PermissionEvaluationResult(
                    granted=False,
                    reason="Permission conditions not met"
                )
        
        return PermissionEvaluationResult(
            granted=True,
            reason=f"Permission granted via role '{role.name}'"
        )
    
    async def _check_resource_scope(
        self,
        user: User,
        permission: Permission,
        context: PermissionContext
    ) -> bool:
        """Check if user has access to resource based on scope"""
        if permission.scope == ResourceScope.GLOBAL:
            return True
        
        if permission.scope == ResourceScope.ORGANIZATION:
            # For now, all users are in the same organization
            return True
        
        if permission.scope == ResourceScope.DEPARTMENT:
            # Check if users are in the same department
            if context.resource_owner_id:
                resource_owner = self.db.query(User).filter(
                    User.id == context.resource_owner_id
                ).first()
                if resource_owner and resource_owner.department == user.department:
                    return True
            return False
        
        if permission.scope == ResourceScope.OWN:
            # User can only access their own resources
            return context.resource_owner_id == str(user.id)
        
        return False
    
    async def _check_conditions(
        self,
        conditions: Dict[str, Any],
        context: PermissionContext
    ) -> bool:
        """Check conditional permission constraints"""
        for condition_type, condition_value in conditions.items():
            if condition_type == "time_based":
                if not await self._check_time_condition(condition_value, context):
                    return False
            elif condition_type == "ip_based":
                if not await self._check_ip_condition(condition_value, context):
                    return False
            elif condition_type == "value_based":
                if not await self._check_value_condition(condition_value, context):
                    return False
            elif condition_type == "location_based":
                if not await self._check_location_condition(condition_value, context):
                    return False
        
        return True
    
    async def _check_time_condition(self, condition: Dict[str, Any], context: PermissionContext) -> bool:
        """Check time-based conditions"""
        current_time = context.request_time.time()
        current_day = context.request_time.weekday()  # 0 = Monday
        
        # Check allowed hours
        if "hours" in condition:
            start_hour = condition["hours"].get("start", 0)
            end_hour = condition["hours"].get("end", 23)
            if not (start_hour <= current_time.hour <= end_hour):
                return False
        
        # Check allowed days
        if "days" in condition:
            allowed_days = condition["days"]  # List of weekday numbers
            if current_day not in allowed_days:
                return False
        
        return True
    
    async def _check_ip_condition(self, condition: Dict[str, Any], context: PermissionContext) -> bool:
        """Check IP-based conditions"""
        if not context.ip_address:
            return False
        
        allowed_ips = condition.get("allowed_ips", [])
        allowed_networks = condition.get("allowed_networks", [])
        
        user_ip = ipaddress.ip_address(context.ip_address)
        
        # Check specific IPs
        for allowed_ip in allowed_ips:
            if user_ip == ipaddress.ip_address(allowed_ip):
                return True
        
        # Check networks
        for network in allowed_networks:
            if user_ip in ipaddress.ip_network(network):
                return True
        
        return len(allowed_ips) == 0 and len(allowed_networks) == 0  # Allow if no restrictions
    
    async def _check_value_condition(self, condition: Dict[str, Any], context: PermissionContext) -> bool:
        """Check value-based conditions (e.g., monetary limits)"""
        if "max_amount" in condition:
            amount = context.additional_context.get("amount", 0)
            if amount > condition["max_amount"]:
                return False
        
        if "max_quantity" in condition:
            quantity = context.additional_context.get("quantity", 0)
            if quantity > condition["max_quantity"]:
                return False
        
        return True
    
    async def _check_location_condition(self, condition: Dict[str, Any], context: PermissionContext) -> bool:
        """Check location-based conditions"""
        # This would integrate with geolocation services
        # For now, return True (implement based on requirements)
        return True
    
    async def _get_delegated_permissions(self, user: User) -> List[Permission]:
        """Get permissions delegated to user"""
        delegations = self.db.query(PermissionDelegation).join(Permission).filter(
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
        
        permissions = []
        for delegation in delegations:
            if delegation.is_valid():
                permissions.append(delegation.permission)
        
        return permissions
    
    async def _log_permission_audit(
        self,
        user: User,
        permission: Optional[Permission] = None,
        role: Optional[Role] = None,
        action: str = "",
        changed_by: Optional[User] = None,
        reason: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log permission audit trail"""
        audit = UserPermissionAudit(
            user_id=user.id,
            permission_id=permission.id if permission else None,
            role_id=role.id if role else None,
            action=action,
            changed_by=changed_by.id if changed_by else None,
            reason=reason,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(audit)
    
    async def _get_cached_permission(self, cache_key: str) -> Optional[PermissionEvaluationResult]:
        """Get cached permission result"""
        if not cache_service:
            return None
        
        try:
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return PermissionEvaluationResult(
                    granted=data["granted"],
                    reason=data["reason"],
                    conditions_met=data.get("conditions_met", []),
                    conditions_failed=data.get("conditions_failed", []),
                    delegated=data.get("delegated", False),
                    expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
                )
        except Exception:
            pass
        
        return None
    
    async def _cache_permission_result(
        self,
        cache_key: str,
        result: PermissionEvaluationResult,
        ttl: int = 300
    ):
        """Cache permission result"""
        if not cache_service:
            return
        
        try:
            data = {
                "granted": result.granted,
                "reason": result.reason,
                "conditions_met": result.conditions_met,
                "conditions_failed": result.conditions_failed,
                "delegated": result.delegated,
                "expires_at": result.expires_at.isoformat() if result.expires_at else None
            }
            await cache_service.set(cache_key, json.dumps(data), ttl)
        except Exception:
            pass
    
    async def _clear_user_permission_cache(self, user_id: str):
        """Clear all cached permissions for a user"""
        if not cache_service:
            return
        
        try:
            pattern = f"permission:{user_id}:*"
            await cache_service.delete_pattern(pattern)
        except Exception:
            pass


# Service instance factory
def get_permission_service(db: Session) -> DropshippingPermissionService:
    """Get permission service instance"""
    return DropshippingPermissionService(db)