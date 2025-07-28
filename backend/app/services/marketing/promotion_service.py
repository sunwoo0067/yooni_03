"""
프로모션 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import string
import random
import uuid

from app.models.marketing import PromotionCode, MarketingSegment
from app.models.crm import Customer
from app.models.order_core import Order
from app.core.exceptions import BusinessException


class PromotionService:
    """프로모션 및 할인 코드 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_promotion_code(self, promotion_data: Dict[str, Any]) -> PromotionCode:
        """프로모션 코드 생성"""
        try:
            # 코드 생성 또는 검증
            if 'code' in promotion_data:
                # 사용자 정의 코드 검증
                if self._is_code_exists(promotion_data['code']):
                    raise BusinessException("이미 존재하는 프로모션 코드입니다")
                code = promotion_data['code']
            else:
                # 자동 코드 생성
                code = await self._generate_unique_code(
                    promotion_data.get('code_prefix', ''),
                    promotion_data.get('code_length', 8)
                )
            
            promotion = PromotionCode(
                code=code,
                code_type=promotion_data['code_type'],
                discount_value=promotion_data['discount_value'],
                minimum_purchase=promotion_data.get('minimum_purchase', 0),
                maximum_discount=promotion_data.get('maximum_discount'),
                usage_limit=promotion_data.get('usage_limit'),
                usage_per_customer=promotion_data.get('usage_per_customer', 1),
                valid_from=promotion_data.get('valid_from', datetime.utcnow()),
                valid_until=promotion_data.get('valid_until'),
                is_active=promotion_data.get('is_active', True),
                is_public=promotion_data.get('is_public', True)
            )
            
            # 캠페인 연결
            if 'campaign_id' in promotion_data:
                promotion.campaign_id = promotion_data['campaign_id']
            
            # 적용 범위 설정
            if 'applicable_products' in promotion_data:
                promotion.applicable_products = promotion_data['applicable_products']
            if 'applicable_categories' in promotion_data:
                promotion.applicable_categories = promotion_data['applicable_categories']
            if 'excluded_products' in promotion_data:
                promotion.excluded_products = promotion_data['excluded_products']
            
            # 타겟팅 설정
            if 'target_segment_id' in promotion_data:
                promotion.target_segment_id = promotion_data['target_segment_id']
            if 'target_customers' in promotion_data:
                promotion.target_customers = promotion_data['target_customers']
            
            self.db.add(promotion)
            self.db.commit()
            self.db.refresh(promotion)
            
            return promotion
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"프로모션 코드 생성 실패: {str(e)}")
    
    async def create_bulk_promotion_codes(self, bulk_data: Dict[str, Any]) -> List[PromotionCode]:
        """대량 프로모션 코드 생성"""
        try:
            count = bulk_data.get('count', 100)
            base_data = bulk_data.get('base_data', {})
            prefix = bulk_data.get('prefix', '')
            
            codes = []
            for i in range(count):
                code = await self._generate_unique_code(prefix, 10)
                
                promotion_data = base_data.copy()
                promotion_data['code'] = code
                
                # 개별 코드별 설정 (옵션)
                if 'individual_settings' in bulk_data:
                    individual = bulk_data['individual_settings'].get(i, {})
                    promotion_data.update(individual)
                
                promotion = await self.create_promotion_code(promotion_data)
                codes.append(promotion)
            
            return codes
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"대량 코드 생성 실패: {str(e)}")
    
    async def validate_promotion_code(self, code: str, customer_id: int, 
                                    order_data: Dict[str, Any]) -> Dict[str, Any]:
        """프로모션 코드 유효성 검증"""
        try:
            promotion = self.db.query(PromotionCode).filter(
                PromotionCode.code == code.upper()
            ).first()
            
            if not promotion:
                return {
                    'valid': False,
                    'error': '유효하지 않은 프로모션 코드입니다'
                }
            
            # 활성 상태 확인
            if not promotion.is_active:
                return {
                    'valid': False,
                    'error': '비활성화된 프로모션 코드입니다'
                }
            
            # 유효 기간 확인
            now = datetime.utcnow()
            if promotion.valid_from and now < promotion.valid_from:
                return {
                    'valid': False,
                    'error': '아직 사용할 수 없는 프로모션 코드입니다'
                }
            
            if promotion.valid_until and now > promotion.valid_until:
                return {
                    'valid': False,
                    'error': '만료된 프로모션 코드입니다'
                }
            
            # 사용 한도 확인
            if promotion.usage_limit and promotion.current_usage >= promotion.usage_limit:
                return {
                    'valid': False,
                    'error': '사용 한도를 초과한 프로모션 코드입니다'
                }
            
            # 고객별 사용 한도 확인
            customer_usage = self._get_customer_usage(promotion.id, customer_id)
            if customer_usage >= promotion.usage_per_customer:
                return {
                    'valid': False,
                    'error': '이미 사용한 프로모션 코드입니다'
                }
            
            # 최소 구매 금액 확인
            order_total = order_data.get('total_amount', 0)
            if order_total < promotion.minimum_purchase:
                return {
                    'valid': False,
                    'error': f'최소 구매 금액 {promotion.minimum_purchase:,}원 이상 구매시 사용 가능합니다'
                }
            
            # 타겟 고객 확인
            if not self._check_target_eligibility(promotion, customer_id):
                return {
                    'valid': False,
                    'error': '이 프로모션 코드를 사용할 수 없는 고객입니다'
                }
            
            # 적용 가능 상품 확인
            if not self._check_product_eligibility(promotion, order_data.get('products', [])):
                return {
                    'valid': False,
                    'error': '프로모션 코드가 적용되지 않는 상품이 포함되어 있습니다'
                }
            
            # 할인 금액 계산
            discount_amount = self._calculate_discount(promotion, order_total)
            
            return {
                'valid': True,
                'promotion_id': promotion.id,
                'code_type': promotion.code_type,
                'discount_value': promotion.discount_value,
                'discount_amount': discount_amount,
                'final_amount': order_total - discount_amount
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'프로모션 코드 검증 실패: {str(e)}'
            }
    
    async def apply_promotion_code(self, code: str, customer_id: int, 
                                 order_id: int) -> Dict[str, Any]:
        """프로모션 코드 적용"""
        try:
            promotion = self.db.query(PromotionCode).filter(
                PromotionCode.code == code.upper()
            ).first()
            
            if not promotion:
                raise BusinessException("프로모션 코드를 찾을 수 없습니다")
            
            # 사용 카운트 증가
            promotion.current_usage += 1
            promotion.redemption_count += 1
            
            # 주문에서 할인 금액 조회 및 수익 추가
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if order:
                discount_amount = order.discount_amount or 0
                promotion.revenue_generated += (order.total_price - discount_amount)
            
            self.db.commit()
            
            return {
                'success': True,
                'promotion_id': promotion.id,
                'message': '프로모션 코드가 적용되었습니다'
            }
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"프로모션 코드 적용 실패: {str(e)}")
    
    async def deactivate_promotion_code(self, promotion_id: int) -> PromotionCode:
        """프로모션 코드 비활성화"""
        try:
            promotion = self.db.query(PromotionCode).filter(
                PromotionCode.id == promotion_id
            ).first()
            
            if not promotion:
                raise BusinessException("프로모션 코드를 찾을 수 없습니다")
            
            promotion.is_active = False
            promotion.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(promotion)
            
            return promotion
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"프로모션 코드 비활성화 실패: {str(e)}")
    
    async def extend_promotion_validity(self, promotion_id: int, 
                                      new_end_date: datetime) -> PromotionCode:
        """프로모션 유효기간 연장"""
        try:
            promotion = self.db.query(PromotionCode).filter(
                PromotionCode.id == promotion_id
            ).first()
            
            if not promotion:
                raise BusinessException("프로모션 코드를 찾을 수 없습니다")
            
            if promotion.valid_until and new_end_date <= promotion.valid_until:
                raise BusinessException("새로운 종료일은 현재 종료일보다 늦어야 합니다")
            
            promotion.valid_until = new_end_date
            promotion.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(promotion)
            
            return promotion
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"유효기간 연장 실패: {str(e)}")
    
    async def get_promotion_analytics(self, promotion_id: int) -> Dict[str, Any]:
        """프로모션 분석 데이터"""
        try:
            promotion = self.db.query(PromotionCode).filter(
                PromotionCode.id == promotion_id
            ).first()
            
            if not promotion:
                raise BusinessException("프로모션 코드를 찾을 수 없습니다")
            
            # 사용 통계
            usage_stats = {
                'total_usage': promotion.redemption_count,
                'unique_customers': self._get_unique_customer_count(promotion_id),
                'usage_rate': (promotion.current_usage / promotion.usage_limit * 100) 
                            if promotion.usage_limit else 0,
                'remaining_uses': (promotion.usage_limit - promotion.current_usage) 
                                if promotion.usage_limit else 'unlimited'
            }
            
            # 수익 통계
            revenue_stats = {
                'total_revenue': promotion.revenue_generated,
                'average_order_value': (promotion.revenue_generated / promotion.redemption_count) 
                                     if promotion.redemption_count > 0 else 0,
                'roi': self._calculate_promotion_roi(promotion)
            }
            
            # 시간대별 사용 패턴
            usage_pattern = self._analyze_usage_pattern(promotion_id)
            
            # 고객 세그먼트별 사용
            segment_usage = self._analyze_segment_usage(promotion_id)
            
            return {
                'promotion': {
                    'id': promotion.id,
                    'code': promotion.code,
                    'type': promotion.code_type,
                    'discount_value': promotion.discount_value,
                    'valid_from': promotion.valid_from.isoformat() if promotion.valid_from else None,
                    'valid_until': promotion.valid_until.isoformat() if promotion.valid_until else None,
                    'is_active': promotion.is_active
                },
                'usage_stats': usage_stats,
                'revenue_stats': revenue_stats,
                'usage_pattern': usage_pattern,
                'segment_usage': segment_usage,
                'recommendations': self._generate_promotion_recommendations(
                    promotion, usage_stats, revenue_stats
                )
            }
            
        except Exception as e:
            raise BusinessException(f"프로모션 분석 실패: {str(e)}")
    
    async def create_dynamic_promotion(self, trigger_data: Dict[str, Any]) -> PromotionCode:
        """동적 프로모션 생성 (이벤트 기반)"""
        try:
            # 트리거 타입별 프로모션 생성
            trigger_type = trigger_data.get('trigger_type')
            
            if trigger_type == 'abandoned_cart':
                return await self._create_abandoned_cart_promotion(trigger_data)
            elif trigger_type == 'birthday':
                return await self._create_birthday_promotion(trigger_data)
            elif trigger_type == 'win_back':
                return await self._create_win_back_promotion(trigger_data)
            elif trigger_type == 'first_purchase':
                return await self._create_first_purchase_promotion(trigger_data)
            else:
                raise BusinessException(f"지원하지 않는 트리거 타입: {trigger_type}")
                
        except Exception as e:
            raise BusinessException(f"동적 프로모션 생성 실패: {str(e)}")
    
    async def _generate_unique_code(self, prefix: str = '', length: int = 8) -> str:
        """고유한 프로모션 코드 생성"""
        characters = string.ascii_uppercase + string.digits
        
        while True:
            # 랜덤 코드 생성
            random_part = ''.join(random.choices(characters, k=length))
            code = f"{prefix}{random_part}".upper()
            
            # 중복 확인
            if not self._is_code_exists(code):
                return code
    
    def _is_code_exists(self, code: str) -> bool:
        """코드 존재 여부 확인"""
        return self.db.query(PromotionCode).filter(
            PromotionCode.code == code.upper()
        ).first() is not None
    
    def _get_customer_usage(self, promotion_id: int, customer_id: int) -> int:
        """고객의 프로모션 사용 횟수"""
        # 실제 구현에서는 주문 테이블과 조인하여 계산
        return 0
    
    def _check_target_eligibility(self, promotion: PromotionCode, customer_id: int) -> bool:
        """타겟 고객 자격 확인"""
        # 공개 프로모션인 경우 모두 사용 가능
        if promotion.is_public and not promotion.target_segment_id and not promotion.target_customers:
            return True
        
        # 특정 고객 타겟팅
        if promotion.target_customers:
            if customer_id in promotion.target_customers:
                return True
        
        # 세그먼트 타겟팅
        if promotion.target_segment_id:
            # 고객이 해당 세그먼트에 속하는지 확인
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if customer:
                # 세그먼트 확인 로직
                return True  # 실제 구현 필요
        
        return False
    
    def _check_product_eligibility(self, promotion: PromotionCode, 
                                 products: List[Dict[str, Any]]) -> bool:
        """상품 적용 가능 여부 확인"""
        # 적용 제한이 없는 경우
        if not promotion.applicable_products and not promotion.applicable_categories:
            # 제외 상품만 확인
            if promotion.excluded_products:
                for product in products:
                    if product.get('id') in promotion.excluded_products:
                        return False
            return True
        
        # 적용 가능 상품/카테고리 확인
        for product in products:
            product_id = product.get('id')
            category = product.get('category')
            
            # 적용 가능 상품 확인
            if promotion.applicable_products:
                if product_id not in promotion.applicable_products:
                    return False
            
            # 적용 가능 카테고리 확인
            if promotion.applicable_categories:
                if category not in promotion.applicable_categories:
                    return False
            
            # 제외 상품 확인
            if promotion.excluded_products:
                if product_id in promotion.excluded_products:
                    return False
        
        return True
    
    def _calculate_discount(self, promotion: PromotionCode, order_total: float) -> float:
        """할인 금액 계산"""
        if promotion.code_type == 'percentage':
            discount = order_total * (promotion.discount_value / 100)
        elif promotion.code_type == 'fixed':
            discount = promotion.discount_value
        elif promotion.code_type == 'free_shipping':
            discount = 0  # 배송비 할인은 별도 처리
        elif promotion.code_type == 'bogo':
            discount = 0  # BOGO는 상품 레벨에서 처리
        else:
            discount = 0
        
        # 최대 할인 금액 제한
        if promotion.maximum_discount:
            discount = min(discount, promotion.maximum_discount)
        
        # 주문 금액을 초과하지 않도록
        discount = min(discount, order_total)
        
        return discount
    
    def _get_unique_customer_count(self, promotion_id: int) -> int:
        """프로모션을 사용한 고유 고객 수"""
        # 실제 구현에서는 주문 테이블과 조인
        return 0
    
    def _calculate_promotion_roi(self, promotion: PromotionCode) -> float:
        """프로모션 ROI 계산"""
        # 할인으로 인한 비용
        if promotion.code_type == 'percentage':
            total_discount = promotion.revenue_generated * (promotion.discount_value / 100)
        else:
            total_discount = promotion.discount_value * promotion.redemption_count
        
        # ROI = (수익 - 비용) / 비용 * 100
        if total_discount > 0:
            roi = ((promotion.revenue_generated - total_discount) / total_discount) * 100
        else:
            roi = 0
        
        return round(roi, 2)
    
    def _analyze_usage_pattern(self, promotion_id: int) -> Dict[str, Any]:
        """프로모션 사용 패턴 분석"""
        # 실제 구현에서는 시간대별, 요일별 사용 패턴 분석
        return {
            'peak_hours': [14, 15, 20, 21],  # 오후 2-3시, 저녁 8-9시
            'peak_days': ['Friday', 'Saturday', 'Sunday'],
            'average_days_to_use': 3.5
        }
    
    def _analyze_segment_usage(self, promotion_id: int) -> List[Dict[str, Any]]:
        """세그먼트별 사용 분석"""
        # 실제 구현에서는 고객 세그먼트별 사용 통계
        return [
            {
                'segment': 'VIP',
                'usage_count': 120,
                'usage_rate': 45.5,
                'average_order_value': 85000
            },
            {
                'segment': 'Regular',
                'usage_count': 200,
                'usage_rate': 35.2,
                'average_order_value': 45000
            }
        ]
    
    def _generate_promotion_recommendations(self, promotion: PromotionCode,
                                          usage_stats: Dict[str, Any],
                                          revenue_stats: Dict[str, Any]) -> List[str]:
        """프로모션 개선 권장사항"""
        recommendations = []
        
        # 사용률이 낮은 경우
        if usage_stats['usage_rate'] < 30 and promotion.is_active:
            recommendations.append("사용률이 낮습니다. 프로모션 홍보를 강화하거나 할인율을 높이는 것을 고려하세요.")
        
        # ROI가 낮은 경우
        if revenue_stats['roi'] < 100:
            recommendations.append("ROI가 낮습니다. 최소 구매 금액을 높이거나 할인율을 조정하세요.")
        
        # 만료 임박
        if promotion.valid_until:
            days_left = (promotion.valid_until - datetime.utcnow()).days
            if days_left <= 7 and promotion.is_active:
                recommendations.append(f"프로모션이 {days_left}일 후 만료됩니다. 연장 여부를 결정하세요.")
        
        # 사용 한도 임박
        if promotion.usage_limit:
            remaining_rate = (1 - usage_stats['usage_rate'] / 100) * 100
            if remaining_rate < 20:
                recommendations.append("사용 한도가 거의 소진되었습니다. 한도 증가를 고려하세요.")
        
        return recommendations
    
    async def _create_abandoned_cart_promotion(self, trigger_data: Dict[str, Any]) -> PromotionCode:
        """장바구니 이탈 프로모션 생성"""
        customer_id = trigger_data.get('customer_id')
        cart_value = trigger_data.get('cart_value', 0)
        
        # 장바구니 금액에 따른 할인율 결정
        if cart_value >= 100000:
            discount_value = 15
        elif cart_value >= 50000:
            discount_value = 10
        else:
            discount_value = 5
        
        promotion_data = {
            'code_prefix': 'CART',
            'code_type': 'percentage',
            'discount_value': discount_value,
            'minimum_purchase': cart_value * 0.8,  # 장바구니 금액의 80%
            'usage_limit': 1,
            'usage_per_customer': 1,
            'valid_until': datetime.utcnow() + timedelta(days=3),  # 3일간 유효
            'target_customers': [customer_id],
            'is_public': False
        }
        
        return await self.create_promotion_code(promotion_data)
    
    async def _create_birthday_promotion(self, trigger_data: Dict[str, Any]) -> PromotionCode:
        """생일 프로모션 생성"""
        customer_id = trigger_data.get('customer_id')
        
        promotion_data = {
            'code_prefix': 'BDAY',
            'code_type': 'percentage',
            'discount_value': 20,  # 20% 할인
            'minimum_purchase': 30000,
            'usage_limit': 1,
            'usage_per_customer': 1,
            'valid_until': datetime.utcnow() + timedelta(days=30),  # 30일간 유효
            'target_customers': [customer_id],
            'is_public': False
        }
        
        return await self.create_promotion_code(promotion_data)
    
    async def _create_win_back_promotion(self, trigger_data: Dict[str, Any]) -> PromotionCode:
        """재활성화 프로모션 생성"""
        customer_id = trigger_data.get('customer_id')
        days_inactive = trigger_data.get('days_inactive', 90)
        
        # 비활성 기간에 따른 할인 결정
        if days_inactive >= 180:
            discount_value = 30
        elif days_inactive >= 120:
            discount_value = 25
        else:
            discount_value = 20
        
        promotion_data = {
            'code_prefix': 'BACK',
            'code_type': 'percentage',
            'discount_value': discount_value,
            'minimum_purchase': 20000,
            'usage_limit': 1,
            'usage_per_customer': 1,
            'valid_until': datetime.utcnow() + timedelta(days=14),  # 14일간 유효
            'target_customers': [customer_id],
            'is_public': False
        }
        
        return await self.create_promotion_code(promotion_data)
    
    async def _create_first_purchase_promotion(self, trigger_data: Dict[str, Any]) -> PromotionCode:
        """첫 구매 프로모션 생성"""
        customer_id = trigger_data.get('customer_id')
        
        promotion_data = {
            'code_prefix': 'FIRST',
            'code_type': 'percentage',
            'discount_value': 15,  # 15% 할인
            'minimum_purchase': 25000,
            'usage_limit': 1,
            'usage_per_customer': 1,
            'valid_until': datetime.utcnow() + timedelta(days=7),  # 7일간 유효
            'target_customers': [customer_id],
            'is_public': False
        }
        
        return await self.create_promotion_code(promotion_data)