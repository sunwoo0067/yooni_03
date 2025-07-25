"""add benchmark tables

Revision ID: 006
Revises: 005
Create Date: 2025-07-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # BenchmarkProduct 테이블 생성
    op.create_table('benchmark_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('market_product_id', sa.String(100), nullable=True),
        sa.Column('market_type', sa.String(50), nullable=True),
        sa.Column('product_name', sa.String(500), nullable=True),
        sa.Column('brand', sa.String(200), nullable=True),
        sa.Column('category_path', sa.String(500), nullable=True),
        sa.Column('main_category', sa.String(100), nullable=True),
        sa.Column('sub_category', sa.String(100), nullable=True),
        sa.Column('original_price', sa.Integer(), nullable=True),
        sa.Column('sale_price', sa.Integer(), nullable=True),
        sa.Column('discount_rate', sa.Float(), nullable=True),
        sa.Column('delivery_fee', sa.Integer(), nullable=True),
        sa.Column('monthly_sales', sa.Integer(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('bestseller_rank', sa.Integer(), nullable=True),
        sa.Column('category_rank', sa.Integer(), nullable=True),
        sa.Column('seller_name', sa.String(200), nullable=True),
        sa.Column('seller_grade', sa.String(50), nullable=True),
        sa.Column('is_power_seller', sa.Boolean(), nullable=True),
        sa.Column('options', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('attributes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_products_id'), 'benchmark_products', ['id'], unique=False)
    op.create_index(op.f('ix_benchmark_products_market_product_id'), 'benchmark_products', ['market_product_id'], unique=False)
    op.create_index(op.f('ix_benchmark_products_market_type'), 'benchmark_products', ['market_type'], unique=False)
    op.create_index(op.f('ix_benchmark_products_main_category'), 'benchmark_products', ['main_category'], unique=False)
    op.create_index(op.f('ix_benchmark_products_sub_category'), 'benchmark_products', ['sub_category'], unique=False)
    op.create_index('idx_market_category', 'benchmark_products', ['market_type', 'main_category'], unique=False)
    op.create_index('idx_bestseller', 'benchmark_products', ['market_type', 'bestseller_rank'], unique=False)
    op.create_index('idx_sales', 'benchmark_products', ['monthly_sales'], unique=False)

    # BenchmarkPriceHistory 테이블 생성
    op.create_table('benchmark_price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('market_product_id', sa.String(100), nullable=True),
        sa.Column('market_type', sa.String(50), nullable=True),
        sa.Column('original_price', sa.Integer(), nullable=True),
        sa.Column('sale_price', sa.Integer(), nullable=True),
        sa.Column('discount_rate', sa.Float(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_price_history_id'), 'benchmark_price_history', ['id'], unique=False)
    op.create_index(op.f('ix_benchmark_price_history_market_product_id'), 'benchmark_price_history', ['market_product_id'], unique=False)
    op.create_index('idx_product_time', 'benchmark_price_history', ['market_product_id', 'recorded_at'], unique=False)

    # BenchmarkKeyword 테이블 생성
    op.create_table('benchmark_keywords',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(100), nullable=True),
        sa.Column('search_volume', sa.Integer(), nullable=True),
        sa.Column('competition', sa.String(20), nullable=True),
        sa.Column('trend_score', sa.Float(), nullable=True),
        sa.Column('growth_rate', sa.Float(), nullable=True),
        sa.Column('related_keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('category_distribution', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('keyword')
    )
    op.create_index(op.f('ix_benchmark_keywords_id'), 'benchmark_keywords', ['id'], unique=False)
    op.create_index(op.f('ix_benchmark_keywords_keyword'), 'benchmark_keywords', ['keyword'], unique=True)

    # BenchmarkReview 테이블 생성
    op.create_table('benchmark_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('market_product_id', sa.String(100), nullable=True),
        sa.Column('market_type', sa.String(50), nullable=True),
        sa.Column('total_reviews', sa.Integer(), nullable=True),
        sa.Column('positive_count', sa.Integer(), nullable=True),
        sa.Column('neutral_count', sa.Integer(), nullable=True),
        sa.Column('negative_count', sa.Integer(), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('positive_keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('negative_keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('improvement_suggestions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_reviews_id'), 'benchmark_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_benchmark_reviews_market_product_id'), 'benchmark_reviews', ['market_product_id'], unique=False)

    # BenchmarkCompetitor 테이블 생성
    op.create_table('benchmark_competitors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('competitor_name', sa.String(200), nullable=True),
        sa.Column('market_share', sa.Float(), nullable=True),
        sa.Column('total_products', sa.Integer(), nullable=True),
        sa.Column('average_rating', sa.Float(), nullable=True),
        sa.Column('avg_price', sa.Integer(), nullable=True),
        sa.Column('price_range_min', sa.Integer(), nullable=True),
        sa.Column('price_range_max', sa.Integer(), nullable=True),
        sa.Column('main_categories', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('bestseller_products', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('monthly_revenue_estimate', sa.Integer(), nullable=True),
        sa.Column('growth_trend', sa.String(20), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competitor_name')
    )
    op.create_index(op.f('ix_benchmark_competitors_id'), 'benchmark_competitors', ['id'], unique=False)
    op.create_index(op.f('ix_benchmark_competitors_competitor_name'), 'benchmark_competitors', ['competitor_name'], unique=True)

    # BenchmarkMarketTrend 테이블 생성
    op.create_table('benchmark_market_trends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('period', sa.String(20), nullable=True),
        sa.Column('market_size', sa.Integer(), nullable=True),
        sa.Column('transaction_volume', sa.Integer(), nullable=True),
        sa.Column('growth_rate', sa.Float(), nullable=True),
        sa.Column('seasonality_index', sa.Float(), nullable=True),
        sa.Column('top_keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('emerging_brands', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('price_trends', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_market_trends_id'), 'benchmark_market_trends', ['id'], unique=False)
    op.create_index(op.f('ix_benchmark_market_trends_category'), 'benchmark_market_trends', ['category'], unique=False)

    # BenchmarkAlert 테이블 생성
    op.create_table('benchmark_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=True),
        sa.Column('target_product_id', sa.String(100), nullable=True),
        sa.Column('target_keyword', sa.String(100), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.Integer(), nullable=True),
        sa.Column('message_template', sa.Text(), nullable=True),
        sa.Column('notification_channels', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_alerts_id'), 'benchmark_alerts', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_benchmark_alerts_id'), table_name='benchmark_alerts')
    op.drop_table('benchmark_alerts')
    
    op.drop_index(op.f('ix_benchmark_market_trends_category'), table_name='benchmark_market_trends')
    op.drop_index(op.f('ix_benchmark_market_trends_id'), table_name='benchmark_market_trends')
    op.drop_table('benchmark_market_trends')
    
    op.drop_index(op.f('ix_benchmark_competitors_competitor_name'), table_name='benchmark_competitors')
    op.drop_index(op.f('ix_benchmark_competitors_id'), table_name='benchmark_competitors')
    op.drop_table('benchmark_competitors')
    
    op.drop_index(op.f('ix_benchmark_reviews_market_product_id'), table_name='benchmark_reviews')
    op.drop_index(op.f('ix_benchmark_reviews_id'), table_name='benchmark_reviews')
    op.drop_table('benchmark_reviews')
    
    op.drop_index(op.f('ix_benchmark_keywords_keyword'), table_name='benchmark_keywords')
    op.drop_index(op.f('ix_benchmark_keywords_id'), table_name='benchmark_keywords')
    op.drop_table('benchmark_keywords')
    
    op.drop_index('idx_product_time', table_name='benchmark_price_history')
    op.drop_index(op.f('ix_benchmark_price_history_market_product_id'), table_name='benchmark_price_history')
    op.drop_index(op.f('ix_benchmark_price_history_id'), table_name='benchmark_price_history')
    op.drop_table('benchmark_price_history')
    
    op.drop_index('idx_sales', table_name='benchmark_products')
    op.drop_index('idx_bestseller', table_name='benchmark_products')
    op.drop_index('idx_market_category', table_name='benchmark_products')
    op.drop_index(op.f('ix_benchmark_products_sub_category'), table_name='benchmark_products')
    op.drop_index(op.f('ix_benchmark_products_main_category'), table_name='benchmark_products')
    op.drop_index(op.f('ix_benchmark_products_market_type'), table_name='benchmark_products')
    op.drop_index(op.f('ix_benchmark_products_market_product_id'), table_name='benchmark_products')
    op.drop_index(op.f('ix_benchmark_products_id'), table_name='benchmark_products')
    op.drop_table('benchmark_products')