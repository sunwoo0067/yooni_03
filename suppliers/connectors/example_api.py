"""
Example API connector implementation.
This serves as a template for creating new supplier connectors.
"""
import httpx
from typing import Any, Dict, List, Optional, Tuple
from django.core.exceptions import ValidationError

from .base import SupplierConnectorBase


class ExampleAPIConnector(SupplierConnectorBase):
    """
    Example implementation of a supplier API connector.
    This demonstrates how to implement the abstract methods.
    """
    
    connector_name = "Example API Connector"
    connector_version = "1.0.0"
    supported_operations = [
        'fetch_products', 
        'fetch_inventory', 
        'fetch_pricing',
        'test_connection'
    ]
    
    def __init__(self, supplier):
        super().__init__(supplier)
        self.base_url = supplier.api_base_url or "https://api.example.com"
        self.timeout = supplier.connection_settings.get('timeout', 30)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        # Add authentication headers based on credentials
        if self.credentials:
            if 'api_key' in self.credentials:
                headers['X-API-Key'] = self.credentials['api_key']
            elif 'bearer_token' in self.credentials:
                headers['Authorization'] = f"Bearer {self.credentials['bearer_token']}"
        
        # Add any custom headers from connection settings
        custom_headers = self.supplier.connection_settings.get('headers', {})
        headers.update(custom_headers)
        
        return headers
    
    def validate_credentials(self) -> Tuple[bool, Optional[str]]:
        """Validate the supplier's API credentials."""
        if not self.credentials:
            return False, "No credentials configured"
        
        required_fields = ['api_key']  # Or whatever fields this API requires
        missing_fields = [field for field in required_fields if field not in self.credentials]
        
        if missing_fields:
            return False, f"Missing required credential fields: {', '.join(missing_fields)}"
        
        return True, None
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the supplier's API."""
        # First validate credentials
        is_valid, error_msg = self.validate_credentials()
        if not is_valid:
            return False, error_msg
        
        try:
            # Make a simple API call to test connectivity
            with httpx.Client() as client:
                response = client.get(
                    f"{self.base_url}/health",  # Or whatever endpoint tests connectivity
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    self.log_activity('test_connection', {'status': 'success'})
                    return True, None
                else:
                    error = f"API returned status code: {response.status_code}"
                    self.log_activity('test_connection', {'error': error}, success=False)
                    return False, error
                    
        except httpx.TimeoutException:
            error = "Connection timeout"
            self.log_activity('test_connection', {'error': error}, success=False)
            return False, error
        except Exception as e:
            error = f"Connection error: {str(e)}"
            self.log_activity('test_connection', {'error': error}, success=False)
            return False, error
    
    def fetch_products(self, page: int = 1, per_page: int = 100, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from the supplier.
        
        Args:
            page: Page number for pagination
            per_page: Number of products per page
            **kwargs: Additional filtering parameters
            
        Returns:
            List of product dictionaries
        """
        endpoint = f"{self.base_url}/products"
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    endpoint,
                    headers=self._get_headers(),
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                products = data.get('products', [])
                
                # Transform each product to our standard format
                transformed_products = [
                    self.transform_product_data(product) 
                    for product in products
                ]
                
                self.log_activity(
                    'fetch_products', 
                    {'count': len(transformed_products), 'page': page}
                )
                
                return transformed_products
                
        except Exception as e:
            self.log_activity(
                'fetch_products', 
                {'error': str(e), 'page': page}, 
                success=False
            )
            raise
    
    def fetch_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific product."""
        endpoint = f"{self.base_url}/products/{product_id}"
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    endpoint,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                product_data = response.json()
                
                return self.transform_product_data(product_data)
                
        except Exception as e:
            self.log_activity(
                'fetch_product_details', 
                {'error': str(e), 'product_id': product_id}, 
                success=False
            )
            raise
    
    def fetch_inventory(self, product_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch inventory levels for products."""
        endpoint = f"{self.base_url}/inventory"
        
        try:
            params = {}
            if product_ids:
                params['product_ids'] = ','.join(product_ids)
            
            with httpx.Client() as client:
                response = client.get(
                    endpoint,
                    headers=self._get_headers(),
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                inventory_data = response.json()
                
                # Transform to standard format: {product_id: {quantity: X, ...}}
                inventory_map = {}
                for item in inventory_data.get('inventory', []):
                    inventory_map[item['product_id']] = {
                        'quantity': item.get('quantity', 0),
                        'available': item.get('available', 0),
                        'reserved': item.get('reserved', 0),
                        'warehouse': item.get('warehouse', 'default')
                    }
                
                self.log_activity(
                    'fetch_inventory', 
                    {'product_count': len(inventory_map)}
                )
                
                return inventory_map
                
        except Exception as e:
            self.log_activity(
                'fetch_inventory', 
                {'error': str(e)}, 
                success=False
            )
            raise
    
    def fetch_pricing(self, product_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch pricing information for products."""
        endpoint = f"{self.base_url}/pricing"
        
        try:
            params = {}
            if product_ids:
                params['product_ids'] = ','.join(product_ids)
            
            with httpx.Client() as client:
                response = client.get(
                    endpoint,
                    headers=self._get_headers(),
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                pricing_data = response.json()
                
                # Transform to standard format: {product_id: {price: X, ...}}
                pricing_map = {}
                for item in pricing_data.get('prices', []):
                    pricing_map[item['product_id']] = {
                        'cost_price': item.get('cost', 0),
                        'msrp': item.get('msrp', 0),
                        'map': item.get('map'),  # Minimum advertised price
                        'currency': item.get('currency', 'USD'),
                        'tier_pricing': item.get('tier_pricing', [])
                    }
                
                self.log_activity(
                    'fetch_pricing', 
                    {'product_count': len(pricing_map)}
                )
                
                return pricing_map
                
        except Exception as e:
            self.log_activity(
                'fetch_pricing', 
                {'error': str(e)}, 
                success=False
            )
            raise
    
    def transform_product_data(self, raw_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw product data from supplier format to standard format.
        
        This method maps supplier-specific field names to our standard fields.
        """
        return {
            'supplier_sku': raw_product.get('id', ''),
            'name': raw_product.get('title', ''),
            'description': raw_product.get('description', ''),
            'category': raw_product.get('category', ''),
            'subcategory': raw_product.get('subcategory', ''),
            'brand': raw_product.get('brand', ''),
            'price': float(raw_product.get('price', 0)),
            'msrp': float(raw_product.get('msrp', 0)),
            'quantity': int(raw_product.get('stock', 0)),
            'min_order_qty': int(raw_product.get('min_order_quantity', 1)),
            'weight': float(raw_product.get('weight', 0)),
            'dimensions': {
                'length': raw_product.get('length'),
                'width': raw_product.get('width'),
                'height': raw_product.get('height'),
                'unit': 'cm'
            },
            'images': raw_product.get('images', []),
            'attributes': raw_product.get('attributes', {}),
            'raw_data': raw_product  # Keep original data for reference
        }