"""Add dropshipping order processing tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-24 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add new order statuses to enum
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'supplier_order_pending'")
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'supplier_order_confirmed'")
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'supplier_order_failed'")
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'out_of_stock'")
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'margin_protected'")
    
    # Create supplier order status enum
    supplier_order_status = postgresql.ENUM(
        'pending', 'submitted', 'confirmed', 'processing', 
        'shipped', 'delivered', 'cancelled', 'failed', 'out_of_stock',
        name='supplierorderstatus'
    )
    supplier_order_status.create(op.get_bind())
    
    # Create dropshipping_orders table
    op.create_table(
        'dropshipping_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        
        # 원본 고객 주문 참조
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False, unique=True),
        
        # 공급업체 정보
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wholesalers.id'), nullable=False),
        sa.Column('supplier_order_id', sa.String(100), nullable=True),
        
        # 마진 정보
        sa.Column('customer_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('supplier_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('margin_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('margin_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('minimum_margin_rate', sa.Numeric(5, 2), nullable=False, default=10.0),
        
        # 자동 처리 설정
        sa.Column('auto_order_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('max_retry_count', sa.Integer, nullable=False, default=3),
        
        # 상태 및 시간 정보
        sa.Column('status', supplier_order_status, nullable=False, default='pending'),
        sa.Column('supplier_order_date', sa.DateTime, nullable=True),
        sa.Column('supplier_confirmed_at', sa.DateTime, nullable=True),
        sa.Column('supplier_shipped_at', sa.DateTime, nullable=True),
        
        # 배송 정보
        sa.Column('supplier_tracking_number', sa.String(100), nullable=True),
        sa.Column('supplier_carrier', sa.String(100), nullable=True),
        sa.Column('estimated_delivery_date', sa.DateTime, nullable=True),
        
        # 오류 및 예외 처리
        sa.Column('last_error_message', sa.Text, nullable=True),
        sa.Column('error_count', sa.Integer, nullable=False, default=0),
        sa.Column('is_blocked', sa.Boolean, nullable=False, default=False),
        sa.Column('blocked_reason', sa.Text, nullable=True),
        
        # 추가 정보
        sa.Column('supplier_response_data', postgresql.JSONB, nullable=True),
        sa.Column('processing_notes', sa.Text, nullable=True),
    )
    
    # Create indexes for dropshipping_orders
    op.create_index('ix_dropshipping_orders_order_id', 'dropshipping_orders', ['order_id'])
    op.create_index('ix_dropshipping_orders_supplier_id', 'dropshipping_orders', ['supplier_id'])
    op.create_index('ix_dropshipping_orders_status', 'dropshipping_orders', ['status'])
    op.create_index('ix_dropshipping_orders_supplier_order_id', 'dropshipping_orders', ['supplier_order_id'])
    op.create_index('ix_dropshipping_orders_supplier_tracking_number', 'dropshipping_orders', ['supplier_tracking_number'])
    
    # Create dropshipping_order_logs table
    op.create_table(
        'dropshipping_order_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.Column('dropshipping_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dropshipping_orders.id'), nullable=False),
        
        # 로그 정보
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('status_before', sa.String(50), nullable=True),
        sa.Column('status_after', sa.String(50), nullable=True),
        
        # 결과 정보
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('response_data', postgresql.JSONB, nullable=True),
        
        # 처리 시간
        sa.Column('processing_time_ms', sa.Integer, nullable=True),
        
        # 추가 정보
        sa.Column('user_agent', sa.String(200), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
    )
    
    # Create indexes for dropshipping_order_logs
    op.create_index('ix_dropshipping_order_logs_dropshipping_order_id', 'dropshipping_order_logs', ['dropshipping_order_id'])
    op.create_index('ix_dropshipping_order_logs_action', 'dropshipping_order_logs', ['action'])
    op.create_index('ix_dropshipping_order_logs_created_at', 'dropshipping_order_logs', ['created_at'])
    
    # Create margin_protection_rules table
    op.create_table(
        'margin_protection_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        
        # 규칙 정보
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        
        # 적용 범위
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wholesalers.id'), nullable=True),
        sa.Column('product_category', sa.String(100), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=True),
        
        # 마진 규칙
        sa.Column('minimum_margin_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('maximum_margin_rate', sa.Numeric(5, 2), nullable=True),
        
        # 가격 변동 대응
        sa.Column('max_price_increase_rate', sa.Numeric(5, 2), nullable=False, default=5.0),
        sa.Column('auto_adjust_price', sa.Boolean, nullable=False, default=False),
        
        # 활성화 상태
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('priority', sa.Integer, nullable=False, default=0),
        
        # 적용 조건
        sa.Column('min_order_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('max_order_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('valid_from', sa.DateTime, nullable=True),
        sa.Column('valid_until', sa.DateTime, nullable=True),
    )
    
    # Create indexes for margin_protection_rules
    op.create_index('ix_margin_protection_rules_supplier_id', 'margin_protection_rules', ['supplier_id'])
    op.create_index('ix_margin_protection_rules_product_id', 'margin_protection_rules', ['product_id'])
    op.create_index('ix_margin_protection_rules_is_active', 'margin_protection_rules', ['is_active'])
    
    # Update orders table to have relationship with dropshipping_orders
    # This is handled by SQLAlchemy relationship, no schema change needed
    
    print("✅ 드롭쉬핑 주문 처리 테이블들이 성공적으로 생성되었습니다.")


def downgrade():
    # Drop tables in reverse order
    op.drop_table('margin_protection_rules')
    op.drop_table('dropshipping_order_logs')
    op.drop_table('dropshipping_orders')
    
    # Drop enum
    op.execute("DROP TYPE IF EXISTS supplierorderstatus")
    
    print("✅ 드롭쉬핑 주문 처리 테이블들이 성공적으로 제거되었습니다.")