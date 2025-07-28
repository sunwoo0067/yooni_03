"""Add performance indexes

Revision ID: add_performance_indexes
Revises: 
Create Date: 2025-01-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_performance_indexes'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes"""
    
    # Products table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_created_at ON products (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_updated_at ON products (updated_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_status ON products (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_wholesale_price ON products (wholesale_price);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_selling_price ON products (selling_price);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_is_active ON products (is_active);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_is_deleted ON products (is_deleted);")
    
    # Orders table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_updated_at ON orders (updated_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_platform_type ON orders (platform_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer_name ON orders (customer_name);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders (order_number);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_tracking_number ON orders (tracking_number);")
    
    # Order Items table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);")
    
    # Users table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);")
    
    # Platform Accounts table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_platform_accounts_user_id ON platform_accounts (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_platform_accounts_platform_type ON platform_accounts (platform_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_platform_accounts_is_active ON platform_accounts (is_active);")
    
    # Collected Products table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_collected_products_wholesaler_type ON collected_products (wholesaler_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collected_products_created_at ON collected_products (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collected_products_price ON collected_products (price);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collected_products_stock_quantity ON collected_products (stock_quantity);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collected_products_category ON collected_products (category);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collected_products_name ON collected_products (name);")
    
    # Inventory table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_inventory_product_id ON inventory (product_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inventory_quantity ON inventory (quantity);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inventory_updated_at ON inventory (updated_at DESC);")
    
    # AI Logs table indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_ai_logs_created_at ON ai_logs (created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ai_logs_user_id ON ai_logs (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ai_logs_operation_type ON ai_logs (operation_type);")
    
    # Wholesaler accounts indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_wholesaler_accounts_wholesaler_type ON wholesaler_accounts (wholesaler_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wholesaler_accounts_is_active ON wholesaler_accounts (is_active);")
    
    # Composite indexes for common queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_active_category ON products (is_active, category_id) WHERE is_deleted = false;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_price_range ON products (wholesale_price, selling_price) WHERE is_active = true AND is_deleted = false;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_status_platform ON orders (status, platform_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_date_status ON orders (created_at DESC, status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collected_products_wholesaler_price ON collected_products (wholesaler_type, price);")


def downgrade() -> None:
    """Remove performance indexes"""
    
    # Drop all indexes
    indexes_to_drop = [
        "idx_products_created_at",
        "idx_products_updated_at", 
        "idx_products_status",
        "idx_products_category_id",
        "idx_products_sku",
        "idx_products_name",
        "idx_products_wholesale_price",
        "idx_products_selling_price",
        "idx_products_is_active",
        "idx_products_is_deleted",
        "idx_orders_created_at",
        "idx_orders_updated_at",
        "idx_orders_status",
        "idx_orders_platform_type",
        "idx_orders_customer_name",
        "idx_orders_order_number",
        "idx_orders_tracking_number",
        "idx_order_items_order_id",
        "idx_order_items_product_id",
        "idx_users_email",
        "idx_users_username",
        "idx_users_created_at",
        "idx_users_is_active",
        "idx_platform_accounts_user_id",
        "idx_platform_accounts_platform_type",
        "idx_platform_accounts_is_active",
        "idx_collected_products_wholesaler_type",
        "idx_collected_products_created_at",
        "idx_collected_products_price",
        "idx_collected_products_stock_quantity",
        "idx_collected_products_category",
        "idx_collected_products_name",
        "idx_inventory_product_id",
        "idx_inventory_quantity",
        "idx_inventory_updated_at",
        "idx_ai_logs_created_at",
        "idx_ai_logs_user_id",
        "idx_ai_logs_operation_type",
        "idx_wholesaler_accounts_wholesaler_type",
        "idx_wholesaler_accounts_is_active",
        "idx_products_active_category",
        "idx_products_price_range",
        "idx_orders_status_platform",
        "idx_orders_date_status",
        "idx_collected_products_wholesaler_price"
    ]
    
    for index_name in indexes_to_drop:
        op.execute(f"DROP INDEX IF EXISTS {index_name};")