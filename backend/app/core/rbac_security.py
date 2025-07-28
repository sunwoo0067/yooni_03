"""
Enhanced RBAC Security Dependencies
Provides granular permission checking, resource-based access control, and security enforcement
"""
from typing import List, Optional, Callable, Any, Dict
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.rbac import Permission, PermissionCategory, PermissionAction, ResourceScope
from app.api.v1.dependencies.database import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.services.rbac import (
    get_permission_service, 
    PermissionContext, 
    DropshippingPermissionService
)

security = HTTPBearer()


class PermissionDependency:
    """Permission-based dependency for API endpoints"""
    
    def __init__(
        self,
        permission: str,
        resource_type: Optional[str] = None,
        require_resource_ownership: bool = False,
        allow_delegated: bool = True,
        error_message: Optional[str] = None
    ):
        self.permission = permission
        self.resource_type = resource_type
        self.require_resource_ownership = require_resource_ownership
        self.allow_delegated = allow_delegated
        self.error_message = error_message or f"권한이 부족합니다: {permission}"
    
    def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check permission and return user if authorized"""
        return self._check_permission(request, current_user, db)
    
    def _check_permission(self, request: Request, user: User, db: Session) -> User:
        """Internal permission checking logic"""
        # Create permission service
        permission_service = get_permission_service(db)
        
        # Create permission context
        context = PermissionContext(
            user=user,
            resource_type=self.resource_type,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            additional_context={"request_url": str(request.url)}
        )
        
        # Check permission asynchronously (we'll handle this in the async wrapper)
        import asyncio
        try:
            # For now, we'll use a sync approach
            # In production, consider making this fully async
            has_perm = asyncio.get_event_loop().run_until_complete(
                permission_service.has_permission(user, self.permission, context)
            )
        except RuntimeError:
            # If no event loop is running, create one
            has_perm = asyncio.run(
                permission_service.has_permission(user, self.permission, context)
            )
        
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=self.error_message
            )
        
        return user
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request.client, "host"):
            return request.client.host
        
        return None


class ResourcePermissionDependency(PermissionDependency):
    """Resource-specific permission dependency"""
    
    def __init__(
        self,
        permission: str,
        resource_type: str,
        resource_id_param: str = "id",
        owner_field: str = "user_id",
        **kwargs
    ):
        super().__init__(permission, resource_type, **kwargs)
        self.resource_id_param = resource_id_param
        self.owner_field = owner_field
    
    def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check resource-specific permission"""
        # Extract resource ID from path parameters
        resource_id = request.path_params.get(self.resource_id_param)
        if not resource_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resource ID '{self.resource_id_param}' not found in path"
            )
        
        # Get resource owner if ownership is required
        resource_owner_id = None
        if self.require_resource_ownership:
            resource_owner_id = self._get_resource_owner(db, resource_id)
        
        # Create enhanced context
        context = PermissionContext(
            user=current_user,
            resource_id=resource_id,
            resource_type=self.resource_type,
            resource_owner_id=resource_owner_id,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            additional_context={"request_url": str(request.url)}
        )
        
        # Check permission
        permission_service = get_permission_service(db)
        import asyncio
        
        try:
            has_perm = asyncio.get_event_loop().run_until_complete(
                permission_service.check_resource_access(
                    current_user,
                    self.permission,
                    resource_id,
                    self.resource_type,
                    resource_owner_id
                )
            )
        except RuntimeError:
            has_perm = asyncio.run(
                permission_service.check_resource_access(
                    current_user,
                    self.permission,
                    resource_id,
                    self.resource_type,
                    resource_owner_id
                )
            )
        
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=self.error_message
            )
        
        return current_user
    
    def _get_resource_owner(self, db: Session, resource_id: str) -> Optional[str]:
        """Get resource owner ID from database"""
        # This is a generic implementation - override for specific resource types
        try:
            # Dynamic table lookup based on resource_type
            from app.models import product, order  # Import your models
            
            model_map = {
                "product": product.Product,
                "order": order.Order,
                # Add more mappings as needed
            }
            
            model_class = model_map.get(self.resource_type)
            if not model_class:
                return None
            
            resource = db.query(model_class).filter(
                model_class.id == resource_id
            ).first()
            
            if resource and hasattr(resource, self.owner_field):
                return str(getattr(resource, self.owner_field))
            
        except Exception:
            pass
        
        return None


