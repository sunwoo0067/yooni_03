"""Order synchronization service."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.order_core import Order, OrderStatus, OrderItem
from app.models.platform_account import PlatformAccount, PlatformType
from app.models.product import Product
from app.services.platforms.platform_manager import PlatformManager
from app.crud.base import CRUDBase

logger = logging.getLogger(__name__)

# Temporarily use direct database operations instead of CRUD
# order_crud = CRUDBase[Order](Order)  # Requires Order schema definitions
# order_item_crud = CRUDBase[OrderItem](OrderItem)  # Requires OrderItem schema definitions


class OrderSyncService:
    """Service for synchronizing orders from platforms."""
    
    def __init__(self, db_session: AsyncSession, platform_manager: PlatformManager):
        """Initialize Order Sync Service.
        
        Args:
            db_session: Database session
            platform_manager: Platform manager instance
        """
        self.db_session = db_session
        self.platform_manager = platform_manager
    
    async def sync_orders_from_platforms(
        self,
        platform_accounts: List[PlatformAccount],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Sync orders from multiple platforms.
        
        Args:
            platform_accounts: List of platform accounts to sync from
            start_date: Start date for order sync
            end_date: End date for order sync
            
        Returns:
            Sync results for each platform
        """
        results = {}
        
        for account in platform_accounts:
            try:
                # Get orders from platform
                platform_orders = await self._get_orders_from_platform(
                    account,
                    start_date,
                    end_date
                )
                
                sync_result = {
                    "total": len(platform_orders),
                    "created": 0,
                    "updated": 0,
                    "errors": []
                }
                
                for platform_order in platform_orders:
                    try:
                        # Check if order exists locally
                        local_order = await self._find_local_order(
                            platform_order["platform_order_id"],
                            account.platform
                        )
                        
                        if local_order:
                            # Update existing order
                            await self._update_local_order(
                                local_order,
                                platform_order,
                                account
                            )
                            sync_result["updated"] += 1
                        else:
                            # Create new order
                            await self._create_local_order(
                                platform_order,
                                account
                            )
                            sync_result["created"] += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to sync order from {account.platform.value}: {str(e)}")
                        sync_result["errors"].append(str(e))
                
                results[f"{account.platform.value}_{account.name}"] = sync_result
                
            except Exception as e:
                logger.error(f"Failed to get orders from {account.platform.value}: {str(e)}")
                results[f"{account.platform.value}_{account.name}"] = {
                    "error": str(e)
                }
        
        return results
    
    async def update_order_status_on_platforms(
        self,
        order: Order,
        new_status: OrderStatus,
        shipping_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Update order status on platforms.
        
        Args:
            order: Order to update
            new_status: New order status
            shipping_info: Optional shipping information for shipped orders
            
        Returns:
            Update results for each platform
        """
        results = {}
        
        # Get platform account
        account = await self.db_session.get(PlatformAccount, order.platform_account_id)
        if not account:
            return {"error": "Platform account not found"}
        
        try:
            api = await self.platform_manager.get_platform_api(account.platform, account.id)
            
            async with api:
                if new_status == OrderStatus.SHIPPED and shipping_info:
                    # Update shipping information
                    if account.platform == PlatformType.COUPANG:
                        result = await api.update_shipping_info(
                            order.platform_order_id,
                            shipping_info
                        )
                    elif account.platform == PlatformType.NAVER:
                        result = await api.dispatch_order(
                            order.platform_order_id,
                            shipping_info
                        )
                    elif account.platform == PlatformType.ELEVENTH_STREET:
                        result = await api.update_delivery_info(
                            order.platform_order_id,
                            shipping_info
                        )
                        
                elif new_status == OrderStatus.CANCELLED:
                    # Cancel order
                    result = await api.cancel_order(
                        order.platform_order_id,
                        "Customer requested cancellation"
                    )
                    
                else:
                    # Other status updates
                    result = {"message": f"Status update to {new_status} not implemented"}
                
                results[account.platform.value] = {
                    "success": True,
                    "result": result
                }
                
        except Exception as e:
            logger.error(f"Failed to update order status on {account.platform.value}: {str(e)}")
            results[account.platform.value] = {
                "success": False,
                "error": str(e)
            }
        
        return results
    
    async def _get_orders_from_platform(
        self,
        account: PlatformAccount,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get orders from a specific platform."""
        api = await self.platform_manager.get_platform_api(account.platform, account.id)
        
        async with api:
            result = await api.get_orders(start_date, end_date)
            
        # Normalize orders using platform manager
        return self.platform_manager._normalize_orders(result, account.platform)
    
    async def _find_local_order(
        self,
        platform_order_id: str,
        platform: PlatformType
    ) -> Optional[Order]:
        """Find local order by platform order ID."""
        result = await self.db_session.execute(
            select(Order).where(
                Order.platform_order_id == platform_order_id,
                Order.platform == platform
            )
        )
        return result.scalar_one_or_none()
    
    async def _create_local_order(
        self,
        platform_order: Dict[str, Any],
        account: PlatformAccount
    ) -> Order:
        """Create local order from platform order data."""
        # Map platform status to local status
        status = self._map_platform_status(platform_order["status"], account.platform)
        
        order_data = {
            "user_id": account.user_id,
            "platform": account.platform,
            "platform_account_id": account.id,
            "platform_order_id": platform_order["platform_order_id"],
            "order_number": self._generate_order_number(),
            "status": status,
            "customer_name": platform_order["customer_name"],
            "customer_phone": platform_order["customer_phone"],
            "customer_email": platform_order.get("customer_email"),
            "shipping_address": platform_order.get("shipping_address", {}),
            "billing_address": platform_order.get("billing_address", {}),
            "subtotal": platform_order["total_amount"],
            "shipping_cost": platform_order.get("shipping_cost", 0),
            "tax": platform_order.get("tax", 0),
            "total": platform_order["total_amount"],
            "currency": "KRW",
            "order_date": datetime.fromisoformat(platform_order["order_date"]) if isinstance(platform_order["order_date"], str) else platform_order["order_date"],
            "payment_method": platform_order.get("payment_method"),
            "payment_status": platform_order.get("payment_status", "paid"),
            "notes": platform_order.get("notes"),
            "platform_data": platform_order
        }
        
        # Create order
        order = await order_crud.create(self.db_session, obj_in=order_data)
        
        # Create order items
        for item_data in platform_order.get("items", []):
            await self._create_order_item(order, item_data, account)
        
        await self.db_session.commit()
        
        return order
    
    async def _update_local_order(
        self,
        local_order: Order,
        platform_order: Dict[str, Any],
        account: PlatformAccount
    ) -> Order:
        """Update local order with platform order data."""
        # Map platform status to local status
        status = self._map_platform_status(platform_order["status"], account.platform)
        
        # Update order fields
        local_order.status = status
        local_order.customer_name = platform_order["customer_name"]
        local_order.customer_phone = platform_order["customer_phone"]
        local_order.shipping_address = platform_order.get("shipping_address", {})
        local_order.total = platform_order["total_amount"]
        local_order.platform_data = platform_order
        local_order.updated_at = datetime.utcnow()
        
        # Update order items if needed
        # This is simplified - in production, you'd want to handle item updates more carefully
        
        await self.db_session.commit()
        
        return local_order
    
    async def _create_order_item(
        self,
        order: Order,
        item_data: Dict[str, Any],
        account: PlatformAccount
    ) -> OrderItem:
        """Create order item from platform item data."""
        # Try to find matching product
        product = await self._find_product_for_item(item_data, account)
        
        order_item_data = {
            "order_id": order.id,
            "product_id": product.id if product else None,
            "product_name": item_data["product_name"],
            "product_sku": item_data.get("product_sku"),
            "quantity": item_data["quantity"],
            "unit_price": item_data["price"],
            "total_price": item_data["quantity"] * item_data["price"],
            "platform_item_id": item_data.get("vendor_item_id") or item_data.get("product_id"),
            "platform_data": item_data
        }
        
        order_item = await order_item_crud.create(self.db_session, obj_in=order_item_data)
        
        # Update product stock if found
        if product and product.stock_quantity is not None:
            product.stock_quantity -= item_data["quantity"]
            if product.stock_quantity < 0:
                product.stock_quantity = 0
        
        return order_item
    
    async def _find_product_for_item(
        self,
        item_data: Dict[str, Any],
        account: PlatformAccount
    ) -> Optional[Product]:
        """Find matching product for order item."""
        # Try to find by platform product ID
        platform_product_id = item_data.get("vendor_item_id") or item_data.get("product_id")
        
        if platform_product_id:
            result = await self.db_session.execute(
                select(Product).where(
                    Product.user_id == account.user_id,
                    Product.platform_data[account.platform.value]["product_id"].astext == platform_product_id
                )
            )
            product = result.scalar_one_or_none()
            if product:
                return product
        
        # Try to find by SKU
        if item_data.get("product_sku"):
            result = await self.db_session.execute(
                select(Product).where(
                    Product.user_id == account.user_id,
                    Product.sku == item_data["product_sku"]
                )
            )
            product = result.scalar_one_or_none()
            if product:
                return product
        
        # Try to find by name (less reliable)
        result = await self.db_session.execute(
            select(Product).where(
                Product.user_id == account.user_id,
                Product.name == item_data["product_name"]
            )
        )
        return result.scalar_one_or_none()
    
    def _map_platform_status(self, platform_status: str, platform: PlatformType) -> OrderStatus:
        """Map platform-specific order status to local status."""
        # Status mapping for each platform
        status_mapping = {
            PlatformType.COUPANG: {
                "ACCEPT": OrderStatus.PENDING,
                "INSTRUCT": OrderStatus.PROCESSING,
                "DEPARTURE": OrderStatus.SHIPPED,
                "DELIVERING": OrderStatus.SHIPPED,
                "FINAL_DELIVERY": OrderStatus.DELIVERED,
                "NONE_TRACKING": OrderStatus.SHIPPED,
                "CANCEL": OrderStatus.CANCELLED,
                "RETURN": OrderStatus.REFUNDED
            },
            PlatformType.NAVER: {
                "PAYED": OrderStatus.PENDING,
                "PLACE": OrderStatus.PROCESSING,
                "DELIVERING": OrderStatus.SHIPPED,
                "DELIVERED": OrderStatus.DELIVERED,
                "PURCHASE_DECIDED": OrderStatus.COMPLETED,
                "CANCELED": OrderStatus.CANCELLED,
                "RETURNED": OrderStatus.REFUNDED,
                "EXCHANGED": OrderStatus.COMPLETED
            },
            PlatformType.ELEVENTH_STREET: {
                "101": OrderStatus.PENDING,      # Order received
                "201": OrderStatus.PROCESSING,   # Payment confirmed
                "301": OrderStatus.PROCESSING,   # Preparing shipment
                "401": OrderStatus.SHIPPED,      # Shipped
                "501": OrderStatus.DELIVERED,    # Delivered
                "601": OrderStatus.COMPLETED,    # Purchase confirmed
                "701": OrderStatus.CANCELLED,    # Cancelled
                "801": OrderStatus.REFUNDED     # Returned
            }
        }
        
        platform_mapping = status_mapping.get(platform, {})
        return platform_mapping.get(platform_status, OrderStatus.PENDING)
    
    def _generate_order_number(self) -> str:
        """Generate unique order number."""
        import uuid
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"ORD-{timestamp}-{unique_id}"
    
    async def process_webhooks(self, webhook_data: Dict[str, Any], platform: PlatformType) -> Dict[str, Any]:
        """Process order webhooks from platforms.
        
        Args:
            webhook_data: Webhook payload
            platform: Platform type
            
        Returns:
            Processing result
        """
        try:
            # Extract order information based on platform
            if platform == PlatformType.COUPANG:
                order_id = webhook_data.get("orderId")
                event_type = webhook_data.get("eventType")
                
            elif platform == PlatformType.NAVER:
                order_id = webhook_data.get("productOrderId")
                event_type = webhook_data.get("eventType")
                
            elif platform == PlatformType.ELEVENTH_STREET:
                order_id = webhook_data.get("ordNo")
                event_type = webhook_data.get("eventType")
                
            else:
                return {"error": f"Unsupported platform: {platform}"}
            
            # Find local order
            local_order = await self._find_local_order(order_id, platform)
            
            if not local_order:
                # New order - fetch from platform and create
                # This would require knowing which account the webhook is for
                return {"error": "Order not found and account information missing"}
            
            # Update order based on event type
            # This is simplified - real implementation would handle various events
            
            return {
                "success": True,
                "order_id": local_order.id,
                "event_type": event_type
            }
            
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return {"error": str(e)}