"""Add product processing tables

Revision ID: 005_add_product_processing_tables
Revises: 004_add_sourcing_models
Create Date: 2025-07-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_product_processing_tables'
down_revision = '004_add_sourcing_models'
branch_labels = None
depends_on = None


def upgrade():
    # 상품가공 이력 테이블
    op.create_table('product_processing_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_product_id', sa.Integer(), nullable=False),
        sa.Column('processed_product_id', sa.Integer(), nullable=True),
        sa.Column('processing_type', sa.String(length=50), nullable=False),
        sa.Column('original_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('processed_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('ai_model_used', sa.String(length=100), nullable=False),
        sa.Column('processing_cost', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['original_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['processed_product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_processing_history_id'), 'product_processing_history', ['id'], unique=False)

    # 베스트셀러 패턴 분석 테이블
    op.create_table('bestseller_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('pattern_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('effectiveness_score', sa.Float(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('last_analyzed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bestseller_patterns_id'), 'bestseller_patterns', ['id'], unique=False)

    # 이미지 가공 이력 테이블
    op.create_table('image_processing_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('original_image_url', sa.Text(), nullable=False),
        sa.Column('processed_image_url', sa.Text(), nullable=True),
        sa.Column('processing_steps', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('market_specifications', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('supabase_path', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('image_quality_score', sa.Float(), nullable=True),
        sa.Column('compression_ratio', sa.Float(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_image_processing_history_id'), 'image_processing_history', ['id'], unique=False)

    # 마켓별 가이드라인 테이블
    op.create_table('market_guidelines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('image_specs', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('naming_rules', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('description_rules', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('prohibited_keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('required_fields', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('guidelines_version', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('marketplace')
    )
    op.create_index(op.f('ix_market_guidelines_id'), 'market_guidelines', ['id'], unique=False)

    # 상품명 생성 이력 테이블
    op.create_table('product_name_generation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('original_name', sa.Text(), nullable=False),
        sa.Column('generated_names', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('selected_name', sa.Text(), nullable=True),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('generation_strategy', sa.String(length=100), nullable=False),
        sa.Column('ai_model_used', sa.String(length=100), nullable=False),
        sa.Column('generation_cost', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('effectiveness_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_name_generation_id'), 'product_name_generation', ['id'], unique=False)

    # 상품 용도 분석 테이블
    op.create_table('product_purpose_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('original_purpose', sa.Text(), nullable=False),
        sa.Column('alternative_purposes', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('selected_purpose', sa.Text(), nullable=True),
        sa.Column('target_audience', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('market_opportunity', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('competition_level', sa.String(length=20), nullable=True),
        sa.Column('ai_model_used', sa.String(length=100), nullable=False),
        sa.Column('analysis_cost', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_purpose_analysis_id'), 'product_purpose_analysis', ['id'], unique=False)

    # 가공 비용 추적 테이블
    op.create_table('processing_cost_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_type', sa.String(length=50), nullable=False),
        sa.Column('ai_model', sa.String(length=100), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('average_cost_per_request', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('cost_optimization_used', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_processing_cost_tracking_id'), 'processing_cost_tracking', ['id'], unique=False)

    # 경쟁사 분석 테이블
    op.create_table('competitor_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('competitor_products', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('price_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('naming_patterns', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('image_strategies', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('market_gap_opportunities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('competitive_advantage', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('analysis_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_competitor_analysis_id'), 'competitor_analysis', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_competitor_analysis_id'), table_name='competitor_analysis')
    op.drop_table('competitor_analysis')
    op.drop_index(op.f('ix_processing_cost_tracking_id'), table_name='processing_cost_tracking')
    op.drop_table('processing_cost_tracking')
    op.drop_index(op.f('ix_product_purpose_analysis_id'), table_name='product_purpose_analysis')
    op.drop_table('product_purpose_analysis')
    op.drop_index(op.f('ix_product_name_generation_id'), table_name='product_name_generation')
    op.drop_table('product_name_generation')
    op.drop_index(op.f('ix_market_guidelines_id'), table_name='market_guidelines')
    op.drop_table('market_guidelines')
    op.drop_index(op.f('ix_image_processing_history_id'), table_name='image_processing_history')
    op.drop_table('image_processing_history')
    op.drop_index(op.f('ix_bestseller_patterns_id'), table_name='bestseller_patterns')
    op.drop_table('bestseller_patterns')
    op.drop_index(op.f('ix_product_processing_history_id'), table_name='product_processing_history')
    op.drop_table('product_processing_history')