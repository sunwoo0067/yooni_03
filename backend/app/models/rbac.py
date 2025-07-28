"""
Role-Based Access Control (RBAC) models for dropshipping platform
Implements granular permissions, resource-based access, and audit trails
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Boolean, Column, String, Text, DateTime, Integer, 
    ForeignKey, Enum as SQLEnum, Table, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.hybrid import hybrid_property
import enum

from .base import BaseModel, Base, get_json_type


class PermissionCategory(enum.Enum):
    """Permission categories for dropshipping operations"""
    # Core business operations
    PRODUCTS = "products"
    ORDERS = "orders"
    INVENTORY = "inventory"
    SOURCING = "sourcing"
    
    # Platform integrations
    MARKETPLACES = "marketplaces"
    WHOLESALERS = "wholesalers"
    
    # Financial operations
    PRICING = "pricing"
    PROFITS = "profits"
    PAYMENTS = "payments"
    
    # Analytics and reporting
    ANALYTICS = "analytics"
    REPORTS = "reports"
    
    # System administration
    USERS = "users"
    ROLES = "roles"
    SETTINGS = "settings"
    
    # AI and automation
    AI_SERVICES = "ai_services"
    AUTOMATION = "automation"


class PermissionAction(enum.Enum):
    """Actions that can be performed on resources"""
    # Basic CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    
    # Bulk operations
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"
    
    # Business-specific actions
    APPROVE = "approve"
    REJECT = "reject"
    PROCESS = "process"
    SYNC = "sync"
    EXPORT = "export"
    IMPORT = "import"
    
    # Administrative actions
    MANAGE = "manage"
    CONFIGURE = "configure"
    AUDIT = "audit"


class ResourceScope(enum.Enum):
    """Scope of resource access"""
    OWN = "own"           # Only resources owned by the user
    DEPARTMENT = "department"  # Resources within user's department
    ORGANIZATION = "organization"  # All organizational resources
    GLOBAL = "global"     # System-wide access


class PermissionCondition(enum.Enum):
    """Conditional permission types"""
    TIME_BASED = "time_based"        # Access during specific hours
    LOCATION_BASED = "location_based"  # Access from specific locations
    IP_BASED = "ip_based"           # Access from specific IPs
    VALUE_BASED = "value_based"     # Access based on monetary limits
    QUANTITY_BASED = "quantity_based"  # Access based on quantity limits


# Association table for many-to-many relationship between roles and permissions
role_permission_association = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('rbac_roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('rbac_permissions.id'), primary_key=True),
    Column('granted_at', DateTime, default=datetime.utcnow),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id'))
)


# Association table for user-specific permission overrides
user_permission_override = Table(
    'user_permission_overrides',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('rbac_permissions.id'), primary_key=True),
    Column('is_granted', Boolean, default=True),
    Column('granted_at', DateTime, default=datetime.utcnow),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id')),
    Column('expires_at', DateTime, nullable=True),
    Column('reason', Text, nullable=True)
)


class Permission(BaseModel):
    """Individual permission definition"""
    __tablename__ = "rbac_permissions"
    
    # Permission identification
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Permission categorization
    category = Column(SQLEnum(PermissionCategory), nullable=False, index=True)
    action = Column(SQLEnum(PermissionAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)  # e.g., "product", "order"
    
    # Access scope
    scope = Column(SQLEnum(ResourceScope), default=ResourceScope.OWN, nullable=False)
    
    # Permission metadata
    is_system_permission = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)  # For conflict resolution
    
    # Conditional access
    conditions = Column(get_json_type(), nullable=True)  # JSON conditions
    
    # Parent-child relationship for permission inheritance
    parent_id = Column(UUID(as_uuid=True), ForeignKey('rbac_permissions.id'), nullable=True)
    parent = relationship("Permission", remote_side="Permission.id", backref="children")
    
    # Relationships
    roles = relationship("Role", secondary=role_permission_association, back_populates="permissions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_permission_category_action', 'category', 'action'),
        Index('idx_permission_active_system', 'is_active', 'is_system_permission'),
    )
    
    def __repr__(self):
        return f"<Permission(name={self.name}, category={self.category.value})>"
    
    @hybrid_property
    def full_name(self):
        """Full permission name in format: category.action.resource"""
        if self.resource_type:
            return f"{self.category.value}.{self.action.value}.{self.resource_type}"
        return f"{self.category.value}.{self.action.value}"


class Role(BaseModel):
    """Role definition with permissions"""
    __tablename__ = "rbac_roles"
    
    # Role identification
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Role properties
    is_system_role = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    level = Column(Integer, default=0, nullable=False)  # Hierarchy level
    
    # Role inheritance
    parent_role_id = Column(UUID(as_uuid=True), ForeignKey('rbac_roles.id'), nullable=True)
    parent_role = relationship("Role", remote_side="Role.id", backref="child_roles")
    
    # Role settings
    max_users = Column(Integer, nullable=True)  # Maximum users with this role
    auto_grant_conditions = Column(get_json_type(), nullable=True)  # Auto-assignment rules
    
    # Relationships
    permissions = relationship("Permission", secondary=role_permission_association, back_populates="roles")
    users = relationship("User", back_populates="role")
    
    # Indexes
    __table_args__ = (
        Index('idx_role_active_system', 'is_active', 'is_system_role'),
        Index('idx_role_level', 'level'),
    )
    
    def __repr__(self):
        return f"<Role(name={self.name}, level={self.level})>"
    
    def get_all_permissions(self) -> List[Permission]:
        """Get all permissions including inherited from parent roles"""
        permissions = list(self.permissions)
        
        # Add parent role permissions
        if self.parent_role:
            permissions.extend(self.parent_role.get_all_permissions())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_permissions = []
        for perm in permissions:
            if perm.id not in seen:
                seen.add(perm.id)
                unique_permissions.append(perm)
        
        return unique_permissions


class UserPermissionAudit(BaseModel):
    """Audit trail for permission changes"""
    __tablename__ = "user_permission_audits"
    
    # Audit information
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey('rbac_permissions.id'), nullable=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey('rbac_roles.id'), nullable=True)
    
    # Action details
    action = Column(String(20), nullable=False)  # GRANT, REVOKE, MODIFY
    changed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    reason = Column(Text, nullable=True)
    
    # Change details
    old_value = Column(get_json_type(), nullable=True)
    new_value = Column(get_json_type(), nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    changed_by_user = relationship("User", foreign_keys=[changed_by])
    permission = relationship("Permission")
    role = relationship("Role")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_user_date', 'user_id', 'created_at'),
        Index('idx_audit_action_date', 'action', 'created_at'),
    )
    
    def __repr__(self):
        return f"<UserPermissionAudit(user_id={self.user_id}, action={self.action})>"


class AccessRequest(BaseModel):
    """Permission access requests"""
    __tablename__ = "access_requests"
    
    # Request details
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey('rbac_permissions.id'), nullable=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey('rbac_roles.id'), nullable=True)
    
    # Request information
    request_type = Column(String(20), nullable=False)  # PERMISSION, ROLE
    justification = Column(Text, nullable=False)
    requested_duration = Column(Integer, nullable=True)  # Duration in days
    
    # Request status
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comments = Column(Text, nullable=True)
    
    # Auto-approval settings
    auto_approved = Column(Boolean, default=False, nullable=False)
    approval_expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    permission = relationship("Permission")
    role = relationship("Role")
    
    # Indexes
    __table_args__ = (
        Index('idx_access_request_status', 'status', 'created_at'),
        Index('idx_access_request_user', 'user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<AccessRequest(user_id={self.user_id}, status={self.status})>"


class PermissionDelegation(BaseModel):
    """Permission delegation system"""
    __tablename__ = "permission_delegations"
    
    # Delegation parties
    delegator_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    delegate_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey('rbac_permissions.id'), nullable=False)
    
    # Delegation terms
    can_redelegate = Column(Boolean, default=False, nullable=False)
    max_delegation_depth = Column(Integer, default=1, nullable=False)
    current_depth = Column(Integer, default=1, nullable=False)
    
    # Time constraints
    valid_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    
    # Conditional constraints
    conditions = Column(get_json_type(), nullable=True)
    usage_limit = Column(Integer, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Relationships
    delegator = relationship("User", foreign_keys=[delegator_id])
    delegate = relationship("User", foreign_keys=[delegate_id])
    permission = relationship("Permission")
    revoker = relationship("User", foreign_keys=[revoked_by])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('delegator_id', 'delegate_id', 'permission_id', 
                        name='uq_delegation_unique'),
        Index('idx_delegation_active', 'is_active', 'valid_until'),
        Index('idx_delegation_delegate', 'delegate_id', 'is_active'),
    )
    
    def is_valid(self) -> bool:
        """Check if delegation is currently valid"""
        now = datetime.utcnow()
        return (
            self.is_active and
            self.valid_from <= now and
            (self.valid_until is None or self.valid_until > now) and
            (self.usage_limit is None or self.usage_count < self.usage_limit)
        )
    
    def __repr__(self):
        return f"<PermissionDelegation(delegator_id={self.delegator_id}, delegate_id={self.delegate_id})>"


# Create default dropshipping permissions
DROPSHIPPING_PERMISSIONS = [
    # Product Management
    ("products.create.own", "Create Own Products", PermissionCategory.PRODUCTS, PermissionAction.CREATE, "product", ResourceScope.OWN),
    ("products.read.own", "View Own Products", PermissionCategory.PRODUCTS, PermissionAction.READ, "product", ResourceScope.OWN),
    ("products.update.own", "Update Own Products", PermissionCategory.PRODUCTS, PermissionAction.UPDATE, "product", ResourceScope.OWN),
    ("products.delete.own", "Delete Own Products", PermissionCategory.PRODUCTS, PermissionAction.DELETE, "product", ResourceScope.OWN),
    ("products.read.all", "View All Products", PermissionCategory.PRODUCTS, PermissionAction.READ, "product", ResourceScope.ORGANIZATION),
    ("products.manage.all", "Manage All Products", PermissionCategory.PRODUCTS, PermissionAction.MANAGE, "product", ResourceScope.ORGANIZATION),
    ("products.bulk_update", "Bulk Update Products", PermissionCategory.PRODUCTS, PermissionAction.BULK_UPDATE, "product", ResourceScope.ORGANIZATION),
    ("products.sync", "Sync Products", PermissionCategory.PRODUCTS, PermissionAction.SYNC, "product", ResourceScope.ORGANIZATION),
    
    # Order Management  
    ("orders.create", "Create Orders", PermissionCategory.ORDERS, PermissionAction.CREATE, "order", ResourceScope.OWN),
    ("orders.read.own", "View Own Orders", PermissionCategory.ORDERS, PermissionAction.READ, "order", ResourceScope.OWN),
    ("orders.read.all", "View All Orders", PermissionCategory.ORDERS, PermissionAction.READ, "order", ResourceScope.ORGANIZATION),
    ("orders.process", "Process Orders", PermissionCategory.ORDERS, PermissionAction.PROCESS, "order", ResourceScope.ORGANIZATION),
    ("orders.approve", "Approve Orders", PermissionCategory.ORDERS, PermissionAction.APPROVE, "order", ResourceScope.ORGANIZATION),
    ("orders.cancel", "Cancel Orders", PermissionCategory.ORDERS, PermissionAction.DELETE, "order", ResourceScope.ORGANIZATION),
    
    # Inventory Management
    ("inventory.read", "View Inventory", PermissionCategory.INVENTORY, PermissionAction.READ, "inventory", ResourceScope.ORGANIZATION),
    ("inventory.update", "Update Inventory", PermissionCategory.INVENTORY, PermissionAction.UPDATE, "inventory", ResourceScope.ORGANIZATION),
    ("inventory.sync", "Sync Inventory", PermissionCategory.INVENTORY, PermissionAction.SYNC, "inventory", ResourceScope.ORGANIZATION),
    
    # Sourcing Operations
    ("sourcing.read", "View Sourcing Data", PermissionCategory.SOURCING, PermissionAction.READ, "sourcing", ResourceScope.ORGANIZATION),
    ("sourcing.create", "Create Sourcing Records", PermissionCategory.SOURCING, PermissionAction.CREATE, "sourcing", ResourceScope.ORGANIZATION),
    ("sourcing.manage", "Manage Sourcing", PermissionCategory.SOURCING, PermissionAction.MANAGE, "sourcing", ResourceScope.ORGANIZATION),
    
    # Marketplace Integration
    ("marketplaces.read", "View Marketplace Data", PermissionCategory.MARKETPLACES, PermissionAction.READ, "marketplace", ResourceScope.ORGANIZATION),
    ("marketplaces.configure", "Configure Marketplaces", PermissionCategory.MARKETPLACES, PermissionAction.CONFIGURE, "marketplace", ResourceScope.ORGANIZATION),
    ("marketplaces.sync", "Sync Marketplace Data", PermissionCategory.MARKETPLACES, PermissionAction.SYNC, "marketplace", ResourceScope.ORGANIZATION),
    
    # Wholesaler Management
    ("wholesalers.read", "View Wholesaler Data", PermissionCategory.WHOLESALERS, PermissionAction.READ, "wholesaler", ResourceScope.ORGANIZATION),
    ("wholesalers.configure", "Configure Wholesalers", PermissionCategory.WHOLESALERS, PermissionAction.CONFIGURE, "wholesaler", ResourceScope.ORGANIZATION),
    ("wholesalers.sync", "Sync Wholesaler Data", PermissionCategory.WHOLESALERS, PermissionAction.SYNC, "wholesaler", ResourceScope.ORGANIZATION),
    
    # Pricing Management
    ("pricing.read", "View Pricing Data", PermissionCategory.PRICING, PermissionAction.READ, "pricing", ResourceScope.ORGANIZATION),
    ("pricing.update", "Update Pricing", PermissionCategory.PRICING, PermissionAction.UPDATE, "pricing", ResourceScope.ORGANIZATION),
    ("pricing.manage", "Manage Pricing Strategy", PermissionCategory.PRICING, PermissionAction.MANAGE, "pricing", ResourceScope.ORGANIZATION),
    
    # Financial Operations
    ("profits.read", "View Profit Data", PermissionCategory.PROFITS, PermissionAction.READ, "profit", ResourceScope.ORGANIZATION),
    ("payments.read", "View Payment Data", PermissionCategory.PAYMENTS, PermissionAction.READ, "payment", ResourceScope.ORGANIZATION),
    ("payments.process", "Process Payments", PermissionCategory.PAYMENTS, PermissionAction.PROCESS, "payment", ResourceScope.ORGANIZATION),
    
    # Analytics and Reporting
    ("analytics.read", "View Analytics", PermissionCategory.ANALYTICS, PermissionAction.READ, "analytics", ResourceScope.ORGANIZATION),
    ("reports.read", "View Reports", PermissionCategory.REPORTS, PermissionAction.READ, "report", ResourceScope.ORGANIZATION),
    ("reports.create", "Create Reports", PermissionCategory.REPORTS, PermissionAction.CREATE, "report", ResourceScope.ORGANIZATION),
    ("reports.export", "Export Reports", PermissionCategory.REPORTS, PermissionAction.EXPORT, "report", ResourceScope.ORGANIZATION),
    
    # User Management
    ("users.read", "View Users", PermissionCategory.USERS, PermissionAction.READ, "user", ResourceScope.ORGANIZATION),
    ("users.create", "Create Users", PermissionCategory.USERS, PermissionAction.CREATE, "user", ResourceScope.ORGANIZATION),
    ("users.update", "Update Users", PermissionCategory.USERS, PermissionAction.UPDATE, "user", ResourceScope.ORGANIZATION),
    ("users.delete", "Delete Users", PermissionCategory.USERS, PermissionAction.DELETE, "user", ResourceScope.ORGANIZATION),
    
    # Role Management
    ("roles.read", "View Roles", PermissionCategory.ROLES, PermissionAction.READ, "role", ResourceScope.ORGANIZATION),
    ("roles.create", "Create Roles", PermissionCategory.ROLES, PermissionAction.CREATE, "role", ResourceScope.ORGANIZATION),
    ("roles.update", "Update Roles", PermissionCategory.ROLES, PermissionAction.UPDATE, "role", ResourceScope.ORGANIZATION),
    ("roles.delete", "Delete Roles", PermissionCategory.ROLES, PermissionAction.DELETE, "role", ResourceScope.ORGANIZATION),
    
    # System Settings
    ("settings.read", "View Settings", PermissionCategory.SETTINGS, PermissionAction.READ, "setting", ResourceScope.ORGANIZATION),
    ("settings.update", "Update Settings", PermissionCategory.SETTINGS, PermissionAction.UPDATE, "setting", ResourceScope.ORGANIZATION),
    
    # AI Services
    ("ai_services.read", "View AI Services", PermissionCategory.AI_SERVICES, PermissionAction.READ, "ai_service", ResourceScope.ORGANIZATION),
    ("ai_services.use", "Use AI Services", PermissionCategory.AI_SERVICES, PermissionAction.PROCESS, "ai_service", ResourceScope.ORGANIZATION),
    ("ai_services.configure", "Configure AI Services", PermissionCategory.AI_SERVICES, PermissionAction.CONFIGURE, "ai_service", ResourceScope.ORGANIZATION),
    
    # Automation
    ("automation.read", "View Automation", PermissionCategory.AUTOMATION, PermissionAction.READ, "automation", ResourceScope.ORGANIZATION),
    ("automation.configure", "Configure Automation", PermissionCategory.AUTOMATION, PermissionAction.CONFIGURE, "automation", ResourceScope.ORGANIZATION),
    ("automation.manage", "Manage Automation", PermissionCategory.AUTOMATION, PermissionAction.MANAGE, "automation", ResourceScope.ORGANIZATION),
]

# Default role definitions with their permissions
DROPSHIPPING_ROLES = {
    "super_admin": {
        "display_name": "Super Administrator",
        "description": "Full system access with all permissions",
        "level": 100,
        "permissions": ["*"]  # All permissions
    },
    "admin": {
        "display_name": "Administrator", 
        "description": "Administrative access to most system functions",
        "level": 80,
        "permissions": [
            "products.manage.all", "orders.read.all", "orders.process", "orders.approve",
            "inventory.read", "inventory.update", "inventory.sync",
            "sourcing.read", "sourcing.create", "sourcing.manage",
            "marketplaces.read", "marketplaces.configure", "marketplaces.sync",
            "wholesalers.read", "wholesalers.configure", "wholesalers.sync",
            "pricing.read", "pricing.update", "pricing.manage",
            "profits.read", "payments.read", "payments.process",
            "analytics.read", "reports.read", "reports.create", "reports.export",
            "users.read", "users.create", "users.update",
            "roles.read", "settings.read", "settings.update",
            "ai_services.read", "ai_services.use", "ai_services.configure",
            "automation.read", "automation.configure", "automation.manage"
        ]
    },
    "manager": {
        "display_name": "Manager",
        "description": "Management access to business operations",
        "level": 60,
        "permissions": [
            "products.read.all", "products.update.own", "products.create.own",
            "orders.read.all", "orders.process", "orders.approve",
            "inventory.read", "inventory.update",
            "sourcing.read", "sourcing.create",
            "marketplaces.read", "marketplaces.sync",
            "wholesalers.read", "wholesalers.sync",
            "pricing.read", "pricing.update",
            "profits.read", "payments.read",
            "analytics.read", "reports.read", "reports.create",
            "users.read", "roles.read",
            "ai_services.read", "ai_services.use",
            "automation.read", "automation.configure"
        ]
    },
    "operator": {
        "display_name": "Operator",
        "description": "Operational access for daily tasks",
        "level": 40,
        "permissions": [
            "products.read.own", "products.update.own", "products.create.own",
            "orders.read.own", "orders.create",
            "inventory.read", "sourcing.read",
            "marketplaces.read", "wholesalers.read",
            "pricing.read", "profits.read",
            "analytics.read", "reports.read",
            "ai_services.read", "ai_services.use",
            "automation.read"
        ]
    },
    "viewer": {
        "display_name": "Viewer",
        "description": "Read-only access to business data",
        "level": 20,
        "permissions": [
            "products.read.own", "orders.read.own",
            "inventory.read", "sourcing.read",
            "marketplaces.read", "wholesalers.read",
            "pricing.read", "profits.read",
            "analytics.read", "reports.read",
            "ai_services.read"
        ]
    }
}