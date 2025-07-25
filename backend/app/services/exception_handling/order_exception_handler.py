"""
드롭쉬핑 주문 예외 처리 서비스
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.order import DropshippingOrder, SupplierOrderStatus, Order, OrderStatus
from app.models.wholesaler import Wholesaler

logger = logging.getLogger(__name__)


class ExceptionType(Enum):
    """예외 타입"""
    OUT_OF_STOCK = "out_of_stock"
    PRICE_CHANGED = "price_changed"
    SUPPLIER_ERROR = "supplier_error"
    PAYMENT_FAILED = "payment_failed"
    DELIVERY_FAILED = "delivery_failed"
    SYSTEM_ERROR = "system_error"
    MARGIN_TOO_LOW = "margin_too_low"
    SUPPLIER_UNAVAILABLE = "supplier_unavailable"
    CUSTOMER_ISSUE = "customer_issue"


class ExceptionSeverity(Enum):
    """예외 심각도"""
    LOW = "low"           # 자동 처리 가능
    MEDIUM = "medium"     # 부분 자동 처리
    HIGH = "high"         # 수동 처리 필요
    CRITICAL = "critical" # 즉시 처리 필요


class OrderExceptionHandler:
    """드롭쉬핑 주문 예외 처리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 예외 타입별 처리 규칙
        self.exception_rules = {
            ExceptionType.OUT_OF_STOCK: {
                'severity': ExceptionSeverity.MEDIUM,
                'auto_retry': True,
                'max_retries': 2,
                'retry_delay_hours': 6,
                'notify_customer': True,
                'actions': ['find_alternative', 'cancel_order']
            },
            ExceptionType.PRICE_CHANGED: {
                'severity': ExceptionSeverity.HIGH,
                'auto_retry': False,
                'max_retries': 0,
                'notify_customer': True,
                'actions': ['margin_check', 'manual_review']
            },
            ExceptionType.SUPPLIER_ERROR: {
                'severity': ExceptionSeverity.MEDIUM,
                'auto_retry': True,
                'max_retries': 3,
                'retry_delay_hours': 2,
                'notify_customer': False,
                'actions': ['retry_order', 'switch_supplier']
            },
            ExceptionType.DELIVERY_FAILED: {
                'severity': ExceptionSeverity.HIGH,
                'auto_retry': False,
                'max_retries': 0,
                'notify_customer': True,
                'actions': ['investigate_delivery', 'customer_contact']
            },
            ExceptionType.MARGIN_TOO_LOW: {
                'severity': ExceptionSeverity.CRITICAL,
                'auto_retry': False,
                'max_retries': 0,
                'notify_customer': False,
                'actions': ['cancel_order', 'price_adjustment']
            }
        }
    
    async def handle_exception(
        self, 
        dropshipping_order: DropshippingOrder,
        exception_type: ExceptionType,
        exception_data: Dict,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        주문 예외 처리
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            exception_type: 예외 타입
            exception_data: 예외 데이터
            context: 추가 컨텍스트
            
        Returns:
            Dict: 처리 결과
        """
        try:
            logger.info(f"주문 예외 처리 시작: {dropshipping_order.order.order_number} ({exception_type.value})")
            
            # 예외 처리 규칙 조회
            rule = self.exception_rules.get(exception_type)
            if not rule:
                return {
                    'success': False,
                    'message': f'지원하지 않는 예외 타입: {exception_type.value}'
                }
            
            # 예외 기록 생성
            exception_record = await self._create_exception_record(
                dropshipping_order, exception_type, exception_data, rule
            )
            
            # 예외 타입별 처리
            if exception_type == ExceptionType.OUT_OF_STOCK:
                result = await self._handle_out_of_stock(dropshipping_order, exception_data, rule)
            elif exception_type == ExceptionType.PRICE_CHANGED:
                result = await self._handle_price_changed(dropshipping_order, exception_data, rule)
            elif exception_type == ExceptionType.SUPPLIER_ERROR:
                result = await self._handle_supplier_error(dropshipping_order, exception_data, rule)
            elif exception_type == ExceptionType.DELIVERY_FAILED:
                result = await self._handle_delivery_failed(dropshipping_order, exception_data, rule)
            elif exception_type == ExceptionType.MARGIN_TOO_LOW:
                result = await self._handle_margin_too_low(dropshipping_order, exception_data, rule)
            else:
                result = await self._handle_generic_exception(dropshipping_order, exception_data, rule)
            
            # 처리 결과 업데이트
            await self._update_exception_record(exception_record, result)
            
            # 고객 알림 (필요시)
            if rule.get('notify_customer', False) and result.get('notify_customer', True):
                await self._notify_customer_about_exception(dropshipping_order, exception_type, result)
            
            # 관리자 알림 (심각한 예외)
            if rule['severity'] in [ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL]:
                await self._notify_admin_about_exception(dropshipping_order, exception_type, result)
            
            logger.info(f"주문 예외 처리 완료: {dropshipping_order.order.order_number}")
            
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'exception_id': exception_record['id'],
                'actions_taken': result.get('actions_taken', []),
                'next_steps': result.get('next_steps', []),
                'resolution_time': result.get('resolution_time'),
                'requires_manual_review': result.get('requires_manual_review', False)
            }
            
        except Exception as e:
            logger.error(f"주문 예외 처리 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'예외 처리 중 오류 발생: {str(e)}'
            }
    
    async def _handle_out_of_stock(self, dropshipping_order: DropshippingOrder, exception_data: Dict, rule: Dict) -> Dict:
        """품절 예외 처리"""
        try:
            actions_taken = []
            next_steps = []
            
            # 1. 대체 상품 찾기
            alternative_result = await self._find_alternative_products(dropshipping_order, exception_data)
            if alternative_result['success'] and alternative_result['alternatives']:
                actions_taken.append('대체 상품 발견')
                next_steps.append('고객에게 대체 상품 제안')
                
                # 주문 상태 업데이트
                dropshipping_order.status = SupplierOrderStatus.OUT_OF_STOCK
                dropshipping_order.processing_notes = f"품절 - 대체 상품 {len(alternative_result['alternatives'])}개 발견"
                
                return {
                    'success': True,
                    'message': '대체 상품을 찾았습니다',
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'alternatives': alternative_result['alternatives'],
                    'notify_customer': True,
                    'requires_manual_review': True
                }
            
            # 2. 재입고 예정 확인
            restock_info = await self._check_restock_schedule(dropshipping_order, exception_data)
            if restock_info['success'] and restock_info.get('expected_date'):
                actions_taken.append('재입고 예정 확인')
                next_steps.append(f"재입고 대기 ({restock_info['expected_date']})")
                
                # 재입고 대기 상태로 변경
                dropshipping_order.processing_notes = f"품절 - 재입고 예정: {restock_info['expected_date']}"
                
                return {
                    'success': True,
                    'message': f"재입고 예정일: {restock_info['expected_date']}",
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'restock_date': restock_info['expected_date'],
                    'notify_customer': True,
                    'requires_manual_review': False
                }
            
            # 3. 주문 취소 처리
            cancel_result = await self._cancel_order_due_to_stock(dropshipping_order, exception_data)
            actions_taken.append('주문 취소 처리')
            next_steps.append('고객에게 취소 안내 및 환불 처리')
            
            return {
                'success': True,
                'message': '품절로 인한 주문 취소 처리',
                'actions_taken': actions_taken,
                'next_steps': next_steps,
                'cancelled': True,
                'notify_customer': True,
                'requires_manual_review': False
            }
            
        except Exception as e:
            logger.error(f"품절 예외 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'품절 예외 처리 중 오류: {str(e)}',
                'requires_manual_review': True
            }
    
    async def _handle_price_changed(self, dropshipping_order: DropshippingOrder, exception_data: Dict, rule: Dict) -> Dict:
        """가격 변동 예외 처리"""
        try:
            old_price = exception_data.get('old_price', 0)
            new_price = exception_data.get('new_price', 0)
            price_change_rate = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
            
            actions_taken = []
            next_steps = []
            
            # 마진 재계산
            from app.services.order_processing.margin_calculator import MarginCalculator
            margin_calculator = MarginCalculator(self.db)
            
            # 새 가격으로 마진 계산
            new_margin = await margin_calculator.calculate_margin(
                dropshipping_order.customer_price,
                new_price
            )
            
            actions_taken.append(f'가격 변동 감지 ({price_change_rate:.1f}%)')
            actions_taken.append('마진 재계산 완료')
            
            # 마진 보호 기준 확인
            if new_margin['margin_rate'] >= dropshipping_order.minimum_margin_rate:
                # 마진이 충분한 경우 - 자동 승인
                dropshipping_order.supplier_price = new_price
                dropshipping_order.margin_amount = new_margin['margin_amount']
                dropshipping_order.margin_rate = new_margin['margin_rate']
                
                actions_taken.append('가격 변동 자동 승인')
                next_steps.append('주문 처리 계속')
                
                return {
                    'success': True,
                    'message': f'가격 변동 자동 승인 (새 마진율: {new_margin["margin_rate"]:.1f}%)',
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'new_price': new_price,
                    'new_margin_rate': new_margin['margin_rate'],
                    'notify_customer': False,
                    'requires_manual_review': False
                }
            else:
                # 마진이 부족한 경우 - 수동 검토 필요
                dropshipping_order.is_blocked = True
                dropshipping_order.blocked_reason = f'가격 인상으로 인한 마진 부족 (현재: {new_margin["margin_rate"]:.1f}%, 최소: {dropshipping_order.minimum_margin_rate}%)'
                
                actions_taken.append('마진 부족으로 주문 블록')
                next_steps.append('수동 검토 필요')
                
                return {
                    'success': True,
                    'message': '마진 부족으로 수동 검토가 필요합니다',
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'new_price': new_price,
                    'new_margin_rate': new_margin['margin_rate'],
                    'margin_shortage': dropshipping_order.minimum_margin_rate - new_margin['margin_rate'],
                    'notify_customer': False,
                    'requires_manual_review': True
                }
            
        except Exception as e:
            logger.error(f"가격 변동 예외 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'가격 변동 예외 처리 중 오류: {str(e)}',
                'requires_manual_review': True
            }
    
    async def _handle_supplier_error(self, dropshipping_order: DropshippingOrder, exception_data: Dict, rule: Dict) -> Dict:
        """공급업체 오류 예외 처리"""
        try:
            error_type = exception_data.get('error_type', 'unknown')
            error_message = exception_data.get('error_message', '')
            
            actions_taken = []
            next_steps = []
            
            # 재시도 가능 여부 확인
            if dropshipping_order.can_retry and rule.get('auto_retry', False):
                actions_taken.append('자동 재시도 예약')
                next_steps.append(f"{rule.get('retry_delay_hours', 2)}시간 후 재시도")
                
                # 재시도 스케줄링
                retry_time = datetime.utcnow() + timedelta(hours=rule.get('retry_delay_hours', 2))
                dropshipping_order.processing_notes = f"공급업체 오류 - {retry_time.strftime('%Y-%m-%d %H:%M')} 재시도 예정"
                
                return {
                    'success': True,
                    'message': '공급업체 오류 - 자동 재시도 예약',
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'retry_scheduled': True,
                    'retry_time': retry_time.isoformat(),
                    'notify_customer': False,
                    'requires_manual_review': False
                }
            
            # 대체 공급업체 찾기
            alternative_supplier = await self._find_alternative_supplier(dropshipping_order)
            if alternative_supplier['success']:
                actions_taken.append('대체 공급업체 발견')
                next_steps.append('대체 공급업체로 주문 재시도')
                
                # 공급업체 변경
                dropshipping_order.supplier_id = alternative_supplier['supplier_id']
                dropshipping_order.processing_notes = f"공급업체 변경: {alternative_supplier['supplier_name']}"
                
                return {
                    'success': True,
                    'message': f"대체 공급업체로 변경: {alternative_supplier['supplier_name']}",
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'new_supplier': alternative_supplier,
                    'notify_customer': False,
                    'requires_manual_review': False
                }
            
            # 수동 처리 필요
            dropshipping_order.is_blocked = True
            dropshipping_order.blocked_reason = f'공급업체 오류: {error_message}'
            
            actions_taken.append('수동 처리로 전환')
            next_steps.append('관리자 검토 필요')
            
            return {
                'success': True,
                'message': '공급업체 오류로 수동 처리가 필요합니다',
                'actions_taken': actions_taken,
                'next_steps': next_steps,
                'error_details': exception_data,
                'notify_customer': False,
                'requires_manual_review': True
            }
            
        except Exception as e:
            logger.error(f"공급업체 오류 예외 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'공급업체 오류 예외 처리 중 오류: {str(e)}',
                'requires_manual_review': True
            }
    
    async def _handle_delivery_failed(self, dropshipping_order: DropshippingOrder, exception_data: Dict, rule: Dict) -> Dict:
        """배송 실패 예외 처리"""
        try:
            failure_reason = exception_data.get('failure_reason', '')
            tracking_number = exception_data.get('tracking_number', '')
            
            actions_taken = []
            next_steps = []
            
            # 배송 상태 업데이트
            dropshipping_order.status = SupplierOrderStatus.FAILED
            dropshipping_order.processing_notes = f"배송 실패: {failure_reason}"
            
            actions_taken.append('배송 실패 확인')
            
            # 배송 실패 유형별 처리
            if '주소오류' in failure_reason or 'address' in failure_reason.lower():
                actions_taken.append('주소 오류 감지')
                next_steps.append('고객에게 주소 확인 요청')
                
                return {
                    'success': True,
                    'message': '배송 주소 오류로 고객 확인이 필요합니다',
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'failure_type': 'address_error',
                    'notify_customer': True,
                    'requires_manual_review': True
                }
            
            elif '부재중' in failure_reason or 'absent' in failure_reason.lower():
                actions_taken.append('고객 부재 확인')
                next_steps.append('재배송 처리')
                
                return {
                    'success': True,
                    'message': '고객 부재로 재배송 처리',
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'failure_type': 'customer_absent',
                    'notify_customer': True,
                    'requires_manual_review': False
                }
            
            else:
                # 기타 배송 실패
                actions_taken.append('배송 실패 조사 필요')
                next_steps.append('배송업체 문의 및 고객 안내')
                
                return {
                    'success': True,
                    'message': '배송 실패 - 조사 및 고객 안내 필요',
                    'actions_taken': actions_taken,
                    'next_steps': next_steps,
                    'failure_type': 'other',
                    'notify_customer': True,
                    'requires_manual_review': True
                }
            
        except Exception as e:
            logger.error(f"배송 실패 예외 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'배송 실패 예외 처리 중 오류: {str(e)}',
                'requires_manual_review': True
            }
    
    async def _handle_margin_too_low(self, dropshipping_order: DropshippingOrder, exception_data: Dict, rule: Dict) -> Dict:
        """마진 부족 예외 처리"""
        try:
            current_margin = exception_data.get('current_margin_rate', 0)
            minimum_margin = exception_data.get('minimum_margin_rate', 0)
            
            actions_taken = []
            next_steps = []
            
            # 즉시 주문 중단
            dropshipping_order.is_blocked = True
            dropshipping_order.blocked_reason = f'마진 부족 (현재: {current_margin:.1f}%, 최소: {minimum_margin:.1f}%)'
            
            actions_taken.append('마진 부족으로 주문 중단')
            
            # 마진 개선 방안 제시
            improvement_suggestions = []
            
            # 1. 판매가 인상 가능성 확인
            price_increase_needed = (minimum_margin - current_margin) / 100 * dropshipping_order.customer_price
            if price_increase_needed < dropshipping_order.customer_price * 0.1:  # 10% 미만 인상
                improvement_suggestions.append(f'판매가 {price_increase_needed:.0f}원 인상 검토')
            
            # 2. 대체 공급업체 확인
            alternative_supplier = await self._find_cheaper_supplier(dropshipping_order)
            if alternative_supplier['success']:
                improvement_suggestions.append(f'더 저렴한 공급업체 발견: {alternative_supplier["supplier_name"]}')
            
            # 3. 주문 취소 권고
            if not improvement_suggestions:
                improvement_suggestions.append('주문 취소 권고')
                next_steps.append('주문 취소 및 고객 안내')
            else:
                next_steps.append('마진 개선 방안 검토')
            
            actions_taken.extend(improvement_suggestions)
            
            return {
                'success': True,
                'message': '마진 부족으로 주문이 중단되었습니다',
                'actions_taken': actions_taken,
                'next_steps': next_steps,
                'current_margin': current_margin,
                'minimum_margin': minimum_margin,
                'improvement_suggestions': improvement_suggestions,
                'notify_customer': False,
                'requires_manual_review': True
            }
            
        except Exception as e:
            logger.error(f"마진 부족 예외 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'마진 부족 예외 처리 중 오류: {str(e)}',
                'requires_manual_review': True
            }
    
    async def _handle_generic_exception(self, dropshipping_order: DropshippingOrder, exception_data: Dict, rule: Dict) -> Dict:
        """일반 예외 처리"""
        try:
            # 기본적인 예외 처리
            dropshipping_order.is_blocked = True
            dropshipping_order.blocked_reason = f"예외 발생: {exception_data.get('message', 'Unknown error')}"
            
            return {
                'success': True,
                'message': '예외가 발생하여 수동 처리가 필요합니다',
                'actions_taken': ['예외 기록', '수동 처리로 전환'],
                'next_steps': ['관리자 검토 필요'],
                'exception_data': exception_data,
                'notify_customer': rule.get('notify_customer', False),
                'requires_manual_review': True
            }
            
        except Exception as e:
            logger.error(f"일반 예외 처리 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'일반 예외 처리 중 오류: {str(e)}',
                'requires_manual_review': True
            }
    
    async def _create_exception_record(
        self, 
        dropshipping_order: DropshippingOrder, 
        exception_type: ExceptionType,
        exception_data: Dict,
        rule: Dict
    ) -> Dict:
        """예외 기록 생성"""
        try:
            # 실제로는 별도의 예외 테이블에 저장
            # 여기서는 드롭쉬핑 주문 로그에 저장
            from app.models.order import DropshippingOrderLog
            
            exception_record = {
                'id': f"EXC_{int(datetime.utcnow().timestamp())}",
                'dropshipping_order_id': dropshipping_order.id,
                'exception_type': exception_type.value,
                'severity': rule['severity'].value,
                'exception_data': exception_data,
                'created_at': datetime.utcnow(),
                'status': 'processing'
            }
            
            log = DropshippingOrderLog(
                dropshipping_order_id=dropshipping_order.id,
                action=f'exception_{exception_type.value}',
                success=False,
                error_message=f"예외 발생: {exception_type.value}",
                response_data=exception_record,
                processing_time_ms=0
            )
            
            self.db.add(log)
            self.db.commit()
            
            return exception_record
            
        except Exception as e:
            logger.error(f"예외 기록 생성 중 오류: {str(e)}")
            return {'id': 'ERROR', 'status': 'failed'}
    
    async def _update_exception_record(self, exception_record: Dict, result: Dict):
        """예외 기록 업데이트"""
        try:
            exception_record['status'] = 'resolved' if result.get('success', False) else 'failed'
            exception_record['resolution_data'] = result
            exception_record['resolved_at'] = datetime.utcnow()
            
            # 실제로는 데이터베이스에 업데이트
            logger.info(f"예외 기록 업데이트: {exception_record['id']}")
            
        except Exception as e:
            logger.error(f"예외 기록 업데이트 중 오류: {str(e)}")
    
    async def _find_alternative_products(self, dropshipping_order: DropshippingOrder, exception_data: Dict) -> Dict:
        """대체 상품 찾기"""
        try:
            # 실제로는 상품 매칭 알고리즘 사용
            # 여기서는 간단한 구현
            
            order_items = dropshipping_order.order.order_items
            alternatives = []
            
            for item in order_items:
                # 유사한 상품 검색 로직
                # 카테고리, 가격대, 브랜드 등을 고려
                alternative = {
                    'original_sku': item.sku,
                    'original_name': item.product_name,
                    'alternative_sku': f"ALT_{item.sku}",
                    'alternative_name': f"대체 상품 - {item.product_name}",
                    'price_difference': 0,
                    'availability': True
                }
                alternatives.append(alternative)
            
            return {
                'success': len(alternatives) > 0,
                'alternatives': alternatives,
                'total_found': len(alternatives)
            }
            
        except Exception as e:
            logger.error(f"대체 상품 찾기 중 오류: {str(e)}")
            return {
                'success': False,
                'alternatives': [],
                'error': str(e)
            }
    
    async def _check_restock_schedule(self, dropshipping_order: DropshippingOrder, exception_data: Dict) -> Dict:
        """재입고 예정 확인"""
        try:
            # 실제로는 공급업체 API를 통해 재입고 정보 조회
            # 여기서는 가상의 데이터 반환
            
            expected_date = (datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')
            
            return {
                'success': True,
                'expected_date': expected_date,
                'confirmed': False,
                'estimated_quantity': 100
            }
            
        except Exception as e:
            logger.error(f"재입고 예정 확인 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _cancel_order_due_to_stock(self, dropshipping_order: DropshippingOrder, exception_data: Dict) -> Dict:
        """품절로 인한 주문 취소"""
        try:
            # 주문 상태 업데이트
            dropshipping_order.status = SupplierOrderStatus.CANCELLED
            dropshipping_order.order.status = OrderStatus.CANCELLED
            dropshipping_order.processing_notes = "품절로 인한 주문 취소"
            
            # 환불 처리는 별도 서비스에서 처리
            
            self.db.commit()
            
            return {
                'success': True,
                'cancelled_at': datetime.utcnow().isoformat(),
                'reason': '품절'
            }
            
        except Exception as e:
            logger.error(f"주문 취소 처리 중 오류: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _find_alternative_supplier(self, dropshipping_order: DropshippingOrder) -> Dict:
        """대체 공급업체 찾기"""
        try:
            # 현재 공급업체 제외하고 활성 공급업체 조회
            current_supplier_id = dropshipping_order.supplier_id
            
            alternative_suppliers = self.db.query(Wholesaler).filter(
                and_(
                    Wholesaler.is_active == True,
                    Wholesaler.id != current_supplier_id
                )
            ).all()
            
            if alternative_suppliers:
                # 첫 번째 대체 공급업체 선택 (실제로는 더 복잡한 선택 로직)
                selected_supplier = alternative_suppliers[0]
                
                return {
                    'success': True,
                    'supplier_id': selected_supplier.id,
                    'supplier_name': selected_supplier.name,
                    'supplier_type': selected_supplier.wholesaler_type
                }
            
            return {
                'success': False,
                'message': '대체 공급업체를 찾을 수 없습니다'
            }
            
        except Exception as e:
            logger.error(f"대체 공급업체 찾기 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _find_cheaper_supplier(self, dropshipping_order: DropshippingOrder) -> Dict:
        """더 저렴한 공급업체 찾기"""
        try:
            # 실제로는 상품별 공급업체 가격 비교
            # 여기서는 간단한 구현
            
            current_price = dropshipping_order.supplier_price
            
            # 가상의 더 저렴한 공급업체
            cheaper_supplier = {
                'supplier_id': 'cheaper_supplier_id',
                'supplier_name': '저렴한 공급업체',
                'price': current_price * 0.9,  # 10% 더 저렴
                'savings': current_price * 0.1
            }
            
            return {
                'success': True,
                **cheaper_supplier
            }
            
        except Exception as e:
            logger.error(f"더 저렴한 공급업체 찾기 중 오류: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _notify_customer_about_exception(self, dropshipping_order: DropshippingOrder, exception_type: ExceptionType, result: Dict):
        """고객에게 예외 상황 알림"""
        try:
            from app.services.shipping.customer_notifier import CustomerNotifier
            
            notifier = CustomerNotifier(self.db)
            
            # 예외 타입별 알림 메시지
            notification_type_map = {
                ExceptionType.OUT_OF_STOCK: 'out_of_stock',
                ExceptionType.DELIVERY_FAILED: 'delivery_delay',
                ExceptionType.PRICE_CHANGED: 'order_cancelled'  # 가격 변동 시 취소 안내
            }
            
            notification_type = notification_type_map.get(exception_type, 'order_cancelled')
            
            await notifier.notify_order_status_change(
                dropshipping_order,
                notification_type,
                {
                    'exception_type': exception_type.value,
                    'message': result.get('message', ''),
                    'actions_taken': result.get('actions_taken', [])
                }
            )
            
        except Exception as e:
            logger.error(f"고객 예외 알림 중 오류: {str(e)}")
    
    async def _notify_admin_about_exception(self, dropshipping_order: DropshippingOrder, exception_type: ExceptionType, result: Dict):
        """관리자에게 예외 상황 알림"""
        try:
            # 관리자 알림 로직 (이메일, 슬랙 등)
            admin_notification = {
                'order_number': dropshipping_order.order.order_number,
                'exception_type': exception_type.value,
                'severity': self.exception_rules[exception_type]['severity'].value,
                'message': result.get('message', ''),
                'requires_manual_review': result.get('requires_manual_review', False),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.warning(f"관리자 알림 필요: {admin_notification}")
            
            # 실제로는 이메일이나 슬랙으로 알림 발송
            
        except Exception as e:
            logger.error(f"관리자 예외 알림 중 오류: {str(e)}")
    
    async def handle_processing_exception(self, order_id: str, exception: Exception) -> Dict:
        """주문 처리 중 발생한 시스템 예외 처리"""
        try:
            dropshipping_order = self.db.query(DropshippingOrder).join(Order).filter(
                Order.id == order_id
            ).first()
            
            if not dropshipping_order:
                return {
                    'success': False,
                    'message': '주문을 찾을 수 없습니다'
                }
            
            exception_data = {
                'error_type': type(exception).__name__,
                'error_message': str(exception),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return await self.handle_exception(
                dropshipping_order,
                ExceptionType.SYSTEM_ERROR,
                exception_data
            )
            
        except Exception as e:
            logger.error(f"시스템 예외 처리 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'시스템 예외 처리 중 오류: {str(e)}'
            }
    
    async def get_exception_statistics(self, days: int = 30) -> Dict:
        """예외 통계 조회"""
        try:
            from app.models.order import DropshippingOrderLog
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 예외 로그 조회
            exception_logs = (
                self.db.query(DropshippingOrderLog)
                .filter(
                    and_(
                        DropshippingOrderLog.action.like('exception_%'),
                        DropshippingOrderLog.created_at >= start_date
                    )
                )
                .all()
            )
            
            # 예외 타입별 통계
            exception_stats = {}
            for log in exception_logs:
                exception_type = log.action.replace('exception_', '')
                if exception_type not in exception_stats:
                    exception_stats[exception_type] = {
                        'count': 0,
                        'resolved': 0,
                        'manual_review': 0
                    }
                
                exception_stats[exception_type]['count'] += 1
                
                if log.response_data and log.response_data.get('status') == 'resolved':
                    exception_stats[exception_type]['resolved'] += 1
                
                if log.response_data and log.response_data.get('requires_manual_review'):
                    exception_stats[exception_type]['manual_review'] += 1
            
            return {
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'total_exceptions': len(exception_logs),
                'exception_types': exception_stats,
                'resolution_rate': sum(stats['resolved'] for stats in exception_stats.values()) / len(exception_logs) * 100 if exception_logs else 0
            }
            
        except Exception as e:
            logger.error(f"예외 통계 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'예외 통계 조회 중 오류: {str(e)}'
            }