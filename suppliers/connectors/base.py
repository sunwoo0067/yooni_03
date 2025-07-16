"""
Base connector class for all supplier integrations.
Provides a standardized interface for interacting with different supplier APIs.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import logging

from django.core.exceptions import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential


logger = logging.getLogger(__name__)


class SupplierConnectorBase(ABC):
    """
    Abstract base class for supplier connectors.
    All supplier-specific connectors should inherit from this class.
    """
    
    # Connector metadata
    connector_name: str = "Base Connector"
    connector_version: str = "1.0.0"
    supported_operations: List[str] = []
    
    def __init__(self, supplier):
        """
        Initialize the connector with a supplier instance.
        
        Args:
            supplier: Supplier model instance
        """
        self.supplier = supplier
        self._credentials = None
        self._connection = None
        self._last_sync = None
    
    @property
    def credentials(self) -> Dict[str, Any]:
        """Get decrypted credentials for the supplier."""
        if self._credentials is None:
            self._credentials = self.supplier.get_decrypted_credentials()
        return self._credentials
    
    @abstractmethod
    def validate_credentials(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the supplier's API credentials.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test the connection to the supplier's API.
        
        Returns:
            Tuple of (is_connected, error_message)
        """
        pass
    
    @abstractmethod
    def fetch_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch products from the supplier.
        
        Args:
            **kwargs: Additional parameters for filtering/pagination
            
        Returns:
            List of product dictionaries
        """
        pass
    
    @abstractmethod
    def fetch_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific product.
        
        Args:
            product_id: Supplier's product identifier
            
        Returns:
            Product details dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def fetch_inventory(self, product_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch inventory levels for products.
        
        Args:
            product_ids: Optional list of product IDs to fetch inventory for
            
        Returns:
            Dictionary mapping product IDs to inventory data
        """
        pass
    
    @abstractmethod
    def fetch_pricing(self, product_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch pricing information for products.
        
        Args:
            product_ids: Optional list of product IDs to fetch pricing for
            
        Returns:
            Dictionary mapping product IDs to pricing data
        """
        pass
    
    # Common utility methods
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an HTTP request to the supplier's API with retry logic.
        
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
            activity_type: Type of activity (e.g., 'fetch_products', 'test_connection')
            details: Additional details about the activity
            success: Whether the activity was successful
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'supplier': self.supplier.name,
            'connector': self.connector_name,
            'activity': activity_type,
            'success': success,
            'details': details
        }
        
        if success:
            logger.info(f"Supplier activity: {log_entry}")
        else:
            logger.error(f"Supplier activity failed: {log_entry}")
    
    def validate_response(self, response: Any) -> bool:
        """
        Validate API response format.
        
        Args:
            response: API response to validate
            
        Returns:
            True if valid, raises ValidationError if not
        """
        # Override in subclasses for specific validation
        return True
    
    def transform_product_data(self, raw_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw product data from supplier format to standard format.
        
        Args:
            raw_product: Raw product data from supplier API
            
        Returns:
            Standardized product dictionary
        """
        # Override in subclasses for specific transformation logic
        return raw_product
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current rate limit information for the API.
        
        Returns:
            Dictionary with rate limit details
        """
        return {
            'requests_remaining': None,
            'reset_time': None,
            'limit': None
        }
    
    def close(self) -> None:
        """Clean up any open connections or resources."""
        if self._connection:
            # Close connection if applicable
            self._connection = None
        self._credentials = None