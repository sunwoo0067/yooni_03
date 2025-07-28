"""
실제 주문 처리 서비스

마켓플레이스에서 수신된 주문을 자동으로 처리하고
도매처에 주문을 전달하는 핵심 서비스
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_core import Order, OrderStatus, OrderItem
from app.models.product import Product
from app.services.ordering.order_manager import OrderManager
from app.services.database.database import get_db
from app.core.exceptions import AppException


class OrderProcessingStatus(Enum):
    """주문 처리 상태"""
    PENDING = "pending"
    VALIDATING = "validating" 
    ORDERING = "ordering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OrderProcessingResult:
    """주문 처리 결과"""
    order_id: int
    status: OrderProcessingStatus
    wholesaler_order_id: Optional[str] = None
    tracking_number: Optional[str] = None
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None


class RealOrderProcessor:
    """실제 주문 처리기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.order_manager = OrderManager()
        
    async def process_new_orders(self, db: AsyncSession) -> List[OrderProcessingResult]:
        """새로운 주문들을 처리"""
        try:
            # 처리 대기 중인 주문 조회
            pending_orders = await self._get_pending_orders(db)
            
            if not pending_orders:
                self.logger.info("처리할 새로운 주문이 없습니다")
                return []
                
            self.logger.info(f"{len(pending_orders)}개의 주문 처리 시작")
            
            results = []
            for order in pending_orders:
                result = await self._process_single_order(db, order)
                results.append(result)
                
            return results
            
        except Exception as e:
            self.logger.error(f"주문 처리 중 오류 발생: {e}")
            raise
            
    async def _get_pending_orders(self, db: AsyncSession) -> List[Order]:
        """처리 대기 중인 주문 조회"""
        from sqlalchemy import select
        
        query = select(Order).where(
            Order.status == OrderStatus.PENDING
        ).order_by(Order.created_at)
        
        result = await db.execute(query)
        return result.scalars().all()
        
    async def _process_single_order(self, db: AsyncSession, order: Order) -> OrderProcessingResult:
        """단일 주문 처리"""
        result = OrderProcessingResult(
            order_id=order.id,
            status=OrderProcessingStatus.PENDING
        )
        
        try:
            # 1. 주문 유효성 검증
            self.logger.info(f"주문 검증 시작: {order.order_number}")
            result.status = OrderProcessingStatus.VALIDATING
            
            is_valid, error_msg = await self._validate_order(db, order)
            if not is_valid:
                result.status = OrderProcessingStatus.FAILED
                result.error_message = error_msg
                await self._update_order_status(db, order.id, OrderStatus.FAILED, error_msg)
                return result
                
            # 2. 재고 확인
            stock_available = await self._check_stock_availability(db, order)
            if not stock_available:
                result.status = OrderProcessingStatus.FAILED
                result.error_message = "재고 부족"
                await self._update_order_status(db, order.id, OrderStatus.FAILED, "재고 부족")
                return result
                
            # 3. 도매처 주문 생성
            self.logger.info(f"도매처 주문 생성 시작: {order.order_number}")
            result.status = OrderProcessingStatus.ORDERING
            
            wholesaler_result = await self._create_wholesaler_order(db, order)
            if not wholesaler_result['success']:
                result.status = OrderProcessingStatus.FAILED
                result.error_message = wholesaler_result['error']
                await self._update_order_status(db, order.id, OrderStatus.FAILED, wholesaler_result['error'])
                return result
                
            # 4. 주문 성공 처리
            result.status = OrderProcessingStatus.COMPLETED
            result.wholesaler_order_id = wholesaler_result['order_id']
            result.tracking_number = wholesaler_result.get('tracking_number')
            result.processed_at = datetime.now()
            
            await self._update_order_status(
                db, 
                order.id, 
                OrderStatus.PROCESSING,
                f"도매처 주문번호: {result.wholesaler_order_id}"
            )
            
            self.logger.info(f"주문 처리 완료: {order.order_number}")
            return result
            
        except Exception as e:
            self.logger.error(f"주문 처리 중 오류: {order.order_number} - {e}")
            result.status = OrderProcessingStatus.FAILED
            result.error_message = str(e)
            await self._update_order_status(db, order.id, OrderStatus.FAILED, str(e))
            return result
            
    async def _validate_order(self, db: AsyncSession, order: Order) -> Tuple[bool, Optional[str]]:
        """주문 유효성 검증"""
        # 필수 정보 확인
        if not order.customer_name or not order.customer_phone:
            return False, "고객 정보 누락"
            
        if not order.shipping_address:
            return False, "배송 주소 누락"
            
        # 주문 아이템 확인
        if not order.items or len(order.items) == 0:
            return False, "주문 상품이 없습니다"
            
        # 상품 존재 여부 확인
        for item in order.items:
            product = await db.get(Product, item.product_id)
            if not product:
                return False, f"상품을 찾을 수 없습니다: {item.product_id}"
                
            if not product.is_active:
                return False, f"판매 중지된 상품입니다: {product.name}"
                
        return True, None
        
    async def _check_stock_availability(self, db: AsyncSession, order: Order) -> bool:
        """재고 확인"""
        for item in order.items:
            product = await db.get(Product, item.product_id)
            if product.stock < item.quantity:
                self.logger.warning(f"재고 부족: {product.name} (필요: {item.quantity}, 재고: {product.stock})")
                return False
                
        return True
        
    async def _create_wholesaler_order(self, db: AsyncSession, order: Order) -> Dict:
        """도매처 주문 생성"""
        try:
            # 주문 항목별로 도매처 그룹화
            wholesaler_items = {}
            
            for item in order.items:
                product = await db.get(Product, item.product_id)
                wholesaler_id = product.wholesaler_id
                
                if wholesaler_id not in wholesaler_items:
                    wholesaler_items[wholesaler_id] = []
                    
                wholesaler_items[wholesaler_id].append({
                    'product': product,
                    'quantity': item.quantity,
                    'price': item.price
                })
                
            # 각 도매처별로 주문 생성
            all_success = True
            order_ids = []
            errors = []
            
            for wholesaler_id, items in wholesaler_items.items():
                result = await self.order_manager.create_order(
                    wholesaler_id=wholesaler_id,
                    items=items,
                    customer_info={
                        'name': order.customer_name,
                        'phone': order.customer_phone,
                        'address': order.shipping_address,
                        'memo': order.customer_memo
                    }
                )
                
                if result['success']:
                    order_ids.append(result['order_id'])
                else:
                    all_success = False
                    errors.append(result['error'])
                    
            if all_success:
                return {
                    'success': True,
                    'order_id': ','.join(order_ids),
                    'tracking_number': None  # 추후 배송 정보 업데이트
                }
            else:
                return {
                    'success': False,
                    'error': '; '.join(errors)
                }
                
        except Exception as e:
            self.logger.error(f"도매처 주문 생성 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def _update_order_status(
        self, 
        db: AsyncSession, 
        order_id: int, 
        status: OrderStatus,
        memo: Optional[str] = None
    ):
        """주문 상태 업데이트"""
        from sqlalchemy import update
        
        stmt = update(Order).where(
            Order.id == order_id
        ).values(
            status=status,
            updated_at=datetime.now()
        )
        
        if memo:
            stmt = stmt.values(internal_memo=memo)
            
        await db.execute(stmt)
        await db.commit()
        
    async def cancel_order(self, db: AsyncSession, order_id: int, reason: str) -> bool:
        """주문 취소"""
        try:
            order = await db.get(Order, order_id)
            if not order:
                raise AppException("주문을 찾을 수 없습니다", status_code=404)
                
            # 이미 발송된 주문은 취소 불가
            if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
                raise AppException("이미 발송된 주문은 취소할 수 없습니다", status_code=400)
                
            # 도매처 주문 취소
            if order.wholesaler_order_id:
                cancel_result = await self.order_manager.cancel_order(
                    order.wholesaler_id,
                    order.wholesaler_order_id,
                    reason
                )
                
                if not cancel_result['success']:
                    self.logger.warning(f"도매처 주문 취소 실패: {cancel_result['error']}")
                    
            # 주문 상태 업데이트
            await self._update_order_status(
                db, 
                order_id, 
                OrderStatus.CANCELLED,
                f"취소 사유: {reason}"
            )
            
            # 재고 복구
            for item in order.items:
                product = await db.get(Product, item.product_id)
                product.stock += item.quantity
                
            await db.commit()
            
            self.logger.info(f"주문 취소 완료: {order.order_number}")
            return True
            
        except Exception as e:
            self.logger.error(f"주문 취소 실패: {e}")
            raise
            
    async def get_order_status(self, db: AsyncSession, order_id: int) -> Dict:
        """주문 상태 조회"""
        order = await db.get(Order, order_id)
        if not order:
            raise AppException("주문을 찾을 수 없습니다", status_code=404)
            
        return {
            'order_id': order.id,
            'order_number': order.order_number,
            'status': order.status.value,
            'tracking_number': order.tracking_number,
            'wholesaler_order_id': order.wholesaler_order_id,
            'created_at': order.created_at,
            'updated_at': order.updated_at
        }


# 싱글톤 인스턴스
real_order_processor = RealOrderProcessor()