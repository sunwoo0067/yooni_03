"""
드롭쉬핑 마진 계산 및 보호 서비스
"""
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.order_core import DropshippingOrder, MarginProtectionRule
from app.models.product import Product
from app.models.wholesaler import Wholesaler

logger = logging.getLogger(__name__)


class MarginCalculator:
    """드롭쉬핑 마진 계산 및 보호"""
    
    def __init__(self, db: Session):
        self.db = db
        self.default_minimum_margin_rate = Decimal('10.0')  # 기본 최소 마진율 10%
        self.safety_margin_buffer = Decimal('2.0')  # 안전 마진 버퍼 2%
    
    async def calculate_margin(
        self, 
        customer_price: Decimal, 
        supplier_price: Decimal,
        shipping_cost: Decimal = Decimal('0'),
        platform_fee_rate: Decimal = Decimal('0')
    ) -> Dict:
        """
        마진 계산
        
        Args:
            customer_price: 고객 판매가
            supplier_price: 공급업체 구매가
            shipping_cost: 배송비
            platform_fee_rate: 플랫폼 수수료율 (%)
            
        Returns:
            Dict: 마진 계산 결과
        """
        try:
            # 플랫폼 수수료 계산
            platform_fee = customer_price * (platform_fee_rate / 100)
            
            # 실제 수익 계산
            net_revenue = customer_price - platform_fee
            total_cost = supplier_price + shipping_cost
            
            # 마진 계산
            margin_amount = net_revenue - total_cost
            margin_rate = (margin_amount / net_revenue * 100) if net_revenue > 0 else Decimal('0')
            
            # 소수점 둘째 자리까지 반올림
            margin_rate = margin_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            margin_amount = margin_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            return {
                'success': True,
                'customer_price': customer_price,
                'supplier_price': supplier_price,
                'shipping_cost': shipping_cost,
                'platform_fee': platform_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'net_revenue': net_revenue.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'total_cost': total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'margin_amount': margin_amount,
                'margin_rate': margin_rate,
                'is_profitable': margin_amount > 0
            }
            
        except Exception as e:
            logger.error(f"마진 계산 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'마진 계산 중 오류 발생: {str(e)}',
                'margin_amount': Decimal('0'),
                'margin_rate': Decimal('0'),
                'is_profitable': False
            }
    
    async def validate_margin(self, dropshipping_order: DropshippingOrder) -> Dict:
        """
        마진 보호 규칙 검증
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            
        Returns:
            Dict: 검증 결과
        """
        try:
            # 적용 가능한 마진 보호 규칙 조회
            protection_rules = await self._get_applicable_protection_rules(dropshipping_order)
            
            # 현재 마진율 계산
            current_margin = await self.calculate_margin(
                dropshipping_order.customer_price,
                dropshipping_order.supplier_price
            )
            
            if not current_margin['success']:
                return current_margin
            
            # 최소 마진율 결정
            minimum_margin_rate = await self._determine_minimum_margin_rate(
                dropshipping_order, protection_rules
            )
            
            # 마진 보호 검증
            current_margin_rate = current_margin['margin_rate']
            required_margin_rate = minimum_margin_rate + self.safety_margin_buffer
            
            validation_result = {
                'success': current_margin_rate >= required_margin_rate,
                'current_margin_rate': current_margin_rate,
                'minimum_margin_rate': minimum_margin_rate,
                'required_margin_rate': required_margin_rate,
                'margin_amount': current_margin['margin_amount'],
                'protection_rules': [rule.name for rule in protection_rules],
                'recommendations': []
            }
            
            if not validation_result['success']:
                shortage = required_margin_rate - current_margin_rate
                validation_result['message'] = f"마진율 부족: {current_margin_rate}% < {required_margin_rate}% (부족: {shortage}%)"
                
                # 개선 방안 제안
                recommendations = await self._generate_margin_recommendations(
                    dropshipping_order, current_margin, shortage
                )
                validation_result['recommendations'] = recommendations
            else:
                validation_result['message'] = "마진 보호 기준을 충족합니다"
            
            # 드롭쉬핑 주문에 마진 정보 업데이트
            await self._update_dropshipping_order_margin(dropshipping_order, current_margin, minimum_margin_rate)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"마진 검증 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'마진 검증 중 오류 발생: {str(e)}'
            }
    
    async def _get_applicable_protection_rules(self, dropshipping_order: DropshippingOrder) -> List[MarginProtectionRule]:
        """적용 가능한 마진 보호 규칙 조회"""
        current_time = datetime.utcnow()
        
        from sqlalchemy import or_
        
        # 기본 쿼리 조건
        query = self.db.query(MarginProtectionRule).filter(
            MarginProtectionRule.is_active == True
        )
        
        # 유효 기간 필터
        query = query.filter(
            or_(
                MarginProtectionRule.valid_from.is_(None),
                MarginProtectionRule.valid_from <= current_time
            ),
            or_(
                MarginProtectionRule.valid_until.is_(None),
                MarginProtectionRule.valid_until >= current_time
            )
        )
        
        # 주문 금액 범위 필터
        order_amount = dropshipping_order.customer_price
        query = query.filter(
            or_(
                MarginProtectionRule.min_order_amount.is_(None),
                MarginProtectionRule.min_order_amount <= order_amount
            ),
            or_(
                MarginProtectionRule.max_order_amount.is_(None),
                MarginProtectionRule.max_order_amount >= order_amount
            )
        )
        
        all_rules = query.all()
        
        # 적용 범위별 필터링
        applicable_rules = []
        for rule in all_rules:
            # 공급업체별 규칙
            if rule.supplier_id and rule.supplier_id == dropshipping_order.supplier_id:
                applicable_rules.append(rule)
                continue
            
            # 상품별 규칙
            if rule.product_id:
                order_items = dropshipping_order.order.order_items
                product_ids = [item.product_id for item in order_items if item.product_id]
                if rule.product_id in product_ids:
                    applicable_rules.append(rule)
                    continue
            
            # 카테고리별 규칙
            if rule.product_category:
                order_items = dropshipping_order.order.order_items
                for item in order_items:
                    if item.product and item.product.category == rule.product_category:
                        applicable_rules.append(rule)
                        break
                continue
            
            # 전역 규칙 (특정 조건이 없는 규칙)
            if not rule.supplier_id and not rule.product_id and not rule.product_category:
                applicable_rules.append(rule)
        
        # 우선순위로 정렬
        applicable_rules.sort(key=lambda x: x.priority, reverse=True)
        
        return applicable_rules
    
    async def _determine_minimum_margin_rate(
        self, 
        dropshipping_order: DropshippingOrder, 
        protection_rules: List[MarginProtectionRule]
    ) -> Decimal:
        """최소 마진율 결정"""
        
        if not protection_rules:
            return self.default_minimum_margin_rate
        
        # 가장 높은 우선순위 규칙의 최소 마진율 사용
        highest_priority_rule = protection_rules[0]
        return highest_priority_rule.minimum_margin_rate
    
    async def _generate_margin_recommendations(
        self, 
        dropshipping_order: DropshippingOrder, 
        current_margin: Dict, 
        shortage: Decimal
    ) -> List[str]:
        """마진 개선 방안 제안"""
        recommendations = []
        
        # 필요한 추가 마진 금액 계산
        needed_amount = (shortage / 100) * current_margin['net_revenue']
        
        # 1. 판매가 인상 제안
        price_increase = needed_amount
        new_customer_price = dropshipping_order.customer_price + price_increase
        price_increase_rate = (price_increase / dropshipping_order.customer_price) * 100
        
        recommendations.append(
            f"판매가 {price_increase_rate:.1f}% 인상 ({dropshipping_order.customer_price} → {new_customer_price})"
        )
        
        # 2. 더 저렴한 공급업체 찾기 제안
        max_acceptable_supplier_price = dropshipping_order.customer_price - needed_amount - current_margin['platform_fee']
        price_reduction_needed = dropshipping_order.supplier_price - max_acceptable_supplier_price
        
        if price_reduction_needed > 0:
            recommendations.append(
                f"공급가 {price_reduction_needed}원 절약 필요 (현재: {dropshipping_order.supplier_price} → 목표: {max_acceptable_supplier_price})"
            )
        
        # 3. 배송비 절약 제안
        if current_margin.get('shipping_cost', 0) > 0:
            recommendations.append("배송비 절약 방안 검토")
        
        # 4. 주문 취소 권고 (마진이 너무 낮은 경우)
        if current_margin['margin_rate'] < 0:
            recommendations.append("손실 방지를 위해 주문 취소 권고")
        
        return recommendations
    
    async def _update_dropshipping_order_margin(
        self, 
        dropshipping_order: DropshippingOrder, 
        margin_info: Dict, 
        minimum_margin_rate: Decimal
    ):
        """드롭쉬핑 주문 마진 정보 업데이트"""
        try:
            dropshipping_order.margin_amount = margin_info['margin_amount']
            dropshipping_order.margin_rate = margin_info['margin_rate']
            dropshipping_order.minimum_margin_rate = minimum_margin_rate
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"마진 정보 업데이트 중 오류: {str(e)}")
            self.db.rollback()
    
    async def analyze_price_change_impact(
        self, 
        dropshipping_order_id: str, 
        new_supplier_price: Decimal
    ) -> Dict:
        """공급가 변동 영향 분석"""
        try:
            dropshipping_order = self.db.query(DropshippingOrder).filter(
                DropshippingOrder.id == dropshipping_order_id
            ).first()
            
            if not dropshipping_order:
                return {
                    'success': False,
                    'message': '드롭쉬핑 주문을 찾을 수 없습니다'
                }
            
            # 현재 마진과 새로운 마진 계산
            current_margin = await self.calculate_margin(
                dropshipping_order.customer_price,
                dropshipping_order.supplier_price
            )
            
            new_margin = await self.calculate_margin(
                dropshipping_order.customer_price,
                new_supplier_price
            )
            
            # 변동 분석
            price_change = new_supplier_price - dropshipping_order.supplier_price
            price_change_rate = (price_change / dropshipping_order.supplier_price) * 100
            margin_change = new_margin['margin_rate'] - current_margin['margin_rate']
            
            # 마진 보호 기준 검증
            protection_rules = await self._get_applicable_protection_rules(dropshipping_order)
            minimum_margin_rate = await self._determine_minimum_margin_rate(dropshipping_order, protection_rules)
            
            analysis_result = {
                'success': True,
                'current_supplier_price': dropshipping_order.supplier_price,
                'new_supplier_price': new_supplier_price,
                'price_change': price_change,
                'price_change_rate': price_change_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'current_margin_rate': current_margin['margin_rate'],
                'new_margin_rate': new_margin['margin_rate'],
                'margin_change': margin_change.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'minimum_margin_rate': minimum_margin_rate,
                'meets_minimum_margin': new_margin['margin_rate'] >= minimum_margin_rate,
                'recommendation': 'accept' if new_margin['margin_rate'] >= minimum_margin_rate else 'reject',
                'actions': []
            }
            
            # 권장 조치 결정
            if not analysis_result['meets_minimum_margin']:
                analysis_result['actions'].append('price_increase_needed')
                analysis_result['actions'].append('find_alternative_supplier')
                
                if new_margin['margin_rate'] < 0:
                    analysis_result['actions'].append('cancel_order')
            
            # 가격 인상률 제한 검증
            max_increase_rate = Decimal('5.0')  # 기본 5% 제한
            if protection_rules:
                max_increase_rate = protection_rules[0].max_price_increase_rate
            
            if price_change_rate > max_increase_rate:
                analysis_result['recommendation'] = 'reject'
                analysis_result['actions'].append('price_increase_limit_exceeded')
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"가격 변동 분석 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'가격 변동 분석 중 오류 발생: {str(e)}'
            }
    
    async def get_margin_analysis_report(self, date_from: datetime, date_to: datetime) -> Dict:
        """마진 분석 리포트 생성"""
        try:
            # 기간 내 드롭쉬핑 주문 조회
            orders = self.db.query(DropshippingOrder).filter(
                DropshippingOrder.created_at >= date_from,
                DropshippingOrder.created_at <= date_to
            ).all()
            
            if not orders:
                return {
                    'success': True,
                    'message': '해당 기간에 주문이 없습니다',
                    'total_orders': 0
                }
            
            # 통계 계산
            total_orders = len(orders)
            total_revenue = sum(order.customer_price for order in orders)
            total_cost = sum(order.supplier_price for order in orders)
            total_margin = sum(order.margin_amount for order in orders)
            
            avg_margin_rate = sum(order.margin_rate for order in orders) / total_orders
            
            # 마진율 분포
            margin_ranges = {
                'negative': 0,     # 0% 미만
                'low': 0,         # 0-10%
                'medium': 0,      # 10-20%
                'high': 0,        # 20-30%
                'very_high': 0    # 30% 이상
            }
            
            for order in orders:
                rate = order.margin_rate
                if rate < 0:
                    margin_ranges['negative'] += 1
                elif rate < 10:
                    margin_ranges['low'] += 1
                elif rate < 20:
                    margin_ranges['medium'] += 1
                elif rate < 30:
                    margin_ranges['high'] += 1
                else:
                    margin_ranges['very_high'] += 1
            
            # 위험 주문 (낮은 마진율)
            risky_orders = [
                {
                    'order_id': str(order.order_id),
                    'margin_rate': float(order.margin_rate),
                    'margin_amount': float(order.margin_amount),
                    'customer_price': float(order.customer_price),
                    'supplier_price': float(order.supplier_price)
                }
                for order in orders if order.margin_rate < 10
            ]
            
            return {
                'success': True,
                'period': {
                    'from': date_from.isoformat(),
                    'to': date_to.isoformat()
                },
                'summary': {
                    'total_orders': total_orders,
                    'total_revenue': float(total_revenue),
                    'total_cost': float(total_cost),
                    'total_margin': float(total_margin),
                    'avg_margin_rate': float(avg_margin_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                },
                'margin_distribution': margin_ranges,
                'risky_orders': risky_orders[:10]  # 상위 10개만
            }
            
        except Exception as e:
            logger.error(f"마진 분석 리포트 생성 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'리포트 생성 중 오류 발생: {str(e)}'
            }