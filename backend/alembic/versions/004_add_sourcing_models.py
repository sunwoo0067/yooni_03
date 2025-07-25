"""Add sourcing models for market and trend analysis

Revision ID: 004
Revises: 003
Create Date: 2025-01-25 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Create market_trends table
    op.create_table('market_trends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('search_volume', sa.Integer(), nullable=True),
        sa.Column('growth_rate', sa.Float(), nullable=True),
        sa.Column('competition_level', sa.String(length=20), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('trend_type', sa.String(length=50), nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=True),
        sa.Column('trend_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_trend_category_date', 'market_trends', ['category', 'created_at'])
    op.create_index('idx_trend_keyword_platform', 'market_trends', ['keyword', 'platform'])
    op.create_index(op.f('ix_market_trends_category'), 'market_trends', ['category'])
    op.create_index(op.f('ix_market_trends_id'), 'market_trends', ['id'])
    op.create_index(op.f('ix_market_trends_keyword'), 'market_trends', ['keyword'])

    # Create market_products table
    op.create_table('market_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('product_id', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('product_name', sa.Text(), nullable=False),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('original_price', sa.Integer(), nullable=True),
        sa.Column('discount_rate', sa.Float(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('is_rocket', sa.Boolean(), nullable=True),
        sa.Column('mall_count', sa.Integer(), nullable=True),
        sa.Column('purchase_count', sa.Integer(), nullable=True),
        sa.Column('brand', sa.String(length=255), nullable=True),
        sa.Column('maker', sa.String(length=255), nullable=True),
        sa.Column('seller_grade', sa.String(length=50), nullable=True),
        sa.Column('delivery_type', sa.String(length=50), nullable=True),
        sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('collected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_marketplace_category', 'market_products', ['marketplace', 'category'])
    op.create_index('idx_marketplace_rank', 'market_products', ['marketplace', 'rank'])
    op.create_index('idx_product_collected', 'market_products', ['product_id', 'collected_at'])
    op.create_index(op.f('ix_market_products_category'), 'market_products', ['category'])
    op.create_index(op.f('ix_market_products_id'), 'market_products', ['id'])
    op.create_index(op.f('ix_market_products_marketplace'), 'market_products', ['marketplace'])
    op.create_index(op.f('ix_market_products_product_id'), 'market_products', ['product_id'])
    op.create_index(op.f('ix_market_products_rank'), 'market_products', ['rank'])

    # Create market_sales_data table
    op.create_table('market_sales_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('market_product_id', sa.Integer(), nullable=False),
        sa.Column('estimated_monthly_sales', sa.Integer(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('discount_rate', sa.Float(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['market_product_id'], ['market_products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_product_recorded', 'market_sales_data', ['market_product_id', 'recorded_at'])
    op.create_index(op.f('ix_market_sales_data_id'), 'market_sales_data', ['id'])
    op.create_index(op.f('ix_market_sales_data_market_product_id'), 'market_sales_data', ['market_product_id'])
    op.create_index(op.f('ix_market_sales_data_recorded_at'), 'market_sales_data', ['recorded_at'])

    # Create market_categories table
    op.create_table('market_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('category_name', sa.String(length=100), nullable=False),
        sa.Column('category_id', sa.String(length=100), nullable=True),
        sa.Column('parent_category', sa.String(length=100), nullable=True),
        sa.Column('total_products', sa.Integer(), nullable=True),
        sa.Column('avg_price', sa.Float(), nullable=True),
        sa.Column('avg_review_count', sa.Float(), nullable=True),
        sa.Column('avg_rating', sa.Float(), nullable=True),
        sa.Column('total_sales_volume', sa.Integer(), nullable=True),
        sa.Column('competition_level', sa.String(length=20), nullable=True),
        sa.Column('growth_rate', sa.Float(), nullable=True),
        sa.Column('market_saturation', sa.Float(), nullable=True),
        sa.Column('entry_barrier', sa.String(length=20), nullable=True),
        sa.Column('analysis_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_category_analyzed', 'market_categories', ['category_name', 'analyzed_at'])
    op.create_index('idx_marketplace_category_name', 'market_categories', ['marketplace', 'category_name'])
    op.create_index(op.f('ix_market_categories_category_name'), 'market_categories', ['category_name'])
    op.create_index(op.f('ix_market_categories_id'), 'market_categories', ['id'])
    op.create_index(op.f('ix_market_categories_marketplace'), 'market_categories', ['marketplace'])

    # Create trend_keywords table
    op.create_table('trend_keywords',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('trend_score', sa.Float(), nullable=True),
        sa.Column('trend_direction', sa.String(length=20), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('search_volume', sa.Integer(), nullable=True),
        sa.Column('competition_level', sa.String(length=20), nullable=True),
        sa.Column('cpc_min', sa.Integer(), nullable=True),
        sa.Column('cpc_max', sa.Integer(), nullable=True),
        sa.Column('rise_percentage', sa.Float(), nullable=True),
        sa.Column('interest_over_time', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('related_queries', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('demographic_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_seasonal', sa.Boolean(), nullable=True),
        sa.Column('peak_months', sa.String(length=100), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_category_platform', 'trend_keywords', ['category', 'platform'])
    op.create_index('idx_keyword_platform_date', 'trend_keywords', ['keyword', 'platform', 'analyzed_at'])
    op.create_index('idx_trend_score_direction', 'trend_keywords', ['trend_score', 'trend_direction'])
    op.create_index(op.f('ix_trend_keywords_analyzed_at'), 'trend_keywords', ['analyzed_at'])
    op.create_index(op.f('ix_trend_keywords_category'), 'trend_keywords', ['category'])
    op.create_index(op.f('ix_trend_keywords_id'), 'trend_keywords', ['id'])
    op.create_index(op.f('ix_trend_keywords_keyword'), 'trend_keywords', ['keyword'])
    op.create_index(op.f('ix_trend_keywords_platform'), 'trend_keywords', ['platform'])

    # Create trend_data table
    op.create_table('trend_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('raw_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('processed_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('completeness', sa.Float(), nullable=True),
        sa.Column('collection_date', sa.DateTime(), nullable=True),
        sa.Column('timeframe', sa.String(length=50), nullable=True),
        sa.Column('geo_location', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_collection_date', 'trend_data', ['collection_date'])
    op.create_index('idx_keyword_platform_type', 'trend_data', ['keyword', 'platform', 'data_type'])
    op.create_index(op.f('ix_trend_data_collection_date'), 'trend_data', ['collection_date'])
    op.create_index(op.f('ix_trend_data_id'), 'trend_data', ['id'])
    op.create_index(op.f('ix_trend_data_keyword'), 'trend_data', ['keyword'])
    op.create_index(op.f('ix_trend_data_platform'), 'trend_data', ['platform'])

    # Create keyword_analyses table
    op.create_table('keyword_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('potential_score', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('competition_score', sa.Float(), nullable=True),
        sa.Column('search_trend_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('seasonal_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('competitive_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('demographic_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('predicted_growth', sa.Float(), nullable=True),
        sa.Column('market_size_estimate', sa.Integer(), nullable=True),
        sa.Column('entry_timing', sa.String(length=50), nullable=True),
        sa.Column('ai_recommendation', sa.String(length=20), nullable=True),
        sa.Column('confidence_level', sa.Float(), nullable=True),
        sa.Column('recommendation_reasons', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('action_items', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('monitoring_alerts', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('next_review_date', sa.DateTime(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_keyword_analyzed', 'keyword_analyses', ['keyword', 'analyzed_at'])
    op.create_index('idx_overall_score', 'keyword_analyses', ['overall_score'])
    op.create_index('idx_recommendation', 'keyword_analyses', ['ai_recommendation', 'confidence_level'])
    op.create_index(op.f('ix_keyword_analyses_analyzed_at'), 'keyword_analyses', ['analyzed_at'])
    op.create_index(op.f('ix_keyword_analyses_category'), 'keyword_analyses', ['category'])
    op.create_index(op.f('ix_keyword_analyses_id'), 'keyword_analyses', ['id'])
    op.create_index(op.f('ix_keyword_analyses_keyword'), 'keyword_analyses', ['keyword'])

    # Create trend_alerts table
    op.create_table('trend_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(length=255), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('current_value', sa.Float(), nullable=False),
        sa.Column('alert_title', sa.String(length=255), nullable=False),
        sa.Column('alert_message', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.String(length=100), nullable=True),
        sa.Column('alert_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('triggered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alert_status', 'trend_alerts', ['is_read', 'is_resolved'])
    op.create_index('idx_keyword_triggered', 'trend_alerts', ['keyword', 'triggered_at'])
    op.create_index('idx_severity_triggered', 'trend_alerts', ['severity', 'triggered_at'])
    op.create_index(op.f('ix_trend_alerts_id'), 'trend_alerts', ['id'])
    op.create_index(op.f('ix_trend_alerts_keyword'), 'trend_alerts', ['keyword'])
    op.create_index(op.f('ix_trend_alerts_triggered_at'), 'trend_alerts', ['triggered_at'])


def downgrade():
    # Drop all tables in reverse order
    op.drop_table('trend_alerts')
    op.drop_table('keyword_analyses')
    op.drop_table('trend_data')
    op.drop_table('trend_keywords')
    op.drop_table('market_sales_data')
    op.drop_table('market_categories')
    op.drop_table('market_products')
    op.drop_table('market_trends')