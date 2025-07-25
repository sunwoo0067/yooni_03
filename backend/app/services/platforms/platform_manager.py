"""Platform Manager for handling multiple e-commerce platform integrations."""

from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_account import PlatformAccount, PlatformType
from app.services.platforms.coupang_api import CoupangAPI
from app.services.platforms.naver_api import NaverAPI
from app.services.platforms.eleventh_street_api import EleventhStreetAPI
from app.utils.encryption import decrypt_sensitive_data


class PlatformManager:
    """Manages multiple platform API connections and operations."""
    
    # Platform API mapping
    PLATFORM_APIS = {
        PlatformType.COUPANG: CoupangAPI,
        PlatformType.NAVER: NaverAPI,
        PlatformType.ELEVEN_ST: EleventhStreetAPI
    }
    
    def __init__(self, db_session: AsyncSession):
        """Initialize Platform Manager.
        
        Args:
            db_session: Database session for accessing platform accounts
        """
        self.db_session = db_session
        self._api_instances = {}
    
    async def get_platform_api(self, platform_type: PlatformType, account_id: int) -> Any:
        """Get platform API instance for a specific account.
        
        Args:
            platform_type: Type of platform
            account_id: Platform account ID
            
        Returns:
            Platform API instance
        """
        cache_key = f"{platform_type.value}_{account_id}"
        
        if cache_key not in self._api_instances:
            # Get account from database
            account = await self.db_session.get(PlatformAccount, account_id)
            if not account or account.platform != platform_type:
                raise ValueError(f"Platform account {account_id} not found or type mismatch")
            
            # Decrypt credentials
            credentials = self._decrypt_credentials(account.encrypted_credentials)
            
            # Create API instance
            api_class = self.PLATFORM_APIS.get(platform_type)
            if not api_class:
                raise ValueError(f"Platform {platform_type} not supported")
                
            self._api_instances[cache_key] = api_class(credentials)
        
        return self._api_instances[cache_key]
    
    def _decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, str]:
        """Decrypt platform credentials."""
        return decrypt_sensitive_data(encrypted_credentials)
    
    async def test_all_connections(self, user_id: int) -> Dict[str, bool]:
        """Test connections for all platform accounts of a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of platform_name: connection_status
        """
        from sqlalchemy import select
        
        # Get all platform accounts for user
        result = await self.db_session.execute(
            select(PlatformAccount).where(
                PlatformAccount.user_id == user_id,
                PlatformAccount.is_active == True
            )
        )
        accounts = result.scalars().all()
        
        connection_status = {}
        
        for account in accounts:
            try:
                api = await self.get_platform_api(account.platform, account.id)
                async with api:
                    status = await api.test_connection()
                connection_status[f"{account.platform.value}_{account.name}"] = status
            except Exception as e:
                connection_status[f"{account.platform.value}_{account.name}"] = False
        
        return connection_status
    
    # Product Management Methods
    async def create_product_on_platforms(
        self, 
        product_data: Dict[str, Any], 
        platform_accounts: List[PlatformAccount]
    ) -> Dict[str, Any]:
        """Create product on multiple platforms simultaneously.
        
        Args:
            product_data: Unified product data
            platform_accounts: List of platform accounts to create product on
            
        Returns:
            Dictionary with results for each platform
        """
        tasks = []
        platform_names = []
        
        for account in platform_accounts:
            platform_data = self._transform_product_data_for_platform(
                product_data, 
                account.platform
            )
            tasks.append(self._create_product_on_platform(account, platform_data))
            platform_names.append(f"{account.platform.value}_{account.name}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return dict(zip(platform_names, results))
    
    async def _create_product_on_platform(
        self, 
        account: PlatformAccount, 
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create product on a single platform."""
        try:
            api = await self.get_platform_api(account.platform, account.id)
            async with api:
                result = await api.create_product(product_data)
                return {
                    "success": True,
                    "platform_product_id": self._extract_product_id(result, account.platform),
                    "result": result
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _transform_product_data_for_platform(
        self, 
        unified_data: Dict[str, Any], 
        platform: PlatformType
    ) -> Dict[str, Any]:
        """Transform unified product data to platform-specific format."""
        if platform == PlatformType.COUPANG:
            return self._transform_for_coupang(unified_data)
        elif platform == PlatformType.NAVER:
            return self._transform_for_naver(unified_data)
        elif platform == PlatformType.ELEVENTH_STREET:
            return self._transform_for_11st(unified_data)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def _transform_for_coupang(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform product data for Coupang format."""
        return {
            "displayCategoryCode": data.get("category_code"),
            "sellerProductName": data.get("name"),
            "vendorId": data.get("vendor_id"),
            "saleStartedAt": data.get("sale_start_date", datetime.now().isoformat()),
            "saleEndedAt": data.get("sale_end_date", "2099-12-31T23:59:59"),
            "displayProductName": data.get("display_name", data.get("name")),
            "brand": data.get("brand", ""),
            "generalProductName": data.get("name"),
            "productGroup": data.get("product_group", ""),
            "deliveryMethod": data.get("delivery_method", "SEQUENCIAL"),
            "deliveryCompanyCode": data.get("delivery_company", ""),
            "deliveryChargeType": data.get("delivery_charge_type", "FREE"),
            "deliveryCharge": data.get("delivery_charge", 0),
            "freeShipOverAmount": data.get("free_ship_over_amount", 0),
            "returnCenterCode": data.get("return_center_code", ""),
            "returnChargeName": data.get("return_charge_name", ""),
            "companyContactNumber": data.get("company_contact", ""),
            "returnZipCode": data.get("return_zip_code", ""),
            "returnAddress": data.get("return_address", ""),
            "returnAddressDetail": data.get("return_address_detail", ""),
            "returnCharge": data.get("return_charge", 0),
            "items": [{
                "itemName": data.get("name"),
                "originalPrice": data.get("original_price", data.get("price")),
                "salePrice": data.get("price"),
                "maximumBuyCount": data.get("max_buy_count", 999),
                "maximumBuyForPerson": data.get("max_buy_per_person", 999),
                "outboundShippingTimeDay": data.get("shipping_time", 2),
                "maximumBuyForPersonPeriod": 1,
                "unitCount": 1,
                "contents": [{
                    "contentsType": "TEXT",
                    "contentDetails": [{
                        "content": data.get("description", ""),
                        "detailType": "TEXT"
                    }]
                }],
                "offerCondition": "NEW",
                "offerDescription": ""
            }]
        }
    
    def _transform_for_naver(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform product data for Naver format."""
        return {
            "name": data.get("name"),
            "detailContent": data.get("description", ""),
            "salePrice": data.get("price"),
            "stockQuantity": data.get("stock_quantity", 0),
            "images": {
                "representativeImage": {
                    "url": data.get("main_image", "")
                },
                "optionalImages": [
                    {"url": img} for img in data.get("additional_images", [])
                ]
            },
            "categoryId": data.get("category_id"),
            "detailAttribute": data.get("attributes", {}),
            "saleStartDate": data.get("sale_start_date", datetime.now().isoformat()),
            "saleEndDate": data.get("sale_end_date", "2099-12-31T23:59:59"),
            "deliveryInfo": {
                "deliveryType": data.get("delivery_type", "DELIVERY"),
                "deliveryAttributeType": data.get("delivery_attribute", "NORMAL"),
                "deliveryFee": data.get("delivery_fee", 0),
                "deliveryBundleGroupId": data.get("delivery_bundle_id"),
                "returnCenterCode": data.get("return_center_code"),
                "installationFee": False
            },
            "productInfoProvidedNotice": data.get("product_info_notice", {}),
            "afterServiceInfo": {
                "afterServiceTelephoneNumber": data.get("as_phone", ""),
                "afterServiceGuideContent": data.get("as_guide", "")
            },
            "originAreaInfo": {
                "originAreaCode": data.get("origin_code", "00"),
                "content": data.get("origin_content", "")
            }
        }
    
    def _transform_for_11st(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform product data for 11st format."""
        return {
            "selMthdCd": "01",  # General sales
            "dispCtgrNo": data.get("category_no"),
            "prdNm": data.get("name"),
            "prdStatCd": "01",  # Selling
            "prdWght": data.get("weight", 0),
            "minorSelCnYn": data.get("minor_purchase", "N"),
            "prdImage01": data.get("main_image", ""),
            "htmlDetail": data.get("description", ""),
            "selPrc": data.get("price"),
            "prdSelQty": data.get("stock_quantity", 0),
            "dlvCstInstBasiCd": data.get("delivery_cost_basis", "02"),
            "rtngdDlvCst": data.get("return_delivery_cost", 0),
            "exchDlvCst": data.get("exchange_delivery_cost", 0),
            "asDetail": data.get("as_detail", ""),
            "rtngExchDetail": data.get("return_exchange_detail", ""),
            "dlvCstPayTypCd": data.get("delivery_payment_type", "01")
        }
    
    def _extract_product_id(self, response: Dict[str, Any], platform: PlatformType) -> str:
        """Extract product ID from platform response."""
        if platform == PlatformType.COUPANG:
            return response.get("data", {}).get("sellerProductId", "")
        elif platform == PlatformType.NAVER:
            return response.get("productId", "")
        elif platform == PlatformType.ELEVENTH_STREET:
            return response.get("Product", {}).get("prdNo", "")
        return ""
    
    # Order Management Methods
    async def sync_orders_from_platforms(
        self, 
        platform_accounts: List[PlatformAccount],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, List[Dict]]:
        """Sync orders from multiple platforms.
        
        Args:
            platform_accounts: List of platform accounts
            start_date: Start date for order sync
            end_date: End date for order sync
            
        Returns:
            Dictionary with orders for each platform
        """
        tasks = []
        platform_names = []
        
        for account in platform_accounts:
            tasks.append(self._get_orders_from_platform(account, start_date, end_date))
            platform_names.append(f"{account.platform.value}_{account.name}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return dict(zip(platform_names, results))
    
    async def _get_orders_from_platform(
        self,
        account: PlatformAccount,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get orders from a single platform."""
        try:
            api = await self.get_platform_api(account.platform, account.id)
            async with api:
                result = await api.get_orders(start_date, end_date)
                return self._normalize_orders(result, account.platform)
        except Exception as e:
            return {"error": str(e)}
    
    def _normalize_orders(self, orders_data: Dict, platform: PlatformType) -> List[Dict]:
        """Normalize orders data from different platforms to unified format."""
        normalized_orders = []
        
        if platform == PlatformType.COUPANG:
            orders = orders_data.get("data", [])
            for order in orders:
                normalized_orders.append({
                    "platform": platform.value,
                    "platform_order_id": order.get("orderId"),
                    "order_date": order.get("orderedAt"),
                    "customer_name": order.get("ordererName"),
                    "customer_phone": order.get("ordererPhoneNumber"),
                    "total_amount": order.get("totalPrice"),
                    "status": order.get("status"),
                    "items": self._normalize_coupang_items(order.get("orderItems", []))
                })
                
        elif platform == PlatformType.NAVER:
            orders = orders_data.get("data", [])
            for order in orders:
                normalized_orders.append({
                    "platform": platform.value,
                    "platform_order_id": order.get("productOrderId"),
                    "order_date": order.get("orderDate"),
                    "customer_name": order.get("ordererName"),
                    "customer_phone": order.get("ordererTel"),
                    "total_amount": order.get("totalPaymentAmount"),
                    "status": order.get("productOrderStatus"),
                    "items": self._normalize_naver_items([order])
                })
                
        elif platform == PlatformType.ELEVENTH_STREET:
            # Handle 11st XML response structure
            orders = orders_data.get("Orders", {}).get("Order", [])
            if not isinstance(orders, list):
                orders = [orders]
            for order in orders:
                normalized_orders.append({
                    "platform": platform.value,
                    "platform_order_id": order.get("ordNo"),
                    "order_date": order.get("ordDt"),
                    "customer_name": order.get("ordNm"),
                    "customer_phone": order.get("ordPrtblTel"),
                    "total_amount": order.get("ordAmt"),
                    "status": order.get("ordStat"),
                    "items": self._normalize_11st_items(order.get("Products", {}).get("Product", []))
                })
        
        return normalized_orders
    
    def _normalize_coupang_items(self, items: List[Dict]) -> List[Dict]:
        """Normalize Coupang order items."""
        return [{
            "product_name": item.get("vendorItemName"),
            "quantity": item.get("shippingCount"),
            "price": item.get("orderPrice"),
            "vendor_item_id": item.get("vendorItemId")
        } for item in items]
    
    def _normalize_naver_items(self, items: List[Dict]) -> List[Dict]:
        """Normalize Naver order items."""
        return [{
            "product_name": item.get("productName"),
            "quantity": item.get("quantity"),
            "price": item.get("unitPrice"),
            "product_id": item.get("productId")
        } for item in items]
    
    def _normalize_11st_items(self, items: List[Dict]) -> List[Dict]:
        """Normalize 11st order items."""
        if not isinstance(items, list):
            items = [items]
        return [{
            "product_name": item.get("prdNm"),
            "quantity": item.get("ordQty"),
            "price": item.get("selPrc"),
            "product_id": item.get("prdNo")
        } for item in items]
    
    # Inventory Sync Methods
    async def sync_inventory_across_platforms(
        self,
        product_mappings: List[Dict[str, Any]],
        platform_accounts: List[PlatformAccount]
    ) -> Dict[str, Any]:
        """Sync inventory levels across multiple platforms.
        
        Args:
            product_mappings: List of product mappings with platform IDs
            platform_accounts: List of platform accounts
            
        Returns:
            Sync results for each platform
        """
        results = {}
        
        for mapping in product_mappings:
            unified_stock = mapping.get("unified_stock", 0)
            
            tasks = []
            platform_names = []
            
            for account in platform_accounts:
                platform_product_id = mapping.get(f"{account.platform.value}_product_id")
                if platform_product_id:
                    tasks.append(
                        self._update_inventory_on_platform(
                            account, 
                            platform_product_id,
                            unified_stock
                        )
                    )
                    platform_names.append(f"{account.platform.value}_{account.name}")
            
            if tasks:
                sync_results = await asyncio.gather(*tasks, return_exceptions=True)
                results[mapping.get("unified_product_id")] = dict(zip(platform_names, sync_results))
        
        return results
    
    async def _update_inventory_on_platform(
        self,
        account: PlatformAccount,
        product_id: str,
        quantity: int
    ) -> Dict[str, Any]:
        """Update inventory on a single platform."""
        try:
            api = await self.get_platform_api(account.platform, account.id)
            async with api:
                if account.platform == PlatformType.COUPANG:
                    # Coupang requires vendor_item_id
                    result = await api.update_inventory(product_id, product_id, quantity)
                else:
                    result = await api.update_stock(product_id, quantity)
                    
                return {
                    "success": True,
                    "result": result
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # Utility Methods
    async def close_all_connections(self):
        """Close all API connections."""
        for api_instance in self._api_instances.values():
            if hasattr(api_instance, 'client'):
                await api_instance.client.aclose()
        self._api_instances.clear()