"""11st (11번가) API integration service."""

import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.platform_account import PlatformType


class EleventhStreetAPI:
    """11st API client."""
    
    BASE_URL = "https://api.11st.co.kr/rest"
    
    def __init__(self, account_credentials: Dict[str, str]):
        """Initialize 11st API client.
        
        Args:
            account_credentials: Dictionary containing:
                - api_key: 11st API key
                - seller_id: Seller ID
        """
        self.api_key = account_credentials.get("api_key")
        self.seller_id = account_credentials.get("seller_id")
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _build_xml_request(self, root_name: str, data: Dict[str, Any]) -> str:
        """Build XML request body from dictionary."""
        root = ET.Element(root_name)
        self._dict_to_xml(root, data)
        return ET.tostring(root, encoding='unicode')
    
    def _dict_to_xml(self, parent: ET.Element, data: Dict[str, Any]):
        """Recursively convert dictionary to XML elements."""
        for key, value in data.items():
            if isinstance(value, dict):
                child = ET.SubElement(parent, key)
                self._dict_to_xml(child, value)
            elif isinstance(value, list):
                for item in value:
                    child = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        self._dict_to_xml(child, item)
                    else:
                        child.text = str(item)
            else:
                child = ET.SubElement(parent, key)
                child.text = str(value) if value is not None else ""
    
    def _parse_xml_response(self, xml_string: str) -> Dict[str, Any]:
        """Parse XML response to dictionary."""
        root = ET.fromstring(xml_string)
        return self._xml_to_dict(root)
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Recursively convert XML element to dictionary."""
        result = {}
        
        # Handle attributes
        if element.attrib:
            result['@attributes'] = element.attrib
        
        # Handle text content
        if element.text and element.text.strip():
            if len(element) == 0:  # No children
                return element.text.strip()
            else:
                result['#text'] = element.text.strip()
        
        # Handle children
        children = {}
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in children:
                # Convert to list if multiple children with same tag
                if not isinstance(children[child.tag], list):
                    children[child.tag] = [children[child.tag]]
                children[child.tag].append(child_data)
            else:
                children[child.tag] = child_data
        
        result.update(children)
        return result if result else None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _request(self, method: str, path: str, data: Optional[str] = None, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request to 11st API with retry logic."""
        headers = {
            "openapikey": self.api_key,
            "Content-Type": "text/xml;charset=UTF-8" if data else "application/x-www-form-urlencoded"
        }
        
        response = await self.client.request(
            method=method,
            url=f"{self.BASE_URL}{path}",
            headers=headers,
            content=data.encode('utf-8') if data else None,
            params=params
        )
        
        if response.status_code not in [200, 201]:
            error_text = response.text
            raise Exception(f"11st API Error: {response.status_code} - {error_text}")
        
        # 11st returns XML responses
        return self._parse_xml_response(response.text)
    
    # Product Management
    async def create_product(self, product_data: Dict[str, Any]) -> Dict:
        """Create a new product on 11st.
        
        Args:
            product_data: Product information including:
                - selMthdCd: Sales method code (01: General)
                - dispCtgrNo: Display category number
                - prdNm: Product name
                - prdStatCd: Product status code (01: Selling)
                - prdWght: Product weight
                - minorSelCnYn: Minor purchase available (Y/N)
                - prdImage01: Main image URL
                - htmlDetail: Product detail HTML
                - selPrc: Selling price
                - prdSelQty: Available quantity
                - dlvCstInstBasiCd: Delivery cost basis
                - rtngdDlvCst: Return delivery cost
                - exchDlvCst: Exchange delivery cost
                - asDetail: AS detail
                - rtngExchDetail: Return/exchange detail
                - dlvCstPayTypCd: Delivery cost payment type
        """
        xml_data = self._build_xml_request("Product", product_data)
        path = "/prodservices/product"
        
        return await self._request("POST", path, data=xml_data)
    
    async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict:
        """Update existing product on 11st."""
        product_data["prdNo"] = product_id
        xml_data = self._build_xml_request("Product", product_data)
        path = f"/prodservices/product/{product_id}"
        
        return await self._request("PUT", path, data=xml_data)
    
    async def delete_product(self, product_id: str) -> Dict:
        """Stop selling product on 11st (change status to stop)."""
        product_data = {
            "prdNo": product_id,
            "prdStatCd": "03"  # 03: Stop selling
        }
        xml_data = self._build_xml_request("Product", product_data)
        path = f"/prodservices/product/{product_id}"
        
        return await self._request("PUT", path, data=xml_data)
    
    async def get_product(self, product_id: str) -> Dict:
        """Get product details from 11st."""
        path = f"/prodservices/product/{product_id}"
        return await self._request("GET", path)
    
    async def list_products(self, page: int = 1, limit: int = 100, status: Optional[str] = None) -> Dict:
        """List products from 11st.
        
        Args:
            page: Page number
            limit: Number of products per page
            status: Product status code (01: Selling, 03: Stop, etc.)
        """
        path = "/prodservices/product"
        params = {
            "page": page,
            "limit": limit,
            "sellerId": self.seller_id
        }
        if status:
            params["prdStatCd"] = status
            
        return await self._request("GET", path, params=params)
    
    # Order Management
    async def get_orders(self, start_date: datetime, end_date: datetime, status: Optional[str] = None) -> Dict:
        """Get orders from 11st.
        
        Args:
            start_date: Start date for order search
            end_date: End date for order search
            status: Order status code
        """
        path = "/ordservices/complete"
        params = {
            "ordStrtDt": start_date.strftime("%Y%m%d"),
            "ordEndDt": end_date.strftime("%Y%m%d")
        }
        if status:
            params["ordStat"] = status
            
        return await self._request("GET", path, params=params)
    
    async def get_order_detail(self, order_id: str) -> Dict:
        """Get detailed order information."""
        path = f"/ordservices/complete/{order_id}"
        return await self._request("GET", path)
    
    async def confirm_order(self, order_id: str) -> Dict:
        """Confirm order for processing."""
        path = f"/ordservices/reqorder/{order_id}"
        xml_data = self._build_xml_request("Order", {"ordNo": order_id})
        
        return await self._request("PUT", path, data=xml_data)
    
    async def update_delivery_info(self, order_id: str, delivery_info: Dict[str, str]) -> Dict:
        """Update delivery information for order.
        
        Args:
            order_id: 11st order ID
            delivery_info: Dictionary containing:
                - dlvEtprsCd: Delivery company code
                - invcNo: Invoice number (tracking number)
                - dlvSndDt: Delivery send date
        """
        xml_data = self._build_xml_request("Delivery", {
            "ordNo": order_id,
            "dlvEtprsCd": delivery_info["dlvEtprsCd"],
            "invcNo": delivery_info["invcNo"],
            "dlvSndDt": delivery_info["dlvSndDt"]
        })
        path = f"/ordservices/reqdeliver/{order_id}"
        
        return await self._request("PUT", path, data=xml_data)
    
    async def cancel_order(self, order_id: str, cancel_reason: str) -> Dict:
        """Cancel order on 11st."""
        xml_data = self._build_xml_request("Cancel", {
            "ordNo": order_id,
            "cancelReason": cancel_reason
        })
        path = f"/ordservices/reqcancel/{order_id}"
        
        return await self._request("PUT", path, data=xml_data)
    
    # Stock Management
    async def update_stock(self, product_id: str, quantity: int) -> Dict:
        """Update product stock quantity.
        
        Args:
            product_id: 11st product ID
            quantity: New stock quantity
        """
        xml_data = self._build_xml_request("Stock", {
            "prdNo": product_id,
            "prdSelQty": quantity
        })
        path = "/prodservices/stock"
        
        return await self._request("PUT", path, data=xml_data)
    
    async def get_stock(self, product_ids: List[str]) -> Dict:
        """Get current stock levels for multiple products."""
        path = "/prodservices/stock"
        params = {
            "prdNoList": ",".join(product_ids)
        }
        
        return await self._request("GET", path, params=params)
    
    # Settlement Management
    async def get_settlement_list(self, year: int, month: int) -> Dict:
        """Get settlement list for a specific month."""
        path = "/settleservices/sellerdaily"
        params = {
            "year": year,
            "month": f"{month:02d}"
        }
        
        return await self._request("GET", path, params=params)
    
    async def get_settlement_detail(self, settlement_date: datetime) -> Dict:
        """Get detailed settlement information for a specific date."""
        path = "/settleservices/sellerdailydetail"
        params = {
            "settleDate": settlement_date.strftime("%Y%m%d")
        }
        
        return await self._request("GET", path, params=params)
    
    # Q&A Management
    async def get_product_qna(self, product_id: Optional[str] = None, page: int = 1) -> Dict:
        """Get product Q&A list."""
        path = "/prodqnaservices/prodqnalist"
        params = {
            "page": page,
            "pageSize": 100
        }
        if product_id:
            params["prdNo"] = product_id
            
        return await self._request("GET", path, params=params)
    
    async def answer_qna(self, qna_id: str, answer: str) -> Dict:
        """Answer product Q&A."""
        xml_data = self._build_xml_request("Answer", {
            "qnaNo": qna_id,
            "answer": answer
        })
        path = f"/prodqnaservices/prodqna/{qna_id}"
        
        return await self._request("PUT", path, data=xml_data)
    
    # Utility Methods
    async def test_connection(self) -> bool:
        """Test API connection and credentials."""
        try:
            # Try to get seller info
            path = "/prodservices/product"
            params = {
                "page": 1,
                "limit": 1,
                "sellerId": self.seller_id
            }
            await self._request("GET", path, params=params)
            return True
        except Exception:
            return False
    
    async def get_categories(self, display_category_code: Optional[str] = None) -> Dict:
        """Get available product categories."""
        path = "/cateservice/category"
        params = {}
        if display_category_code:
            params["dispCtgrNo"] = display_category_code
            
        return await self._request("GET", path, params=params)
    
    async def get_delivery_companies(self) -> Dict:
        """Get list of available delivery companies."""
        path = "/commonservice/deliverycompany"
        return await self._request("GET", path)