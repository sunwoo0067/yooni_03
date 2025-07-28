"""
드롭쉬핑 통합 발주 관리자
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.order_core import DropshippingOrder, SupplierOrderStatus, DropshippingOrderLog
from app.models.wholesaler import Wholesaler
from app.services.ordering.domeggook_ordering import DomeggookOrderingService
from app.services.ordering.ownerclan_ordering import OwnerClanOrderingService
from app.services.ordering.zentrade_ordering import ZentradeOrderingService

logger = logging.getLogger(__name__)


class OrderManager:
    """드롭쉬핑 통합 발주 관리자"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 공급업체별 발주 서비스 초기화
        self.ordering_services = {
            'domeggook': DomeggookOrderingService(db),
            'ownerclan': OwnerClanOrderingService(db),
            'zentrade': ZentradeOrderingService(db)
        }
    
    async def submit_order(self, dropshipping_order: DropshippingOrder) -> Dict:
        """
        공급업체에 주문 제출
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            
        Returns:
            Dict: 발주 결과
        """
        start_time = datetime.utcnow()
        
        try:
            # 공급업체 정보 조회
            supplier = self.db.query(Wholesaler).filter(
                Wholesaler.id == dropshipping_order.supplier_id
            ).first()
            
            if not supplier:
                return await self._create_error_result(
                    dropshipping_order, 
                    "공급업체 정보를 찾을 수 없습니다",
                    start_time
                )
            
            # 공급업체별 발주 서비스 선택
            supplier_type = supplier.wholesaler_type.lower()
            ordering_service = self.ordering_services.get(supplier_type)
            
            if not ordering_service:
                return await self._create_error_result(
                    dropshipping_order,
                    f"지원하지 않는 공급업체 타입: {supplier_type}",
                    start_time
                )
            
            logger.info(f"발주 시작: {supplier.name} ({supplier_type})")
            
            # 발주 실행
            order_result = await ordering_service.submit_order(dropshipping_order, supplier)
            
            # 결과 처리
            if order_result['success']:
                await self._handle_successful_order(dropshipping_order, order_result, start_time)
                logger.info(f"발주 성공: {supplier.name} (주문ID: {order_result.get('supplier_order_id')})")
            else:
                await self._handle_failed_order(dropshipping_order, order_result, start_time)
                logger.warning(f"발주 실패: {supplier.name} - {order_result.get('message')}")
            
            return order_result
            
        except Exception as e:
            logger.error(f"발주 처리 중 예외 발생: {str(e)}", exc_info=True)
            return await self._create_error_result(
                dropshipping_order,
                f"발주 처리 중 오류 발생: {str(e)}",
                start_time
            )
    
    async def check_order_status(self, dropshipping_order: DropshippingOrder) -> Dict:
        """
        공급업체 주문 상태 확인
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            
        Returns:
            Dict: 상태 확인 결과
        """
        try:
            if not dropshipping_order.supplier_order_id:
                return {
                    'success': False,
                    'message': '공급업체 주문 ID가 없습니다'
                }
            
            # 공급업체 정보 조회
            supplier = self.db.query(Wholesaler).filter(
                Wholesaler.id == dropshipping_order.supplier_id
            ).first()
            
            if not supplier:
                return {
                    'success': False,
                    'message': '공급업체 정보를 찾을 수 없습니다'
                }
            
            # 공급업체별 상태 확인 서비스 선택
            supplier_type = supplier.wholesaler_type.lower()
            ordering_service = self.ordering_services.get(supplier_type)
            
            if not ordering_service:
                return {
                    'success': False,
                    'message': f'지원하지 않는 공급업체 타입: {supplier_type}'
                }
            
            # 상태 확인 실행
            status_result = await ordering_service.check_order_status(
                dropshipping_order.supplier_order_id, 
                supplier
            )
            
            # 상태 업데이트
            if status_result['success']:
                await self._update_order_status(dropshipping_order, status_result)
            
            return status_result
            
        except Exception as e:
            logger.error(f"주문 상태 확인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 상태 확인 중 오류 발생: {str(e)}'
            }
    
    async def cancel_order(self, dropshipping_order: DropshippingOrder, reason: str = "") -> Dict:
        """
        공급업체 주문 취소
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            reason: 취소 사유
            
        Returns:
            Dict: 취소 결과
        """
        try:
            if not dropshipping_order.supplier_order_id:
                return {
                    'success': False,
                    'message': '공급업체 주문 ID가 없습니다'
                }
            
            # 취소 가능 상태 확인
            cancellable_statuses = [
                SupplierOrderStatus.SUBMITTED,
                SupplierOrderStatus.CONFIRMED,
                SupplierOrderStatus.PROCESSING
            ]
            
            if dropshipping_order.status not in cancellable_statuses:
                return {
                    'success': False,
                    'message': f'취소할 수 없는 주문 상태입니다: {dropshipping_order.status.value}'
                }
            
            # 공급업체 정보 조회
            supplier = self.db.query(Wholesaler).filter(
                Wholesaler.id == dropshipping_order.supplier_id
            ).first()
            
            if not supplier:
                return {
                    'success': False,
                    'message': '공급업체 정보를 찾을 수 없습니다'
                }
            
            # 공급업체별 취소 서비스 선택
            supplier_type = supplier.wholesaler_type.lower()
            ordering_service = self.ordering_services.get(supplier_type)
            
            if not ordering_service:
                return {
                    'success': False,
                    'message': f'지원하지 않는 공급업체 타입: {supplier_type}'
                }
            
            # 취소 실행
            cancel_result = await ordering_service.cancel_order(
                dropshipping_order.supplier_order_id, 
                supplier, 
                reason
            )
            
            # 취소 결과 처리
            if cancel_result['success']:
                dropshipping_order.status = SupplierOrderStatus.CANCELLED
                dropshipping_order.processing_notes = f"취소 완료: {reason}"
                self.db.commit()
                
                logger.info(f"주문 취소 완료: {dropshipping_order.supplier_order_id}")
            
            return cancel_result
            
        except Exception as e:
            logger.error(f"주문 취소 중 오러: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 취소 중 오류 발생: {str(e)}'
            }
    
    async def get_tracking_info(self, dropshipping_order: DropshippingOrder) -> Dict:
        """
        배송 추적 정보 조회
        
        Args:  
            dropshipping_order: 드롭쉬핑 주문
            
        Returns:
            Dict: 추적 정보
        """
        try:
            if not dropshipping_order.supplier_tracking_number:
                return {
                    'success': False,
                    'message': '배송 추적 번호가 없습니다'
                }
            
            # 공급업체 정보 조회
            supplier = self.db.query(Wholesaler).filter(
                Wholesaler.id == dropshipping_order.supplier_id
            ).first()
            
            if not supplier:
                return {
                    'success': False,
                    'message': '공급업체 정보를 찾을 수 없습니다'
                }
            
            # 공급업체별 추적 서비스 선택
            supplier_type = supplier.wholesaler_type.lower()
            ordering_service = self.ordering_services.get(supplier_type)
            
            if not ordering_service:
                return {
                    'success': False,
                    'message': f'지원하지 않는 공급업체 타입: {supplier_type}'
                }
            
            # 추적 정보 조회
            tracking_result = await ordering_service.get_tracking_info(
                dropshipping_order.supplier_tracking_number,
                supplier
            )
            
            return tracking_result
            
        except Exception as e:
            logger.error(f"추적 정보 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'추적 정보 조회 중 오류 발생: {str(e)}'
            }
    
    async def bulk_submit_orders(self, dropshipping_orders: List[DropshippingOrder]) -> Dict:
        """
        대량 발주 처리
        
        Args:
            dropshipping_orders: 드롭쉬핑 주문 리스트
            
        Returns:
            Dict: 대량 발주 결과
        """
        results = {
            'total_orders': len(dropshipping_orders),
            'successful_orders': 0,
            'failed_orders': 0,
            'results': []
        }
        
        for dropshipping_order in dropshipping_orders:
            try:
                result = await self.submit_order(dropshipping_order)
                results['results'].append({
                    'order_id': str(dropshipping_order.order_id),
                    'supplier_order_id': result.get('supplier_order_id'),
                    'success': result['success'],
                    'message': result.get('message')
                })
                
                if result['success']:
                    results['successful_orders'] += 1
                else:
                    results['failed_orders'] += 1
                    
            except Exception as e:
                logger.error(f"대량 발주 중 오류 (주문: {dropshipping_order.order_id}): {str(e)}")
                results['results'].append({
                    'order_id': str(dropshipping_order.order_id),
                    'success': False,
                    'message': str(e)
                })
                results['failed_orders'] += 1
        
        logger.info(f"대량 발주 완료: {results['successful_orders']}/{results['total_orders']} 성공")
        
        return results
    
    async def _create_error_result(
        self, 
        dropshipping_order: DropshippingOrder, 
        message: str, 
        start_time: datetime
    ) -> Dict:
        """오류 결과 생성"""
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 오류 로그 저장
        await self._save_order_log(
            dropshipping_order, 
            'submit_order', 
            False, 
            message, 
            None, 
            processing_time
        )
        
        return {
            'success': False,
            'message': message,
            'processing_time': processing_time
        }
    
    async def _handle_successful_order(
        self, 
        dropshipping_order: DropshippingOrder, 
        order_result: Dict, 
        start_time: datetime
    ):
        """성공적인 발주 처리"""
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 드롭쉬핑 주문 상태 업데이트
        dropshipping_order.status = SupplierOrderStatus.SUBMITTED
        dropshipping_order.supplier_order_id = order_result.get('supplier_order_id')
        dropshipping_order.supplier_order_date = datetime.utcnow()
        dropshipping_order.supplier_response_data = order_result.get('response_data')
        
        self.db.commit()
        
        # 성공 로그 저장
        await self._save_order_log(
            dropshipping_order,
            'submit_order',
            True,
            '발주 성공',
            order_result,
            processing_time
        )
    
    async def _handle_failed_order(
        self, 
        dropshipping_order: DropshippingOrder, 
        order_result: Dict, 
        start_time: datetime
    ):
        """실패한 발주 처리"""
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 드롭쉬핑 주문 상태 업데이트
        dropshipping_order.status = SupplierOrderStatus.FAILED
        dropshipping_order.last_error_message = order_result.get('message')
        dropshipping_order.error_count += 1
        dropshipping_order.supplier_response_data = order_result.get('response_data')
        
        self.db.commit()
        
        # 실패 로그 저장
        await self._save_order_log(
            dropshipping_order,
            'submit_order',
            False,
            order_result.get('message'),
            order_result,
            processing_time
        )
    
    async def _update_order_status(self, dropshipping_order: DropshippingOrder, status_result: Dict):
        """주문 상태 업데이트"""
        try:
            new_status = status_result.get('status')
            if new_status and new_status != dropshipping_order.status.value:
                old_status = dropshipping_order.status.value
                
                # 상태별 처리
                status_mapping = {
                    'confirmed': SupplierOrderStatus.CONFIRMED,
                    'processing': SupplierOrderStatus.PROCESSING,
                    'shipped': SupplierOrderStatus.SHIPPED,
                    'delivered': SupplierOrderStatus.DELIVERED,
                    'cancelled': SupplierOrderStatus.CANCELLED,
                    'out_of_stock': SupplierOrderStatus.OUT_OF_STOCK
                }
                
                if new_status in status_mapping:
                    dropshipping_order.status = status_mapping[new_status]
                
                # 배송 정보 업데이트
                if new_status == 'shipped':
                    dropshipping_order.supplier_shipped_at = datetime.utcnow()
                    if 'tracking_number' in status_result:
                        dropshipping_order.supplier_tracking_number = status_result['tracking_number']
                    if 'carrier' in status_result:
                        dropshipping_order.supplier_carrier = status_result['carrier']
                
                # 확인 시간 업데이트
                if new_status == 'confirmed':
                    dropshipping_order.supplier_confirmed_at = datetime.utcnow()
                
                self.db.commit()
                
                # 상태 변경 로그 저장
                await self._save_order_log(
                    dropshipping_order,
                    'status_update',
                    True,
                    f'상태 변경: {old_status} → {new_status}',
                    status_result,
                    0
                )
                
                logger.info(f"주문 상태 업데이트: {dropshipping_order.supplier_order_id} ({old_status} → {new_status})")
            
        except Exception as e:
            logger.error(f"주문 상태 업데이트 중 오류: {str(e)}")
            self.db.rollback()
    
    async def _save_order_log(
        self, 
        dropshipping_order: DropshippingOrder, 
        action: str, 
        success: bool, 
        message: str, 
        response_data: Dict, 
        processing_time: float
    ):
        """발주 로그 저장"""
        try:
            log = DropshippingOrderLog(
                dropshipping_order_id=dropshipping_order.id,
                action=action,
                status_before=None,
                status_after=dropshipping_order.status.value if dropshipping_order.status else None,
                success=success,
                error_message=message if not success else None,
                response_data=response_data,
                processing_time_ms=int(processing_time * 1000)
            )
            
            self.db.add(log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"발주 로그 저장 중 오류: {str(e)}")
            self.db.rollback()
    
    async def get_order_statistics(self, days: int = 30) -> Dict:
        """발주 통계 조회"""
        try:
            from datetime import timedelta
            from sqlalchemy import and_, func
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 기간 내 발주 현황
            orders_query = self.db.query(DropshippingOrder).filter(
                and_(
                    DropshippingOrder.created_at >= start_date,
                    DropshippingOrder.created_at <= end_date
                )
            )
            
            total_orders = orders_query.count()
            
            # 상태별 통계
            status_stats = {}
            for status in SupplierOrderStatus:
                count = orders_query.filter(DropshippingOrder.status == status).count()
                status_stats[status.value] = count
            
            # 공급업체별 통계
            supplier_stats = (
                self.db.query(
                    Wholesaler.name,
                    func.count(DropshippingOrder.id).label('order_count'),
                    func.avg(DropshippingOrder.margin_rate).label('avg_margin_rate')
                )
                .join(DropshippingOrder, Wholesaler.id == DropshippingOrder.supplier_id)
                .filter(
                    and_(
                        DropshippingOrder.created_at >= start_date,
                        DropshippingOrder.created_at <= end_date
                    )
                )
                .group_by(Wholesaler.name)
                .all()
            )
            
            return {
                'success': True,
                'period': {
                    'days': days,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': {
                    'total_orders': total_orders,
                    'success_rate': (status_stats.get('confirmed', 0) + status_stats.get('shipped', 0) + status_stats.get('delivered', 0)) / total_orders * 100 if total_orders > 0 else 0
                },
                'status_distribution': status_stats,
                'supplier_performance': [
                    {
                        'supplier_name': stat.name,
                        'order_count': stat.order_count,
                        'avg_margin_rate': float(stat.avg_margin_rate) if stat.avg_margin_rate else 0
                    }
                    for stat in supplier_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"발주 통계 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'통계 조회 중 오류 발생: {str(e)}'
            }