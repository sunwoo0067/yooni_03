"""
드롭쉬핑 환불 처리 서비스
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.order import DropshippingOrder, SupplierOrderStatus, Order, OrderStatus, OrderPayment, PaymentStatus
from app.models.wholesaler import Wholesaler

logger = logging.getLogger(__name__)


class RefundReason(Enum):
    """환불 사유"""
    OUT_OF_STOCK = "out_of_stock"           # 품절
    PRICE_CHANGE = "price_change"           # 가격 변동
    CUSTOMER_REQUEST = "customer_request"   # 고객 요청
    DELIVERY_FAILED = "delivery_failed"     # 배송 실패
    PRODUCT_DEFECT = "product_defect"       # 상품 불량
    SUPPLIER_ERROR = "supplier_error"       # 공급업체 오류
    SYSTEM_ERROR = "system_error"           # 시스템 오류


class RefundType(Enum):
    """환불 유형"""
    FULL = "full"        # 전체 환불
    PARTIAL = "partial"  # 부분 환불
    ITEM = "item"        # 상품별 환불


class RefundStatus(Enum):
    """환불 상태"""
    REQUESTED = "requested"       # 환불 요청
    APPROVED = "approved"         # 환불 승인
    PROCESSING = "processing"     # 환불 처리중
    COMPLETED = "completed"       # 환불 완료
    REJECTED = "rejected"         # 환불 거부
    FAILED = "failed"            # 환불 실패


class RefundProcessor:
    """드롭쉬핑 환불 처리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 환불 정책
        self.refund_policies = {
            RefundReason.OUT_OF_STOCK: {
                'auto_approve': True,
                'full_refund': True,
                'processing_days': 1,
                'compensation': True,
                'compensation_rate': 0.05  # 5% 보상
            },
            RefundReason.PRICE_CHANGE: {
                'auto_approve': True,
                'full_refund': True,
                'processing_days': 1,
                'compensation': False
            },
            RefundReason.CUSTOMER_REQUEST: {
                'auto_approve': False,
                'full_refund': False,
                'processing_days': 3,
                'compensation': False,
                'review_required': True
            },
            RefundReason.DELIVERY_FAILED: {
                'auto_approve': True,
                'full_refund': True,
                'processing_days': 2,
                'compensation': True,
                'compensation_rate': 0.03  # 3% 보상
            },
            RefundReason.SUPPLIER_ERROR: {
                'auto_approve': True,
                'full_refund': True,
                'processing_days': 1,
                'compensation': True,
                'compensation_rate': 0.1   # 10% 보상
            }
        }
    
    async def process_refund_request(
        self,
        dropshipping_order: DropshippingOrder,
        refund_reason: RefundReason,
        refund_type: RefundType = RefundType.FULL,
        refund_amount: Optional[Decimal] = None,
        refund_items: Optional[List[Dict]] = None,
        additional_data: Optional[Dict] = None
    ) -> Dict:
        """
        환불 요청 처리
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            refund_reason: 환불 사유
            refund_type: 환불 유형
            refund_amount: 환불 금액 (부분 환불시)
            refund_items: 환불 상품 목록 (상품별 환불시)
            additional_data: 추가 데이터
            
        Returns:
            Dict: 환불 처리 결과
        """
        try:
            logger.info(f"환불 요청 처리 시작: {dropshipping_order.order.order_number} ({refund_reason.value})")
            
            # 환불 가능 여부 검증
            validation_result = await self._validate_refund_request(
                dropshipping_order, refund_reason, refund_type, refund_amount, refund_items
            )
            
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': validation_result['message'],
                    'errors': validation_result['errors']
                }
            
            # 환불 정책 조회
            policy = self.refund_policies.get(refund_reason)
            if not policy:
                return {
                    'success': False,
                    'message': f'지원하지 않는 환불 사유: {refund_reason.value}'
                }
            
            # 환불 기록 생성
            refund_record = await self._create_refund_record(
                dropshipping_order, refund_reason, refund_type, refund_amount, refund_items, additional_data
            )
            
            # 자동 승인 여부 확인
            if policy.get('auto_approve', False):
                # 자동 승인 및 처리
                result = await self._process_automatic_refund(dropshipping_order, refund_record, policy)
            else:
                # 수동 검토 필요
                result = await self._request_manual_review(dropshipping_order, refund_record, policy)
            
            # 환불 기록 업데이트
            await self._update_refund_record(refund_record, result)
            
            # 고객 알림
            await self._notify_customer_about_refund(dropshipping_order, refund_record, result)
            
            # 관리자 알림 (필요시)
            if not policy.get('auto_approve', False) or not result.get('success', False):
                await self._notify_admin_about_refund(dropshipping_order, refund_record, result)
            
            logger.info(f"환불 요청 처리 완료: {dropshipping_order.order.order_number}")
            
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'refund_id': refund_record['id'],
                'refund_status': result.get('status', RefundStatus.REQUESTED.value),
                'refund_amount': result.get('refund_amount', 0),
                'processing_time': result.get('processing_time', policy.get('processing_days', 3)),
                'compensation': result.get('compensation', {}),
                'next_steps': result.get('next_steps', [])
            }
            
        except Exception as e:
            logger.error(f"환불 요청 처리 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'환불 요청 처리 중 오류 발생: {str(e)}'
            }
    
    async def _validate_refund_request(
        self,
        dropshipping_order: DropshippingOrder,
        refund_reason: RefundReason,
        refund_type: RefundType,
        refund_amount: Optional[Decimal],
        refund_items: Optional[List[Dict]]
    ) -> Dict:
        """환불 요청 검증"""
        try:
            errors = []
            
            # 1. 주문 상태 검증
            valid_statuses = [
                SupplierOrderStatus.CANCELLED,
                SupplierOrderStatus.FAILED,
                SupplierOrderStatus.OUT_OF_STOCK,
                SupplierOrderStatus.CONFIRMED,
                SupplierOrderStatus.PROCESSING
            ]
            
            if dropshipping_order.status not in valid_statuses:
                errors.append(f"환불할 수 없는 주문 상태: {dropshipping_order.status.value}")
            
            # 2. 결제 상태 검증
            order = dropshipping_order.order
            if order.payment_status != PaymentStatus.PAID:
                errors.append(f"결제되지 않은 주문: {order.payment_status.value}")
            
            # 3. 이미 환불된 주문 검증
            if order.status == OrderStatus.REFUNDED:
                errors.append("이미 환불된 주문입니다")
            
            # 4. 환불 금액 검증
            if refund_type == RefundType.PARTIAL:
                if not refund_amount or refund_amount <= 0:
                    errors.append("부분 환불시 환불 금액을 지정해야 합니다")
                elif refund_amount > order.total_amount:
                    errors.append("환불 금액이 주문 금액을 초과합니다")
            
            # 5. 환불 상품 검증
            if refund_type == RefundType.ITEM:
                if not refund_items:
                    errors.append("상품별 환불시 환불 상품을 지정해야 합니다")
                else:
                    order_item_ids = {str(item.id) for item in order.order_items}
                    for refund_item in refund_items:
                        if refund_item.get('item_id') not in order_item_ids:
                            errors.append(f"존재하지 않는 주문 상품: {refund_item.get('item_id')}")
            
            # 6. 환불 기한 검증 (주문 후 30일 이내)
            if order.order_date:
                days_since_order = (datetime.utcnow() - order.order_date).days
                if days_since_order > 30 and refund_reason == RefundReason.CUSTOMER_REQUEST:
                    errors.append("고객 요청 환불은 주문 후 30일 이내에만 가능합니다")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'message': errors[0] if errors else '검증 완료'
            }
            
        except Exception as e:
            logger.error(f"환불 요청 검증 중 오류: {str(e)}")
            return {
                'valid': False,
                'errors': [f'검증 중 오류 발생: {str(e)}'],
                'message': f'검증 중 오류 발생: {str(e)}'
            }
    
    async def _create_refund_record(
        self,
        dropshipping_order: DropshippingOrder,
        refund_reason: RefundReason,
        refund_type: RefundType,
        refund_amount: Optional[Decimal],
        refund_items: Optional[List[Dict]],
        additional_data: Optional[Dict]
    ) -> Dict:
        """환불 기록 생성"""
        try:
            order = dropshipping_order.order
            
            # 환불 금액 계산
            if refund_type == RefundType.FULL:
                calculated_amount = order.total_amount
            elif refund_type == RefundType.PARTIAL:
                calculated_amount = refund_amount
            elif refund_type == RefundType.ITEM:
                calculated_amount = Decimal('0')
                for refund_item in refund_items or []:
                    item_id = refund_item.get('item_id')
                    quantity = refund_item.get('quantity', 0)
                    
                    # 주문 상품에서 단가 조회
                    order_item = next((item for item in order.order_items if str(item.id) == item_id), None)
                    if order_item:
                        calculated_amount += order_item.unit_price * quantity
            else:
                calculated_amount = order.total_amount
            
            refund_record = {
                'id': f"REF_{int(datetime.utcnow().timestamp())}",
                'dropshipping_order_id': dropshipping_order.id,
                'order_id': order.id,
                'refund_reason': refund_reason.value,
                'refund_type': refund_type.value,
                'refund_amount': calculated_amount,
                'refund_items': refund_items or [],
                'status': RefundStatus.REQUESTED.value,
                'created_at': datetime.utcnow(),
                'additional_data': additional_data or {},
                'processing_logs': []
            }
            
            # 실제로는 별도의 환불 테이블에 저장
            # 여기서는 드롭쉬핑 주문 로그에 저장
            from app.models.order import DropshippingOrderLog
            
            log = DropshippingOrderLog(
                dropshipping_order_id=dropshipping_order.id,
                action='refund_requested',
                success=True,
                response_data=refund_record,
                processing_time_ms=0
            )
            
            self.db.add(log)
            self.db.commit()
            
            return refund_record
            
        except Exception as e:
            logger.error(f"환불 기록 생성 중 오류: {str(e)}")
            self.db.rollback()
            raise
    
    async def _process_automatic_refund(self, dropshipping_order: DropshippingOrder, refund_record: Dict, policy: Dict) -> Dict:
        """자동 환불 처리"""
        try:
            order = dropshipping_order.order
            refund_amount = refund_record['refund_amount']
            
            # 1. 결제 취소/환불 처리
            refund_result = await self._process_payment_refund(order, refund_amount)
            
            if not refund_result['success']:
                return {
                    'success': False,
                    'message': f'결제 환불 실패: {refund_result["message"]}',
                    'status': RefundStatus.FAILED.value
                }
            
            # 2. 주문 상태 업데이트
            order.status = OrderStatus.REFUNDED
            dropshipping_order.status = SupplierOrderStatus.CANCELLED
            
            # 3. 보상 계산 (정책에 따라)
            compensation = {}
            if policy.get('compensation', False):
                compensation_rate = policy.get('compensation_rate', 0)
                compensation_amount = refund_amount * Decimal(str(compensation_rate))
                
                compensation = {
                    'enabled': True,
                    'rate': compensation_rate,
                    'amount': compensation_amount,
                    'reason': '서비스 불편에 대한 보상'
                }
                
                # 실제로는 보상 적립 처리
                logger.info(f"보상 적립: {order.order_number} - {compensation_amount}원")
            
            # 4. 공급업체 주문 취소 (필요시)
            if dropshipping_order.supplier_order_id:
                await self._cancel_supplier_order(dropshipping_order)
            
            self.db.commit()
            
            return {
                'success': True,
                'message': '자동 환불 처리 완료',
                'status': RefundStatus.COMPLETED.value,
                'refund_amount': refund_amount,
                'refund_method': refund_result.get('refund_method', ''),
                'refund_transaction_id': refund_result.get('transaction_id', ''),
                'compensation': compensation,
                'processing_time': policy.get('processing_days', 1),
                'completed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"자동 환불 처리 중 오류: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'message': f'자동 환불 처리 중 오류 발생: {str(e)}',
                'status': RefundStatus.FAILED.value
            }
    
    async def _request_manual_review(self, dropshipping_order: DropshippingOrder, refund_record: Dict, policy: Dict) -> Dict:
        """수동 검토 요청"""
        try:
            # 수동 검토 상태로 변경
            dropshipping_order.is_blocked = True
            dropshipping_order.blocked_reason = f"환불 수동 검토 필요: {refund_record['refund_reason']}"
            
            self.db.commit()
            
            return {
                'success': True,
                'message': '환불 요청이 검토 대기 중입니다',
                'status': RefundStatus.REQUESTED.value,
                'refund_amount': refund_record['refund_amount'],
                'processing_time': policy.get('processing_days', 3),
                'next_steps': [
                    '관리자 검토 대기',
                    '검토 후 환불 승인/거부 결정',
                    '결정 후 고객 안내'
                ],
                'requires_manual_review': True
            }
            
        except Exception as e:
            logger.error(f"수동 검토 요청 중 오류: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'message': f'수동 검토 요청 중 오류 발생: {str(e)}',
                'status': RefundStatus.FAILED.value
            }
    
    async def _process_payment_refund(self, order: Order, refund_amount: Decimal) -> Dict:
        """결제 환불 처리"""
        try:
            # 주문의 결제 정보 조회
            payment = self.db.query(OrderPayment).filter(
                and_(
                    OrderPayment.order_id == order.id,
                    OrderPayment.status == PaymentStatus.PAID
                )
            ).first()
            
            if not payment:
                return {
                    'success': False,
                    'message': '결제 정보를 찾을 수 없습니다'
                }
            
            # 실제 결제 게이트웨이를 통한 환불 처리
            # 여기서는 가상의 환불 처리
            refund_data = {
                'original_transaction_id': payment.transaction_id,
                'refund_amount': float(refund_amount),
                'refund_reason': '드롭쉬핑 환불',
                'refund_method': payment.payment_method
            }
            
            # 가상의 환불 API 호출
            # refund_response = await payment_gateway.refund(refund_data)
            refund_response = {
                'success': True,
                'refund_transaction_id': f"REF_{payment.transaction_id}",
                'refund_amount': float(refund_amount),
                'refund_method': payment.payment_method,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            if refund_response['success']:
                # 환불 결제 기록 생성
                refund_payment = OrderPayment(
                    order_id=order.id,
                    payment_method=payment.payment_method,
                    payment_gateway=payment.payment_gateway,
                    transaction_id=refund_response['refund_transaction_id'],
                    amount=-refund_amount,  # 음수로 환불 표시
                    currency=payment.currency,
                    status=PaymentStatus.REFUNDED,
                    payment_date=datetime.utcnow(),
                    gateway_response=refund_response
                )
                
                self.db.add(refund_payment)
                
                # 원래 결제 상태 업데이트
                payment.status = PaymentStatus.REFUNDED
                
                return {
                    'success': True,
                    'message': '결제 환불 완료',
                    'refund_method': payment.payment_method,
                    'transaction_id': refund_response['refund_transaction_id'],
                    'refund_amount': refund_amount
                }
            else:
                return {
                    'success': False,
                    'message': f'결제 환불 실패: {refund_response.get("error", "Unknown error")}'
                }
            
        except Exception as e:
            logger.error(f"결제 환불 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'결제 환불 처리 중 오류 발생: {str(e)}'
            }
    
    async def _cancel_supplier_order(self, dropshipping_order: DropshippingOrder) -> Dict:
        """공급업체 주문 취소"""
        try:
            from app.services.ordering.order_manager import OrderManager
            
            order_manager = OrderManager(self.db)
            cancel_result = await order_manager.cancel_order(
                dropshipping_order,
                "환불로 인한 주문 취소"
            )
            
            return cancel_result
            
        except Exception as e:
            logger.error(f"공급업체 주문 취소 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'공급업체 주문 취소 중 오류: {str(e)}'
            }
    
    async def _update_refund_record(self, refund_record: Dict, result: Dict):
        """환불 기록 업데이트"""
        try:
            refund_record['status'] = result.get('status', RefundStatus.FAILED.value)
            refund_record['result'] = result
            refund_record['updated_at'] = datetime.utcnow()
            
            if result.get('success', False):
                refund_record['completed_at'] = datetime.utcnow()
            
            # 실제로는 데이터베이스에 업데이트
            logger.info(f"환불 기록 업데이트: {refund_record['id']}")
            
        except Exception as e:
            logger.error(f"환불 기록 업데이트 중 오류: {str(e)}")
    
    async def _notify_customer_about_refund(self, dropshipping_order: DropshippingOrder, refund_record: Dict, result: Dict):
        """고객에게 환불 알림"""
        try:
            from app.services.shipping.customer_notifier import CustomerNotifier
            
            notifier = CustomerNotifier(self.db)
            
            # 환불 상태에 따른 알림 타입
            if result.get('status') == RefundStatus.COMPLETED.value:
                notification_type = 'refund_completed' 
            elif result.get('status') == RefundStatus.REQUESTED.value:
                notification_type = 'refund_requested'
            else:
                notification_type = 'refund_failed'
            
            additional_data = {
                'refund_amount': float(result.get('refund_amount', 0)),
                'refund_reason': refund_record['refund_reason'],
                'processing_time': result.get('processing_time', 3),
                'compensation': result.get('compensation', {})
            }
            
            await notifier.notify_order_status_change(
                dropshipping_order,
                notification_type,
                additional_data
            )
            
        except Exception as e:
            logger.error(f"고객 환불 알림 중 오류: {str(e)}")
    
    async def _notify_admin_about_refund(self, dropshipping_order: DropshippingOrder, refund_record: Dict, result: Dict):
        """관리자에게 환불 알림"""
        try:
            admin_notification = {
                'refund_id': refund_record['id'],
                'order_number': dropshipping_order.order.order_number,
                'refund_reason': refund_record['refund_reason'],
                'refund_amount': float(refund_record['refund_amount']),
                'status': result.get('status'),
                'requires_review': result.get('requires_manual_review', False),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"관리자 환불 알림: {admin_notification}")
            
            # 실제로는 이메일이나 슬랙으로 알림 발송
            
        except Exception as e:
            logger.error(f"관리자 환불 알림 중 오류: {str(e)}")
    
    async def approve_refund(self, refund_id: str, approved_by: str, notes: Optional[str] = None) -> Dict:
        """환불 승인 (관리자용)"""
        try:
            # 환불 기록 조회 (실제로는 환불 테이블에서 조회)
            # 여기서는 간단한 구현
            
            logger.info(f"환불 승인: {refund_id} by {approved_by}")
            
            # 환불 처리 로직 실행
            # 실제로는 승인된 환불을 결제 시스템에서 처리
            
            return {
                'success': True,
                'message': '환불이 승인되었습니다',
                'refund_id': refund_id,
                'approved_by': approved_by,
                'approved_at': datetime.utcnow().isoformat(),
                'notes': notes
            }
            
        except Exception as e:
            logger.error(f"환불 승인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'환불 승인 중 오류 발생: {str(e)}'
            }
    
    async def reject_refund(self, refund_id: str, rejected_by: str, reason: str) -> Dict:
        """환불 거부 (관리자용)"""
        try:
            logger.info(f"환불 거부: {refund_id} by {rejected_by} - {reason}")
            
            # 환불 거부 처리
            # 주문 상태 복원 등의 작업
            
            return {
                'success': True,
                'message': '환불이 거부되었습니다',
                'refund_id': refund_id,
                'rejected_by': rejected_by,
                'rejected_at': datetime.utcnow().isoformat(),
                'rejection_reason': reason
            }
            
        except Exception as e:
            logger.error(f"환불 거부 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'환불 거부 중 오류 발생: {str(e)}'
            }
    
    async def get_refund_statistics(self, days: int = 30) -> Dict:
        """환불 통계 조회"""
        try:
            from app.models.order import DropshippingOrderLog
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 환불 로그 조회
            refund_logs = (
                self.db.query(DropshippingOrderLog)
                .filter(
                    and_(
                        DropshippingOrderLog.action == 'refund_requested',
                        DropshippingOrderLog.created_at >= start_date
                    )
                )
                .all()
            )
            
            # 통계 계산
            total_refunds = len(refund_logs)
            completed_refunds = 0
            total_refund_amount = Decimal('0')
            refund_reasons = {}
            
            for log in refund_logs:
                if log.response_data:
                    refund_data = log.response_data
                    
                    # 완료된 환불 카운트
                    if refund_data.get('status') == RefundStatus.COMPLETED.value:
                        completed_refunds += 1
                        total_refund_amount += Decimal(str(refund_data.get('refund_amount', 0)))
                    
                    # 환불 사유별 통계
                    reason = refund_data.get('refund_reason', 'unknown')
                    refund_reasons[reason] = refund_reasons.get(reason, 0) + 1
            
            return {
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'summary': {
                    'total_refunds': total_refunds,
                    'completed_refunds': completed_refunds,
                    'pending_refunds': total_refunds - completed_refunds,
                    'completion_rate': (completed_refunds / total_refunds * 100) if total_refunds > 0 else 0,
                    'total_refund_amount': float(total_refund_amount)
                },
                'refund_reasons': refund_reasons,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"환불 통계 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'환불 통계 조회 중 오류: {str(e)}'
            }
    
    async def get_pending_refunds(self, limit: int = 50) -> List[Dict]:
        """대기 중인 환불 목록 조회"""
        try:
            from app.models.order import DropshippingOrderLog
            
            # 수동 검토가 필요한 환불 요청들 조회
            pending_logs = (
                self.db.query(DropshippingOrderLog)
                .join(DropshippingOrder, DropshippingOrderLog.dropshipping_order_id == DropshippingOrder.id)
                .filter(
                    and_(
                        DropshippingOrderLog.action == 'refund_requested',
                        DropshippingOrder.is_blocked == True
                    )
                )
                .limit(limit)
                .all()
            )
            
            pending_refunds = []
            for log in pending_logs:
                if log.response_data:
                    refund_data = log.response_data
                    dropshipping_order = log.dropshipping_order
                    
                    pending_refunds.append({
                        'refund_id': refund_data.get('id'),
                        'order_number': dropshipping_order.order.order_number,
                        'customer_name': dropshipping_order.order.customer_name,
                        'refund_reason': refund_data.get('refund_reason'),
                        'refund_amount': refund_data.get('refund_amount'),
                        'requested_at': log.created_at.isoformat(),
                        'days_pending': (datetime.utcnow() - log.created_at).days
                    })
            
            return pending_refunds
            
        except Exception as e:
            logger.error(f"대기 중인 환불 목록 조회 중 오류: {str(e)}")
            return []