"""Add order automation tables

Revision ID: 003_add_order_automation_tables
Revises: 002_add_dropshipping_tables
Create Date: 2024-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_order_automation_tables'
down_revision = '002_add_dropshipping_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add order automation tables"""
    
    # Create enum types
    op.execute("CREATE TYPE wholesaleorderstatus AS ENUM ('pending', 'submitted', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'failed', 'out_of_stock', 'partial_shipped')")
    op.execute("CREATE TYPE shippingtrackingstatus AS ENUM ('pending', 'collected', 'in_transit', 'out_for_delivery', 'delivered', 'failed_delivery', 'returned', 'exception')")
    op.execute("CREATE TYPE settlementstatus AS ENUM ('pending', 'calculated', 'approved', 'completed', 'disputed')")
    
    # wholesale_orders table
    op.create_table('wholesale_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('wholesaler_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wholesaler_order_id', sa.String(length=100), nullable=True),
        sa.Column('product_sku', sa.String(length=100), nullable=False),
        sa.Column('product_name', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'SUBMITTED', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'FAILED', 'OUT_OF_STOCK', 'PARTIAL_SHIPPED', name='wholesaleorderstatus'), nullable=False),
        sa.Column('auto_order_enabled', sa.Boolean(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('max_retry_count', sa.Integer(), nullable=False),
        sa.Column('ordered_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('shipped_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_delivery_date', sa.DateTime(), nullable=True),
        sa.Column('tracking_number', sa.String(length=100), nullable=True),
        sa.Column('carrier', sa.String(length=100), nullable=True),
        sa.Column('shipping_method', sa.String(length=100), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False),
        sa.Column('is_manual_hold', sa.Boolean(), nullable=False),
        sa.Column('hold_reason', sa.Text(), nullable=True),
        sa.Column('wholesaler_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ),
        sa.ForeignKeyConstraint(['wholesaler_id'], ['wholesalers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_wholesale_orders_order_id', 'order_id'),
        sa.Index('ix_wholesale_orders_order_item_id', 'order_item_id'),
        sa.Index('ix_wholesale_orders_wholesaler_id', 'wholesaler_id'),
        sa.Index('ix_wholesale_orders_wholesaler_order_id', 'wholesaler_order_id'),
        sa.Index('ix_wholesale_orders_product_sku', 'product_sku'),
        sa.Index('ix_wholesale_orders_status', 'status'),
        sa.Index('ix_wholesale_orders_ordered_at', 'ordered_at'),
        sa.Index('ix_wholesale_orders_tracking_number', 'tracking_number')
    )
    
    # shipping_tracking table
    op.create_table('shipping_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('wholesale_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tracking_number', sa.String(length=100), nullable=False),
        sa.Column('carrier', sa.String(length=100), nullable=False),
        sa.Column('service_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'COLLECTED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED', 'FAILED_DELIVERY', 'RETURNED', 'EXCEPTION', name='shippingtrackingstatus'), nullable=False),
        sa.Column('current_location', sa.String(length=200), nullable=True),
        sa.Column('last_scan_time', sa.DateTime(), nullable=True),
        sa.Column('origin_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('destination_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('estimated_delivery', sa.DateTime(), nullable=True),
        sa.Column('actual_delivery', sa.DateTime(), nullable=True),
        sa.Column('tracking_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.Column('update_frequency_minutes', sa.Integer(), nullable=False),
        sa.Column('customer_notified', sa.Boolean(), nullable=False),
        sa.Column('notification_sent_at', sa.DateTime(), nullable=True),
        sa.Column('tracking_api_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('api_error_count', sa.Integer(), nullable=False),
        sa.Column('last_api_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['wholesale_order_id'], ['wholesale_orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_shipping_tracking_wholesale_order_id', 'wholesale_order_id'),
        sa.Index('ix_shipping_tracking_tracking_number', 'tracking_number'),
        sa.Index('ix_shipping_tracking_status', 'status'),
        sa.Index('ix_shipping_tracking_last_scan_time', 'last_scan_time'),
        sa.Index('ix_shipping_tracking_actual_delivery', 'actual_delivery'),
        sa.Index('ix_shipping_tracking_last_updated', 'last_updated')
    )
    
    # settlements table
    op.create_table('settlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wholesale_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_payment', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('marketplace_fee', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_gateway_fee', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('wholesale_cost', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('shipping_cost', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('packaging_cost', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('other_costs', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('gross_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_costs', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('net_profit', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('profit_margin', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('vat_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('income_tax', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'CALCULATED', 'APPROVED', 'COMPLETED', 'DISPUTED', name='settlementstatus'), nullable=False),
        sa.Column('settlement_date', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('calculation_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cost_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('dispute_reason', sa.Text(), nullable=True),
        sa.Column('adjustment_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('adjustment_reason', sa.Text(), nullable=True),
        sa.Column('calculation_date', sa.DateTime(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=True),
        sa.Column('period_end', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['wholesale_order_id'], ['wholesale_orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
        sa.Index('ix_settlements_order_id', 'order_id'),
        sa.Index('ix_settlements_wholesale_order_id', 'wholesale_order_id'),
        sa.Index('ix_settlements_status', 'status'),
        sa.Index('ix_settlements_settlement_date', 'settlement_date'),
        sa.Index('ix_settlements_calculation_date', 'calculation_date')
    )
    
    # order_processing_rules table
    op.create_table('order_processing_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=True),
        sa.Column('wholesaler_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('product_category', sa.String(length=100), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('execution_count', sa.Integer(), nullable=False),
        sa.Column('success_count', sa.Integer(), nullable=False),
        sa.Column('failure_count', sa.Integer(), nullable=False),
        sa.Column('last_executed_at', sa.DateTime(), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['wholesaler_id'], ['wholesalers.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_order_processing_rules_wholesaler_id', 'wholesaler_id'),
        sa.Index('ix_order_processing_rules_product_id', 'product_id')
    )
    
    # order_processing_logs table
    op.create_table('order_processing_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wholesale_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processing_rule_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processing_step', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processor_name', sa.String(length=100), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['wholesale_order_id'], ['wholesale_orders.id'], ),
        sa.ForeignKeyConstraint(['processing_rule_id'], ['order_processing_rules.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_order_processing_logs_order_id', 'order_id'),
        sa.Index('ix_order_processing_logs_wholesale_order_id', 'wholesale_order_id'),
        sa.Index('ix_order_processing_logs_processing_rule_id', 'processing_rule_id'),
        sa.Index('ix_order_processing_logs_processing_step', 'processing_step'),
        sa.Index('ix_order_processing_logs_success', 'success')
    )
    
    # exception_cases table
    op.create_table('exception_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wholesale_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('exception_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('resolution_action', sa.String(length=100), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.String(length=100), nullable=True),
        sa.Column('auto_resolution_attempted', sa.Boolean(), nullable=False),
        sa.Column('auto_resolution_success', sa.Boolean(), nullable=False),
        sa.Column('auto_resolution_notes', sa.Text(), nullable=True),
        sa.Column('customer_notified', sa.Boolean(), nullable=False),
        sa.Column('customer_notification_sent_at', sa.DateTime(), nullable=True),
        sa.Column('customer_compensation_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('exception_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('priority_score', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['wholesale_order_id'], ['wholesale_orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_exception_cases_order_id', 'order_id'),
        sa.Index('ix_exception_cases_wholesale_order_id', 'wholesale_order_id'),
        sa.Index('ix_exception_cases_exception_type', 'exception_type'),
        sa.Index('ix_exception_cases_status', 'status'),
        sa.Index('ix_exception_cases_resolved_at', 'resolved_at'),
        sa.Index('ix_exception_cases_priority_score', 'priority_score')
    )
    
    # Set default values for existing columns
    op.execute("ALTER TABLE wholesale_orders ALTER COLUMN auto_order_enabled SET DEFAULT TRUE")
    op.execute("ALTER TABLE wholesale_orders ALTER COLUMN retry_count SET DEFAULT 0")
    op.execute("ALTER TABLE wholesale_orders ALTER COLUMN max_retry_count SET DEFAULT 3")
    op.execute("ALTER TABLE wholesale_orders ALTER COLUMN error_count SET DEFAULT 0")
    op.execute("ALTER TABLE wholesale_orders ALTER COLUMN is_manual_hold SET DEFAULT FALSE")
    op.execute("ALTER TABLE wholesale_orders ALTER COLUMN status SET DEFAULT 'pending'")
    
    op.execute("ALTER TABLE shipping_tracking ALTER COLUMN update_frequency_minutes SET DEFAULT 60")
    op.execute("ALTER TABLE shipping_tracking ALTER COLUMN customer_notified SET DEFAULT FALSE")
    op.execute("ALTER TABLE shipping_tracking ALTER COLUMN api_error_count SET DEFAULT 0")
    
    op.execute("ALTER TABLE settlements ALTER COLUMN marketplace_fee SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN payment_gateway_fee SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN shipping_cost SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN packaging_cost SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN other_costs SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN vat_amount SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN income_tax SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN adjustment_amount SET DEFAULT 0")
    op.execute("ALTER TABLE settlements ALTER COLUMN status SET DEFAULT 'pending'")
    
    op.execute("ALTER TABLE order_processing_rules ALTER COLUMN priority SET DEFAULT 0")
    op.execute("ALTER TABLE order_processing_rules ALTER COLUMN is_active SET DEFAULT TRUE")
    op.execute("ALTER TABLE order_processing_rules ALTER COLUMN execution_count SET DEFAULT 0")
    op.execute("ALTER TABLE order_processing_rules ALTER COLUMN success_count SET DEFAULT 0")
    op.execute("ALTER TABLE order_processing_rules ALTER COLUMN failure_count SET DEFAULT 0")
    
    op.execute("ALTER TABLE exception_cases ALTER COLUMN severity SET DEFAULT 'medium'")
    op.execute("ALTER TABLE exception_cases ALTER COLUMN status SET DEFAULT 'open'")
    op.execute("ALTER TABLE exception_cases ALTER COLUMN auto_resolution_attempted SET DEFAULT FALSE")
    op.execute("ALTER TABLE exception_cases ALTER COLUMN auto_resolution_success SET DEFAULT FALSE")
    op.execute("ALTER TABLE exception_cases ALTER COLUMN customer_notified SET DEFAULT FALSE")
    op.execute("ALTER TABLE exception_cases ALTER COLUMN priority_score SET DEFAULT 0")


def downgrade():
    """Drop order automation tables"""
    
    # Drop tables in reverse order
    op.drop_table('exception_cases')
    op.drop_table('order_processing_logs')
    op.drop_table('order_processing_rules')
    op.drop_table('settlements')
    op.drop_table('shipping_tracking')
    op.drop_table('wholesale_orders')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS settlementstatus")
    op.execute("DROP TYPE IF EXISTS shippingtrackingstatus")
    op.execute("DROP TYPE IF EXISTS wholesaleorderstatus")