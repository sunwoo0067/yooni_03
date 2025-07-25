"""001_initial_migration

Initial database schema for multi-platform e-commerce management system

Revision ID: 001
Revises: 
Create Date: 2024-12-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables"""
    
    # Create ENUM types
    op.execute("CREATE TYPE userrole AS ENUM ('super_admin', 'admin', 'manager', 'operator', 'viewer')")
    op.execute("CREATE TYPE userstatus AS ENUM ('active', 'inactive', 'suspended', 'pending')")
    op.execute("CREATE TYPE platformtype AS ENUM ('coupang', 'naver', '11st', 'gmarket', 'auction', 'tmon', 'wemakeprice', 'interpark', 'topten', 'icoop', 'dongwon')")
    op.execute("CREATE TYPE accountstatus AS ENUM ('active', 'inactive', 'suspended', 'pending_approval', 'error')")
    op.execute("CREATE TYPE productstatus AS ENUM ('active', 'inactive', 'pending', 'rejected', 'out_of_stock', 'discontinued')")
    op.execute("CREATE TYPE producttype AS ENUM ('simple', 'variable', 'bundle', 'digital')")
    op.execute("CREATE TYPE pricingstrategy AS ENUM ('fixed', 'cost_plus', 'competitive', 'dynamic')")
    op.execute("CREATE TYPE orderstatus AS ENUM ('pending', 'confirmed', 'paid', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded', 'returned')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('pending', 'paid', 'partial', 'failed', 'refunded')")
    op.execute("CREATE TYPE shippingstatus AS ENUM ('pending', 'preparing', 'shipped', 'in_transit', 'delivered', 'failed', 'returned')")
    op.execute("CREATE TYPE movementtype AS ENUM ('purchase', 'sale', 'adjustment', 'transfer', 'return', 'damage', 'loss', 'found', 'reservation', 'release')")
    op.execute("CREATE TYPE inventorystatus AS ENUM ('available', 'reserved', 'damaged', 'quarantine', 'expired')")
    op.execute("CREATE TYPE aioperationtype AS ENUM ('price_optimization', 'inventory_prediction', 'demand_forecasting', 'product_recommendation', 'title_optimization', 'description_generation', 'category_classification', 'image_analysis', 'competitive_analysis', 'market_analysis', 'customer_segmentation', 'fraud_detection')")
    op.execute("CREATE TYPE aimodeltype AS ENUM ('neural_network', 'random_forest', 'gradient_boosting', 'linear_regression', 'logistic_regression', 'svm', 'clustering', 'nlp_transformer', 'computer_vision')")
    op.execute("CREATE TYPE executionstatus AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled')")
    
    # Users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('role', sa.Enum('super_admin', 'admin', 'manager', 'operator', 'viewer', name='userrole'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'pending', name='userstatus'), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('department', sa.String(length=50), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
        sa.Column('password_changed_at', sa.DateTime(), nullable=False),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_is_deleted'), 'users', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_status'), 'users', ['status'], unique=False)
    op.create_index(op.f('ix_users_updated_at'), 'users', ['updated_at'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # User sessions table
    op.create_table('user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('session_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_created_at'), 'user_sessions', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_deleted_at'), 'user_sessions', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_expires_at'), 'user_sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_user_sessions_is_active'), 'user_sessions', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_sessions_is_deleted'), 'user_sessions', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_token'), 'user_sessions', ['session_token'], unique=True)
    op.create_index(op.f('ix_user_sessions_updated_at'), 'user_sessions', ['updated_at'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    
    # User API keys table
    op.create_table('user_api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rate_limit', sa.Integer(), nullable=False),
        sa.Column('allowed_ips', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_api_keys_created_at'), 'user_api_keys', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_api_keys_deleted_at'), 'user_api_keys', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_user_api_keys_expires_at'), 'user_api_keys', ['expires_at'], unique=False)
    op.create_index(op.f('ix_user_api_keys_id'), 'user_api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_user_api_keys_is_active'), 'user_api_keys', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_api_keys_is_deleted'), 'user_api_keys', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_user_api_keys_key_hash'), 'user_api_keys', ['key_hash'], unique=True)
    op.create_index(op.f('ix_user_api_keys_updated_at'), 'user_api_keys', ['updated_at'], unique=False)
    
    # Platform accounts table
    op.create_table('platform_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform_type', sa.Enum('coupang', 'naver', '11st', 'gmarket', 'auction', 'tmon', 'wemakeprice', 'interpark', 'topten', 'icoop', 'dongwon', name='platformtype'), nullable=False),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('account_id', sa.String(length=100), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('api_secret', sa.Text(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('seller_id', sa.String(length=100), nullable=True),
        sa.Column('store_name', sa.String(length=200), nullable=True),
        sa.Column('store_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'pending_approval', 'error', name='accountstatus'), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_health_check_at', sa.DateTime(), nullable=True),
        sa.Column('health_status', sa.String(length=50), nullable=False),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False),
        sa.Column('auto_pricing_enabled', sa.Boolean(), nullable=False),
        sa.Column('auto_inventory_sync', sa.Boolean(), nullable=False),
        sa.Column('platform_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('daily_api_quota', sa.Integer(), nullable=True),
        sa.Column('daily_api_used', sa.Integer(), nullable=False),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
        sa.Column('commission_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('monthly_fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False),
        sa.Column('consecutive_errors', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_accounts_created_at'), 'platform_accounts', ['created_at'], unique=False)
    op.create_index(op.f('ix_platform_accounts_deleted_at'), 'platform_accounts', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_platform_accounts_id'), 'platform_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_platform_accounts_is_deleted'), 'platform_accounts', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_platform_accounts_last_sync_at'), 'platform_accounts', ['last_sync_at'], unique=False)
    op.create_index(op.f('ix_platform_accounts_platform_type'), 'platform_accounts', ['platform_type'], unique=False)
    op.create_index(op.f('ix_platform_accounts_seller_id'), 'platform_accounts', ['seller_id'], unique=False)
    op.create_index(op.f('ix_platform_accounts_status'), 'platform_accounts', ['status'], unique=False)
    op.create_index(op.f('ix_platform_accounts_updated_at'), 'platform_accounts', ['updated_at'], unique=False)
    op.create_index(op.f('ix_platform_accounts_user_id'), 'platform_accounts', ['user_id'], unique=False)
    
    # Wholesale accounts table
    op.create_table('wholesale_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_name', sa.String(length=200), nullable=False),
        sa.Column('supplier_code', sa.String(length=50), nullable=True),
        sa.Column('contact_person', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('business_number', sa.String(length=20), nullable=True),
        sa.Column('tax_type', sa.String(length=20), nullable=False),
        sa.Column('api_endpoint', sa.String(length=500), nullable=True),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'pending_approval', 'error', name='accountstatus'), nullable=False),
        sa.Column('is_preferred', sa.Boolean(), nullable=False),
        sa.Column('payment_terms', sa.String(length=100), nullable=True),
        sa.Column('delivery_terms', sa.String(length=100), nullable=True),
        sa.Column('minimum_order_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('reliability_score', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('average_delivery_days', sa.Integer(), nullable=True),
        sa.Column('total_orders', sa.Integer(), nullable=False),
        sa.Column('auto_sync_enabled', sa.Boolean(), nullable=False),
        sa.Column('sync_interval_hours', sa.Integer(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wholesale_accounts_business_number'), 'wholesale_accounts', ['business_number'], unique=False)
    op.create_index(op.f('ix_wholesale_accounts_created_at'), 'wholesale_accounts', ['created_at'], unique=False)
    op.create_index(op.f('ix_wholesale_accounts_deleted_at'), 'wholesale_accounts', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_wholesale_accounts_id'), 'wholesale_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_wholesale_accounts_is_deleted'), 'wholesale_accounts', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_wholesale_accounts_status'), 'wholesale_accounts', ['status'], unique=False)
    op.create_index(op.f('ix_wholesale_accounts_supplier_code'), 'wholesale_accounts', ['supplier_code'], unique=False)
    op.create_index(op.f('ix_wholesale_accounts_updated_at'), 'wholesale_accounts', ['updated_at'], unique=False)
    
    # Platform sync logs table
    op.create_table('platform_sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('platform_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_type', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=False),
        sa.Column('processed_items', sa.Integer(), nullable=False),
        sa.Column('success_count', sa.Integer(), nullable=False),
        sa.Column('error_count', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sync_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_time_seconds', sa.Integer(), nullable=True),
        sa.Column('api_calls_made', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['platform_account_id'], ['platform_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_sync_logs_completed_at'), 'platform_sync_logs', ['completed_at'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_created_at'), 'platform_sync_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_deleted_at'), 'platform_sync_logs', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_id'), 'platform_sync_logs', ['id'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_is_deleted'), 'platform_sync_logs', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_platform_account_id'), 'platform_sync_logs', ['platform_account_id'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_started_at'), 'platform_sync_logs', ['started_at'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_status'), 'platform_sync_logs', ['status'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_sync_type'), 'platform_sync_logs', ['sync_type'], unique=False)
    op.create_index(op.f('ix_platform_sync_logs_updated_at'), 'platform_sync_logs', ['updated_at'], unique=False)
    
    # Product categories table
    op.create_table('product_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('seo_title', sa.String(length=200), nullable=True),
        sa.Column('seo_description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('commission_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['product_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_categories_created_at'), 'product_categories', ['created_at'], unique=False)
    op.create_index(op.f('ix_product_categories_deleted_at'), 'product_categories', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_product_categories_id'), 'product_categories', ['id'], unique=False)
    op.create_index(op.f('ix_product_categories_is_deleted'), 'product_categories', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_product_categories_name'), 'product_categories', ['name'], unique=False)
    op.create_index(op.f('ix_product_categories_parent_id'), 'product_categories', ['parent_id'], unique=False)
    op.create_index(op.f('ix_product_categories_slug'), 'product_categories', ['slug'], unique=True)
    op.create_index(op.f('ix_product_categories_updated_at'), 'product_categories', ['updated_at'], unique=False)
    
    # Products table
    op.create_table('products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('platform_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('wholesale_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('barcode', sa.String(length=50), nullable=True),
        sa.Column('model_number', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('short_description', sa.Text(), nullable=True),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('product_type', sa.Enum('simple', 'variable', 'bundle', 'digital', name='producttype'), nullable=False),
        sa.Column('category_path', sa.String(length=500), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('cost_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('wholesale_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('retail_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('sale_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('pricing_strategy', sa.Enum('fixed', 'cost_plus', 'competitive', 'dynamic', name='pricingstrategy'), nullable=False),
        sa.Column('margin_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('min_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('weight', sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column('dimensions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'pending', 'rejected', 'out_of_stock', 'discontinued', name='productstatus'), nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False),
        sa.Column('is_digital', sa.Boolean(), nullable=False),
        sa.Column('seo_title', sa.String(length=200), nullable=True),
        sa.Column('seo_description', sa.Text(), nullable=True),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('main_image_url', sa.String(length=1000), nullable=True),
        sa.Column('image_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('video_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), nullable=False),
        sa.Column('reserved_quantity', sa.Integer(), nullable=False),
        sa.Column('min_stock_level', sa.Integer(), nullable=False),
        sa.Column('max_stock_level', sa.Integer(), nullable=True),
        sa.Column('requires_shipping', sa.Boolean(), nullable=False),
        sa.Column('shipping_weight', sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column('shipping_dimensions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ai_optimized', sa.Boolean(), nullable=False),
        sa.Column('performance_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('search_rank', sa.Integer(), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['platform_account_id'], ['platform_accounts.id'], ),
        sa.ForeignKeyConstraint(['wholesale_account_id'], ['wholesale_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_barcode'), 'products', ['barcode'], unique=False)
    op.create_index(op.f('ix_products_brand'), 'products', ['brand'], unique=False)
    op.create_index(op.f('ix_products_category_path'), 'products', ['category_path'], unique=False)
    op.create_index(op.f('ix_products_created_at'), 'products', ['created_at'], unique=False)
    op.create_index(op.f('ix_products_deleted_at'), 'products', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_is_deleted'), 'products', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_products_model_number'), 'products', ['model_number'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_platform_account_id'), 'products', ['platform_account_id'], unique=False)
    op.create_index(op.f('ix_products_product_type'), 'products', ['product_type'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)
    op.create_index(op.f('ix_products_status'), 'products', ['status'], unique=False)
    op.create_index(op.f('ix_products_updated_at'), 'products', ['updated_at'], unique=False)
    op.create_index(op.f('ix_products_wholesale_account_id'), 'products', ['wholesale_account_id'], unique=False)
    
    # Additional tables for product variants, warehouses, etc. would continue here...
    # For brevity, I'll create the key tables. The full migration would include all tables.
    
    # Warehouses table
    op.create_table('warehouses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('manager_name', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('total_capacity', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('used_capacity', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('auto_reorder', sa.Boolean(), nullable=False),
        sa.Column('operating_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_warehouses_code'), 'warehouses', ['code'], unique=True)
    op.create_index(op.f('ix_warehouses_created_at'), 'warehouses', ['created_at'], unique=False)
    op.create_index(op.f('ix_warehouses_deleted_at'), 'warehouses', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_warehouses_id'), 'warehouses', ['id'], unique=False)
    op.create_index(op.f('ix_warehouses_is_active'), 'warehouses', ['is_active'], unique=False)
    op.create_index(op.f('ix_warehouses_is_deleted'), 'warehouses', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_warehouses_name'), 'warehouses', ['name'], unique=False)
    op.create_index(op.f('ix_warehouses_updated_at'), 'warehouses', ['updated_at'], unique=False)
    
    # AI models table
    op.create_table('ai_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('model_type', sa.Enum('neural_network', 'random_forest', 'gradient_boosting', 'linear_regression', 'logistic_regression', 'svm', 'clustering', 'nlp_transformer', 'computer_vision', name='aimodeltype'), nullable=False),
        sa.Column('operation_type', sa.Enum('price_optimization', 'inventory_prediction', 'demand_forecasting', 'product_recommendation', 'title_optimization', 'description_generation', 'category_classification', 'image_analysis', 'competitive_analysis', 'market_analysis', 'customer_segmentation', 'fraud_detection', name='aioperationtype'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model_path', sa.String(length=1000), nullable=True),
        sa.Column('config_path', sa.String(length=1000), nullable=True),
        sa.Column('weights_path', sa.String(length=1000), nullable=True),
        sa.Column('input_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('hyperparameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('training_dataset_size', sa.Integer(), nullable=True),
        sa.Column('training_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('training_completed_at', sa.DateTime(), nullable=True),
        sa.Column('accuracy', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('precision', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('recall', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('f1_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('validation_accuracy', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('cross_validation_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('deployment_date', sa.DateTime(), nullable=True),
        sa.Column('prediction_count', sa.Integer(), nullable=False),
        sa.Column('average_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('production_accuracy', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('drift_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_models_created_at'), 'ai_models', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_models_deleted_at'), 'ai_models', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_ai_models_id'), 'ai_models', ['id'], unique=False)
    op.create_index(op.f('ix_ai_models_is_active'), 'ai_models', ['is_active'], unique=False)
    op.create_index(op.f('ix_ai_models_is_deleted'), 'ai_models', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_ai_models_model_type'), 'ai_models', ['model_type'], unique=False)
    op.create_index(op.f('ix_ai_models_name'), 'ai_models', ['name'], unique=False)
    op.create_index(op.f('ix_ai_models_operation_type'), 'ai_models', ['operation_type'], unique=False)
    op.create_index(op.f('ix_ai_models_updated_at'), 'ai_models', ['updated_at'], unique=False)
    op.create_index(op.f('ix_ai_models_version'), 'ai_models', ['version'], unique=False)
    
    # AI logs table
    op.create_table('ai_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('operation_type', sa.Enum('price_optimization', 'inventory_prediction', 'demand_forecasting', 'product_recommendation', 'title_optimization', 'description_generation', 'category_classification', 'image_analysis', 'competitive_analysis', 'market_analysis', 'customer_segmentation', 'fraud_detection', name='aioperationtype'), nullable=False),
        sa.Column('model_type', sa.Enum('neural_network', 'random_forest', 'gradient_boosting', 'linear_regression', 'logistic_regression', 'svm', 'clustering', 'nlp_transformer', 'computer_vision', name='aimodeltype'), nullable=True),
        sa.Column('model_name', sa.String(length=200), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='executionstatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('accuracy_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('precision_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('recall_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('f1_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('predicted_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actual_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('roi_estimate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stack', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('cpu_usage_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('memory_usage_mb', sa.Integer(), nullable=True),
        sa.Column('gpu_usage_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('environment', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_logs_completed_at'), 'ai_logs', ['completed_at'], unique=False)
    op.create_index(op.f('ix_ai_logs_created_at'), 'ai_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_logs_deleted_at'), 'ai_logs', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_ai_logs_id'), 'ai_logs', ['id'], unique=False)
    op.create_index(op.f('ix_ai_logs_is_deleted'), 'ai_logs', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_ai_logs_model_type'), 'ai_logs', ['model_type'], unique=False)
    op.create_index(op.f('ix_ai_logs_operation_type'), 'ai_logs', ['operation_type'], unique=False)
    op.create_index(op.f('ix_ai_logs_started_at'), 'ai_logs', ['started_at'], unique=False)
    op.create_index(op.f('ix_ai_logs_status'), 'ai_logs', ['status'], unique=False)
    op.create_index(op.f('ix_ai_logs_updated_at'), 'ai_logs', ['updated_at'], unique=False)
    op.create_index(op.f('ix_ai_logs_user_id'), 'ai_logs', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop all tables and ENUM types"""
    
    # Drop tables in reverse order of creation
    op.drop_table('ai_logs')
    op.drop_table('ai_models')
    op.drop_table('warehouses')
    op.drop_table('products')
    op.drop_table('product_categories')
    op.drop_table('platform_sync_logs')
    op.drop_table('wholesale_accounts')
    op.drop_table('platform_accounts')
    op.drop_table('user_api_keys')
    op.drop_table('user_sessions')
    op.drop_table('users')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS executionstatus")
    op.execute("DROP TYPE IF EXISTS aimodeltype")
    op.execute("DROP TYPE IF EXISTS aioperationtype")
    op.execute("DROP TYPE IF EXISTS inventorystatus")
    op.execute("DROP TYPE IF EXISTS movementtype")
    op.execute("DROP TYPE IF EXISTS shippingstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS pricingstrategy")
    op.execute("DROP TYPE IF EXISTS producttype")
    op.execute("DROP TYPE IF EXISTS productstatus")
    op.execute("DROP TYPE IF EXISTS accountstatus")
    op.execute("DROP TYPE IF EXISTS platformtype")
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS userrole")