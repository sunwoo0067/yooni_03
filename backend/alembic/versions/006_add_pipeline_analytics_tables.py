"""add pipeline analytics tables

Revision ID: 006
Revises: 005
Create Date: 2025-01-25 12:00:00.000000

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
    # Create pipeline_executions table
    op.create_table('pipeline_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_completion', sa.DateTime(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('completed_steps', sa.Integer(), nullable=True),
        sa.Column('failed_steps', sa.Integer(), nullable=True),
        sa.Column('total_products_to_process', sa.Integer(), nullable=True),
        sa.Column('products_processed', sa.Integer(), nullable=True),
        sa.Column('products_succeeded', sa.Integer(), nullable=True),
        sa.Column('products_failed', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('processing_rate', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('error_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('execution_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('results_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('cpu_usage_avg', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('memory_usage_avg', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_executions_created_at'), 'pipeline_executions', ['created_at'], unique=False)
    op.create_index(op.f('ix_pipeline_executions_id'), 'pipeline_executions', ['id'], unique=False)
    op.create_index(op.f('ix_pipeline_executions_is_deleted'), 'pipeline_executions', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_pipeline_executions_status'), 'pipeline_executions', ['status'], unique=False)
    op.create_index(op.f('ix_pipeline_executions_updated_at'), 'pipeline_executions', ['updated_at'], unique=False)
    op.create_index(op.f('ix_pipeline_executions_workflow_id'), 'pipeline_executions', ['workflow_id'], unique=True)
    op.create_index(op.f('ix_pipeline_executions_deleted_at'), 'pipeline_executions', ['deleted_at'], unique=False)

    # Create pipeline_steps table
    op.create_table('pipeline_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(length=100), nullable=False),
        sa.Column('step_type', sa.String(length=50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('total_items', sa.Integer(), nullable=True),
        sa.Column('processed_items', sa.Integer(), nullable=True),
        sa.Column('succeeded_items', sa.Integer(), nullable=True),
        sa.Column('failed_items', sa.Integer(), nullable=True),
        sa.Column('step_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('step_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('processing_rate', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('resource_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['pipeline_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_steps_created_at'), 'pipeline_steps', ['created_at'], unique=False)
    op.create_index(op.f('ix_pipeline_steps_id'), 'pipeline_steps', ['id'], unique=False)
    op.create_index(op.f('ix_pipeline_steps_is_deleted'), 'pipeline_steps', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_pipeline_steps_updated_at'), 'pipeline_steps', ['updated_at'], unique=False)
    op.create_index(op.f('ix_pipeline_steps_deleted_at'), 'pipeline_steps', ['deleted_at'], unique=False)

    # Create pipeline_product_results table
    op.create_table('pipeline_product_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_code', sa.String(length=100), nullable=True),
        sa.Column('sourcing_status', sa.String(length=20), nullable=True),
        sa.Column('processing_status', sa.String(length=20), nullable=True),
        sa.Column('registration_status', sa.String(length=20), nullable=True),
        sa.Column('sourcing_completed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(), nullable=True),
        sa.Column('registration_completed_at', sa.DateTime(), nullable=True),
        sa.Column('sourcing_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('sourcing_reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_quality_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('registration_platforms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('registration_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('final_status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('total_processing_time', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['pipeline_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_product_results_created_at'), 'pipeline_product_results', ['created_at'], unique=False)
    op.create_index(op.f('ix_pipeline_product_results_id'), 'pipeline_product_results', ['id'], unique=False)
    op.create_index(op.f('ix_pipeline_product_results_is_deleted'), 'pipeline_product_results', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_pipeline_product_results_updated_at'), 'pipeline_product_results', ['updated_at'], unique=False)
    op.create_index(op.f('ix_pipeline_product_results_deleted_at'), 'pipeline_product_results', ['deleted_at'], unique=False)

    # Create workflow_templates table
    op.create_table('workflow_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('steps_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('default_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_workflow_templates_created_at'), 'workflow_templates', ['created_at'], unique=False)
    op.create_index(op.f('ix_workflow_templates_id'), 'workflow_templates', ['id'], unique=False)
    op.create_index(op.f('ix_workflow_templates_is_deleted'), 'workflow_templates', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_workflow_templates_updated_at'), 'workflow_templates', ['updated_at'], unique=False)
    op.create_index(op.f('ix_workflow_templates_deleted_at'), 'workflow_templates', ['deleted_at'], unique=False)

    # Create pipeline_alerts table
    op.create_table('pipeline_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=True),
        sa.Column('step_name', sa.String(length=100), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('action_required', sa.Boolean(), nullable=True),
        sa.Column('action_taken', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('alert_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['pipeline_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_alerts_created_at'), 'pipeline_alerts', ['created_at'], unique=False)
    op.create_index(op.f('ix_pipeline_alerts_id'), 'pipeline_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_pipeline_alerts_is_deleted'), 'pipeline_alerts', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_pipeline_alerts_updated_at'), 'pipeline_alerts', ['updated_at'], unique=False)
    op.create_index(op.f('ix_pipeline_alerts_deleted_at'), 'pipeline_alerts', ['deleted_at'], unique=False)

    # Create pipeline_schedules table
    op.create_table('pipeline_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('workflow_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('cron_expression', sa.String(length=100), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('max_parallel_executions', sa.Integer(), nullable=True),
        sa.Column('timeout_minutes', sa.Integer(), nullable=True),
        sa.Column('execution_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_execution_at', sa.DateTime(), nullable=True),
        sa.Column('next_execution_at', sa.DateTime(), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=True),
        sa.Column('failure_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_template_id'], ['workflow_templates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pipeline_schedules_created_at'), 'pipeline_schedules', ['created_at'], unique=False)
    op.create_index(op.f('ix_pipeline_schedules_id'), 'pipeline_schedules', ['id'], unique=False)
    op.create_index(op.f('ix_pipeline_schedules_is_deleted'), 'pipeline_schedules', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_pipeline_schedules_updated_at'), 'pipeline_schedules', ['updated_at'], unique=False)
    op.create_index(op.f('ix_pipeline_schedules_deleted_at'), 'pipeline_schedules', ['deleted_at'], unique=False)

    # Create sales_analytics table
    op.create_table('sales_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_code', sa.String(length=100), nullable=True),
        sa.Column('product_name', sa.String(length=500), nullable=True),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('platform_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('platform_product_id', sa.String(length=100), nullable=True),
        sa.Column('collection_date', sa.Date(), nullable=False),
        sa.Column('data_period_start', sa.Date(), nullable=False),
        sa.Column('data_period_end', sa.Date(), nullable=False),
        sa.Column('sales_volume', sa.Integer(), nullable=True),
        sa.Column('revenue', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('profit', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('page_views', sa.Integer(), nullable=True),
        sa.Column('unique_visitors', sa.Integer(), nullable=True),
        sa.Column('click_count', sa.Integer(), nullable=True),
        sa.Column('impression_count', sa.Integer(), nullable=True),
        sa.Column('conversion_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('view_to_cart_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('cart_to_purchase_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('wishlist_adds', sa.Integer(), nullable=True),
        sa.Column('reviews_count', sa.Integer(), nullable=True),
        sa.Column('questions_count', sa.Integer(), nullable=True),
        sa.Column('average_rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('search_ranking_avg', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('search_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('traffic_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('competitor_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('market_share', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('price_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('competitor_prices', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('price_competitiveness', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('return_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('refund_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('customer_acquisition_cost', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('lifetime_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('data_completeness', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('collection_method', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sales_analytics_created_at'), 'sales_analytics', ['created_at'], unique=False)
    op.create_index(op.f('ix_sales_analytics_id'), 'sales_analytics', ['id'], unique=False)
    op.create_index(op.f('ix_sales_analytics_is_deleted'), 'sales_analytics', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_sales_analytics_updated_at'), 'sales_analytics', ['updated_at'], unique=False)
    op.create_index(op.f('ix_sales_analytics_deleted_at'), 'sales_analytics', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_sales_analytics_product_id'), 'sales_analytics', ['product_id'], unique=False)
    op.create_index(op.f('ix_sales_analytics_marketplace'), 'sales_analytics', ['marketplace'], unique=False)
    op.create_index(op.f('ix_sales_analytics_collection_date'), 'sales_analytics', ['collection_date'], unique=False)

    # Create marketplace_sessions table
    op.create_table('marketplace_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('marketplace', sa.String(length=50), nullable=False),
        sa.Column('account_identifier', sa.String(length=100), nullable=False),
        sa.Column('session_type', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('target_date_start', sa.Date(), nullable=False),
        sa.Column('target_date_end', sa.Date(), nullable=False),
        sa.Column('target_products', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_items_target', sa.Integer(), nullable=True),
        sa.Column('total_items_collected', sa.Integer(), nullable=True),
        sa.Column('total_items_failed', sa.Integer(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('proxy_used', sa.String(length=100), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True),
        sa.Column('rate_limit_hits', sa.Integer(), nullable=True),
        sa.Column('avg_response_time', sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column('session_cookies', sa.Text(), nullable=True),
        sa.Column('session_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_marketplace_sessions_created_at'), 'marketplace_sessions', ['created_at'], unique=False)
    op.create_index(op.f('ix_marketplace_sessions_id'), 'marketplace_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_marketplace_sessions_is_deleted'), 'marketplace_sessions', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_marketplace_sessions_updated_at'), 'marketplace_sessions', ['updated_at'], unique=False)
    op.create_index(op.f('ix_marketplace_sessions_deleted_at'), 'marketplace_sessions', ['deleted_at'], unique=False)

    # Create traffic_sources table
    op.create_table('traffic_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('analytics_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('medium', sa.String(length=50), nullable=True),
        sa.Column('campaign', sa.String(length=100), nullable=True),
        sa.Column('sessions', sa.Integer(), nullable=True),
        sa.Column('users', sa.Integer(), nullable=True),
        sa.Column('page_views', sa.Integer(), nullable=True),
        sa.Column('bounces', sa.Integer(), nullable=True),
        sa.Column('transactions', sa.Integer(), nullable=True),
        sa.Column('revenue', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('bounce_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('conversion_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('avg_session_value', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['analytics_id'], ['sales_analytics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_traffic_sources_created_at'), 'traffic_sources', ['created_at'], unique=False)
    op.create_index(op.f('ix_traffic_sources_id'), 'traffic_sources', ['id'], unique=False)
    op.create_index(op.f('ix_traffic_sources_is_deleted'), 'traffic_sources', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_traffic_sources_updated_at'), 'traffic_sources', ['updated_at'], unique=False)
    op.create_index(op.f('ix_traffic_sources_deleted_at'), 'traffic_sources', ['deleted_at'], unique=False)

    # Create search_keywords table
    op.create_table('search_keywords',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('analytics_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('keyword', sa.String(length=200), nullable=False),
        sa.Column('search_volume', sa.Integer(), nullable=True),
        sa.Column('ranking_position', sa.Integer(), nullable=True),
        sa.Column('click_count', sa.Integer(), nullable=True),
        sa.Column('impression_count', sa.Integer(), nullable=True),
        sa.Column('click_through_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('conversion_count', sa.Integer(), nullable=True),
        sa.Column('conversion_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('revenue', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('keyword_type', sa.String(length=50), nullable=True),
        sa.Column('intent_type', sa.String(length=50), nullable=True),
        sa.Column('competition_level', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['analytics_id'], ['sales_analytics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_keywords_created_at'), 'search_keywords', ['created_at'], unique=False)
    op.create_index(op.f('ix_search_keywords_id'), 'search_keywords', ['id'], unique=False)
    op.create_index(op.f('ix_search_keywords_is_deleted'), 'search_keywords', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_search_keywords_updated_at'), 'search_keywords', ['updated_at'], unique=False)
    op.create_index(op.f('ix_search_keywords_deleted_at'), 'search_keywords', ['deleted_at'], unique=False)

    # Create competitor_analysis table
    op.create_table('competitor_analysis',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('analytics_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competitor_name', sa.String(length=200), nullable=False),
        sa.Column('competitor_product_id', sa.String(length=100), nullable=True),
        sa.Column('competitor_product_url', sa.String(length=1000), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('discount_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('estimated_sales', sa.Integer(), nullable=True),
        sa.Column('ranking_position', sa.Integer(), nullable=True),
        sa.Column('availability_status', sa.String(length=50), nullable=True),
        sa.Column('feature_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('content_quality_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('price_competitiveness', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('feature_competitiveness', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('overall_competitiveness', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['analytics_id'], ['sales_analytics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_competitor_analysis_created_at'), 'competitor_analysis', ['created_at'], unique=False)
    op.create_index(op.f('ix_competitor_analysis_id'), 'competitor_analysis', ['id'], unique=False)
    op.create_index(op.f('ix_competitor_analysis_is_deleted'), 'competitor_analysis', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_competitor_analysis_updated_at'), 'competitor_analysis', ['updated_at'], unique=False)
    op.create_index(op.f('ix_competitor_analysis_deleted_at'), 'competitor_analysis', ['deleted_at'], unique=False)

    # Create performance_reports table
    op.create_table('performance_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('marketplace', sa.String(length=50), nullable=True),
        sa.Column('product_category', sa.String(length=100), nullable=True),
        sa.Column('product_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_products', sa.Integer(), nullable=True),
        sa.Column('active_products', sa.Integer(), nullable=True),
        sa.Column('total_revenue', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_profit', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_cost', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_sales_volume', sa.Integer(), nullable=True),
        sa.Column('sourcing_accuracy', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('processing_effectiveness', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('registration_success_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('ai_prediction_accuracy', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('ai_processing_time_avg', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('ai_cost_per_product', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('growth_rate', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('trend_direction', sa.String(length=20), nullable=True),
        sa.Column('cost_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('profit_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('action_items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_by', sa.String(length=100), nullable=True),
        sa.Column('generation_time_seconds', sa.Integer(), nullable=True),
        sa.Column('data_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_performance_reports_created_at'), 'performance_reports', ['created_at'], unique=False)
    op.create_index(op.f('ix_performance_reports_id'), 'performance_reports', ['id'], unique=False)
    op.create_index(op.f('ix_performance_reports_is_deleted'), 'performance_reports', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_performance_reports_updated_at'), 'performance_reports', ['updated_at'], unique=False)
    op.create_index(op.f('ix_performance_reports_deleted_at'), 'performance_reports', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_performance_reports_report_date'), 'performance_reports', ['report_date'], unique=False)

    # Create data_collection_logs table
    op.create_table('data_collection_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_url', sa.String(length=1000), nullable=False),
        sa.Column('method', sa.String(length=20), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('request_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('request_data', sa.Text(), nullable=True),
        sa.Column('response_size_bytes', sa.Integer(), nullable=True),
        sa.Column('response_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('data_extracted', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('captcha_encountered', sa.Boolean(), nullable=True),
        sa.Column('rate_limited', sa.Boolean(), nullable=True),
        sa.Column('ip_blocked', sa.Boolean(), nullable=True),
        sa.Column('data_points_extracted', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['marketplace_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_collection_logs_created_at'), 'data_collection_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_data_collection_logs_id'), 'data_collection_logs', ['id'], unique=False)
    op.create_index(op.f('ix_data_collection_logs_is_deleted'), 'data_collection_logs', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_data_collection_logs_updated_at'), 'data_collection_logs', ['updated_at'], unique=False)
    op.create_index(op.f('ix_data_collection_logs_deleted_at'), 'data_collection_logs', ['deleted_at'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('data_collection_logs')
    op.drop_table('performance_reports')
    op.drop_table('competitor_analysis')
    op.drop_table('search_keywords')
    op.drop_table('traffic_sources')
    op.drop_table('marketplace_sessions')
    op.drop_table('sales_analytics')
    op.drop_table('pipeline_schedules')
    op.drop_table('pipeline_alerts')
    op.drop_table('workflow_templates')
    op.drop_table('pipeline_product_results')
    op.drop_table('pipeline_steps')
    op.drop_table('pipeline_executions')