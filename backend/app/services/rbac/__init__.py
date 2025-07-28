"""
RBAC (Role-Based Access Control) services for dropshipping platform
"""

from .permission_service import (
    DropshippingPermissionService,
    PermissionContext,
    PermissionEvaluationResult,
    get_permission_service
)

__all__ = [
    "DropshippingPermissionService",
    "PermissionContext", 
    "PermissionEvaluationResult",
    "get_permission_service"
]