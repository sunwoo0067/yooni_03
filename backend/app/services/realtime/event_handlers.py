"""
강화된 실시간 이벤트 핸들러
상품, 주문, 재고, 가격 변경 이벤트를 처리하는 개별 핸들러
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from sqlalchemy.orm import Session

from app.services.realtime.event_processor import EventProcessor, EventType
from app.services.realtime.websocket_manager import connection_manager
from app.core.logging import logger
from app.models.product import Product
from app.models.order_core import Order
from app.models.inventory import Inventory
from app.services.cache_service import CacheService


class ProductEventHandler:
    """상품 관련 이벤트 핸들러"""
    
    def __init__(self):
        self.cache = CacheService()
        self.event_processor = EventProcessor()
        
    async def handle_product_created(
        self,
        user_id: int,
        product: Product,
        db: Session
    ) -> None:
        """상품 생성 이벤트 처리"""
        try:
            # 이벤트 데이터 준비
            event_data = {
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "platform": product.platform,
                    "price": product.price,
                    "created_at": product.created_at.isoformat()
                }
            }
            
            # WebSocket으로 실시간 알림
            await connection_manager.broadcast_to_channel(
                f"products:{user_id}",
                {
                    "type": "product_created",
                    "data": event_data["product"]
                }
            )
            
            # 캐시 무효화
            await self._invalidate_product_cache(user_id)
            
            logger.info(f"상품 생성 이벤트 처리 완료: product_id={product.id}")
            
        except Exception as e:
            logger.error(f"상품 생성 이벤트 처리 실패: {str(e)}")
            
    async def handle_product_updated(
        self,
        user_id: int,
        product: Product,
        changes: Dict[str, Any],
        db: Session
    ) -> None:
        """상품 업데이트 이벤트 처리"""
        try:
            # 가격 변경 확인
            if "price" in changes:
                await self.event_processor.process_event(
                    EventType.PRICE_UPDATED,
                    user_id,
                    {
                        "price": {
                            "product_id": product.id,
                            "product_name": product.name,
                            "old_price": changes["price"]["old"],
                            "new_price": changes["price"]["new"],
                            "platform": product.platform
                        }
                    },
                    db
                )
                
            # 상품 업데이트 알림
            await connection_manager.broadcast_to_channel(
                f"products:{user_id}",
                {
                    "type": "product_updated",
                    "data": {
                        "id": product.id,
                        "changes": changes,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            # 캐시 무효화
            await self._invalidate_product_cache(user_id)
            
        except Exception as e:
            logger.error(f"상품 업데이트 이벤트 처리 실패: {str(e)}")
            
    async def handle_product_deleted(
        self,
        user_id: int,
        product_id: int,
        db: Session
    ) -> None:
        """상품 삭제 이벤트 처리"""
        try:
            # 삭제 알림
            await connection_manager.broadcast_to_channel(
                f"products:{user_id}",
                {
                    "type": "product_deleted",
                    "data": {
                        "id": product_id,
                        "deleted_at": datetime.now().isoformat()
                    }
                }
            )
            
            # 캐시 무효화
            await self._invalidate_product_cache(user_id)
            
        except Exception as e:
            logger.error(f"상품 삭제 이벤트 처리 실패: {str(e)}")
            
    async def handle_bulk_products_updated(
        self,
        user_id: int,
        product_ids: List[int],
        update_type: str,
        db: Session
    ) -> None:
        """대량 상품 업데이트 이벤트 처리"""
        try:
            # 대량 업데이트 알림
            await connection_manager.broadcast_to_channel(
                f"products:{user_id}",
                {
                    "type": "bulk_products_updated",
                    "data": {
                        "product_ids": product_ids,
                        "count": len(product_ids),
                        "update_type": update_type,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            # 캐시 무효화
            await self._invalidate_product_cache(user_id)
            
        except Exception as e:
            logger.error(f"대량 상품 업데이트 이벤트 처리 실패: {str(e)}")
            
    async def _invalidate_product_cache(self, user_id: int) -> None:
        """상품 캐시 무효화"""
        try:
            cache_keys = [
                f"products:list:{user_id}",
                f"products:count:{user_id}",
                f"products:stats:{user_id}"
            ]
            
            for key in cache_keys:
                await self.cache.delete(key)
                
        except Exception as e:
            logger.error(f"캐시 무효화 실패: {str(e)}")


class OrderEventHandler:
    """주문 관련 이벤트 핸들러"""
    
    def __init__(self):
        self.cache = CacheService()
        self.event_processor = EventProcessor()
        
    async def handle_order_created(
        self,
        user_id: int,
        order: Order,
        db: Session
    ) -> None:
        """주문 생성 이벤트 처리"""
        try:
            # 이벤트 프로세서로 처리
            await self.event_processor.process_event(
                EventType.ORDER_CREATED,
                user_id,
                {
                    "order": {
                        "id": order.id,
                        "platform": order.platform,
                        "order_number": order.order_number,
                        "total_amount": order.total_amount,
                        "items_count": len(order.items),
                        "customer": {
                            "name": order.customer_name,
                            "phone": order.customer_phone
                        },
                        "created_at": order.created_at.isoformat()
                    }
                },
                db
            )
            
            # 주문 목록 갱신 알림
            await self._broadcast_order_list_update(user_id)
            
        except Exception as e:
            logger.error(f"주문 생성 이벤트 처리 실패: {str(e)}")
            
    async def handle_order_status_changed(
        self,
        user_id: int,
        order: Order,
        old_status: str,
        new_status: str,
        db: Session
    ) -> None:
        """주문 상태 변경 이벤트 처리"""
        try:
            # 이벤트 프로세서로 처리
            await self.event_processor.process_event(
                EventType.ORDER_STATUS_CHANGED,
                user_id,
                {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "old_status": old_status,
                    "new_status": new_status
                },
                db
            )
            
            # 특정 상태 변경에 대한 추가 처리
            if new_status == "cancelled":
                await self.event_processor.process_event(
                    EventType.ORDER_CANCELLED,
                    user_id,
                    {
                        "order": {
                            "id": order.id,
                            "order_number": order.order_number,
                            "total_amount": order.total_amount,
                            "items": [
                                {
                                    "product_id": item.product_id,
                                    "quantity": item.quantity
                                }
                                for item in order.items
                            ]
                        },
                        "reason": order.cancel_reason or "사유 없음"
                    },
                    db
                )
                
        except Exception as e:
            logger.error(f"주문 상태 변경 이벤트 처리 실패: {str(e)}")
            
    async def handle_bulk_order_status_update(
        self,
        user_id: int,
        order_ids: List[int],
        new_status: str,
        db: Session
    ) -> None:
        """대량 주문 상태 업데이트 이벤트 처리"""
        try:
            # 대량 업데이트 알림
            await connection_manager.broadcast_to_channel(
                f"orders:{user_id}",
                {
                    "type": "bulk_order_status_update",
                    "data": {
                        "order_ids": order_ids,
                        "count": len(order_ids),
                        "new_status": new_status,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            # 주문 목록 갱신 알림
            await self._broadcast_order_list_update(user_id)
            
        except Exception as e:
            logger.error(f"대량 주문 상태 업데이트 이벤트 처리 실패: {str(e)}")
            
    async def _broadcast_order_list_update(self, user_id: int) -> None:
        """주문 목록 업데이트 브로드캐스트"""
        try:
            await connection_manager.broadcast_to_channel(
                f"orders:{user_id}",
                {
                    "type": "order_list_updated",
                    "data": {
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
        except Exception as e:
            logger.error(f"주문 목록 업데이트 브로드캐스트 실패: {str(e)}")


class InventoryEventHandler:
    """재고 관련 이벤트 핸들러"""
    
    def __init__(self):
        self.cache = CacheService()
        self.event_processor = EventProcessor()
        
    async def handle_inventory_updated(
        self,
        user_id: int,
        inventory: Inventory,
        old_quantity: int,
        new_quantity: int,
        db: Session
    ) -> None:
        """재고 업데이트 이벤트 처리"""
        try:
            # 이벤트 프로세서로 처리
            await self.event_processor.process_event(
                EventType.INVENTORY_UPDATED,
                user_id,
                {
                    "inventory": {
                        "id": inventory.id,
                        "product_id": inventory.product_id,
                        "product_name": inventory.product.name if inventory.product else "Unknown",
                        "platform": inventory.platform,
                        "old_quantity": old_quantity,
                        "new_quantity": new_quantity,
                        "min_quantity": inventory.min_quantity or 10,
                        "recommended_order": self._calculate_recommended_order(inventory)
                    }
                },
                db
            )
            
            # 재고 목록 갱신 알림
            await self._broadcast_inventory_update(user_id)
            
        except Exception as e:
            logger.error(f"재고 업데이트 이벤트 처리 실패: {str(e)}")
            
    async def handle_bulk_inventory_sync(
        self,
        user_id: int,
        platform: str,
        sync_results: Dict[str, Any],
        db: Session
    ) -> None:
        """대량 재고 동기화 이벤트 처리"""
        try:
            # 동기화 결과 알림
            await connection_manager.broadcast_to_channel(
                f"inventory:{user_id}",
                {
                    "type": "bulk_inventory_sync",
                    "data": {
                        "platform": platform,
                        "total_synced": sync_results.get("total", 0),
                        "updated": sync_results.get("updated", 0),
                        "failed": sync_results.get("failed", 0),
                        "synced_at": datetime.now().isoformat()
                    }
                }
            )
            
            # 재고 목록 갱신 알림
            await self._broadcast_inventory_update(user_id)
            
        except Exception as e:
            logger.error(f"대량 재고 동기화 이벤트 처리 실패: {str(e)}")
            
    async def handle_stock_alert(
        self,
        user_id: int,
        alert_type: str,
        products: List[Dict[str, Any]],
        db: Session
    ) -> None:
        """재고 알림 이벤트 처리"""
        try:
            # 재고 알림 브로드캐스트
            await connection_manager.broadcast_to_channel(
                f"alerts:{user_id}",
                {
                    "type": "stock_alert",
                    "data": {
                        "alert_type": alert_type,  # "low_stock", "out_of_stock", "overstock"
                        "products": products,
                        "count": len(products),
                        "created_at": datetime.now().isoformat()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"재고 알림 이벤트 처리 실패: {str(e)}")
            
    def _calculate_recommended_order(self, inventory: Inventory) -> int:
        """추천 주문 수량 계산"""
        try:
            # 간단한 추천 로직 (실제로는 더 복잡한 로직 필요)
            min_quantity = inventory.min_quantity or 10
            current_quantity = inventory.quantity or 0
            
            if current_quantity == 0:
                return min_quantity * 3
            elif current_quantity < min_quantity:
                return min_quantity * 2
            else:
                return 0
                
        except Exception:
            return 0
            
    async def _broadcast_inventory_update(self, user_id: int) -> None:
        """재고 업데이트 브로드캐스트"""
        try:
            await connection_manager.broadcast_to_channel(
                f"inventory:{user_id}",
                {
                    "type": "inventory_list_updated",
                    "data": {
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
        except Exception as e:
            logger.error(f"재고 업데이트 브로드캐스트 실패: {str(e)}")


class PriceEventHandler:
    """가격 관련 이벤트 핸들러"""
    
    def __init__(self):
        self.cache = CacheService()
        self.event_processor = EventProcessor()
        
    async def handle_price_updated(
        self,
        user_id: int,
        product_id: int,
        old_price: float,
        new_price: float,
        platform: str,
        db: Session
    ) -> None:
        """가격 업데이트 이벤트 처리"""
        try:
            # 가격 변화율 계산
            change_percentage = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
            
            # 가격 업데이트 알림
            await connection_manager.broadcast_to_channel(
                f"prices:{user_id}",
                {
                    "type": "price_updated",
                    "data": {
                        "product_id": product_id,
                        "old_price": old_price,
                        "new_price": new_price,
                        "change_percentage": round(change_percentage, 2),
                        "platform": platform,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            # 중요한 가격 변동은 알림
            if abs(change_percentage) > 10:
                await connection_manager.send_notification(
                    user_id,
                    {
                        "type": "warning" if change_percentage > 0 else "info",
                        "title": "가격 변동 알림",
                        "message": f"상품의 가격이 {change_percentage:+.1f}% 변경되었습니다.",
                        "priority": "high" if abs(change_percentage) > 20 else "medium"
                    }
                )
                
        except Exception as e:
            logger.error(f"가격 업데이트 이벤트 처리 실패: {str(e)}")
            
    async def handle_competitor_price_change(
        self,
        user_id: int,
        product_id: int,
        competitor_data: Dict[str, Any],
        db: Session
    ) -> None:
        """경쟁사 가격 변경 이벤트 처리"""
        try:
            # 경쟁사 가격 변경 알림
            await connection_manager.broadcast_to_channel(
                f"competitor:{user_id}",
                {
                    "type": "competitor_price_change",
                    "data": {
                        "product_id": product_id,
                        "competitor": competitor_data.get("name"),
                        "competitor_price": competitor_data.get("price"),
                        "our_price": competitor_data.get("our_price"),
                        "price_difference": competitor_data.get("price_difference"),
                        "detected_at": datetime.now().isoformat()
                    }
                }
            )
            
            # 가격 경쟁력 알림
            if competitor_data.get("price_difference", 0) < -10:
                await connection_manager.send_notification(
                    user_id,
                    {
                        "type": "warning",
                        "title": "가격 경쟁력 알림",
                        "message": f"경쟁사보다 가격이 {abs(competitor_data.get('price_difference', 0)):.1f}% 높습니다.",
                        "priority": "high",
                        "action": {
                            "type": "review_price",
                            "product_id": product_id
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"경쟁사 가격 변경 이벤트 처리 실패: {str(e)}")


# 전역 이벤트 핸들러 인스턴스
product_event_handler = ProductEventHandler()
order_event_handler = OrderEventHandler()
inventory_event_handler = InventoryEventHandler()
price_event_handler = PriceEventHandler()