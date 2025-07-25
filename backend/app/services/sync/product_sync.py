"""Product synchronization service."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.product import Product
from app.models.platform_account import PlatformAccount, PlatformType
from app.services.platforms.platform_manager import PlatformManager
from app.crud.product import product_crud

logger = logging.getLogger(__name__)


class ProductSyncService:
    """Service for synchronizing products across platforms."""
    
    def __init__(self, db_session: AsyncSession, platform_manager: PlatformManager):
        """Initialize Product Sync Service.
        
        Args:
            db_session: Database session
            platform_manager: Platform manager instance
        """
        self.db_session = db_session
        self.platform_manager = platform_manager
    
    async def sync_product_to_platforms(
        self, 
        product: Product, 
        platform_accounts: List[PlatformAccount]
    ) -> Dict[str, Any]:
        """Sync a single product to multiple platforms.
        
        Args:
            product: Product to sync
            platform_accounts: List of platform accounts to sync to
            
        Returns:
            Sync results for each platform
        """
        results = {}
        
        # Prepare unified product data
        unified_data = self._prepare_unified_product_data(product)
        
        for account in platform_accounts:
            try:
                # Check if product already exists on platform
                platform_product_id = self._get_platform_product_id(product, account.platform)
                
                if platform_product_id:
                    # Update existing product
                    result = await self._update_product_on_platform(
                        account,
                        platform_product_id,
                        unified_data
                    )
                    result["action"] = "updated"
                else:
                    # Create new product
                    result = await self._create_product_on_platform(
                        account,
                        unified_data
                    )
                    result["action"] = "created"
                    
                    # Store platform product ID
                    if result.get("success"):
                        await self._store_platform_product_id(
                            product,
                            account.platform,
                            result.get("platform_product_id")
                        )
                
                results[f"{account.platform.value}_{account.name}"] = result
                
            except Exception as e:
                logger.error(f"Failed to sync product {product.id} to {account.platform.value}: {str(e)}")
                results[f"{account.platform.value}_{account.name}"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def sync_products_from_platforms(
        self,
        platform_accounts: List[PlatformAccount]
    ) -> Dict[str, Any]:
        """Sync products from platforms to local database.
        
        Args:
            platform_accounts: List of platform accounts to sync from
            
        Returns:
            Sync results for each platform
        """
        results = {}
        
        for account in platform_accounts:
            try:
                # Get products from platform
                platform_products = await self._get_products_from_platform(account)
                
                sync_result = {
                    "total": len(platform_products),
                    "created": 0,
                    "updated": 0,
                    "errors": []
                }
                
                for platform_product in platform_products:
                    try:
                        # Check if product exists locally
                        local_product = await self._find_local_product(
                            platform_product,
                            account
                        )
                        
                        if local_product:
                            # Update existing product
                            await self._update_local_product(
                                local_product,
                                platform_product,
                                account.platform
                            )
                            sync_result["updated"] += 1
                        else:
                            # Create new product
                            await self._create_local_product(
                                platform_product,
                                account
                            )
                            sync_result["created"] += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to sync product from {account.platform.value}: {str(e)}")
                        sync_result["errors"].append(str(e))
                
                results[f"{account.platform.value}_{account.name}"] = sync_result
                
            except Exception as e:
                logger.error(f"Failed to get products from {account.platform.value}: {str(e)}")
                results[f"{account.platform.value}_{account.name}"] = {
                    "error": str(e)
                }
        
        return results
    
    def _prepare_unified_product_data(self, product: Product) -> Dict[str, Any]:
        """Prepare unified product data for platform sync."""
        return {
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "original_price": float(product.original_price) if product.original_price else float(product.price),
            "stock_quantity": product.stock_quantity,
            "category_id": product.category_id,
            "category_code": product.category_code,
            "category_no": product.category_no,
            "brand": product.brand,
            "weight": product.weight,
            "main_image": product.main_image,
            "additional_images": product.additional_images or [],
            "attributes": product.attributes or {},
            "options": product.options or [],
            "tags": product.tags or [],
            "sale_start_date": product.sale_start_date.isoformat() if product.sale_start_date else None,
            "sale_end_date": product.sale_end_date.isoformat() if product.sale_end_date else None,
            # Delivery info
            "delivery_type": product.delivery_type,
            "delivery_fee": float(product.delivery_fee) if product.delivery_fee else 0,
            "delivery_method": product.delivery_method,
            # Additional platform-specific data can be added here
        }
    
    def _get_platform_product_id(self, product: Product, platform: PlatformType) -> Optional[str]:
        """Get platform-specific product ID from product's platform_data."""
        if not product.platform_data:
            return None
        
        platform_info = product.platform_data.get(platform.value, {})
        return platform_info.get("product_id")
    
    async def _create_product_on_platform(
        self,
        account: PlatformAccount,
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create product on a specific platform."""
        api = await self.platform_manager.get_platform_api(account.platform, account.id)
        
        # Add account-specific data
        if account.platform == PlatformType.COUPANG:
            product_data["vendor_id"] = account.credentials.get("vendor_id")
        
        async with api:
            result = await api.create_product(product_data)
            
        return {
            "success": True,
            "platform_product_id": self._extract_product_id(result, account.platform),
            "result": result
        }
    
    async def _update_product_on_platform(
        self,
        account: PlatformAccount,
        platform_product_id: str,
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update product on a specific platform."""
        api = await self.platform_manager.get_platform_api(account.platform, account.id)
        
        async with api:
            result = await api.update_product(platform_product_id, product_data)
            
        return {
            "success": True,
            "platform_product_id": platform_product_id,
            "result": result
        }
    
    async def _get_products_from_platform(self, account: PlatformAccount) -> List[Dict[str, Any]]:
        """Get all products from a specific platform."""
        api = await self.platform_manager.get_platform_api(account.platform, account.id)
        
        products = []
        next_token = None
        page = 1
        
        async with api:
            while True:
                if account.platform == PlatformType.COUPANG:
                    result = await api.list_products(limit=100, next_token=next_token)
                    products.extend(result.get("data", []))
                    next_token = result.get("nextToken")
                    if not next_token:
                        break
                        
                elif account.platform == PlatformType.NAVER:
                    result = await api.list_products(page=page, size=100)
                    products.extend(result.get("contents", []))
                    if len(result.get("contents", [])) < 100:
                        break
                    page += 1
                    
                elif account.platform == PlatformType.ELEVENTH_STREET:
                    result = await api.list_products(page=page, limit=100)
                    product_list = result.get("Products", {}).get("Product", [])
                    if not isinstance(product_list, list):
                        product_list = [product_list]
                    products.extend(product_list)
                    if len(product_list) < 100:
                        break
                    page += 1
                    
                # Prevent infinite loops
                if len(products) > 10000:
                    logger.warning(f"Too many products from {account.platform.value}, stopping at 10000")
                    break
        
        return products
    
    async def _find_local_product(
        self,
        platform_product: Dict[str, Any],
        account: PlatformAccount
    ) -> Optional[Product]:
        """Find local product matching platform product."""
        # First try to find by platform product ID
        platform_product_id = self._extract_platform_product_id(platform_product, account.platform)
        
        result = await self.db_session.execute(
            select(Product).where(
                Product.user_id == account.user_id,
                Product.platform_data[account.platform.value]["product_id"].astext == platform_product_id
            )
        )
        product = result.scalar_one_or_none()
        
        if product:
            return product
        
        # Try to find by SKU or name
        product_name = self._extract_product_name(platform_product, account.platform)
        sku = self._extract_product_sku(platform_product, account.platform)
        
        if sku:
            result = await self.db_session.execute(
                select(Product).where(
                    Product.user_id == account.user_id,
                    Product.sku == sku
                )
            )
            product = result.scalar_one_or_none()
            if product:
                return product
        
        # Last resort: try to match by name
        result = await self.db_session.execute(
            select(Product).where(
                Product.user_id == account.user_id,
                Product.name == product_name
            )
        )
        return result.scalar_one_or_none()
    
    async def _create_local_product(
        self,
        platform_product: Dict[str, Any],
        account: PlatformAccount
    ) -> Product:
        """Create local product from platform product data."""
        product_data = self._normalize_platform_product(platform_product, account.platform)
        product_data["user_id"] = account.user_id
        
        # Store platform-specific data
        product_data["platform_data"] = {
            account.platform.value: {
                "product_id": self._extract_platform_product_id(platform_product, account.platform),
                "synced_at": datetime.now().isoformat()
            }
        }
        
        product = await product_crud.create(self.db_session, obj_in=product_data)
        await self.db_session.commit()
        
        return product
    
    async def _update_local_product(
        self,
        local_product: Product,
        platform_product: Dict[str, Any],
        platform: PlatformType
    ) -> Product:
        """Update local product with platform product data."""
        update_data = self._normalize_platform_product(platform_product, platform)
        
        # Update platform data
        if not local_product.platform_data:
            local_product.platform_data = {}
            
        local_product.platform_data[platform.value] = {
            "product_id": self._extract_platform_product_id(platform_product, platform),
            "synced_at": datetime.now().isoformat()
        }
        
        # Update product fields
        for key, value in update_data.items():
            if hasattr(local_product, key) and value is not None:
                setattr(local_product, key, value)
        
        await self.db_session.commit()
        
        return local_product
    
    async def _store_platform_product_id(
        self,
        product: Product,
        platform: PlatformType,
        platform_product_id: str
    ):
        """Store platform product ID in product's platform_data."""
        if not product.platform_data:
            product.platform_data = {}
            
        product.platform_data[platform.value] = {
            "product_id": platform_product_id,
            "synced_at": datetime.now().isoformat()
        }
        
        await self.db_session.commit()
    
    def _extract_product_id(self, response: Dict[str, Any], platform: PlatformType) -> str:
        """Extract product ID from platform response."""
        if platform == PlatformType.COUPANG:
            return response.get("data", {}).get("sellerProductId", "")
        elif platform == PlatformType.NAVER:
            return response.get("productId", "")
        elif platform == PlatformType.ELEVENTH_STREET:
            return response.get("Product", {}).get("prdNo", "")
        return ""
    
    def _extract_platform_product_id(self, platform_product: Dict[str, Any], platform: PlatformType) -> str:
        """Extract product ID from platform product data."""
        if platform == PlatformType.COUPANG:
            return platform_product.get("sellerProductId", "")
        elif platform == PlatformType.NAVER:
            return platform_product.get("productId", "")
        elif platform == PlatformType.ELEVENTH_STREET:
            return platform_product.get("prdNo", "")
        return ""
    
    def _extract_product_name(self, platform_product: Dict[str, Any], platform: PlatformType) -> str:
        """Extract product name from platform product data."""
        if platform == PlatformType.COUPANG:
            return platform_product.get("sellerProductName", "")
        elif platform == PlatformType.NAVER:
            return platform_product.get("name", "")
        elif platform == PlatformType.ELEVENTH_STREET:
            return platform_product.get("prdNm", "")
        return ""
    
    def _extract_product_sku(self, platform_product: Dict[str, Any], platform: PlatformType) -> Optional[str]:
        """Extract product SKU from platform product data."""
        if platform == PlatformType.COUPANG:
            return platform_product.get("vendorItemId")
        elif platform == PlatformType.NAVER:
            return platform_product.get("sellerManagementCode")
        elif platform == PlatformType.ELEVENTH_STREET:
            return platform_product.get("selMngCd")
        return None
    
    def _normalize_platform_product(self, platform_product: Dict[str, Any], platform: PlatformType) -> Dict[str, Any]:
        """Normalize platform product data to unified format."""
        if platform == PlatformType.COUPANG:
            return self._normalize_coupang_product(platform_product)
        elif platform == PlatformType.NAVER:
            return self._normalize_naver_product(platform_product)
        elif platform == PlatformType.ELEVENTH_STREET:
            return self._normalize_11st_product(platform_product)
        return {}
    
    def _normalize_coupang_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Coupang product data."""
        items = product.get("items", [])
        first_item = items[0] if items else {}
        
        return {
            "name": product.get("sellerProductName"),
            "description": first_item.get("contents", [{}])[0].get("contentDetails", [{}])[0].get("content", ""),
            "price": first_item.get("salePrice"),
            "original_price": first_item.get("originalPrice"),
            "sku": first_item.get("vendorItemId"),
            "brand": product.get("brand"),
            "status": product.get("status"),
            "stock_quantity": first_item.get("quantity", 0),
            "main_image": first_item.get("images", [{}])[0].get("imageUrl") if first_item.get("images") else None
        }
    
    def _normalize_naver_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Naver product data."""
        images = product.get("images", {})
        
        return {
            "name": product.get("name"),
            "description": product.get("detailContent"),
            "price": product.get("salePrice"),
            "original_price": product.get("salePrice"),
            "sku": product.get("sellerManagementCode"),
            "brand": product.get("brand"),
            "status": product.get("statusType"),
            "stock_quantity": product.get("stockQuantity", 0),
            "main_image": images.get("representativeImage", {}).get("url")
        }
    
    def _normalize_11st_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize 11st product data."""
        return {
            "name": product.get("prdNm"),
            "description": product.get("htmlDetail"),
            "price": product.get("selPrc"),
            "original_price": product.get("selPrc"),
            "sku": product.get("selMngCd"),
            "brand": product.get("brand"),
            "status": product.get("prdStatCd"),
            "stock_quantity": int(product.get("prdSelQty", 0)),
            "main_image": product.get("prdImage01")
        }