# Convenient permission decorators for specific dropshipping operations

# Product permissions
require_product_read = PermissionDependency("products.read.own")
require_product_read_all = PermissionDependency("products.read.all")
require_product_create = PermissionDependency("products.create.own")
require_product_update = PermissionDependency("products.update.own")
require_product_delete = PermissionDependency("products.delete.own")
require_product_manage = PermissionDependency("products.manage.all")
require_product_bulk_update = PermissionDependency("products.bulk_update")
require_product_sync = PermissionDependency("products.sync")

# Order permissions
require_order_read = PermissionDependency("orders.read.own")
require_order_read_all = PermissionDependency("orders.read.all")
require_order_create = PermissionDependency("orders.create")
require_order_process = PermissionDependency("orders.process")
require_order_approve = PermissionDependency("orders.approve")
require_order_cancel = PermissionDependency("orders.cancel")

# Inventory permissions
require_inventory_read = PermissionDependency("inventory.read")
require_inventory_update = PermissionDependency("inventory.update")
require_inventory_sync = PermissionDependency("inventory.sync")

# Sourcing permissions
require_sourcing_read = PermissionDependency("sourcing.read")
require_sourcing_create = PermissionDependency("sourcing.create")
require_sourcing_manage = PermissionDependency("sourcing.manage")

# Marketplace permissions
require_marketplace_read = PermissionDependency("marketplaces.read")
require_marketplace_configure = PermissionDependency("marketplaces.configure")
require_marketplace_sync = PermissionDependency("marketplaces.sync")

# Wholesaler permissions
require_wholesaler_read = PermissionDependency("wholesalers.read")
require_wholesaler_configure = PermissionDependency("wholesalers.configure")
require_wholesaler_sync = PermissionDependency("wholesalers.sync")

# Pricing permissions
require_pricing_read = PermissionDependency("pricing.read")
require_pricing_update = PermissionDependency("pricing.update")
require_pricing_manage = PermissionDependency("pricing.manage")

# Financial permissions
require_profit_read = PermissionDependency("profits.read")
require_payment_read = PermissionDependency("payments.read")
require_payment_process = PermissionDependency("payments.process")

# Analytics permissions
require_analytics_read = PermissionDependency("analytics.read")
require_report_read = PermissionDependency("reports.read")
require_report_create = PermissionDependency("reports.create")
require_report_export = PermissionDependency("reports.export")

# User management permissions
require_user_read = PermissionDependency("users.read")
require_user_create = PermissionDependency("users.create")
require_user_update = PermissionDependency("users.update")
require_user_delete = PermissionDependency("users.delete")

# Role management permissions
require_role_read = PermissionDependency("roles.read")
require_role_create = PermissionDependency("roles.create")
require_role_update = PermissionDependency("roles.update")
require_role_delete = PermissionDependency("roles.delete")

# Settings permissions
require_settings_read = PermissionDependency("settings.read")
require_settings_update = PermissionDependency("settings.update")

# AI services permissions
require_ai_read = PermissionDependency("ai_services.read")
require_ai_use = PermissionDependency("ai_services.use")
require_ai_configure = PermissionDependency("ai_services.configure")

# Automation permissions
require_automation_read = PermissionDependency("automation.read")
require_automation_configure = PermissionDependency("automation.configure")
require_automation_manage = PermissionDependency("automation.manage")

# Resource-specific dependencies
require_product_resource_access = lambda permission: ResourcePermissionDependency(
    permission, "product", "product_id", "user_id"
)
require_order_resource_access = lambda permission: ResourcePermissionDependency(
    permission, "order", "order_id", "user_id"
)

# Role-based dependencies (legacy support)
class RoleRequirement:
    """Role-based access requirement"""
    
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한이 부족합니다. 필요한 역할: {[role.value for role in self.allowed_roles]}"
            )
        return current_user

# Role-based requirements
require_super_admin = RoleRequirement([UserRole.SUPER_ADMIN])
require_admin = RoleRequirement([UserRole.SUPER_ADMIN, UserRole.ADMIN])
require_manager = RoleRequirement([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER])
require_operator = RoleRequirement([
    UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR
])

