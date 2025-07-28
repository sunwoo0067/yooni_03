"""Add security audit and token blacklist tables

Revision ID: 007_add_security_audit_tables
Revises: 
Create Date: 2025-01-28 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '007_add_security_audit_tables'
down_revision = '006_add_benchmark_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add security audit and token management tables"""
    
    # Create security_audit_logs table
    op.create_table(
        'security_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    # Create indexes for security_audit_logs
    op.create_index('idx_security_audit_user_action', 'security_audit_logs', ['user_id', 'action'])
    op.create_index('idx_security_audit_time_action', 'security_audit_logs', ['created_at', 'action'])
    op.create_index('idx_security_audit_ip_time', 'security_audit_logs', ['ip_address', 'created_at'])
    op.create_index('idx_security_audit_success_time', 'security_audit_logs', ['success', 'created_at'])
    op.create_index('ix_security_audit_logs_user_id', 'security_audit_logs', ['user_id'])
    op.create_index('ix_security_audit_logs_action', 'security_audit_logs', ['action'])
    op.create_index('ix_security_audit_logs_ip_address', 'security_audit_logs', ['ip_address'])
    op.create_index('ix_security_audit_logs_success', 'security_audit_logs', ['success'])
    op.create_index('ix_security_audit_logs_session_id', 'security_audit_logs', ['session_id'])
    op.create_index('ix_security_audit_logs_created_at', 'security_audit_logs', ['created_at'])
    op.create_index('ix_security_audit_logs_is_deleted', 'security_audit_logs', ['is_deleted'])
    
    # Create token_blacklist table
    op.create_table(
        'token_blacklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('jti', sa.String(255), unique=True, nullable=False),
        sa.Column('token_type', sa.String(20), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=False),
        sa.Column('revoke_reason', sa.String(100), nullable=True),
        sa.Column('revoke_ip', sa.String(45), nullable=True),
        sa.Column('revoke_user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    # Create indexes for token_blacklist
    op.create_index('idx_token_blacklist_expires', 'token_blacklist', ['expires_at'])
    op.create_index('idx_token_blacklist_user_type', 'token_blacklist', ['user_id', 'token_type'])
    op.create_index('idx_token_blacklist_revoked', 'token_blacklist', ['revoked_at'])
    op.create_index('ix_token_blacklist_jti', 'token_blacklist', ['jti'])
    op.create_index('ix_token_blacklist_token_type', 'token_blacklist', ['token_type'])
    op.create_index('ix_token_blacklist_user_id', 'token_blacklist', ['user_id'])
    op.create_index('ix_token_blacklist_created_at', 'token_blacklist', ['created_at'])
    op.create_index('ix_token_blacklist_is_deleted', 'token_blacklist', ['is_deleted'])
    
    # Create login_attempts table
    op.create_table(
        'login_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(100), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    # Create indexes for login_attempts
    op.create_index('idx_login_attempts_email_ip', 'login_attempts', ['email', 'ip_address'])
    op.create_index('idx_login_attempts_ip_time', 'login_attempts', ['ip_address', 'created_at'])
    op.create_index('idx_login_attempts_email_time', 'login_attempts', ['email', 'created_at'])
    op.create_index('idx_login_attempts_success_time', 'login_attempts', ['success', 'created_at'])
    op.create_index('ix_login_attempts_email', 'login_attempts', ['email'])
    op.create_index('ix_login_attempts_ip_address', 'login_attempts', ['ip_address'])
    op.create_index('ix_login_attempts_success', 'login_attempts', ['success'])
    op.create_index('ix_login_attempts_user_id', 'login_attempts', ['user_id'])
    op.create_index('ix_login_attempts_created_at', 'login_attempts', ['created_at'])
    op.create_index('ix_login_attempts_is_deleted', 'login_attempts', ['is_deleted'])
    
    # Create password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('token', sa.String(255), unique=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('is_used', sa.Boolean(), default=False, nullable=False),
        sa.Column('request_ip', sa.String(45), nullable=True),
        sa.Column('request_user_agent', sa.Text(), nullable=True),
        sa.Column('used_ip', sa.String(45), nullable=True),
        sa.Column('used_user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    # Create indexes for password_reset_tokens
    op.create_index('idx_password_reset_user_expires', 'password_reset_tokens', ['user_id', 'expires_at'])
    op.create_index('idx_password_reset_expires_used', 'password_reset_tokens', ['expires_at', 'is_used'])
    op.create_index('ix_password_reset_tokens_token', 'password_reset_tokens', ['token'])
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])
    op.create_index('ix_password_reset_tokens_is_used', 'password_reset_tokens', ['is_used'])
    op.create_index('ix_password_reset_tokens_created_at', 'password_reset_tokens', ['created_at'])
    op.create_index('ix_password_reset_tokens_is_deleted', 'password_reset_tokens', ['is_deleted'])


def downgrade():
    """Remove security audit and token management tables"""
    
    # Drop password_reset_tokens table and indexes
    op.drop_index('ix_password_reset_tokens_is_deleted', 'password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_created_at', 'password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_is_used', 'password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', 'password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token', 'password_reset_tokens')
    op.drop_index('idx_password_reset_expires_used', 'password_reset_tokens')
    op.drop_index('idx_password_reset_user_expires', 'password_reset_tokens')
    op.drop_table('password_reset_tokens')
    
    # Drop login_attempts table and indexes
    op.drop_index('ix_login_attempts_is_deleted', 'login_attempts')
    op.drop_index('ix_login_attempts_created_at', 'login_attempts')
    op.drop_index('ix_login_attempts_user_id', 'login_attempts')
    op.drop_index('ix_login_attempts_success', 'login_attempts')
    op.drop_index('ix_login_attempts_ip_address', 'login_attempts')
    op.drop_index('ix_login_attempts_email', 'login_attempts')
    op.drop_index('idx_login_attempts_success_time', 'login_attempts')
    op.drop_index('idx_login_attempts_email_time', 'login_attempts')
    op.drop_index('idx_login_attempts_ip_time', 'login_attempts')
    op.drop_index('idx_login_attempts_email_ip', 'login_attempts')
    op.drop_table('login_attempts')
    
    # Drop token_blacklist table and indexes
    op.drop_index('ix_token_blacklist_is_deleted', 'token_blacklist')
    op.drop_index('ix_token_blacklist_created_at', 'token_blacklist')
    op.drop_index('ix_token_blacklist_user_id', 'token_blacklist')
    op.drop_index('ix_token_blacklist_token_type', 'token_blacklist')
    op.drop_index('ix_token_blacklist_jti', 'token_blacklist')
    op.drop_index('idx_token_blacklist_revoked', 'token_blacklist')
    op.drop_index('idx_token_blacklist_user_type', 'token_blacklist')
    op.drop_index('idx_token_blacklist_expires', 'token_blacklist')
    op.drop_table('token_blacklist')
    
    # Drop security_audit_logs table and indexes
    op.drop_index('ix_security_audit_logs_is_deleted', 'security_audit_logs')
    op.drop_index('ix_security_audit_logs_created_at', 'security_audit_logs')
    op.drop_index('ix_security_audit_logs_session_id', 'security_audit_logs')
    op.drop_index('ix_security_audit_logs_success', 'security_audit_logs')
    op.drop_index('ix_security_audit_logs_ip_address', 'security_audit_logs')
    op.drop_index('ix_security_audit_logs_action', 'security_audit_logs')
    op.drop_index('ix_security_audit_logs_user_id', 'security_audit_logs')
    op.drop_index('idx_security_audit_success_time', 'security_audit_logs')
    op.drop_index('idx_security_audit_ip_time', 'security_audit_logs')
    op.drop_index('idx_security_audit_time_action', 'security_audit_logs')
    op.drop_index('idx_security_audit_user_action', 'security_audit_logs')
    op.drop_table('security_audit_logs')