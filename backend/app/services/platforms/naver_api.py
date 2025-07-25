"""Naver Shopping (Smart Store) API integration service."""

import base64
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.platform_account import PlatformType


class NaverAPI:
    """Naver Shopping API client for Smart Store."""
    
    BASE_URL = "https://api.commerce.naver.com"
    AUTH_URL = "https://api.commerce.naver.com/external/v1/oauth2/token"
    
    def __init__(self, account_credentials: Dict[str, str]):
        """Initialize Naver API client.
        
        Args:
            account_credentials: Dictionary containing:
                - client_id: Naver API client ID
                - client_secret: Naver API client secret
                - access_token: OAuth access token (optional, will refresh if needed)
                - refresh_token: OAuth refresh token
        """
        self.client_id = account_credentials.get("client_id")
        self.client_secret = account_credentials.get("client_secret")
        self.access_token = account_credentials.get("access_token")
        self.refresh_token = account_credentials.get("refresh_token")
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _refresh_access_token(self) -> str:
        """Refresh OAuth access token using refresh token."""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        response = await self.client.post(self.AUTH_URL, headers=headers, data=data)
        
        if response.status_code != 200:
            raise Exception(f"Failed to refresh access token: {response.text}")
            
        token_data = response.json()
        self.access_token = token_data["access_token"]
        return self.access_token
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _request(self, method: str, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request to Naver API with retry logic."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.request(
                method=method,
                url=f"{self.BASE_URL}{path}",
                headers=headers,
                json=data,
                params=params
            )
            
            if response.status_code == 401:
                # Token expired, refresh and retry
                await self._refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = await self.client.request(
                    method=method,
                    url=f"{self.BASE_URL}{path}",
                    headers=headers,
                    json=data,
                    params=params
                )
            
            if response.status_code not in [200, 201]:
                error_data = response.json() if response.content else {}
                raise Exception(f"Naver API Error: {response.status_code} - {error_data}")
                
            return response.json()
            
        except httpx.TimeoutException:
            raise Exception("Naver API request timeout")
    
    # Product Management
    async def create_product(self, product_data: Dict[str, Any]) -> Dict:
        """Create a new product on Naver Smart Store.
        
        Args:
            product_data: Product information including:
                - name: Product name
                - detailContent: Product description (HTML)
                - salePrice: Sale price
                - stockQuantity: Stock quantity
                - images: List of image URLs
                - categoryId: Naver category ID
                - detailAttribute: Product attributes
                - saleStartDate: Sale start date
                - saleEndDate: Sale end date
                - deliveryInfo: Delivery information
                - productInfoProvidedNotice: Product info notice
                - afterServiceInfo: After service info
                - originAreaInfo: Origin area info
        """
        path = "/external/v2/products"
        return await self._request("POST", path, data=product_data)
    
    async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict:
        """Update existing product on Naver Smart Store."""
        path = f"/external/v2/products/{product_id}"
        return await self._request("PUT", path, data=product_data)
    
    async def delete_product(self, product_id: str) -> Dict:
        """Delete product from Naver Smart Store."""
        path = f"/external/v2/products/{product_id}"
        return await self._request("DELETE", path)
    
    async def get_product(self, product_id: str) -> Dict:
        """Get product details from Naver Smart Store."""
        path = f"/external/v2/products/{product_id}"
        return await self._request("GET", path)
    
    async def list_products(self, page: int = 1, size: int = 100, status: Optional[str] = None) -> Dict:
        """List products from Naver Smart Store.
        
        Args:
            page: Page number (1-based)
            size: Page size (max 100)
            status: Product status filter (SALE, SUSPENSION, OUTOFSTOCK, PROHIBITION)
        """
        path = "/external/v2/products"
        params = {
            "page": page,
            "size": size
        }
        if status:
            params["productStatusType"] = status
            
        return await self._request("GET", path, params=params)
    
    # Order Management
    async def get_orders(self, start_date: datetime, end_date: datetime, status: Optional[str] = None) -> Dict:
        """Get orders from Naver Smart Store.
        
        Args:
            start_date: Start date for order search
            end_date: End date for order search
            status: Order status filter (PAYED, DELIVERING, DELIVERED, etc.)
        """
        path = "/external/v1/pay-order/seller/orders"
        params = {
            "startTime": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "endTime": end_date.strftime("%Y-%m-%dT%H:%M:%S")
        }
        if status:
            params["productOrderStatus"] = status
            
        return await self._request("GET", path, params=params)
    
    async def get_order_detail(self, order_id: str) -> Dict:
        """Get detailed order information."""
        path = f"/external/v1/pay-order/seller/orders/{order_id}"
        return await self._request("GET", path)
    
    async def dispatch_order(self, order_id: str, shipping_info: Dict[str, str]) -> Dict:
        """Dispatch order with shipping information.
        
        Args:
            order_id: Naver order ID
            shipping_info: Dictionary containing:
                - deliveryCompanyCode: Delivery company code
                - trackingNumber: Tracking number
                - sendDate: Send date
        """
        path = f"/external/v1/pay-order/seller/orders/{order_id}/ship"
        data = {
            "dispatchDetails": [{
                "deliveryCompanyCode": shipping_info["deliveryCompanyCode"],
                "trackingNumber": shipping_info["trackingNumber"],
                "sendDate": shipping_info["sendDate"]
            }]
        }
        
        return await self._request("POST", path, data=data)
    
    async def cancel_order(self, order_id: str, cancel_reason: str) -> Dict:
        """Cancel order on Naver Smart Store."""
        path = f"/external/v1/pay-order/seller/orders/{order_id}/cancel"
        data = {
            "cancelReason": cancel_reason,
            "cancelDetailedReason": cancel_reason
        }
        
        return await self._request("POST", path, data=data)
    
    async def process_return(self, order_id: str, return_data: Dict[str, Any]) -> Dict:
        """Process return request."""
        path = f"/external/v1/pay-order/seller/orders/{order_id}/return"
        return await self._request("POST", path, data=return_data)
    
    # Inventory Management
    async def update_stock(self, product_id: str, quantity: int) -> Dict:
        """Update product stock quantity.
        
        Args:
            product_id: Naver product ID
            quantity: New stock quantity
        """
        path = f"/external/v2/products/{product_id}/stock"
        data = {
            "stockQuantity": quantity
        }
        
        return await self._request("PUT", path, data=data)
    
    async def get_stock(self, product_ids: List[str]) -> Dict:
        """Get current stock levels for multiple products."""
        path = "/external/v2/products/stock"
        params = {
            "productIds": ",".join(product_ids)
        }
        
        return await self._request("GET", path, params=params)
    
    # Review Management
    async def get_reviews(self, product_id: str, page: int = 1, size: int = 100) -> Dict:
        """Get product reviews."""
        path = f"/external/v1/reviews/product/{product_id}"
        params = {
            "page": page,
            "size": size
        }
        
        return await self._request("GET", path, params=params)
    
    async def reply_to_review(self, review_id: str, reply: str) -> Dict:
        """Reply to customer review."""
        path = f"/external/v1/reviews/{review_id}/reply"
        data = {
            "replyContent": reply
        }
        
        return await self._request("POST", path, data=data)
    
    # Question Management
    async def get_questions(self, product_id: Optional[str] = None, page: int = 1, size: int = 100) -> Dict:
        """Get customer questions."""
        path = "/external/v1/customer-inquiries"
        params = {
            "page": page,
            "size": size
        }
        if product_id:
            params["productId"] = product_id
            
        return await self._request("GET", path, params=params)
    
    async def answer_question(self, question_id: str, answer: str) -> Dict:
        """Answer customer question."""
        path = f"/external/v1/customer-inquiries/{question_id}/answer"
        data = {
            "answerContent": answer
        }
        
        return await self._request("POST", path, data=data)
    
    # Settlement Management
    async def get_settlement_summary(self, year: int, month: int) -> Dict:
        """Get monthly settlement summary."""
        path = "/external/v1/pay-settle/seller/month-summary"
        params = {
            "year": year,
            "month": month
        }
        
        return await self._request("GET", path, params=params)
    
    async def get_settlement_details(self, settlement_date: datetime) -> Dict:
        """Get detailed settlement information."""
        path = "/external/v1/pay-settle/seller/daily-detail"
        params = {
            "settlementDate": settlement_date.strftime("%Y-%m-%d")
        }
        
        return await self._request("GET", path, params=params)
    
    # Utility Methods
    async def test_connection(self) -> bool:
        """Test API connection and credentials."""
        try:
            # Try to get seller info
            path = "/external/v1/seller/info"
            await self._request("GET", path)
            return True
        except Exception:
            return False
    
    async def get_categories(self, category_id: Optional[str] = None) -> Dict:
        """Get available product categories."""
        path = "/external/v1/categories"
        params = {}
        if category_id:
            params["categoryId"] = category_id
            
        return await self._request("GET", path, params=params)
    
    async def get_delivery_companies(self) -> Dict:
        """Get list of available delivery companies."""
        path = "/external/v1/delivery-companies"
        return await self._request("GET", path)
    
    async def upload_image(self, image_url: str) -> Dict:
        """Upload product image to Naver."""
        path = "/external/v1/product-images"
        data = {
            "imageUrl": image_url
        }
        
        return await self._request("POST", path, data=data)