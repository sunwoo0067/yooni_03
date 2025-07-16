"""
Example marketplace connector for testing and development.
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import random
import uuid

from .base import MarketplaceConnectorBase


class ExampleMarketplaceConnector(MarketplaceConnectorBase):
    """
    Example connector implementation for testing marketplace integration.
    This simulates a marketplace API without making actual HTTP requests.
    """
    
    connector_name = "Example Marketplace Connector"
    connector_version = "1.0.0"
    supported_operations = [
        'listings', 'orders', 'inventory', 'pricing', 'categories'
    ]
    marketplace_type = "example"
    
    def __init__(self, marketplace):
        super().__init__(marketplace)
        # Simulate in-memory storage for testing
        self._listings = {}
        self._orders = {}
        self._inventory = {}
    
    def validate_credentials(self) -> Tuple[bool, Optional[str]]:
        """Validate the marketplace's API credentials."""
        if not self.credentials:
            return False, "No credentials configured"
        
        # Check for required fields in credentials
        required_fields = ['api_key', 'api_secret']
        for field in required_fields:
            if field not in self.credentials:
                return False, f"Missing required credential: {field}"
        
        # Simulate credential validation
        if self.credentials.get('api_key') == 'invalid':
            return False, "Invalid API key"
        
        return True, None
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test the connection to the marketplace's API."""
        # First validate credentials
        is_valid, error = self.validate_credentials()
        if not is_valid:
            return False, error
        
        # Simulate connection test
        if self.marketplace.api_base_url == 'http://error.example.com':
            return False, "Connection failed: Unable to reach API"
        
        self.log_activity('test_connection', {'status': 'success'})
        return True, None
    
    # Listing Management
    
    def create_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new listing on the marketplace."""
        self.validate_listing_data(listing_data)
        
        # Generate a fake listing ID
        listing_id = f"LISTING-{uuid.uuid4().hex[:8].upper()}"
        
        # Store the listing
        self._listings[listing_id] = {
            'id': listing_id,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            **listing_data
        }
        
        self.log_activity('create_listing', {
            'listing_id': listing_id,
            'title': listing_data.get('title')
        })
        
        return {
            'success': True,
            'listing_id': listing_id,
            'url': f"https://example-marketplace.com/listing/{listing_id}"
        }
    
    def update_listing(self, listing_id: str, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing listing on the marketplace."""
        if listing_id not in self._listings:
            return {
                'success': False,
                'error': 'Listing not found'
            }
        
        # Update the listing
        self._listings[listing_id].update(listing_data)
        self._listings[listing_id]['updated_at'] = datetime.utcnow().isoformat()
        
        self.log_activity('update_listing', {
            'listing_id': listing_id,
            'fields_updated': list(listing_data.keys())
        })
        
        return {
            'success': True,
            'listing_id': listing_id
        }
    
    def get_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get listing details from the marketplace."""
        return self._listings.get(listing_id)
    
    def delete_listing(self, listing_id: str) -> bool:
        """Delete/end a listing on the marketplace."""
        if listing_id in self._listings:
            self._listings[listing_id]['status'] = 'ended'
            self._listings[listing_id]['ended_at'] = datetime.utcnow().isoformat()
            return True
        return False
    
    def search_listings(self, **kwargs) -> List[Dict[str, Any]]:
        """Search/list listings on the marketplace."""
        results = []
        status_filter = kwargs.get('status', 'active')
        
        for listing in self._listings.values():
            if listing.get('status') == status_filter:
                results.append(listing)
        
        return results
    
    # Order Management
    
    def fetch_orders(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch orders from the marketplace."""
        # Generate some fake orders for testing
        orders = []
        
        for i in range(random.randint(0, 5)):
            order_id = f"ORDER-{uuid.uuid4().hex[:8].upper()}"
            order = {
                'order_id': order_id,
                'status': random.choice(['pending', 'processing', 'shipped']),
                'customer': {
                    'name': f'Customer {i+1}',
                    'email': f'customer{i+1}@example.com'
                },
                'total': Decimal(random.uniform(10, 500)).quantize(Decimal('0.01')),
                'items': [
                    {
                        'sku': f'SKU-{random.randint(1000, 9999)}',
                        'quantity': random.randint(1, 5),
                        'price': Decimal(random.uniform(5, 100)).quantize(Decimal('0.01'))
                    }
                ],
                'created_at': datetime.utcnow().isoformat()
            }
            self._orders[order_id] = order
            orders.append(order)
        
        return orders
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific order."""
        return self._orders.get(order_id)
    
    def acknowledge_order(self, order_id: str) -> bool:
        """Acknowledge receipt of an order."""
        if order_id in self._orders:
            self._orders[order_id]['acknowledged'] = True
            self._orders[order_id]['acknowledged_at'] = datetime.utcnow().isoformat()
            return True
        return False
    
    def update_order_status(self, order_id: str, status: str, **kwargs) -> bool:
        """Update order status on the marketplace."""
        if order_id in self._orders:
            self._orders[order_id]['status'] = status
            self._orders[order_id]['status_updated_at'] = datetime.utcnow().isoformat()
            return True
        return False
    
    def ship_order(self, order_id: str, tracking_number: str, carrier: str, 
                  ship_date: datetime = None) -> bool:
        """Mark order as shipped with tracking information."""
        if order_id in self._orders:
            self._orders[order_id].update({
                'status': 'shipped',
                'tracking_number': tracking_number,
                'carrier': carrier,
                'ship_date': (ship_date or datetime.utcnow()).isoformat()
            })
            return True
        return False
    
    # Inventory Management
    
    def update_inventory(self, sku: str, quantity: int) -> bool:
        """Update inventory quantity for a SKU."""
        self._inventory[sku] = {
            'sku': sku,
            'quantity': quantity,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        self.log_activity('update_inventory', {
            'sku': sku,
            'quantity': quantity
        })
        
        return True
    
    def get_inventory(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get current inventory levels for a SKU."""
        return self._inventory.get(sku)
    
    def bulk_update_inventory(self, inventory_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update inventory for multiple SKUs."""
        results = {
            'success': [],
            'failed': []
        }
        
        for update in inventory_updates:
            sku = update.get('sku')
            quantity = update.get('quantity', 0)
            
            if sku and isinstance(quantity, int) and quantity >= 0:
                self._inventory[sku] = {
                    'sku': sku,
                    'quantity': quantity,
                    'updated_at': datetime.utcnow().isoformat()
                }
                results['success'].append(sku)
            else:
                results['failed'].append({
                    'sku': sku,
                    'error': 'Invalid data'
                })
        
        return results
    
    # Pricing Management
    
    def update_price(self, sku: str, price: Decimal, 
                    sale_price: Optional[Decimal] = None) -> bool:
        """Update pricing for a SKU."""
        # Find listing with this SKU and update price
        for listing in self._listings.values():
            if listing.get('sku') == sku:
                listing['price'] = float(price)
                if sale_price is not None:
                    listing['sale_price'] = float(sale_price)
                listing['price_updated_at'] = datetime.utcnow().isoformat()
                return True
        return False
    
    # Category and Attributes
    
    def get_categories(self, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get marketplace categories."""
        # Return some example categories
        categories = [
            {'id': '1', 'name': 'Electronics', 'parent_id': None},
            {'id': '2', 'name': 'Clothing', 'parent_id': None},
            {'id': '3', 'name': 'Home & Garden', 'parent_id': None},
            {'id': '11', 'name': 'Computers', 'parent_id': '1'},
            {'id': '12', 'name': 'Mobile Phones', 'parent_id': '1'},
        ]
        
        if parent_id:
            return [c for c in categories if c['parent_id'] == parent_id]
        else:
            return [c for c in categories if c['parent_id'] is None]
    
    def get_category_attributes(self, category_id: str) -> List[Dict[str, Any]]:
        """Get required/optional attributes for a category."""
        # Return example attributes based on category
        if category_id == '12':  # Mobile Phones
            return [
                {
                    'name': 'brand',
                    'type': 'text',
                    'required': True,
                    'values': ['Apple', 'Samsung', 'Google', 'Other']
                },
                {
                    'name': 'storage',
                    'type': 'select',
                    'required': True,
                    'values': ['64GB', '128GB', '256GB', '512GB']
                },
                {
                    'name': 'color',
                    'type': 'text',
                    'required': False
                }
            ]
        
        # Default attributes for other categories
        return [
            {
                'name': 'brand',
                'type': 'text',
                'required': False
            },
            {
                'name': 'condition',
                'type': 'select',
                'required': True,
                'values': ['New', 'Used', 'Refurbished']
            }
        ]