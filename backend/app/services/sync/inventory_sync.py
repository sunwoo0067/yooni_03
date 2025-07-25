"""Inventory synchronization service."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging
import asyncio

from app.models.product import Product
from app.models.inventory import InventoryLog, InventoryMovement
from app.models.platform_account import PlatformAccount, PlatformType
from app.services.platforms.platform_manager import PlatformManager
from app.crud.base import CRUDBase

logger = logging.getLogger(__name__)

# Create CRUD instance for InventoryLog
inventory_log_crud = CRUDBase[InventoryLog](InventoryLog)


class InventorySyncService:
    """Service for synchronizing inventory across platforms."""
    
    def __init__(self, db_session: AsyncSession, platform_manager: PlatformManager):
        """Initialize Inventory Sync Service.
        
        Args:
            db_session: Database session
            platform_manager: Platform manager instance
        """
        self.db_session = db_session
        self.platform_manager = platform_manager
        
        # Safety stock levels
        self.safety_stock_levels = {
            "default": 5,
            "high_volume": 20,
            "low_volume": 2
        }
    
    async def sync_inventory_levels(
        self,
        product_mappings: List[Dict[str, Any]],
        platform_accounts: List[PlatformAccount]
    ) -> Dict[str, Any]:
        """Sync inventory levels across all platforms.
        
        Args:
            product_mappings: List of product mappings with unified and platform IDs
            platform_accounts: List of platform accounts to sync
            
        Returns:
            Sync results for each product and platform
        """
        results = {}
        
        for mapping in product_mappings:
            product_id = mapping["unified_product_id"]
            
            try:
                # Get current inventory from all platforms
                platform_inventories = await self._get_platform_inventories(
                    mapping,
                    platform_accounts
                )
                
                # Calculate unified inventory
                unified_inventory = await self._calculate_unified_inventory(
                    product_id,
                    platform_inventories
                )
                
                # Update platforms with unified inventory
                sync_results = await self._update_platform_inventories(
                    mapping,
                    platform_accounts,
                    unified_inventory
                )
                
                # Log inventory changes
                await self._log_inventory_sync(
                    product_id,
                    platform_inventories,
                    unified_inventory,
                    sync_results
                )
                
                results[str(product_id)] = {
                    "unified_inventory": unified_inventory,
                    "platform_inventories": platform_inventories,
                    "sync_results": sync_results
                }
                
            except Exception as e:
                logger.error(f"Failed to sync inventory for product {product_id}: {str(e)}")
                results[str(product_id)] = {
                    "error": str(e)
                }
        
        return results
    
    async def update_inventory_from_order(
        self,
        order_items: List[Dict[str, Any]],
        operation: str = "decrease"
    ) -> Dict[str, Any]:
        """Update inventory based on order operations.
        
        Args:
            order_items: List of order items with product_id and quantity
            operation: "decrease" for new orders, "increase" for cancellations
            
        Returns:
            Update results
        """
        results = {
            "updated_products": [],
            "errors": []
        }
        
        for item in order_items:
            try:
                product = await self.db_session.get(Product, item["product_id"])
                if not product:
                    results["errors"].append(f"Product {item['product_id']} not found")
                    continue
                
                # Update local inventory
                if operation == "decrease":
                    new_quantity = max(0, product.stock_quantity - item["quantity"])
                else:  # increase
                    new_quantity = product.stock_quantity + item["quantity"]
                
                product.stock_quantity = new_quantity
                
                # Get platform accounts
                platform_accounts = await self._get_product_platform_accounts(product.user_id)
                
                # Update inventory on all platforms
                sync_results = await self._sync_product_inventory_to_platforms(
                    product,
                    platform_accounts,
                    new_quantity
                )
                
                # Log inventory movement
                await self._log_inventory_movement(
                    product.id,
                    operation,
                    item["quantity"],
                    f"Order {item.get('order_id', 'N/A')}"
                )
                
                results["updated_products"].append({
                    "product_id": product.id,
                    "new_quantity": new_quantity,
                    "sync_results": sync_results
                })
                
            except Exception as e:
                logger.error(f"Failed to update inventory for item: {str(e)}")
                results["errors"].append(str(e))
        
        await self.db_session.commit()
        
        return results
    
    async def check_low_stock(self, user_id: int) -> List[Dict[str, Any]]:
        """Check for products with low stock levels.
        
        Args:
            user_id: User ID
            
        Returns:
            List of products with low stock
        """
        low_stock_products = []
        
        # Get all active products
        result = await self.db_session.execute(
            select(Product).where(
                Product.user_id == user_id,
                Product.is_active == True
            )
        )
        products = result.scalars().all()
        
        for product in products:
            # Determine safety stock level
            safety_stock = self._get_safety_stock_level(product)
            
            if product.stock_quantity <= safety_stock:
                low_stock_products.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "sku": product.sku,
                    "current_stock": product.stock_quantity,
                    "safety_stock": safety_stock,
                    "stock_status": "out_of_stock" if product.stock_quantity == 0 else "low_stock"
                })
        
        return low_stock_products
    
    async def auto_disable_out_of_stock(self, user_id: int) -> Dict[str, Any]:
        """Automatically disable products that are out of stock on platforms.
        
        Args:
            user_id: User ID
            
        Returns:
            Results of auto-disable operation
        """
        results = {
            "disabled_count": 0,
            "platform_results": {}
        }
        
        # Get products with zero stock
        result = await self.db_session.execute(
            select(Product).where(
                Product.user_id == user_id,
                Product.stock_quantity == 0,
                Product.is_active == True
            )
        )
        out_of_stock_products = result.scalars().all()
        
        # Get platform accounts
        platform_accounts = await self._get_product_platform_accounts(user_id)
        
        for product in out_of_stock_products:
            try:
                # Disable on each platform
                for account in platform_accounts:
                    platform_product_id = self._get_platform_product_id(product, account.platform)
                    if platform_product_id:
                        result = await self._disable_product_on_platform(
                            account,
                            platform_product_id
                        )
                        
                        platform_key = f"{account.platform.value}_{product.id}"
                        results["platform_results"][platform_key] = result
                
                # Mark product as inactive locally
                product.is_active = False
                product.status = "out_of_stock"
                results["disabled_count"] += 1
                
            except Exception as e:
                logger.error(f"Failed to disable out of stock product {product.id}: {str(e)}")
        
        await self.db_session.commit()
        
        return results
    
    async def _get_platform_inventories(
        self,
        mapping: Dict[str, Any],
        platform_accounts: List[PlatformAccount]
    ) -> Dict[str, int]:
        """Get current inventory levels from all platforms."""
        inventories = {}
        
        tasks = []
        platform_keys = []
        
        for account in platform_accounts:
            platform_product_id = mapping.get(f"{account.platform.value}_product_id")
            if platform_product_id:
                tasks.append(self._get_inventory_from_platform(account, platform_product_id))
                platform_keys.append(account.platform.value)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for key, result in zip(platform_keys, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to get inventory from {key}: {str(result)}")
                    inventories[key] = 0
                else:
                    inventories[key] = result
        
        return inventories
    
    async def _get_inventory_from_platform(
        self,
        account: PlatformAccount,
        platform_product_id: str
    ) -> int:
        """Get inventory level from a specific platform."""
        api = await self.platform_manager.get_platform_api(account.platform, account.id)
        
        async with api:
            if account.platform == PlatformType.COUPANG:
                result = await api.get_inventory([platform_product_id])
                # Extract quantity from Coupang response
                return result.get("data", [{}])[0].get("quantity", 0)
                
            elif account.platform == PlatformType.NAVER:
                result = await api.get_stock([platform_product_id])
                # Extract quantity from Naver response
                return result.get("contents", [{}])[0].get("stockQuantity", 0)
                
            elif account.platform == PlatformType.ELEVENTH_STREET:
                result = await api.get_stock([platform_product_id])
                # Extract quantity from 11st response
                stock_info = result.get("StockList", {}).get("Stock", [{}])[0]
                return int(stock_info.get("prdSelQty", 0))
        
        return 0
    
    async def _calculate_unified_inventory(
        self,
        product_id: int,
        platform_inventories: Dict[str, int]
    ) -> int:
        """Calculate unified inventory based on platform inventories and local data."""
        # Get local product
        product = await self.db_session.get(Product, product_id)
        if not product:
            return 0
        
        # Strategy 1: Use minimum inventory across platforms (conservative)
        if platform_inventories:
            min_inventory = min(platform_inventories.values())
            
            # If local inventory differs significantly, log warning
            if abs(product.stock_quantity - min_inventory) > 5:
                logger.warning(
                    f"Large inventory discrepancy for product {product_id}: "
                    f"Local={product.stock_quantity}, Platforms={platform_inventories}"
                )
            
            return min_inventory
        
        # If no platform data, use local inventory
        return product.stock_quantity
    
    async def _update_platform_inventories(
        self,
        mapping: Dict[str, Any],
        platform_accounts: List[PlatformAccount],
        unified_inventory: int
    ) -> Dict[str, Any]:
        """Update inventory on all platforms with unified value."""
        results = {}
        
        tasks = []
        platform_keys = []
        
        for account in platform_accounts:
            platform_product_id = mapping.get(f"{account.platform.value}_product_id")
            if platform_product_id:
                tasks.append(
                    self._update_inventory_on_platform(
                        account,
                        platform_product_id,
                        unified_inventory
                    )
                )
                platform_keys.append(account.platform.value)
        
        if tasks:
            sync_results = await asyncio.gather(*tasks, return_exceptions=True)
            for key, result in zip(platform_keys, sync_results):
                if isinstance(result, Exception):
                    results[key] = {"success": False, "error": str(result)}
                else:
                    results[key] = result
        
        # Update local inventory
        product = await self.db_session.get(Product, mapping["unified_product_id"])
        if product:
            product.stock_quantity = unified_inventory
        
        return results
    
    async def _update_inventory_on_platform(
        self,
        account: PlatformAccount,
        platform_product_id: str,
        quantity: int
    ) -> Dict[str, Any]:
        """Update inventory on a specific platform."""
        try:
            api = await self.platform_manager.get_platform_api(account.platform, account.id)
            
            async with api:
                if account.platform == PlatformType.COUPANG:
                    result = await api.update_inventory(
                        platform_product_id,
                        platform_product_id,  # vendor_item_id
                        quantity
                    )
                else:
                    result = await api.update_stock(platform_product_id, quantity)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _sync_product_inventory_to_platforms(
        self,
        product: Product,
        platform_accounts: List[PlatformAccount],
        quantity: int
    ) -> Dict[str, Any]:
        """Sync single product inventory to all platforms."""
        results = {}
        
        for account in platform_accounts:
            platform_product_id = self._get_platform_product_id(product, account.platform)
            if platform_product_id:
                result = await self._update_inventory_on_platform(
                    account,
                    platform_product_id,
                    quantity
                )
                results[account.platform.value] = result
        
        return results
    
    async def _disable_product_on_platform(
        self,
        account: PlatformAccount,
        platform_product_id: str
    ) -> Dict[str, Any]:
        """Disable product on a specific platform."""
        try:
            api = await self.platform_manager.get_platform_api(account.platform, account.id)
            
            async with api:
                if account.platform == PlatformType.COUPANG:
                    # Coupang: Change product status to STOP_SELLING
                    result = await api.update_product(
                        platform_product_id,
                        {"status": "STOP_SELLING"}
                    )
                elif account.platform == PlatformType.NAVER:
                    # Naver: Change product status to SUSPENSION
                    result = await api.update_product(
                        platform_product_id,
                        {"productStatusType": "SUSPENSION"}
                    )
                elif account.platform == PlatformType.ELEVENTH_STREET:
                    # 11st: Use delete method which sets status to stop
                    result = await api.delete_product(platform_product_id)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _log_inventory_sync(
        self,
        product_id: int,
        platform_inventories: Dict[str, int],
        unified_inventory: int,
        sync_results: Dict[str, Any]
    ):
        """Log inventory synchronization operation."""
        log_data = {
            "product_id": product_id,
            "movement_type": InventoryMovement.SYNC,
            "quantity_change": 0,  # Sync doesn't change total quantity
            "reference": "inventory_sync",
            "notes": {
                "platform_inventories": platform_inventories,
                "unified_inventory": unified_inventory,
                "sync_results": sync_results
            }
        }
        
        await inventory_log_crud.create(self.db_session, obj_in=log_data)
    
    async def _log_inventory_movement(
        self,
        product_id: int,
        operation: str,
        quantity: int,
        reference: str
    ):
        """Log inventory movement."""
        movement_type = (
            InventoryMovement.SALE if operation == "decrease"
            else InventoryMovement.RETURN
        )
        
        log_data = {
            "product_id": product_id,
            "movement_type": movement_type,
            "quantity_change": -quantity if operation == "decrease" else quantity,
            "reference": reference
        }
        
        await inventory_log_crud.create(self.db_session, obj_in=log_data)
    
    async def _get_product_platform_accounts(self, user_id: int) -> List[PlatformAccount]:
        """Get all active platform accounts for a user."""
        result = await self.db_session.execute(
            select(PlatformAccount).where(
                PlatformAccount.user_id == user_id,
                PlatformAccount.is_active == True
            )
        )
        return result.scalars().all()
    
    def _get_platform_product_id(self, product: Product, platform: PlatformType) -> Optional[str]:
        """Get platform-specific product ID."""
        if not product.platform_data:
            return None
        
        platform_info = product.platform_data.get(platform.value, {})
        return platform_info.get("product_id")
    
    def _get_safety_stock_level(self, product: Product) -> int:
        """Determine safety stock level for a product."""
        # This could be more sophisticated based on:
        # - Historical sales data
        # - Product category
        # - Seasonality
        # - Lead time
        
        # For now, use simple logic
        if product.tags and "high_volume" in product.tags:
            return self.safety_stock_levels["high_volume"]
        elif product.tags and "low_volume" in product.tags:
            return self.safety_stock_levels["low_volume"]
        else:
            return self.safety_stock_levels["default"]