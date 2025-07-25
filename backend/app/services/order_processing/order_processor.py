"""
드롭쉬핑 주문 자동 처리 엔진
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.order import (
    Order, OrderStatus, DropshippingOrder, SupplierOrderStatus, 
    DropshippingOrderLog, OrderItem
)
from app.models.product import Product
from app.models.wholesaler import Wholesaler
from app.services.order_processing.order_validator import OrderValidator
from app.services.order_processing.margin_calculator import MarginCalculator
from app.services.order_processing.supplier_selector import SupplierSelector
from app.services.ordering.order_manager import OrderManager
from app.services.exception_handling.order_exception_handler import OrderExceptionHandler

logger = logging.getLogger(__name__)


class OrderProcessor:
    """드롭쉬핑 주문 자동 처리 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.validator = OrderValidator(db)
        self.margin_calculator = MarginCalculator(db)
        self.supplier_selector = SupplierSelector(db)
        self.order_manager = OrderManager(db)
        self.exception_handler = OrderExceptionHandler(db)
        
    async def process_order(self, order_id: str) -> Dict:
        """
        주문 자동 처리 메인 함수
        
        Args:
            order_id: 처리할 주문 ID
            
        Returns:
            Dict: 처리 결과
        """
        start_time = datetime.utcnow()
        processing_result = {
            'order_id': order_id,
            'success': False,
            'message': '',
            'processing_time': 0,
            'steps_completed': [],
            'errors': []
        }
        
        try:
            logger.info(f"주문 자동 처리 시작: {order_id}")
            
            # 1. 주문 조회 및 검증
            order = await self._get_and_validate_order(order_id)
            if not order:
                processing_result['message'] = '주문을 찾을 수 없거나 처리할 수 없는 상태입니다.'
                return processing_result
            
            processing_result['steps_completed'].append('order_validation')
            
            # 2. 드롭쉬핑 주문 생성 또는 조회
            dropshipping_order = await self._get_or_create_dropshipping_order(order)
            processing_result['steps_completed'].append('dropshipping_order_setup')
            
            # 3. 마진 검증
            margin_check = await self._check_margin_protection(dropshipping_order)
            if not margin_check['success']:
                processing_result['message'] = margin_check['message']
                processing_result['errors'].append(margin_check)
                return processing_result
            
            processing_result['steps_completed'].append('margin_validation')
            
            # 4. 최적 공급업체 선택
            supplier_selection = await self._select_optimal_supplier(order, dropshipping_order)
            if not supplier_selection['success']:
                processing_result['message'] = supplier_selection['message']
                processing_result['errors'].append(supplier_selection)
                return processing_result
            
            processing_result['steps_completed'].append('supplier_selection')
            
            # 5. 공급업체 발주 처리
            order_result = await self._submit_supplier_order(dropshipping_order)
            if not order_result['success']:
                processing_result['message'] = order_result['message']
                processing_result['errors'].append(order_result)
                return processing_result
            
            processing_result['steps_completed'].append('supplier_order_submission')
            
            # 6. 주문 상태 업데이트
            await self._update_order_status(order, dropshipping_order, order_result)
            processing_result['steps_completed'].append('status_update')
            
            # 7. 고객 알림 (필요시)
            await self._notify_customer_if_needed(order, dropshipping_order)
            processing_result['steps_completed'].append('customer_notification')
            
            processing_result['success'] = True
            processing_result['message'] = '주문이 성공적으로 처리되었습니다.'
            
            logger.info(f"주문 자동 처리 완료: {order_id}")
            
        except Exception as e:
            logger.error(f"주문 처리 중 예외 발생 ({order_id}): {str(e)}", exc_info=True)
            processing_result['message'] = f'처리 중 오류가 발생했습니다: {str(e)}'
            processing_result['errors'].append({
                'type': 'system_error',
                'message': str(e)
            })
            
            # 예외 상황 처리
            await self.exception_handler.handle_processing_exception(order_id, e)
            
        finally:
            # 처리 시간 계산
            end_time = datetime.utcnow()
            processing_result['processing_time'] = (end_time - start_time).total_seconds()
            
            # 처리 로그 저장
            await self._save_processing_log(order_id, processing_result)
            
        return processing_result
    
    async def process_bulk_orders(self, order_ids: List[str]) -> Dict:
        """
        대량 주문 일괄 처리
        
        Args:
            order_ids: 처리할 주문 ID 리스트
            
        Returns:
            Dict: 일괄 처리 결과
        """
        results = {
            'total_orders': len(order_ids),
            'successful_orders': 0,
            'failed_orders': 0,
            'results': [],
            'processing_time': 0
        }
        
        start_time = datetime.utcnow()
        
        for order_id in order_ids:
            try:
                result = await self.process_order(order_id)
                results['results'].append(result)
                
                if result['success']:
                    results['successful_orders'] += 1
                else:
                    results['failed_orders'] += 1
                    
            except Exception as e:
                logger.error(f"대량 처리 중 오류 ({order_id}): {str(e)}")
                results['results'].append({
                    'order_id': order_id,
                    'success': False,
                    'message': str(e)
                })
                results['failed_orders'] += 1
        
        end_time = datetime.utcnow()
        results['processing_time'] = (end_time - start_time).total_seconds()
        
        logger.info(f"대량 주문 처리 완료: {results['successful_orders']}/{results['total_orders']} 성공")
        
        return results
    
    async def retry_failed_order(self, order_id: str) -> Dict:
        """
        실패한 주문 재처리
        
        Args:
            order_id: 재처리할 주문 ID
            
        Returns:
            Dict: 재처리 결과
        """
        dropshipping_order = self.db.query(DropshippingOrder).join(Order).filter(
            Order.id == order_id
        ).first()
        
        if not dropshipping_order:
            return {
                'success': False,
                'message': '드롭쉬핑 주문을 찾을 수 없습니다.'
            }
        
        if not dropshipping_order.can_retry:
            return {
                'success': False,
                'message': '재시도 횟수를 초과했거나 수동 처리가 필요한 주문입니다.'
            }
        
        # 재시도 횟수 증가
        dropshipping_order.retry_count += 1
        self.db.commit()
        
        return await self.process_order(order_id)
    
    async def _get_and_validate_order(self, order_id: str) -> Optional[Order]:
        """주문 조회 및 검증"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            logger.warning(f"주문을 찾을 수 없음: {order_id}")
            return None
        
        # 주문 상태 검증
        valid_statuses = [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PAID]
        if order.status not in valid_statuses:
            logger.warning(f"처리할 수 없는 주문 상태: {order.status.value} (주문: {order_id})")
            return None
        
        # 결제 상태 검증
        if not order.is_paid:
            logger.warning(f"미결제 주문: {order_id}")
            return None
        
        return order
    
    async def _get_or_create_dropshipping_order(self, order: Order) -> DropshippingOrder:
        """드롭쉬핑 주문 생성 또는 조회"""
        dropshipping_order = self.db.query(DropshippingOrder).filter(
            DropshippingOrder.order_id == order.id
        ).first()
        
        if dropshipping_order:
            return dropshipping_order
        
        # 새 드롭쉬핑 주문 생성
        dropshipping_order = DropshippingOrder(
            order_id=order.id,
            supplier_id=None,  # 나중에 설정
            customer_price=order.total_amount,
            supplier_price=Decimal('0'),
            margin_amount=Decimal('0'),
            margin_rate=Decimal('0'),
            minimum_margin_rate=Decimal('10.0'),  # 기본 최소 마진율 10%
            status=SupplierOrderStatus.PENDING
        )
        
        self.db.add(dropshipping_order)
        self.db.commit()
        self.db.refresh(dropshipping_order)
        
        return dropshipping_order
    
    async def _check_margin_protection(self, dropshipping_order: DropshippingOrder) -> Dict:
        """마진 보호 검증"""
        try:
            return await self.margin_calculator.validate_margin(dropshipping_order)
        except Exception as e:
            logger.error(f"마진 검증 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'마진 검증 중 오류가 발생했습니다: {str(e)}'
            }
    
    async def _select_optimal_supplier(self, order: Order, dropshipping_order: DropshippingOrder) -> Dict:
        """최적 공급업체 선택"""
        try:
            return await self.supplier_selector.select_best_supplier(order, dropshipping_order)
        except Exception as e:
            logger.error(f"공급업체 선택 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'공급업체 선택 중 오류가 발생했습니다: {str(e)}'
            }
    
    async def _submit_supplier_order(self, dropshipping_order: DropshippingOrder) -> Dict:
        """공급업체 발주 처리"""
        try:
            return await self.order_manager.submit_order(dropshipping_order)
        except Exception as e:
            logger.error(f"공급업체 발주 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'공급업체 발주 중 오류가 발생했습니다: {str(e)}'
            }
    
    async def _update_order_status(self, order: Order, dropshipping_order: DropshippingOrder, order_result: Dict):
        """주문 상태 업데이트"""
        if order_result['success']:
            order.status = OrderStatus.SUPPLIER_ORDER_CONFIRMED
            dropshipping_order.status = SupplierOrderStatus.CONFIRMED
            dropshipping_order.supplier_order_id = order_result.get('supplier_order_id')
            dropshipping_order.supplier_confirmed_at = datetime.utcnow()
        else:
            order.status = OrderStatus.SUPPLIER_ORDER_FAILED
            dropshipping_order.status = SupplierOrderStatus.FAILED
            dropshipping_order.last_error_message = order_result.get('message')
            dropshipping_order.error_count += 1
        
        self.db.commit()
    
    async def _notify_customer_if_needed(self, order: Order, dropshipping_order: DropshippingOrder):
        """필요시 고객 알림"""
        # 발주 성공시 고객에게 처리 시작 알림
        if dropshipping_order.status == SupplierOrderStatus.CONFIRMED:
            logger.info(f"고객 알림 - 주문 처리 시작: {order.order_number}")
            # 실제 알림 로직은 notification service에서 구현
        
        # 발주 실패시 고객에게 지연 알림
        elif dropshipping_order.status == SupplierOrderStatus.FAILED:
            logger.info(f"고객 알림 - 주문 처리 지연: {order.order_number}")
    
    async def _save_processing_log(self, order_id: str, result: Dict):
        """처리 로그 저장"""
        try:
            dropshipping_order = self.db.query(DropshippingOrder).join(Order).filter(
                Order.id == order_id
            ).first()
            
            if dropshipping_order:
                log = DropshippingOrderLog(
                    dropshipping_order_id=dropshipping_order.id,
                    action='process_order',
                    status_before=None,
                    status_after=dropshipping_order.status.value if dropshipping_order.status else None,
                    success=result['success'],
                    error_message=result.get('message') if not result['success'] else None,
                    response_data=result,
                    processing_time_ms=int(result['processing_time'] * 1000)
                )
                
                self.db.add(log)
                self.db.commit()
                
        except Exception as e:
            logger.error(f"처리 로그 저장 중 오류: {str(e)}")
    
    async def get_processing_status(self, order_id: str) -> Dict:
        """주문 처리 상태 조회"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {
                'success': False,
                'message': '주문을 찾을 수 없습니다.'
            }
        
        dropshipping_order = self.db.query(DropshippingOrder).filter(
            DropshippingOrder.order_id == order.id
        ).first()
        
        return {
            'success': True,
            'order_status': order.status.value,
            'dropshipping_status': dropshipping_order.status.value if dropshipping_order else None,
            'supplier_order_id': dropshipping_order.supplier_order_id if dropshipping_order else None,
            'retry_count': dropshipping_order.retry_count if dropshipping_order else 0,
            'can_retry': dropshipping_order.can_retry if dropshipping_order else False,
            'last_error': dropshipping_order.last_error_message if dropshipping_order else None
        }
    
    async def get_failed_orders(self, limit: int = 50) -> List[Dict]:
        """실패한 주문 목록 조회"""
        failed_orders = self.db.query(DropshippingOrder).join(Order).filter(
            DropshippingOrder.status.in_([
                SupplierOrderStatus.FAILED, 
                SupplierOrderStatus.OUT_OF_STOCK
            ])
        ).limit(limit).all()
        
        return [
            {
                'order_id': str(do.order_id),
                'order_number': do.order.order_number,
                'status': do.status.value,
                'retry_count': do.retry_count,
                'can_retry': do.can_retry,
                'last_error': do.last_error_message,
                'created_at': do.created_at.isoformat(),
            }
            for do in failed_orders
        ]