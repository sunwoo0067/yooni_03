"""Coupang Partners API integration service."""

import time
import hmac
import hashlib
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.platform_account import PlatformType


class CoupangAPI:
    """Coupang Partners API client."""
    
    BASE_URL = "https://api-gateway.coupang.com"
    
    def __init__(self, account_credentials: Dict[str, str]):
        """Initialize Coupang API client.
        
        Args:
            account_credentials: Dictionary containing:
                - access_key: Coupang access key
                - secret_key: Coupang secret key
                - vendor_id: Vendor ID
        """
        self.access_key = account_credentials.get("access_key")
        self.secret_key = account_credentials.get("secret_key")
        self.vendor_id = account_credentials.get("vendor_id")
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    def _generate_signature(self, method: str, path: str, query: str = "") -> Dict[str, str]:
        """Generate HMAC signature for Coupang API authentication."""
        datetime_str = time.strftime('%y%m%d')
        datetime_time = time.strftime('T%H%M%SZ')
        datetime_now = datetime_str + datetime_time
        
        message = datetime_now + method + path + query
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "Authorization": f"CEA algorithm=HmacSHA256, access-key={self.access_key}, signed-date={datetime_now}, signature={signature}",
            "Content-Type": "application/json;charset=UTF-8"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _request(self, method: str, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request to Coupang API with retry logic."""
        query_string = urllib.parse.urlencode(params) if params else ""
        full_path = f"{path}?{query_string}" if query_string else path
        
        headers = self._generate_signature(method, path, query_string)
        
        response = await self.client.request(
            method=method,
            url=f"{self.BASE_URL}{full_path}",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            raise Exception(f"Coupang API Error: {response.status_code} - {error_data}")
            
        return response.json()
    
    # Product Management
    async def create_product(self, product_data: Dict[str, Any]) -> Dict:
        """Create a new product on Coupang.
        
        Args:
            product_data: Product information including:
                - displayCategoryCode: Category code
                - sellerProductName: Product name
                - vendorId: Vendor ID
                - saleStartedAt: Sale start date
                - saleEndedAt: Sale end date
                - displayProductName: Display name
                - brand: Brand name
                - generalProductName: General product name
                - productGroup: Product group
                - deliveryMethod: Delivery method
                - deliveryCompanyCode: Delivery company code
                - deliveryChargeType: Delivery charge type
                - deliveryCharge: Delivery charge
                - freeShipOverAmount: Free shipping threshold
                - returnCenterCode: Return center code
                - returnChargeName: Return charge name
                - companyContactNumber: Company contact
                - returnZipCode: Return zip code
                - returnAddress: Return address
                - returnAddressDetail: Return address detail
                - returnCharge: Return charge
                - items: List of product items
        """
        path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        return await self._request("POST", path, data=product_data)
    
    async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict:
        """Update existing product on Coupang."""
        path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{product_id}"
        return await self._request("PUT", path, data=product_data)
    
    async def delete_product(self, product_id: str) -> Dict:
        """Delete product from Coupang."""
        path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{product_id}"
        return await self._request("DELETE", path)
    
    async def get_product(self, product_id: str) -> Dict:
        """Get product details from Coupang."""
        path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{product_id}"
        return await self._request("GET", path)
    
    async def list_products(self, status: Optional[str] = None, limit: int = 50, next_token: Optional[str] = None) -> Dict:
        """List products from Coupang.
        
        Args:
            status: Product status filter (ACTIVE, INACTIVE, etc.)
            limit: Number of products to retrieve
            next_token: Pagination token
        """
        path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        params = {
            "vendorId": self.vendor_id,
            "limit": limit
        }
        if status:
            params["status"] = status
        if next_token:
            params["nextToken"] = next_token
            
        return await self._request("GET", path, params=params)
    
    # Order Management
    async def get_orders(self, start_date: datetime, end_date: datetime, status: Optional[str] = None) -> Dict:
        """Get orders from Coupang.
        
        Args:
            start_date: Start date for order search
            end_date: End date for order search
            status: Order status filter
        """
        path = "/v2/providers/openapi/apis/api/v4/vendors/A00000000/ordersheets"
        params = {
            "createdAtFrom": start_date.strftime("%Y-%m-%d"),
            "createdAtTo": end_date.strftime("%Y-%m-%d"),
            "status": status or "UC"  # UC: Unconfirmed
        }
        
        return await self._request("GET", path, params=params)
    
    async def confirm_order(self, order_id: str, ship_date: datetime) -> Dict:
        """Confirm order and prepare for shipping."""
        path = f"/v2/providers/openapi/apis/api/v4/vendors/{self.vendor_id}/ordersheets/acknowledgement"
        data = {
            "vendorId": self.vendor_id,
            "orderIds": [order_id],
            "shippingDate": ship_date.strftime("%Y-%m-%d")
        }
        
        return await self._request("PUT", path, data=data)
    
    async def update_shipping_info(self, order_id: str, tracking_info: Dict[str, str]) -> Dict:
        """Update shipping information for order.
        
        Args:
            order_id: Coupang order ID
            tracking_info: Dictionary containing:
                - deliveryCompanyCode: Delivery company code
                - trackingNumber: Tracking number
        """
        path = f"/v2/providers/openapi/apis/api/v4/vendors/{self.vendor_id}/ordersheets/shipments"
        data = {
            "vendorId": self.vendor_id,
            "orderSheetId": order_id,
            "deliveryCompanyCode": tracking_info["deliveryCompanyCode"],
            "trackingNumber": tracking_info["trackingNumber"]
        }
        
        return await self._request("POST", path, data=data)
    
    async def cancel_order(self, order_id: str, cancel_reason: str) -> Dict:
        """Cancel order on Coupang."""
        path = f"/v2/providers/openapi/apis/api/v4/vendors/{self.vendor_id}/ordersheets/{order_id}/cancel"
        data = {
            "vendorId": self.vendor_id,
            "cancelReason": cancel_reason
        }
        
        return await self._request("PUT", path, data=data)
    
    # Inventory Management
    async def update_inventory(self, product_id: str, vendor_item_id: str, quantity: int) -> Dict:
        """Update product inventory on Coupang.
        
        Args:
            product_id: Coupang product ID
            vendor_item_id: Vendor's item ID
            quantity: New inventory quantity
        """
        path = f"/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{vendor_item_id}/quantities"
        data = {
            "vendorId": self.vendor_id,
            "vendorItemId": vendor_item_id,
            "quantity": quantity
        }
        
        return await self._request("PUT", path, data=data)
    
    async def get_inventory(self, vendor_item_ids: List[str]) -> Dict:
        """Get current inventory levels from Coupang."""
        path = "/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/quantities"
        params = {
            "vendorId": self.vendor_id,
            "vendorItemIds": ",".join(vendor_item_ids)
        }
        
        return await self._request("GET", path, params=params)
    
    # Settlement Management
    async def get_settlement_summary(self, settlement_date: datetime) -> Dict:
        """Get settlement summary for a specific date."""
        path = f"/v2/providers/openapi/apis/api/v2/vendors/{self.vendor_id}/settlement-summaries"
        params = {
            "settlementDate": settlement_date.strftime("%Y-%m-%d")
        }
        
        return await self._request("GET", path, params=params)
    
    async def get_settlement_details(self, settlement_id: str) -> Dict:
        """Get detailed settlement information."""
        path = f"/v2/providers/openapi/apis/api/v2/vendors/{self.vendor_id}/settlement-details/{settlement_id}"
        
        return await self._request("GET", path)
    
    # Utility Methods
    async def test_connection(self) -> bool:
        """Test API connection and credentials."""
        try:
            # Try to get vendor info
            path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
            params = {
                "vendorId": self.vendor_id,
                "limit": 1
            }
            await self._request("GET", path, params=params)
            return True
        except Exception:
            return False
    
    async def get_categories(self, display_category_code: Optional[str] = None) -> Dict:
        """Get available product categories."""
        path = "/v2/providers/seller_api/apis/api/v1/marketplace/meta/categories"
        params = {}
        if display_category_code:
            params["displayCategoryCode"] = display_category_code
            
        return await self._request("GET", path, params=params)
    
    async def get_delivery_companies(self) -> Dict:
        """Get list of available delivery companies."""
        path = "/v2/providers/openapi/apis/api/v1/marketplace/meta/delivery-companies"
        
        return await self._request("GET", path)