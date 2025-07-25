"""Add dropshipping tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create outofstock_history table
    op.create_table('outofstock_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('wholesaler_id', sa.Integer(), nullable=False),
        sa.Column('out_of_stock_time', sa.DateTime(), nullable=False),
        sa.Column('restock_time', sa.DateTime(), nullable=True),
        sa.Column('duration_hours', sa.Float(), nullable=True),
        sa.Column('action_taken', sa.String(length=50), nullable=True),
        sa.Column('alternative_suggested', sa.Boolean(), nullable=True),
        sa.Column('estimated_lost_sales', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['wholesaler_id'], ['wholesaler_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outofstock_history_id'), 'outofstock_history', ['id'], unique=False)
    op.create_index(op.f('ix_outofstock_history_product_id'), 'outofstock_history', ['product_id'], unique=False)

    # Create supplier_reliability table
    op.create_table('supplier_reliability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('outofstock_rate', sa.Float(), nullable=True),
        sa.Column('avg_outofstock_duration', sa.Float(), nullable=True),
        sa.Column('response_time_avg', sa.Float(), nullable=True),
        sa.Column('restock_speed_avg', sa.Float(), nullable=True),
        sa.Column('price_stability', sa.Float(), nullable=True),
        sa.Column('reliability_score', sa.Float(), nullable=True),
        sa.Column('grade', sa.String(length=20), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('last_analyzed', sa.DateTime(), nullable=True),
        sa.Column('analysis_period_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['wholesaler_accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_id')
    )
    op.create_index(op.f('ix_supplier_reliability_id'), 'supplier_reliability', ['id'], unique=False)
    op.create_index(op.f('ix_supplier_reliability_supplier_id'), 'supplier_reliability', ['supplier_id'], unique=True)

    # Create restock_history table
    op.create_table('restock_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('previous_stock', sa.Integer(), nullable=True),
        sa.Column('current_stock', sa.Integer(), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('wholesale_price_before', sa.Float(), nullable=True),
        sa.Column('wholesale_price_after', sa.Float(), nullable=True),
        sa.Column('price_change_rate', sa.Float(), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('auto_reactivated', sa.Boolean(), nullable=True),
        sa.Column('review_required', sa.Boolean(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_restock_history_id'), 'restock_history', ['id'], unique=False)
    op.create_index(op.f('ix_restock_history_product_id'), 'restock_history', ['product_id'], unique=False)

    # Create stock_check_log table
    op.create_table('stock_check_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('wholesaler_id', sa.Integer(), nullable=False),
        sa.Column('previous_stock', sa.Integer(), nullable=True),
        sa.Column('current_stock', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('status_changed', sa.Boolean(), nullable=True),
        sa.Column('check_time', sa.DateTime(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['wholesaler_id'], ['wholesaler_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_check_log_id'), 'stock_check_log', ['id'], unique=False)
    op.create_index(op.f('ix_stock_check_log_product_id'), 'stock_check_log', ['product_id'], unique=False)

    # Create price_history table
    op.create_table('price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('wholesaler_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('price_type', sa.String(length=20), nullable=True),
        sa.Column('previous_price', sa.Float(), nullable=True),
        sa.Column('change_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('recorded_by', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['wholesaler_id'], ['wholesaler_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_history_id'), 'price_history', ['id'], unique=False)
    op.create_index(op.f('ix_price_history_product_id'), 'price_history', ['product_id'], unique=False)

    # Create profit_protection_log table
    op.create_table('profit_protection_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('current_margin', sa.Float(), nullable=False),
        sa.Column('target_margin', sa.Float(), nullable=False),
        sa.Column('margin_gap', sa.Float(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('competitor_price_avg', sa.Float(), nullable=True),
        sa.Column('market_position', sa.String(length=20), nullable=True),
        sa.Column('recommended_action', sa.Text(), nullable=True),
        sa.Column('action_taken', sa.Boolean(), nullable=True),
        sa.Column('estimated_loss_per_day', sa.Float(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_profit_protection_log_id'), 'profit_protection_log', ['id'], unique=False)
    op.create_index(op.f('ix_profit_protection_log_product_id'), 'profit_protection_log', ['product_id'], unique=False)

    # Create stockout_prediction_history table
    op.create_table('stockout_prediction_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('current_stock', sa.Integer(), nullable=False),
        sa.Column('predicted_stockout_date', sa.DateTime(), nullable=True),
        sa.Column('days_until_stockout', sa.Integer(), nullable=True),
        sa.Column('confidence_level', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('predicted_by', sa.String(length=100), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('factors', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('predicted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stockout_prediction_history_id'), 'stockout_prediction_history', ['id'], unique=False)
    op.create_index(op.f('ix_stockout_prediction_history_product_id'), 'stockout_prediction_history', ['product_id'], unique=False)

    # Create demand_analysis_history table
    op.create_table('demand_analysis_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('demand_score', sa.Float(), nullable=True),
        sa.Column('trend', sa.String(length=20), nullable=False),
        sa.Column('weekly_pattern', sa.Text(), nullable=True),
        sa.Column('monthly_pattern', sa.Text(), nullable=True),
        sa.Column('seasonal_index', sa.Float(), nullable=True),
        sa.Column('price_elasticity', sa.Float(), nullable=True),
        sa.Column('demand_volatility', sa.Float(), nullable=True),
        sa.Column('growth_rate', sa.Float(), nullable=True),
        sa.Column('peak_demand_period', sa.String(length=50), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.Column('analysis_period_days', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_demand_analysis_history_id'), 'demand_analysis_history', ['id'], unique=False)
    op.create_index(op.f('ix_demand_analysis_history_product_id'), 'demand_analysis_history', ['product_id'], unique=False)

    # Create automation_rules table
    op.create_table('automation_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('condition', sa.Text(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=True),
        sa.Column('last_executed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_id')
    )
    op.create_index(op.f('ix_automation_rules_id'), 'automation_rules', ['id'], unique=False)
    op.create_index(op.f('ix_automation_rules_rule_id'), 'automation_rules', ['rule_id'], unique=True)

    # Create automation_executions table
    op.create_table('automation_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.String(length=50), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('action_taken', sa.String(length=50), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['rule_id'], ['automation_rules.rule_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_executions_id'), 'automation_executions', ['id'], unique=False)
    op.create_index(op.f('ix_automation_executions_product_id'), 'automation_executions', ['product_id'], unique=False)
    op.create_index(op.f('ix_automation_executions_rule_id'), 'automation_executions', ['rule_id'], unique=False)

    # Create alternative_recommendations table
    op.create_table('alternative_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_product_id', sa.Integer(), nullable=False),
        sa.Column('alternative_product_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('alternative_type', sa.String(length=30), nullable=False),
        sa.Column('recommendation_reason', sa.Text(), nullable=True),
        sa.Column('click_count', sa.Integer(), nullable=True),
        sa.Column('conversion_count', sa.Integer(), nullable=True),
        sa.Column('conversion_rate', sa.Float(), nullable=True),
        sa.Column('recommended_at', sa.DateTime(), nullable=True),
        sa.Column('last_clicked', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['alternative_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['original_product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alternative_recommendations_id'), 'alternative_recommendations', ['id'], unique=False)
    op.create_index(op.f('ix_alternative_recommendations_original_product_id'), 'alternative_recommendations', ['original_product_id'], unique=False)

    # Create dropshipping_settings table
    op.create_table('dropshipping_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('monitoring_enabled', sa.Boolean(), nullable=True),
        sa.Column('check_interval_seconds', sa.Integer(), nullable=True),
        sa.Column('low_stock_threshold', sa.Integer(), nullable=True),
        sa.Column('automation_enabled', sa.Boolean(), nullable=True),
        sa.Column('auto_deactivate_on_stockout', sa.Boolean(), nullable=True),
        sa.Column('auto_reactivate_on_restock', sa.Boolean(), nullable=True),
        sa.Column('price_change_threshold', sa.Float(), nullable=True),
        sa.Column('profit_protection_enabled', sa.Boolean(), nullable=True),
        sa.Column('min_margin_rate', sa.Float(), nullable=True),
        sa.Column('target_margin_rate', sa.Float(), nullable=True),
        sa.Column('max_price_adjustment', sa.Float(), nullable=True),
        sa.Column('prediction_enabled', sa.Boolean(), nullable=True),
        sa.Column('prediction_horizon_days', sa.Integer(), nullable=True),
        sa.Column('high_risk_threshold_days', sa.Integer(), nullable=True),
        sa.Column('notification_enabled', sa.Boolean(), nullable=True),
        sa.Column('email_notifications', sa.Boolean(), nullable=True),
        sa.Column('slack_notifications', sa.Boolean(), nullable=True),
        sa.Column('critical_alerts_only', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dropshipping_settings_id'), 'dropshipping_settings', ['id'], unique=False)

    # Add dropshipping columns to products table
    op.add_column('products', sa.Column('is_dropshipping', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('products', sa.Column('wholesaler_id', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('wholesaler_product_id', sa.String(length=100), nullable=True))
    op.add_column('products', sa.Column('selling_price', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('products', sa.Column('deactivated_at', sa.DateTime(), nullable=True))
    op.add_column('products', sa.Column('reactivated_at', sa.DateTime(), nullable=True))
    op.add_column('products', sa.Column('price_updated_at', sa.DateTime(), nullable=True))
    
    # Create indexes for new product columns
    op.create_index(op.f('ix_products_is_dropshipping'), 'products', ['is_dropshipping'], unique=False)
    op.create_index(op.f('ix_products_wholesaler_id'), 'products', ['wholesaler_id'], unique=False)
    op.create_index(op.f('ix_products_wholesaler_product_id'), 'products', ['wholesaler_product_id'], unique=False)
    
    # Create foreign key constraint for wholesaler_id
    op.create_foreign_key(None, 'products', 'wholesaler_accounts', ['wholesaler_id'], ['id'])


def downgrade():
    # Drop foreign key and indexes from products table
    op.drop_constraint(None, 'products', type_='foreignkey')
    op.drop_index(op.f('ix_products_wholesaler_product_id'), table_name='products')
    op.drop_index(op.f('ix_products_wholesaler_id'), table_name='products')
    op.drop_index(op.f('ix_products_is_dropshipping'), table_name='products')
    
    # Drop columns from products table
    op.drop_column('products', 'price_updated_at')
    op.drop_column('products', 'reactivated_at')
    op.drop_column('products', 'deactivated_at')
    op.drop_column('products', 'selling_price')
    op.drop_column('products', 'wholesaler_product_id')
    op.drop_column('products', 'wholesaler_id')
    op.drop_column('products', 'is_dropshipping')

    # Drop all dropshipping tables
    op.drop_index(op.f('ix_dropshipping_settings_id'), table_name='dropshipping_settings')
    op.drop_table('dropshipping_settings')
    
    op.drop_index(op.f('ix_alternative_recommendations_original_product_id'), table_name='alternative_recommendations')
    op.drop_index(op.f('ix_alternative_recommendations_id'), table_name='alternative_recommendations')
    op.drop_table('alternative_recommendations')
    
    op.drop_index(op.f('ix_automation_executions_rule_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_product_id'), table_name='automation_executions')
    op.drop_index(op.f('ix_automation_executions_id'), table_name='automation_executions')
    op.drop_table('automation_executions')
    
    op.drop_index(op.f('ix_automation_rules_rule_id'), table_name='automation_rules')
    op.drop_index(op.f('ix_automation_rules_id'), table_name='automation_rules')
    op.drop_table('automation_rules')
    
    op.drop_index(op.f('ix_demand_analysis_history_product_id'), table_name='demand_analysis_history')
    op.drop_index(op.f('ix_demand_analysis_history_id'), table_name='demand_analysis_history')
    op.drop_table('demand_analysis_history')
    
    op.drop_index(op.f('ix_stockout_prediction_history_product_id'), table_name='stockout_prediction_history')
    op.drop_index(op.f('ix_stockout_prediction_history_id'), table_name='stockout_prediction_history')
    op.drop_table('stockout_prediction_history')
    
    op.drop_index(op.f('ix_profit_protection_log_product_id'), table_name='profit_protection_log')
    op.drop_index(op.f('ix_profit_protection_log_id'), table_name='profit_protection_log')
    op.drop_table('profit_protection_log')
    
    op.drop_index(op.f('ix_price_history_product_id'), table_name='price_history')
    op.drop_index(op.f('ix_price_history_id'), table_name='price_history')
    op.drop_table('price_history')
    
    op.drop_index(op.f('ix_stock_check_log_product_id'), table_name='stock_check_log')
    op.drop_index(op.f('ix_stock_check_log_id'), table_name='stock_check_log')
    op.drop_table('stock_check_log')
    
    op.drop_index(op.f('ix_restock_history_product_id'), table_name='restock_history')
    op.drop_index(op.f('ix_restock_history_id'), table_name='restock_history')
    op.drop_table('restock_history')
    
    op.drop_index(op.f('ix_supplier_reliability_supplier_id'), table_name='supplier_reliability')
    op.drop_index(op.f('ix_supplier_reliability_id'), table_name='supplier_reliability')
    op.drop_table('supplier_reliability')
    
    op.drop_index(op.f('ix_outofstock_history_product_id'), table_name='outofstock_history')
    op.drop_index(op.f('ix_outofstock_history_id'), table_name='outofstock_history')
    op.drop_table('outofstock_history')