# Advanced permission decorators
class ConditionalPermissionDependency(PermissionDependency):
    """Permission dependency with additional conditions"""
    
    def __init__(
        self,
        permission: str,
        conditions: Dict[str, Any],
        **kwargs
    ):
        super().__init__(permission, **kwargs)
        self.conditions = conditions
    
    def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check permission with additional conditions"""
        # Create enhanced context with conditions
        context = PermissionContext(
            user=current_user,
            resource_type=self.resource_type,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            additional_context={
                "request_url": str(request.url),
                **self.conditions
            }
        )
        
        # Check permission
        permission_service = get_permission_service(db)
        import asyncio
        
        try:
            result = asyncio.get_event_loop().run_until_complete(
                permission_service.evaluate_permission(current_user, self.permission, context)
            )
        except RuntimeError:
            result = asyncio.run(
                permission_service.evaluate_permission(current_user, self.permission, context)
            )
        
        if not result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{self.error_message}. 사유: {result.reason}"
            )
        
        return current_user

# Time-based permissions
def require_time_based_permission(
    permission: str,
    allowed_hours: Optional[tuple] = None,
    allowed_days: Optional[List[int]] = None
):
    """Require permission with time-based conditions"""
    conditions = {}
    if allowed_hours:
        conditions["time_based"] = {
            "hours": {"start": allowed_hours[0], "end": allowed_hours[1]}
        }
    if allowed_days:
        conditions["time_based"] = conditions.get("time_based", {})
        conditions["time_based"]["days"] = allowed_days
    
    return ConditionalPermissionDependency(permission, conditions)

# IP-based permissions
def require_ip_based_permission(
    permission: str,
    allowed_ips: Optional[List[str]] = None,
    allowed_networks: Optional[List[str]] = None
):
    """Require permission with IP-based conditions"""
    conditions = {
        "ip_based": {
            "allowed_ips": allowed_ips or [],
            "allowed_networks": allowed_networks or []
        }
    }
    return ConditionalPermissionDependency(permission, conditions)

# Value-based permissions (for financial operations)
def require_value_limited_permission(
    permission: str,
    max_amount: Optional[float] = None,
    max_quantity: Optional[int] = None
):
    """Require permission with value/quantity limits"""
    conditions = {
        "value_based": {}
    }
    if max_amount is not None:
        conditions["value_based"]["max_amount"] = max_amount
    if max_quantity is not None:
        conditions["value_based"]["max_quantity"] = max_quantity
    
    return ConditionalPermissionDependency(permission, conditions)


# Async permission checking utilities
async def check_permission_async(
    user: User,
    permission: str,
    db: Session,
    context: Optional[PermissionContext] = None
) -> bool:
    """Async permission check utility"""
    permission_service = get_permission_service(db)
    if context is None:
        context = PermissionContext(user)
    return await permission_service.has_permission(user, permission, context)

async def check_resource_permission_async(
    user: User,
    permission: str,
    resource_id: str,
    resource_type: str,
    db: Session,
    resource_owner_id: Optional[str] = None
) -> bool:
    """Async resource permission check utility"""
    permission_service = get_permission_service(db)
    return await permission_service.check_resource_access(
        user, permission, resource_id, resource_type, resource_owner_id
    )

# Permission enforcement decorator for service methods
def enforce_permission(permission: str, resource_type: Optional[str] = None):
    """Decorator to enforce permissions on service methods"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user and db from function arguments
            user = None
            db = None
            
            # Look for user and db in kwargs
            if 'user' in kwargs:
                user = kwargs['user']
            if 'db' in kwargs:
                db = kwargs['db']
            
            # Look for user and db in args (assuming they're the first two)
            if not user and len(args) > 0 and isinstance(args[0], User):
                user = args[0]
            if not db and len(args) > 1 and hasattr(args[1], 'query'):
                db = args[1]
            
            if not user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission enforcement requires user and db parameters"
                )
            
            # Check permission
            has_perm = await check_permission_async(user, permission, db)
            if not has_perm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"권한이 부족합니다: {permission}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator