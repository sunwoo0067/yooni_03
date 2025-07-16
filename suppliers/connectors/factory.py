"""
Factory for creating supplier connector instances.
"""
from typing import Dict, Type, Optional

from django.core.exceptions import ImproperlyConfigured

from .base import SupplierConnectorBase
from .example_api import ExampleAPIConnector


# Registry of available connectors
CONNECTOR_REGISTRY: Dict[str, Type[SupplierConnectorBase]] = {
    'example_api': ExampleAPIConnector,
    # Add more connectors here as they are implemented:
    # 'shopify': ShopifyConnector,
    # 'woocommerce': WooCommerceConnector,
    # 'magento': MagentoConnector,
    # 'custom_api': CustomAPIConnector,
}


def get_connector_class(connector_type: str) -> Optional[Type[SupplierConnectorBase]]:
    """
    Get the connector class for a given connector type.
    
    Args:
        connector_type: The type identifier for the connector
        
    Returns:
        The connector class or None if not found
    """
    return CONNECTOR_REGISTRY.get(connector_type)


def create_connector(supplier) -> SupplierConnectorBase:
    """
    Create a connector instance for a supplier.
    
    Args:
        supplier: Supplier model instance
        
    Returns:
        Configured connector instance
        
    Raises:
        ImproperlyConfigured: If connector type is not registered
    """
    # Get connector type from supplier or use a mapping based on other fields
    connector_type = _determine_connector_type(supplier)
    
    connector_class = get_connector_class(connector_type)
    if not connector_class:
        raise ImproperlyConfigured(
            f"No connector registered for type: {connector_type}. "
            f"Available types: {', '.join(CONNECTOR_REGISTRY.keys())}"
        )
    
    return connector_class(supplier)


def _determine_connector_type(supplier) -> str:
    """
    Determine the connector type for a supplier.
    
    This can be based on various supplier attributes like:
    - A specific connector_class field
    - The API base URL pattern
    - The supplier code/name
    
    Args:
        supplier: Supplier model instance
        
    Returns:
        Connector type identifier
    """
    # First check if supplier has a specific connector class attribute
    if hasattr(supplier, 'connector_class') and supplier.connector_class:
        return supplier.connector_class
    
    # Check connection settings for connector type
    if supplier.connection_settings.get('connector_type'):
        return supplier.connection_settings['connector_type']
    
    # Map based on known supplier codes or patterns
    supplier_code_mapping = {
        'example': 'example_api',
        # Add more mappings as needed
    }
    
    if supplier.code in supplier_code_mapping:
        return supplier_code_mapping[supplier.code]
    
    # Default to example_api for now
    # In production, this might raise an exception or use a generic connector
    return 'example_api'


def register_connector(connector_type: str, connector_class: Type[SupplierConnectorBase]) -> None:
    """
    Register a new connector type.
    
    Args:
        connector_type: Unique identifier for the connector
        connector_class: The connector class to register
    """
    if not issubclass(connector_class, SupplierConnectorBase):
        raise ValueError(
            f"Connector class must inherit from SupplierConnectorBase, "
            f"got {connector_class.__name__}"
        )
    
    CONNECTOR_REGISTRY[connector_type] = connector_class


def list_available_connectors() -> Dict[str, Dict[str, str]]:
    """
    List all available connectors with their metadata.
    
    Returns:
        Dictionary of connector information
    """
    connectors = {}
    for conn_type, conn_class in CONNECTOR_REGISTRY.items():
        connectors[conn_type] = {
            'name': conn_class.connector_name,
            'version': conn_class.connector_version,
            'operations': conn_class.supported_operations,
            'class': f"{conn_class.__module__}.{conn_class.__name__}"
        }
    return connectors