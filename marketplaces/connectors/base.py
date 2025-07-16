"""
Base connector class for all marketplace integrations.
Provides a standardized interface for interacting with different marketplace APIs.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import logging

from django.core.exceptions import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential


logger = logging.getLogger(__name__)


class MarketplaceConnectorBase(ABC):
    """
    Abstract base class for marketplace connectors.
    All marketplace-specific connectors should inherit from this class.
    """
    
    # Connector metadata
    connector_name: str = "Base Connector"
    connector_version: str = "1.0.0"
    supported_operations: List[str] = []
    marketplace_type: str = "base"
    
    def __init__(self, marketplace):
        """
        Initialize the connector with a marketplace instance.
        
        Args:
            marketplace: Marketplace model instance
        """
        self.marketplace = marketplace
        self._credentials = None
        self._connection = None
        self._last_sync = None
        self._rate_limiter = None
    
    @property
    def credentials(self) -> Dict[str, Any]:
        """Get decrypted credentials for the marketplace."""
        if self._credentials is None:
            self._credentials = self.marketplace.get_decrypted_credentials()
        return self._credentials
    
    @abstractmethod
    def validate_credentials(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the marketplace's API credentials.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test the connection to the marketplace's API.
        
        Returns:
            Tuple of (is_connected, error_message)
        """
        pass
    
    # Listing Management
    
    @abstractmethod
    def create_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new listing on the marketplace.
        
        Args:
            listing_data: Dictionary containing listing information
            
        Returns:
            Response data with listing ID and status
        """
        pass
    
    @abstractmethod
    def update_listing(self, listing_id: str, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing listing on the marketplace.
        
        Args:
            listing_id: Marketplace listing ID
            listing_data: Updated listing information
            
        Returns:
            Response data with update status
        """
        pass
    
    @abstractmethod
    def get_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """
        Get listing details from the marketplace.
        
        Args:
            listing_id: Marketplace listing ID
            
        Returns:
            Listing data or None if not found
        """
        pass
    
    @abstractmethod
    def delete_listing(self, listing_id: str) -> bool:
        """
        Delete/end a listing on the marketplace.
        
        Args:
            listing_id: Marketplace listing ID
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def search_listings(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Search/list listings on the marketplace.
        
        Args:
            **kwargs: Search parameters (status, sku, etc.)
            
        Returns:
            List of listing dictionaries
        """
        pass
    
    # Order Management
    
    @abstractmethod
    def fetch_orders(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch orders from the marketplace.
        
        Args:
            **kwargs: Filter parameters (date range, status, etc.)
            
        Returns:
            List of order dictionaries
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific order.
        
        Args:
            order_id: Marketplace order ID
            
        Returns:
            Order details or None if not found
        """
        pass
    
    @abstractmethod
    def acknowledge_order(self, order_id: str) -> bool:
        """
        Acknowledge receipt of an order.
        
        Args:
            order_id: Marketplace order ID
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def update_order_status(self, order_id: str, status: str, **kwargs) -> bool:
        """
        Update order status on the marketplace.
        
        Args:
            order_id: Marketplace order ID
            status: New status
            **kwargs: Additional status-specific data (tracking, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def ship_order(self, order_id: str, tracking_number: str, carrier: str, 
                  ship_date: datetime = None) -> bool:
        """
        Mark order as shipped with tracking information.
        
        Args:
            order_id: Marketplace order ID
            tracking_number: Shipment tracking number
            carrier: Shipping carrier
            ship_date: Optional ship date (defaults to now)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    # Inventory Management
    
    @abstractmethod
    def update_inventory(self, sku: str, quantity: int) -> bool:
        """
        Update inventory quantity for a SKU.
        
        Args:
            sku: Marketplace SKU
            quantity: New quantity
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_inventory(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get current inventory levels for a SKU.
        
        Args:
            sku: Marketplace SKU
            
        Returns:
            Inventory data or None if not found
        """
        pass
    
    @abstractmethod
    def bulk_update_inventory(self, inventory_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update inventory for multiple SKUs.
        
        Args:
            inventory_updates: List of {sku, quantity} dictionaries
            
        Returns:
            Results dictionary with success/failure for each SKU
        """
        pass
    
    # Pricing Management
    
    @abstractmethod
    def update_price(self, sku: str, price: Decimal, 
                    sale_price: Optional[Decimal] = None) -> bool:
        """
        Update pricing for a SKU.
        
        Args:
            sku: Marketplace SKU
            price: Regular price
            sale_price: Optional sale price
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    # Category and Attributes
    
    @abstractmethod
    def get_categories(self, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get marketplace categories.
        
        Args:
            parent_id: Optional parent category ID
            
        Returns:
            List of category dictionaries
        """
        pass
    
    @abstractmethod
    def get_category_attributes(self, category_id: str) -> List[Dict[str, Any]]:
        """
        Get required/optional attributes for a category.
        
        Args:
            category_id: Marketplace category ID
            
        Returns:
            List of attribute definitions
        """
        pass
    
    # Reports and Analytics
    
    def get_sales_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get sales report for date range.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Sales report data
        """
        # Default implementation - override in specific connectors
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_sales': Decimal('0.00'),
            'order_count': 0,
            'items': []
        }
    
    # Common utility methods
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an HTTP request to the marketplace's API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        # This is a placeholder - actual implementation would use httpx or requests
        # Each connector should implement their specific request logic
        raise NotImplementedError("Subclasses must implement make_request")
    
    def log_activity(self, activity_type: str, details: Dict[str, Any], 
                    success: bool = True) -> None:
        """
        Log connector activity for monitoring and debugging.
        
        Args:
            activity_type: Type of activity (e.g., 'create_listing', 'fetch_orders')
            details: Additional details about the activity
            success: Whether the activity was successful
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'marketplace': self.marketplace.name,
            'platform': self.marketplace.platform_type,
            'connector': self.connector_name,
            'activity': activity_type,
            'success': success,
            'details': details
        }
        
        if success:
            logger.info(f"Marketplace activity: {log_entry}")
        else:
            logger.error(f"Marketplace activity failed: {log_entry}")
    
    def validate_listing_data(self, listing_data: Dict[str, Any]) -> bool:
        """
        Validate listing data before submission.
        
        Args:
            listing_data: Listing data to validate
            
        Returns:
            True if valid, raises ValidationError if not
        """
        required_fields = ['title', 'price', 'quantity']
        for field in required_fields:
            if field not in listing_data:
                raise ValidationError(f"Missing required field: {field}")
        
        if listing_data['price'] <= 0:
            raise ValidationError("Price must be greater than 0")
        
        if listing_data['quantity'] < 0:
            raise ValidationError("Quantity cannot be negative")
        
        return True
    
    def transform_order_data(self, raw_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw order data from marketplace format to standard format.
        
        Args:
            raw_order: Raw order data from marketplace API
            
        Returns:
            Standardized order dictionary
        """
        # Override in subclasses for specific transformation logic
        return raw_order
    
    def calculate_fees(self, order_amount: Decimal) -> Dict[str, Decimal]:
        """
        Calculate marketplace fees for an order.
        
        Args:
            order_amount: Order total amount
            
        Returns:
            Dictionary with fee breakdown
        """
        return self.marketplace.calculate_marketplace_fees(order_amount)
    
    def handle_rate_limit(self, response: Any) -> None:
        """
        Handle rate limiting from marketplace API.
        
        Args:
            response: API response object
        """
        # Override in subclasses to handle specific rate limit headers
        pass
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current rate limit information for the API.
        
        Returns:
            Dictionary with rate limit details
        """
        return {
            'requests_remaining': None,
            'reset_time': None,
            'limit': self.marketplace.rate_limit_requests,
            'window': self.marketplace.rate_limit_window
        }
    
    def close(self) -> None:
        """Clean up any open connections or resources."""
        if self._connection:
            # Close connection if applicable
            self._connection = None
        self._credentials = None