"""Add comprehensive RBAC system for dropshipping platform

Revision ID: add_rbac_system
Revises: 
Create Date: 2025-07-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy import text

# revision identifiers
revision = 'add_rbac_system'
down_revision = None  # Set this to your latest migration
branch_labels = None
depends_on = None

# Check if we're using PostgreSQL or SQLite
def get_json_type():
    """Get appropriate JSON type for the database"""
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        return postgresql.JSONB
    else:
        return sa.Text  # SQLite fallback


def upgrade() -> None:
    """Create RBAC tables and relationships"""
    
    # Create RBAC permissions table
    op.create_table('rbac_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum('PRODUCTS', 'ORDERS', 'INVENTORY', 'SOURCING', 'MARKETPLACES', 'WHOLESALERS', 'PRICING', 'PROFITS', 'PAYMENTS', 'ANALYTICS', 'REPORTS', 'USERS', 'ROLES', 'SETTINGS', 'AI_SERVICES', 'AUTOMATION', name='permissioncategory'), nullable=False),
        sa.Column('action', sa.Enum('CREATE', 'READ', 'UPDATE', 'DELETE', 'BULK_CREATE', 'BULK_UPDATE', 'BULK_DELETE', 'APPROVE', 'REJECT', 'PROCESS', 'SYNC', 'EXPORT', 'IMPORT', 'MANAGE', 'CONFIGURE', 'AUDIT', name='permissionaction'), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('scope', sa.Enum('OWN', 'DEPARTMENT', 'ORGANIZATION', 'GLOBAL', name='resourcescope'), nullable=False),
        sa.Column('is_system_permission', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('conditions', get_json_type(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['rbac_permissions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for permissions
    op.create_index('idx_permission_category_action', 'rbac_permissions', ['category', 'action'])
    op.create_index('idx_permission_active_system', 'rbac_permissions', ['is_active', 'is_system_permission'])
    op.create_index(op.f('ix_rbac_permissions_name'), 'rbac_permissions', ['name'], unique=True)

    # Create RBAC roles table
    op.create_table('rbac_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('parent_role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('auto_grant_conditions', get_json_type(), nullable=True),
        sa.ForeignKeyConstraint(['parent_role_id'], ['rbac_roles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for roles
    op.create_index('idx_role_active_system', 'rbac_roles', ['is_active', 'is_system_role'])
    op.create_index('idx_role_level', 'rbac_roles', ['level'])
    op.create_index(op.f('ix_rbac_roles_name'), 'rbac_roles', ['name'], unique=True)

    # Create role-permission association table
    op.create_table('role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['rbac_roles.id'], ),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Create user permission overrides table
    op.create_table('user_permission_overrides',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_granted', sa.Boolean(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'permission_id')
    )

    # Create user permission audit table
    op.create_table('user_permission_audits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('old_value', get_json_type(), nullable=True),
        sa.Column('new_value', get_json_type(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['rbac_roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for audit logs
    op.create_index('idx_audit_user_date', 'user_permission_audits', ['user_id', 'created_at'])
    op.create_index('idx_audit_action_date', 'user_permission_audits', ['action', 'created_at'])

    # Create access requests table
    op.create_table('access_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('request_type', sa.String(length=20), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('requested_duration', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_comments', sa.Text(), nullable=True),
        sa.Column('auto_approved', sa.Boolean(), nullable=False),
        sa.Column('approval_expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['rbac_roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for access requests
    op.create_index('idx_access_request_status', 'access_requests', ['status', 'created_at'])
    op.create_index('idx_access_request_user', 'access_requests', ['user_id', 'status'])

    # Create permission delegations table
    op.create_table('permission_delegations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('delegator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delegate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('can_redelegate', sa.Boolean(), nullable=False),
        sa.Column('max_delegation_depth', sa.Integer(), nullable=False),
        sa.Column('current_depth', sa.Integer(), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('conditions', get_json_type(), nullable=True),
        sa.Column('usage_limit', sa.Integer(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['delegate_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['delegator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes and constraints for delegations
    op.create_index('idx_delegation_active', 'permission_delegations', ['is_active', 'valid_until'])
    op.create_index('idx_delegation_delegate', 'permission_delegations', ['delegate_id', 'is_active'])
    
    # Create unique constraint for delegation uniqueness
    op.create_unique_constraint('uq_delegation_unique', 'permission_delegations', ['delegator_id', 'delegate_id', 'permission_id'])


def downgrade() -> None:
    """Remove RBAC tables"""
    
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('permission_delegations')
    op.drop_table('access_requests')
    op.drop_table('user_permission_audits')
    op.drop_table('user_permission_overrides')
    op.drop_table('role_permissions')
    op.drop_table('rbac_roles')
    op.drop_table('rbac_permissions')
    
    # Drop custom enums if using PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS permissioncategory')
        op.execute('DROP TYPE IF EXISTS permissionaction')
        op.execute('DROP TYPE IF EXISTS resourcescope')
        op.execute('DROP TYPE IF EXISTS permissioncondition')