"""
Test fixtures and data factories for dropshipping tests
"""

from .product_fixtures import *
from .user_fixtures import *
from .order_fixtures import *
from .external_api_fixtures import *

__all__ = [
    # Product fixtures
    'sample_product_data',
    'sample_collected_products',
    'product_categories',
    'product_variants',
    
    # User fixtures  
    'sample_user_data',
    'admin_user_data',
    'platform_account_data',
    
    # Order fixtures
    'sample_order_data',
    'order_items_data',
    'shipping_addresses',
    
    # External API fixtures
    'wholesaler_responses',
    'marketplace_responses',
    'ai_service_responses'
]