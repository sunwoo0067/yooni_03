"""
Factory for creating marketplace connector instances.
"""
from typing import TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from ..models import Marketplace
    from .base import MarketplaceConnectorBase


# Registry of available connectors
CONNECTOR_REGISTRY = {
    # Add marketplace connectors here as they are implemented
    # 'amazon': 'marketplaces.connectors.amazon.AmazonConnector',
    # 'ebay': 'marketplaces.connectors.ebay.EbayConnector',
    # 'shopify': 'marketplaces.connectors.shopify.ShopifyConnector',
}


def create_connector(marketplace: 'Marketplace') -> 'MarketplaceConnectorBase':
    """
    Create a connector instance for the given marketplace.
    
    Args:
        marketplace: Marketplace model instance
        
    Returns:
        Connector instance
        
    Raises:
        ImproperlyConfigured: If connector is not found or cannot be imported
    """
    platform_type = marketplace.platform_type
    
    if platform_type not in CONNECTOR_REGISTRY:
        # For now, return a mock connector for platforms not yet implemented
        from .example import ExampleMarketplaceConnector
        return ExampleMarketplaceConnector(marketplace)
    
    connector_path = CONNECTOR_REGISTRY[platform_type]
    
    try:
        # Dynamic import of the connector class
        module_path, class_name = connector_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        connector_class = getattr(module, class_name)
        
        return connector_class(marketplace)
    except (ImportError, AttributeError) as e:
        raise ImproperlyConfigured(
            f"Could not import connector '{connector_path}' for "
            f"platform '{platform_type}': {str(e)}"
        )


def get_available_connectors() -> dict:
    """
    Get list of available marketplace connectors.
    
    Returns:
        Dictionary mapping platform types to connector information
    """
    available = {}
    
    for platform_type, connector_path in CONNECTOR_REGISTRY.items():
        try:
            module_path, class_name = connector_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            connector_class = getattr(module, class_name)
            
            available[platform_type] = {
                'name': connector_class.connector_name,
                'version': connector_class.connector_version,
                'operations': connector_class.supported_operations,
            }
        except Exception:
            # Skip connectors that can't be imported
            pass
    
    return available