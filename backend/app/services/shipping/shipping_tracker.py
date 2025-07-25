"""
드롭쉬핑 배송 추적 서비스
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.order import DropshippingOrder, SupplierOrderStatus, Order
from app.models.wholesaler import Wholesaler
from app.services.ordering.order_manager import OrderManager

logger = logging.getLogger(__name__)


class ShippingTracker:
    """드롭쉬핑 배송 추적 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.order_manager = OrderManager(db)
        self.tracking_interval_hours = 4  # 4시간마다 추적 업데이트
        
    async def track_order(self, dropshipping_order_id: str) -> Dict:
        """
        단일 주문 배송 추적
        
        Args:
            dropshipping_order_id: 드롭쉬핑 주문 ID
            
        Returns:
            Dict: 추적 결과
        """
        try:
            dropshipping_order = self.db.query(DropshippingOrder).filter(
                DropshippingOrder.id == dropshipping_order_id
            ).first()
            
            if not dropshipping_order:
                return {
                    'success': False,
                    'message': '드롭쉬핑 주문을 찾을 수 없습니다'
                }
            
            # 추적 번호가 없으면 먼저 주문 상태 확인
            if not dropshipping_order.supplier_tracking_number:
                status_result = await self.order_manager.check_order_status(dropshipping_order)
                
                if status_result['success'] and status_result.get('tracking_number'):
                    dropshipping_order.supplier_tracking_number = status_result['tracking_number']
                    if status_result.get('carrier'):
                        dropshipping_order.supplier_carrier = status_result['carrier']
                    self.db.commit()
                else:
                    return {
                        'success': False,
                        'message': '추적 번호가 아직 발급되지 않았습니다',
                        'order_status': dropshipping_order.status.value
                    }
            
            # 배송 추적 정보 조회
            tracking_result = await self.order_manager.get_tracking_info(dropshipping_order)
            
            if tracking_result['success']:
                # 추적 정보를 바탕으로 주문 상태 업데이트
                await self._update_order_from_tracking(dropshipping_order, tracking_result)
                
                return {
                    'success': True,
                    'order_id': str(dropshipping_order.order_id),
                    'supplier_order_id': dropshipping_order.supplier_order_id,
                    'tracking_number': dropshipping_order.supplier_tracking_number,
                    'carrier': dropshipping_order.supplier_carrier,
                    'current_status': tracking_result.get('current_status'),
                    'current_location': tracking_result.get('current_location'),
                    'estimated_delivery': tracking_result.get('estimated_delivery'),
                    'tracking_events': tracking_result.get('tracking_events', []),
                    'last_updated': tracking_result.get('last_updated'),
                    'delivery_progress': await self._calculate_delivery_progress(tracking_result)
                }
            else:
                return {
                    'success': False,
                    'message': f'배송 추적 실패: {tracking_result.get("message")}',
                    'tracking_number': dropshipping_order.supplier_tracking_number
                }
                
        except Exception as e:
            logger.error(f"배송 추적 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 추적 중 오류 발생: {str(e)}'
            }
    
    async def track_all_active_orders(self) -> Dict:
        """
        모든 활성 주문 배송 추적 (배치 작업용)
        
        Returns:
            Dict: 일괄 추적 결과
        """
        try:
            # 배송 추적이 필요한 주문들 조회
            active_orders = self.db.query(DropshippingOrder).filter(
                and_(
                    DropshippingOrder.status.in_([
                        SupplierOrderStatus.SHIPPED,
                        SupplierOrderStatus.CONFIRMED,
                        SupplierOrderStatus.PROCESSING
                    ]),
                    DropshippingOrder.supplier_tracking_number.isnot(None),
                    or_(
                        DropshippingOrder.updated_at.is_(None),
                        DropshippingOrder.updated_at < datetime.utcnow() - timedelta(hours=self.tracking_interval_hours)
                    )
                )
            ).limit(50).all()  # 한 번에 최대 50개씩 처리
            
            results = {
                'total_orders': len(active_orders),
                'successful_updates': 0,
                'failed_updates': 0,
                'delivered_orders': 0,
                'updated_orders': [],
                'errors': []
            }
            
            for order in active_orders:
                try:
                    tracking_result = await self.track_order(str(order.id))
                    
                    if tracking_result['success']:
                        results['successful_updates'] += 1
                        
                        # 배송 완료된 주문 카운트
                        if order.status == SupplierOrderStatus.DELIVERED:
                            results['delivered_orders'] += 1
                        
                        results['updated_orders'].append({
                            'order_id': str(order.order_id),
                            'tracking_number': order.supplier_tracking_number,
                            'status': order.status.value,
                            'current_location': tracking_result.get('current_location')
                        })
                    else:
                        results['failed_updates'] += 1
                        results['errors'].append({
                            'order_id': str(order.order_id),
                            'error': tracking_result.get('message')
                        })
                    
                    # API 호출 간격 조절
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    results['failed_updates'] += 1
                    results['errors'].append({
                        'order_id': str(order.order_id),
                        'error': str(e)
                    })
                    logger.error(f"주문 추적 중 오류 ({order.order_id}): {str(e)}")
            
            logger.info(f"배송 추적 완료: {results['successful_updates']}/{results['total_orders']} 성공")
            
            return {
                'success': True,
                'results': results,
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"일괄 배송 추적 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'일괄 배송 추적 중 오류 발생: {str(e)}'
            }
    
    async def get_delivery_status_summary(self) -> Dict:
        """
        배송 상태 요약 정보 조회
        
        Returns:
            Dict: 배송 상태 요약
        """
        try:
            from sqlalchemy import func, case
            from datetime import date, timedelta
            
            # 오늘 기준 통계
            today = date.today()
            week_ago = today - timedelta(days=7)
            
            # 배송 상태별 통계
            status_stats = (
                self.db.query(
                    DropshippingOrder.status,
                    func.count(DropshippingOrder.id).label('count')
                )
                .filter(DropshippingOrder.created_at >= week_ago)
                .group_by(DropshippingOrder.status)
                .all()
            )
            
            # 배송업체별 통계
            carrier_stats = (
                self.db.query(
                    DropshippingOrder.supplier_carrier,
                    func.count(DropshippingOrder.id).label('count'),
                    func.avg(
                        case(
                            [(DropshippingOrder.supplier_shipped_at.isnot(None), 
                              func.extract('epoch', func.now() - DropshippingOrder.supplier_shipped_at) / 86400)],
                            else_=None
                        )
                    ).label('avg_days')
                )
                .filter(
                    and_(
                        DropshippingOrder.status == SupplierOrderStatus.SHIPPED,
                        DropshippingOrder.supplier_carrier.isnot(None)
                    )
                )
                .group_by(DropshippingOrder.supplier_carrier)
                .all()
            )
            
            # 지연 배송 주문 (5일 이상)
            delayed_orders = (
                self.db.query(DropshippingOrder)
                .filter(
                    and_(
                        DropshippingOrder.status == SupplierOrderStatus.SHIPPED,
                        DropshippingOrder.supplier_shipped_at < datetime.utcnow() - timedelta(days=5)
                    )
                )
                .count()
            )
            
            return {
                'success': True,
                'summary': {
                    'period': f'{week_ago} ~ {today}',
                    'status_distribution': {
                        stat.status.value: stat.count for stat in status_stats
                    },
                    'carrier_performance': [
                        {
                            'carrier': stat.supplier_carrier or 'Unknown',
                            'order_count': stat.count,
                            'avg_delivery_days': float(stat.avg_days) if stat.avg_days else None
                        }
                        for stat in carrier_stats
                    ],
                    'delayed_orders': delayed_orders,
                    'total_tracking_orders': sum(stat.count for stat in status_stats)
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"배송 상태 요약 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 상태 요약 조회 중 오류 발생: {str(e)}'
            }
    
    async def get_order_tracking_history(self, order_id: str) -> Dict:
        """
        주문 배송 추적 이력 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Dict: 추적 이력
        """
        try:
            dropshipping_order = self.db.query(DropshippingOrder).join(Order).filter(
                Order.id == order_id
            ).first()
            
            if not dropshipping_order:
                return {
                    'success': False,
                    'message': '주문을 찾을 수 없습니다'
                }
            
            # 현재 추적 정보 조회
            current_tracking = await self.track_order(str(dropshipping_order.id))
            
            # 주문 상태 변경 이력 조회
            from app.models.order import DropshippingOrderLog
            status_history = (
                self.db.query(DropshippingOrderLog)
                .filter(DropshippingOrderLog.dropshipping_order_id == dropshipping_order.id)
                .order_by(DropshippingOrderLog.created_at.desc())
                .all()
            )
            
            return {
                'success': True,
                'order_id': order_id,
                'order_number': dropshipping_order.order.order_number,
                'current_tracking': current_tracking,
                'tracking_history': [
                    {
                        'action': log.action,
                        'status_before': log.status_before,
                        'status_after': log.status_after,
                        'success': log.success,
                        'message': log.error_message if not log.success else f'성공: {log.action}',
                        'created_at': log.created_at.isoformat(),
                        'processing_time_ms': log.processing_time_ms
                    }
                    for log in status_history
                ],
                'timeline': await self._build_delivery_timeline(dropshipping_order, current_tracking)
            }
            
        except Exception as e:
            logger.error(f"주문 추적 이력 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'추적 이력 조회 중 오류 발생: {str(e)}'
            }
    
    async def _update_order_from_tracking(self, dropshipping_order: DropshippingOrder, tracking_result: Dict):
        """추적 정보를 바탕으로 주문 상태 업데이트"""
        try:
            current_status = tracking_result.get('current_status', '').lower()
            
            # 배송 상태에 따른 주문 상태 업데이트
            if '배송완료' in current_status or 'delivered' in current_status:
                if dropshipping_order.status != SupplierOrderStatus.DELIVERED:
                    dropshipping_order.status = SupplierOrderStatus.DELIVERED
                    # 주문도 함께 업데이트
                    dropshipping_order.order.status = 'delivered'
                    logger.info(f"주문 배송 완료 업데이트: {dropshipping_order.order.order_number}")
            
            elif '배송중' in current_status or 'in_transit' in current_status:
                if dropshipping_order.status != SupplierOrderStatus.SHIPPED:
                    dropshipping_order.status = SupplierOrderStatus.SHIPPED
                    if not dropshipping_order.supplier_shipped_at:
                        dropshipping_order.supplier_shipped_at = datetime.utcnow()
            
            # 예상 배송일 업데이트
            if tracking_result.get('estimated_delivery'):
                try:
                    est_delivery = datetime.fromisoformat(tracking_result['estimated_delivery'].replace('Z', '+00:00'))
                    dropshipping_order.estimated_delivery_date = est_delivery
                except:
                    pass
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"추적 정보 기반 주문 상태 업데이트 중 오류: {str(e)}")
            self.db.rollback()
    
    async def _calculate_delivery_progress(self, tracking_result: Dict) -> Dict:
        """배송 진행률 계산"""
        try:
            events = tracking_result.get('tracking_events', [])
            if not events:
                return {'progress_percentage': 0, 'current_stage': 'unknown'}
            
            # 일반적인 배송 단계
            delivery_stages = [
                '상품준비중',
                '출고완료',
                '배송시작',
                '배송중',
                '배송완료'
            ]
            
            current_status = tracking_result.get('current_status', '').lower()
            
            # 현재 단계 결정
            current_stage_index = 0
            for i, stage in enumerate(delivery_stages):
                if stage.lower() in current_status:
                    current_stage_index = i
                    break
            
            progress_percentage = min(((current_stage_index + 1) / len(delivery_stages)) * 100, 100)
            
            return {
                'progress_percentage': int(progress_percentage),
                'current_stage': delivery_stages[current_stage_index],
                'total_stages': len(delivery_stages),
                'stage_details': delivery_stages
            }
            
        except Exception as e:
            logger.error(f"배송 진행률 계산 중 오류: {str(e)}")
            return {'progress_percentage': 0, 'current_stage': 'unknown'}
    
    async def _build_delivery_timeline(self, dropshipping_order: DropshippingOrder, tracking_result: Dict) -> List[Dict]:
        """배송 타임라인 구성"""
        timeline = []
        
        try:
            # 주문 접수
            if dropshipping_order.created_at:
                timeline.append({
                    'stage': '주문 접수',
                    'status': 'completed',
                    'timestamp': dropshipping_order.created_at.isoformat(),
                    'description': '드롭쉬핑 주문이 접수되었습니다'
                })
            
            # 공급업체 발주
            if dropshipping_order.supplier_order_date:
                timeline.append({
                    'stage': '공급업체 발주',
                    'status': 'completed',
                    'timestamp': dropshipping_order.supplier_order_date.isoformat(),
                    'description': '공급업체에 상품을 주문했습니다'
                })
            
            # 주문 확인
            if dropshipping_order.supplier_confirmed_at:
                timeline.append({
                    'stage': '주문 확인',
                    'status': 'completed',
                    'timestamp': dropshipping_order.supplier_confirmed_at.isoformat(),
                    'description': '공급업체에서 주문을 확인했습니다'
                })
            
            # 배송 시작
            if dropshipping_order.supplier_shipped_at:
                timeline.append({
                    'stage': '배송 시작',
                    'status': 'completed',
                    'timestamp': dropshipping_order.supplier_shipped_at.isoformat(),
                    'description': f'상품이 출고되어 배송을 시작했습니다 (송장번호: {dropshipping_order.supplier_tracking_number})'
                })
            
            # 추적 이벤트들 추가
            if tracking_result.get('success') and tracking_result.get('tracking_events'):
                for event in tracking_result['tracking_events'][-3:]:  # 최근 3개만
                    timeline.append({
                        'stage': '배송 진행',
                        'status': 'in_progress',
                        'timestamp': event.get('timestamp', ''),
                        'description': event.get('description', ''),
                        'location': event.get('location', '')
                    })
            
            # 배송 완료 (예상)
            if dropshipping_order.estimated_delivery_date:
                timeline.append({
                    'stage': '배송 완료 예정',
                    'status': 'pending' if dropshipping_order.status != SupplierOrderStatus.DELIVERED else 'completed',
                    'timestamp': dropshipping_order.estimated_delivery_date.isoformat(),
                    'description': '배송 완료 예정일입니다'
                })
            
            # 시간순 정렬
            timeline.sort(key=lambda x: x.get('timestamp', ''))
            
        except Exception as e:
            logger.error(f"배송 타임라인 구성 중 오류: {str(e)}")
        
        return timeline
    
    async def notify_delivery_delays(self, delay_threshold_days: int = 7) -> Dict:
        """
        배송 지연 알림
        
        Args:
            delay_threshold_days: 지연 기준 일수
            
        Returns:
            Dict: 지연 알림 결과
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=delay_threshold_days)
            
            # 지연된 주문 조회
            delayed_orders = (
                self.db.query(DropshippingOrder)
                .filter(
                    and_(
                        DropshippingOrder.status.in_([
                            SupplierOrderStatus.SHIPPED,
                            SupplierOrderStatus.PROCESSING
                        ]),
                        or_(
                            DropshippingOrder.supplier_shipped_at < cutoff_date,
                            and_(
                                DropshippingOrder.supplier_shipped_at.is_(None),
                                DropshippingOrder.created_at < cutoff_date
                            )
                        )
                    )
                )
                .all()
            )
            
            notification_results = []
            
            for order in delayed_orders:
                # 각 지연 주문에 대한 알림 처리
                delay_days = (datetime.utcnow() - (order.supplier_shipped_at or order.created_at)).days
                
                notification_result = {
                    'order_id': str(order.order_id),
                    'order_number': order.order.order_number,
                    'customer_name': order.order.customer_name,
                    'delay_days': delay_days,
                    'tracking_number': order.supplier_tracking_number,
                    'supplier_name': order.supplier.name if order.supplier else 'Unknown',
                    'notification_sent': False
                }
                
                try:
                    # 실제 알림 발송 로직 (이메일, SMS 등)
                    # await self._send_delay_notification(order)
                    notification_result['notification_sent'] = True
                    logger.info(f"배송 지연 알림 발송: {order.order.order_number} ({delay_days}일 지연)")
                except Exception as e:
                    logger.error(f"배송 지연 알림 발송 실패: {str(e)}")
                
                notification_results.append(notification_result)
            
            return {
                'success': True,
                'delayed_orders_count': len(delayed_orders),
                'notifications_sent': sum(1 for r in notification_results if r['notification_sent']),
                'delay_threshold_days': delay_threshold_days,
                'notifications': notification_results
            }
            
        except Exception as e:
            logger.error(f"배송 지연 알림 처리 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 지연 알림 처리 중 오류 발생: {str(e)}'
            }