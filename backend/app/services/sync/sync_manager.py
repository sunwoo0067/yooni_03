"""Synchronization Manager for coordinating all sync operations."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.platform_account import PlatformAccount, PlatformType
from app.models.product import Product
from app.models.order_core import Order
from app.services.platforms.platform_manager import PlatformManager
from app.services.sync.product_sync import ProductSyncService
from app.services.sync.order_sync import OrderSyncService
from app.services.sync.inventory_sync import InventorySyncService

logger = logging.getLogger(__name__)


class SyncStatus:
    """Sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class SyncManager:
    """Manages all synchronization operations across platforms."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize Sync Manager.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self.platform_manager = PlatformManager(db_session)
        self.product_sync = ProductSyncService(db_session, self.platform_manager)
        self.order_sync = OrderSyncService(db_session, self.platform_manager)
        self.inventory_sync = InventorySyncService(db_session, self.platform_manager)
        
        # Sync status tracking
        self._active_syncs = {}
        self._sync_history = []
        
    async def sync_all(self, user_id: int, sync_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Perform full synchronization for a user.
        
        Args:
            user_id: User ID
            sync_types: List of sync types to perform (products, orders, inventory)
                       If None, performs all sync types
            
        Returns:
            Sync results
        """
        sync_id = self._generate_sync_id()
        self._active_syncs[sync_id] = {
            "status": SyncStatus.IN_PROGRESS,
            "started_at": datetime.now(),
            "user_id": user_id,
            "types": sync_types or ["products", "orders", "inventory"]
        }
        
        try:
            # Get all active platform accounts for user
            platform_accounts = await self._get_user_platform_accounts(user_id)
            if not platform_accounts:
                raise ValueError("No active platform accounts found")
            
            results = {
                "sync_id": sync_id,
                "started_at": datetime.now(),
                "platforms": [acc.platform.value for acc in platform_accounts]
            }
            
            # Determine which syncs to perform
            sync_types = sync_types or ["products", "orders", "inventory"]
            
            # Execute syncs in order
            if "products" in sync_types:
                results["products"] = await self.sync_products(user_id, platform_accounts)
                
            if "orders" in sync_types:
                results["orders"] = await self.sync_orders(user_id, platform_accounts)
                
            if "inventory" in sync_types:
                results["inventory"] = await self.sync_inventory(user_id, platform_accounts)
            
            # Update sync status
            self._active_syncs[sync_id]["status"] = SyncStatus.COMPLETED
            self._active_syncs[sync_id]["completed_at"] = datetime.now()
            results["status"] = SyncStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Sync failed for user {user_id}: {str(e)}")
            self._active_syncs[sync_id]["status"] = SyncStatus.FAILED
            self._active_syncs[sync_id]["error"] = str(e)
            results["status"] = SyncStatus.FAILED
            results["error"] = str(e)
            
        finally:
            # Store in history
            self._sync_history.append(self._active_syncs[sync_id])
            # Keep only last 100 sync records
            if len(self._sync_history) > 100:
                self._sync_history = self._sync_history[-100:]
        
        return results
    
    async def sync_products(self, user_id: int, platform_accounts: Optional[List[PlatformAccount]] = None) -> Dict[str, Any]:
        """Sync products across platforms.
        
        Args:
            user_id: User ID
            platform_accounts: Optional list of platform accounts to sync
            
        Returns:
            Product sync results
        """
        if not platform_accounts:
            platform_accounts = await self._get_user_platform_accounts(user_id)
        
        logger.info(f"Starting product sync for user {user_id}")
        
        results = {
            "synced_count": 0,
            "created_count": 0,
            "updated_count": 0,
            "failed_count": 0,
            "platform_results": {}
        }
        
        try:
            # Get all products for user
            products = await self._get_user_products(user_id)
            
            for product in products:
                try:
                    sync_result = await self.product_sync.sync_product_to_platforms(
                        product,
                        platform_accounts
                    )
                    
                    # Count results
                    for platform_result in sync_result.values():
                        if platform_result.get("success"):
                            if platform_result.get("action") == "created":
                                results["created_count"] += 1
                            else:
                                results["updated_count"] += 1
                        else:
                            results["failed_count"] += 1
                    
                    results["synced_count"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync product {product.id}: {str(e)}")
                    results["failed_count"] += 1
            
            # Sync products from platforms to local
            platform_sync_results = await self.product_sync.sync_products_from_platforms(
                platform_accounts
            )
            results["platform_results"] = platform_sync_results
            
        except Exception as e:
            logger.error(f"Product sync error: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    async def sync_orders(self, user_id: int, platform_accounts: Optional[List[PlatformAccount]] = None) -> Dict[str, Any]:
        """Sync orders from platforms.
        
        Args:
            user_id: User ID
            platform_accounts: Optional list of platform accounts to sync
            
        Returns:
            Order sync results
        """
        if not platform_accounts:
            platform_accounts = await self._get_user_platform_accounts(user_id)
        
        logger.info(f"Starting order sync for user {user_id}")
        
        # Default to last 7 days if not specified
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        results = {
            "synced_count": 0,
            "new_orders": 0,
            "updated_orders": 0,
            "platform_results": {}
        }
        
        try:
            sync_results = await self.order_sync.sync_orders_from_platforms(
                platform_accounts,
                start_date,
                end_date
            )
            
            for platform, orders in sync_results.items():
                if isinstance(orders, list):
                    results["synced_count"] += len(orders)
                    results["platform_results"][platform] = {
                        "count": len(orders),
                        "status": "success"
                    }
                else:
                    results["platform_results"][platform] = {
                        "status": "error",
                        "error": str(orders)
                    }
            
        except Exception as e:
            logger.error(f"Order sync error: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    async def sync_inventory(self, user_id: int, platform_accounts: Optional[List[PlatformAccount]] = None) -> Dict[str, Any]:
        """Sync inventory across platforms.
        
        Args:
            user_id: User ID
            platform_accounts: Optional list of platform accounts to sync
            
        Returns:
            Inventory sync results
        """
        if not platform_accounts:
            platform_accounts = await self._get_user_platform_accounts(user_id)
        
        logger.info(f"Starting inventory sync for user {user_id}")
        
        results = {
            "synced_products": 0,
            "platform_results": {},
            "low_stock_alerts": []
        }
        
        try:
            # Get product mappings
            product_mappings = await self._get_product_mappings(user_id)
            
            # Sync inventory levels
            sync_results = await self.inventory_sync.sync_inventory_levels(
                product_mappings,
                platform_accounts
            )
            
            results["synced_products"] = len(sync_results)
            results["platform_results"] = sync_results
            
            # Check for low stock
            low_stock = await self.inventory_sync.check_low_stock(user_id)
            results["low_stock_alerts"] = low_stock
            
        except Exception as e:
            logger.error(f"Inventory sync error: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    async def get_sync_status(self, sync_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of sync operations.
        
        Args:
            sync_id: Optional specific sync ID to get status for
            
        Returns:
            Sync status information
        """
        if sync_id:
            return self._active_syncs.get(sync_id, {"error": "Sync ID not found"})
        
        return {
            "active_syncs": self._active_syncs,
            "recent_history": self._sync_history[-10:]  # Last 10 syncs
        }
    
    async def test_platform_connection(self, platform_type: PlatformType, account_id: int) -> Dict[str, Any]:
        """Test connection to a specific platform.
        
        Args:
            platform_type: Platform type
            account_id: Platform account ID
            
        Returns:
            Connection test results
        """
        try:
            api = await self.platform_manager.get_platform_api(platform_type, account_id)
            async with api:
                success = await api.test_connection()
                
            return {
                "platform": platform_type.value,
                "account_id": account_id,
                "connected": success,
                "tested_at": datetime.now()
            }
            
        except Exception as e:
            return {
                "platform": platform_type.value,
                "account_id": account_id,
                "connected": False,
                "error": str(e),
                "tested_at": datetime.now()
            }
    
    async def schedule_sync(self, user_id: int, schedule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule automatic synchronization.
        
        Args:
            user_id: User ID
            schedule_config: Configuration for scheduled sync including:
                - interval: Sync interval in minutes
                - sync_types: List of sync types to perform
                - active_hours: Optional active hours configuration
                
        Returns:
            Schedule configuration
        """
        # This would typically integrate with a task scheduler like Celery
        # For now, we'll just store the configuration
        schedule = {
            "user_id": user_id,
            "interval_minutes": schedule_config.get("interval", 60),
            "sync_types": schedule_config.get("sync_types", ["products", "orders", "inventory"]),
            "active_hours": schedule_config.get("active_hours"),
            "created_at": datetime.now(),
            "next_run": datetime.now() + timedelta(minutes=schedule_config.get("interval", 60))
        }
        
        # In a real implementation, this would register with a scheduler
        logger.info(f"Scheduled sync for user {user_id}: {schedule}")
        
        return schedule
    
    # Helper methods
    async def _get_user_platform_accounts(self, user_id: int) -> List[PlatformAccount]:
        """Get all active platform accounts for a user."""
        result = await self.db_session.execute(
            select(PlatformAccount).where(
                PlatformAccount.user_id == user_id,
                PlatformAccount.is_active == True
            )
        )
        return result.scalars().all()
    
    async def _get_user_products(self, user_id: int) -> List[Product]:
        """Get all products for a user."""
        result = await self.db_session.execute(
            select(Product).where(
                Product.user_id == user_id,
                Product.is_active == True
            )
        )
        return result.scalars().all()
    
    async def _get_product_mappings(self, user_id: int) -> List[Dict[str, Any]]:
        """Get product platform mappings for inventory sync."""
        products = await self._get_user_products(user_id)
        
        mappings = []
        for product in products:
            mapping = {
                "unified_product_id": product.id,
                "unified_stock": product.stock_quantity
            }
            
            # Add platform-specific product IDs
            if product.platform_data:
                for platform, data in product.platform_data.items():
                    mapping[f"{platform}_product_id"] = data.get("product_id")
            
            mappings.append(mapping)
        
        return mappings
    
    def _generate_sync_id(self) -> str:
        """Generate unique sync ID."""
        import uuid
        return f"sync_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"