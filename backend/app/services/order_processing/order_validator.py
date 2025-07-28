"""
드롭쉬핑 주문 검증 서비스
"""
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.order_core import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.product import Product
from app.models.wholesaler import Wholesaler
from app.models.platform_account import PlatformAccount

logger = logging.getLogger(__name__)


class OrderValidator:
    """드롭쉬핑 주문 검증"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def validate_order_for_dropshipping(self, order: Order) -> Dict:
        """
        드롭쉬핑 처리 가능 여부 검증
        
        Args:
            order: 검증할 주문
            
        Returns:
            Dict: 검증 결과
        """
        validation_result = {
            'success': True,
            'message': '주문 검증 완료',
            'issues': [],
            'warnings': []
        }
        
        try:
            # 1. 기본 주문 정보 검증
            basic_validation = await self._validate_basic_order_info(order)
            if not basic_validation['success']:
                validation_result['success'] = False
                validation_result['issues'].extend(basic_validation['issues'])
            
            # 2. 결제 상태 검증
            payment_validation = await self._validate_payment_status(order)
            if not payment_validation['success']:
                validation_result['success'] = False
                validation_result['issues'].extend(payment_validation['issues'])
            
            # 3. 주문 상품 검증
            items_validation = await self._validate_order_items(order)
            if not items_validation['success']:
                validation_result['success'] = False
                validation_result['issues'].extend(items_validation['issues'])
            validation_result['warnings'].extend(items_validation.get('warnings', []))
            
            # 4. 배송 정보 검증
            shipping_validation = await self._validate_shipping_info(order)
            if not shipping_validation['success']:
                validation_result['success'] = False
                validation_result['issues'].extend(shipping_validation['issues'])
            
            # 5. 플랫폼 계정 검증
            platform_validation = await self._validate_platform_account(order)
            if not platform_validation['success']:
                validation_result['success'] = False
                validation_result['issues'].extend(platform_validation['issues'])
            
            # 6. 중복 처리 검증
            duplicate_validation = await self._validate_duplicate_processing(order)
            if not duplicate_validation['success']:
                validation_result['success'] = False
                validation_result['issues'].extend(duplicate_validation['issues'])
            
            if not validation_result['success']:
                validation_result['message'] = f"주문 검증 실패: {len(validation_result['issues'])}개 문제 발견"
            elif validation_result['warnings']:
                validation_result['message'] = f"주문 검증 완료 ({len(validation_result['warnings'])}개 경고)"
            
            logger.info(f"주문 검증 완료 ({order.order_number}): {validation_result['message']}")
            
        except Exception as e:
            logger.error(f"주문 검증 중 예외 발생: {str(e)}", exc_info=True)
            validation_result['success'] = False
            validation_result['message'] = f'검증 중 오류 발생: {str(e)}'
            validation_result['issues'].append(f'시스템 오류: {str(e)}')
        
        return validation_result
    
    async def _validate_basic_order_info(self, order: Order) -> Dict:
        """기본 주문 정보 검증"""
        issues = []
        
        # 주문 상태 검증
        valid_statuses = [
            OrderStatus.PENDING, 
            OrderStatus.CONFIRMED, 
            OrderStatus.PAID,
            OrderStatus.SUPPLIER_ORDER_PENDING
        ]
        
        if order.status not in valid_statuses:
            issues.append(f"처리할 수 없는 주문 상태: {order.status.value}")
        
        # 주문 금액 검증
        if order.total_amount <= 0:
            issues.append("주문 금액이 0 이하입니다")
        
        # 주문 일자 검증 (너무 오래된 주문)
        if order.order_date:
            days_old = (datetime.utcnow() - order.order_date).days
            if days_old > 30:
                issues.append(f"주문이 너무 오래되었습니다 ({days_old}일)")
        
        # 고객 정보 검증
        if not order.customer_name or not order.customer_name.strip():
            issues.append("고객명이 누락되었습니다")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    async def _validate_payment_status(self, order: Order) -> Dict:
        """결제 상태 검증"""
        issues = []
        
        # 결제 완료 여부 확인
        if order.payment_status != PaymentStatus.PAID:
            issues.append(f"결제가 완료되지 않았습니다: {order.payment_status.value}")
        
        # 결제 금액 검증
        if hasattr(order, 'payments') and order.payments:
            total_paid = sum(payment.amount for payment in order.payments 
                           if payment.status == PaymentStatus.PAID)
            if total_paid < order.total_amount:
                issues.append(f"결제 금액 부족: {total_paid} < {order.total_amount}")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    async def _validate_order_items(self, order: Order) -> Dict:
        """주문 상품 검증"""
        issues = []
        warnings = []
        
        if not order.order_items or len(order.order_items) == 0:
            issues.append("주문 상품이 없습니다")
            return {'success': False, 'issues': issues, 'warnings': warnings}
        
        for item in order.order_items:
            # 수량 검증
            if item.quantity <= 0:
                issues.append(f"상품 수량이 잘못되었습니다: {item.sku} (수량: {item.quantity})")
            
            # 가격 검증
            if item.unit_price <= 0:
                issues.append(f"상품 가격이 잘못되었습니다: {item.sku} (가격: {item.unit_price})")
            
            # 상품 정보 검증
            if item.product_id:
                product = self.db.query(Product).filter(Product.id == item.product_id).first()
                if not product:
                    issues.append(f"상품 정보를 찾을 수 없습니다: {item.sku}")
                elif not product.is_active:
                    warnings.append(f"비활성 상품입니다: {item.sku}")
            
            # SKU 검증
            if not item.sku or not item.sku.strip():
                issues.append("상품 SKU가 누락되었습니다")
            
            # 상품명 검증
            if not item.product_name or not item.product_name.strip():
                issues.append(f"상품명이 누락되었습니다: {item.sku}")
        
        return {
            'success': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    async def _validate_shipping_info(self, order: Order) -> Dict:
        """배송 정보 검증"""
        issues = []
        
        # 배송 주소 검증
        required_fields = ['shipping_address1', 'shipping_city']
        for field in required_fields:
            value = getattr(order, field, None)
            if not value or not value.strip():
                issues.append(f"배송 정보 누락: {field}")
        
        # 배송 국가 검증 (한국 내 배송만 지원한다고 가정)
        if order.shipping_country and order.shipping_country.upper() != 'KR':
            issues.append(f"지원하지 않는 배송 국가: {order.shipping_country}")
        
        # 배송비 검증
        if order.shipping_cost < 0:
            issues.append("배송비가 음수입니다")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    async def _validate_platform_account(self, order: Order) -> Dict:
        """플랫폼 계정 검증"""
        issues = []
        
        if not order.platform_account_id:
            issues.append("플랫폼 계정 정보가 누락되었습니다")
            return {'success': False, 'issues': issues}
        
        platform_account = self.db.query(PlatformAccount).filter(
            PlatformAccount.id == order.platform_account_id
        ).first()
        
        if not platform_account:
            issues.append("플랫폼 계정을 찾을 수 없습니다")
        elif not platform_account.is_active:
            issues.append("비활성 플랫폼 계정입니다")
        elif not platform_account.api_credentials:
            issues.append("플랫폼 API 인증 정보가 없습니다")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    async def _validate_duplicate_processing(self, order: Order) -> Dict:
        """중복 처리 검증"""
        issues = []
        
        # 이미 처리 중인 주문인지 확인
        from app.models.order_core import DropshippingOrder
        existing = self.db.query(DropshippingOrder).filter(
            DropshippingOrder.order_id == order.id
        ).first()
        
        if existing:
            # 이미 성공적으로 처리된 주문
            success_statuses = [
                'confirmed', 'processing', 'shipped', 'delivered'
            ]
            if existing.status.value in success_statuses:
                issues.append("이미 처리된 주문입니다")
            
            # 현재 처리 중인 주문
            elif existing.status.value == 'submitted':
                issues.append("현재 처리 중인 주문입니다")
        
        return {
            'success': len(issues) == 0,
            'issues': issues
        }
    
    async def validate_order_items_availability(self, order: Order) -> Dict:
        """주문 상품 재고 확인"""
        availability_result = {
            'success': True,
            'message': '모든 상품이 주문 가능합니다',
            'items': []
        }
        
        try:
            for item in order.order_items:
                item_result = {
                    'sku': item.sku,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'available': True,
                    'available_quantity': 0,
                    'suppliers': []
                }
                
                # 상품에 연결된 공급업체들의 재고 확인
                if item.product_id:
                    product = self.db.query(Product).filter(Product.id == item.product_id).first()
                    if product:
                        # 공급업체 재고 정보 조회 (실제 구현에서는 wholesaler API 호출)
                        suppliers = self.db.query(Wholesaler).filter(
                            Wholesaler.is_active == True
                        ).all()
                        
                        for supplier in suppliers:
                            # 여기서는 가상의 재고 정보를 생성
                            # 실제로는 각 공급업체 API를 호출해야 함
                            supplier_stock = {
                                'supplier_id': str(supplier.id),
                                'supplier_name': supplier.name,
                                'available_quantity': 100,  # 실제 API 호출 필요
                                'price': item.unit_price * Decimal('0.7'),  # 가상의 공급가격
                                'lead_time_days': 2
                            }
                            item_result['suppliers'].append(supplier_stock)
                
                # 최대 가용 수량 계산
                if item_result['suppliers']:
                    item_result['available_quantity'] = max(
                        s['available_quantity'] for s in item_result['suppliers']
                    )
                    item_result['available'] = item_result['available_quantity'] >= item.quantity
                else:
                    item_result['available'] = False
                    availability_result['success'] = False
                
                availability_result['items'].append(item_result)
            
            unavailable_items = [item for item in availability_result['items'] if not item['available']]
            if unavailable_items:
                availability_result['success'] = False
                availability_result['message'] = f"{len(unavailable_items)}개 상품의 재고가 부족합니다"
            
        except Exception as e:
            logger.error(f"재고 확인 중 오류: {str(e)}", exc_info=True)
            availability_result['success'] = False
            availability_result['message'] = f'재고 확인 중 오류 발생: {str(e)}'
        
        return availability_result
    
    async def validate_order_for_retry(self, order_id: str) -> Dict:
        """재시도 가능 여부 검증"""
        try:
            from app.models.order_core import DropshippingOrder
            
            dropshipping_order = self.db.query(DropshippingOrder).join(Order).filter(
                Order.id == order_id
            ).first()
            
            if not dropshipping_order:
                return {
                    'success': False,
                    'message': '드롭쉬핑 주문 정보를 찾을 수 없습니다'
                }
            
            if not dropshipping_order.can_retry:
                return {
                    'success': False,
                    'message': '재시도 횟수를 초과했거나 수동 처리가 필요합니다'
                }
            
            # 재시도 간격 확인 (최소 5분 간격)
            if dropshipping_order.updated_at:
                minutes_since_last_try = (datetime.utcnow() - dropshipping_order.updated_at).total_seconds() / 60
                if minutes_since_last_try < 5:
                    return {
                        'success': False,
                        'message': f'재시도는 최소 5분 후에 가능합니다 ({minutes_since_last_try:.1f}분 경과)'
                    }
            
            return {
                'success': True,
                'message': '재시도 가능',
                'retry_count': dropshipping_order.retry_count,
                'max_retry_count': dropshipping_order.max_retry_count
            }
            
        except Exception as e:
            logger.error(f"재시도 검증 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'재시도 검증 중 오류 발생: {str(e)}'
            }