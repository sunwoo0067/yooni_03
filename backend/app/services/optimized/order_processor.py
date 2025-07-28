"""
최적화된 주문 처리 서비스
- 트랜잭션 관리 개선
- N+1 쿼리 해결
- 비동기 처리 최적화
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select, update, and_
import asyncio
import logging

from ...models.order import Order, OrderItem, OrderStatus
from ...models.product import Product
from ...models.dropshipping import DropshippingOrder, SupplierOrderStatus
from ...models.inventory import InventoryItem
from ..cache.cache_manager import CacheManager
from ...core.decorators import transactional, cached_query


class OptimizedOrderProcessor:
    """최적화된 주문 처리 서비스"""
    
    def __init__(self, db: AsyncSession, cache: CacheManager):
        self.db = db
        self.cache = cache
        self.logger = logging.getLogger(__name__)
    
    @transactional
    async def process_order_batch(self, order_ids: List[str]) -> Dict[str, Any]:
        """
        주문 일괄 처리 (트랜잭션 보장)
        N+1 쿼리 문제 해결
        """
        # 1. Eager loading으로 관련 데이터 한번에 조회
        stmt = select(Order).options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.dropshipping_orders)
        ).where(Order.id.in_(order_ids))
        
        result = await self.db.execute(stmt)
        orders = result.scalars().all()
        
        if not orders:
            return {"status": "error", "message": "주문을 찾을 수 없습니다"}
        
        # 2. 재고 확인 (bulk query)
        product_ids = [
            item.product_id 
            for order in orders 
            for item in order.items
        ]
        
        inventory_map = await self._get_inventory_bulk(product_ids)
        
        # 3. 병렬 처리를 위한 작업 준비
        processing_tasks = []
        for order in orders:
            # 재고 확인
            if not self._check_inventory(order, inventory_map):
                order.status = OrderStatus.OUT_OF_STOCK
                continue
            
            # 마진 확인 (캐시 활용)
            margin_ok = await self._check_margin_cached(order)
            if not margin_ok:
                order.status = OrderStatus.MARGIN_ERROR
                continue
            
            processing_tasks.append(self._process_single_order(order))
        
        # 4. 병렬 실행
        results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        
        # 5. 결과 집계
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.get('success'))
        
        # 6. 일괄 커밋 (트랜잭션 데코레이터가 처리)
        return {
            "status": "success",
            "processed": len(orders),
            "successful": success_count,
            "failed": len(orders) - success_count
        }
    
    async def _get_inventory_bulk(self, product_ids: List[str]) -> Dict[str, int]:
        """재고 일괄 조회"""
        stmt = select(InventoryItem).where(
            InventoryItem.product_id.in_(product_ids)
        )
        result = await self.db.execute(stmt)
        inventory_items = result.scalars().all()
        
        return {
            item.product_id: item.quantity 
            for item in inventory_items
        }
    
    def _check_inventory(self, order: Order, inventory_map: Dict[str, int]) -> bool:
        """재고 확인 (메모리에서 처리)"""
        for item in order.items:
            available = inventory_map.get(item.product_id, 0)
            if available < item.quantity:
                return False
        return True
    
    @cached_query(ttl=300)  # 5분 캐싱
    async def _check_margin_cached(self, order: Order) -> bool:
        """마진 확인 (캐시 활용)"""
        total_cost = 0
        total_revenue = 0
        
        for item in order.items:
            # Product는 이미 eager loading됨
            product = item.product
            total_cost += product.wholesale_price * item.quantity
            total_revenue += item.price * item.quantity
        
        margin = (total_revenue - total_cost) / total_revenue * 100
        return margin >= 15  # 최소 15% 마진
    
    async def _process_single_order(self, order: Order) -> Dict[str, Any]:
        """개별 주문 처리"""
        try:
            # 드랍쉬핑 주문 생성
            dropship_order = DropshippingOrder(
                order_id=order.id,
                supplier_id=order.items[0].product.wholesale_account_id,
                status=SupplierOrderStatus.PENDING,
                total_amount=sum(
                    item.product.wholesale_price * item.quantity 
                    for item in order.items
                )
            )
            self.db.add(dropship_order)
            
            # 재고 업데이트 (bulk update)
            for item in order.items:
                await self._update_inventory_async(item.product_id, -item.quantity)
            
            # 주문 상태 업데이트
            order.status = OrderStatus.PROCESSING
            order.processed_at = datetime.utcnow()
            
            return {"success": True, "order_id": order.id}
            
        except Exception as e:
            self.logger.error(f"주문 처리 실패 {order.id}: {str(e)}")
            return {"success": False, "order_id": order.id, "error": str(e)}
    
    async def _update_inventory_async(self, product_id: str, quantity_change: int):
        """비동기 재고 업데이트"""
        stmt = (
            update(InventoryItem)
            .where(InventoryItem.product_id == product_id)
            .values(quantity=InventoryItem.quantity + quantity_change)
        )
        await self.db.execute(stmt)
    
    async def get_order_with_details(self, order_id: str) -> Optional[Order]:
        """주문 상세 조회 (최적화된 쿼리)"""
        stmt = select(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.dropshipping_orders),
            joinedload(Order.platform_account)
        ).where(Order.id == order_id)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_pending_orders_paginated(
        self, 
        page: int = 1, 
        size: int = 100
    ) -> List[Order]:
        """대기 중인 주문 페이지네이션 조회"""
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.status == OrderStatus.PENDING)
            .order_by(Order.created_at)
            .offset((page - 1) * size)
            .limit(size)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()