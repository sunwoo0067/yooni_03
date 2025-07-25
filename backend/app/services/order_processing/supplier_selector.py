"""
드롭쉬핑 최적 공급업체 선택 서비스
"""
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.order import Order, DropshippingOrder, OrderItem
from app.models.product import Product
from app.models.wholesaler import Wholesaler
from app.services.order_processing.margin_calculator import MarginCalculator

logger = logging.getLogger(__name__)


class SupplierSelectionCriteria:
    """공급업체 선택 기준"""
    def __init__(self):
        self.margin_weight = 0.4      # 마진 가중치 40%
        self.reliability_weight = 0.3  # 신뢰도 가중치 30%
        self.delivery_weight = 0.2     # 배송 가중치 20%
        self.price_weight = 0.1        # 가격 가중치 10%


class SupplierSelector:
    """드롭쉬핑 최적 공급업체 선택"""
    
    def __init__(self, db: Session):
        self.db = db
        self.margin_calculator = MarginCalculator(db)
        self.selection_criteria = SupplierSelectionCriteria()
    
    async def select_best_supplier(self, order: Order, dropshipping_order: DropshippingOrder) -> Dict:
        """
        최적 공급업체 선택
        
        Args:
            order: 고객 주문
            dropshipping_order: 드롭쉬핑 주문
            
        Returns:
            Dict: 선택 결과
        """
        try:
            logger.info(f"최적 공급업체 선택 시작: 주문 {order.order_number}")
            
            # 1. 가능한 공급업체 목록 조회
            available_suppliers = await self._get_available_suppliers(order)
            
            if not available_suppliers:
                return {
                    'success': False,
                    'message': '사용 가능한 공급업체가 없습니다',
                    'suppliers_checked': 0
                }
            
            logger.info(f"검토할 공급업체 수: {len(available_suppliers)}")
            
            # 2. 각 공급업체별 상품 정보 및 재고 확인
            supplier_evaluations = []
            for supplier in available_suppliers:
                evaluation = await self._evaluate_supplier(order, supplier)
                if evaluation['available']:
                    supplier_evaluations.append(evaluation)
            
            if not supplier_evaluations:
                return {
                    'success': False,
                    'message': '재고가 있는 공급업체가 없습니다',
                    'suppliers_checked': len(available_suppliers)
                }
            
            # 3. 마진 계산 및 수익성 검증
            profitable_suppliers = []
            for evaluation in supplier_evaluations:
                margin_info = await self._calculate_supplier_margin(
                    dropshipping_order.customer_price, 
                    evaluation
                )
                evaluation['margin_info'] = margin_info
                
                if margin_info['is_profitable'] and margin_info['margin_rate'] >= dropshipping_order.minimum_margin_rate:
                    profitable_suppliers.append(evaluation)
            
            if not profitable_suppliers:
                return {
                    'success': False,
                    'message': '최소 마진율을 충족하는 공급업체가 없습니다',
                    'suppliers_checked': len(supplier_evaluations),
                    'margin_issues': [
                        {
                            'supplier_name': eval['supplier']['name'],
                            'margin_rate': eval['margin_info']['margin_rate'],
                            'minimum_required': dropshipping_order.minimum_margin_rate
                        }
                        for eval in supplier_evaluations
                    ]
                }
            
            # 4. 종합 점수 계산 및 최적 공급업체 선택
            best_supplier = await self._select_optimal_supplier(profitable_suppliers)
            
            # 5. 드롭쉬핑 주문 업데이트
            await self._update_dropshipping_order(dropshipping_order, best_supplier)
            
            return {
                'success': True,
                'message': f"최적 공급업체 선택 완료: {best_supplier['supplier']['name']}",
                'selected_supplier': {
                    'id': best_supplier['supplier']['id'],
                    'name': best_supplier['supplier']['name'],
                    'total_score': best_supplier['total_score'],
                    'margin_rate': best_supplier['margin_info']['margin_rate'],
                    'estimated_delivery_days': best_supplier['delivery_info']['estimated_days'],
                    'reliability_score': best_supplier['reliability_score']
                },
                'suppliers_evaluated': len(supplier_evaluations),
                'alternatives': [
                    {
                        'name': eval['supplier']['name'],
                        'score': eval['total_score'],
                        'margin_rate': eval['margin_info']['margin_rate']
                    }
                    for eval in profitable_suppliers[1:3]  # 상위 2개 대안만
                ]
            }
            
        except Exception as e:
            logger.error(f"공급업체 선택 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'공급업체 선택 중 오류 발생: {str(e)}'
            }
    
    async def _get_available_suppliers(self, order: Order) -> List[Wholesaler]:
        """사용 가능한 공급업체 목록 조회"""
        # 활성 상태인 공급업체만 조회
        suppliers = self.db.query(Wholesaler).filter(
            Wholesaler.is_active == True,
            Wholesaler.api_status == 'active'  # API 상태가 활성인 것만
        ).all()
        
        # 주문 상품과 매칭되는 공급업체 필터링
        available_suppliers = []
        for supplier in suppliers:
            if await self._supplier_has_products(supplier, order):
                available_suppliers.append(supplier)
        
        return available_suppliers
    
    async def _supplier_has_products(self, supplier: Wholesaler, order: Order) -> bool:
        """공급업체가 주문 상품을 보유하는지 확인"""
        # 간단한 구현: 모든 공급업체가 모든 상품을 보유한다고 가정
        # 실제로는 공급업체별 상품 매핑 테이블을 확인해야 함
        return True
    
    async def _evaluate_supplier(self, order: Order, supplier: Wholesaler) -> Dict:
        """공급업체 평가"""
        evaluation = {
            'supplier': {
                'id': str(supplier.id),
                'name': supplier.name,
                'type': supplier.wholesaler_type
            },
            'available': False,
            'total_score': 0,
            'products': [],
            'total_cost': Decimal('0'),
            'delivery_info': {},
            'reliability_score': 0
        }
        
        try:
            # 1. 상품별 재고 및 가격 확인
            all_available = True
            total_cost = Decimal('0')
            
            for item in order.order_items:
                product_info = await self._get_product_info_from_supplier(supplier, item)
                evaluation['products'].append(product_info)
                
                if not product_info['available'] or product_info['stock'] < item.quantity:
                    all_available = False
                    break
                
                total_cost += product_info['unit_price'] * item.quantity
            
            evaluation['available'] = all_available
            evaluation['total_cost'] = total_cost
            
            if all_available:
                # 2. 배송 정보 평가
                evaluation['delivery_info'] = await self._evaluate_delivery_capability(supplier, order)
                
                # 3. 신뢰도 점수 계산
                evaluation['reliability_score'] = await self._calculate_reliability_score(supplier)
                
                # 4. 종합 점수 계산
                evaluation['total_score'] = await self._calculate_total_score(evaluation)
            
        except Exception as e:
            logger.error(f"공급업체 평가 중 오류 ({supplier.name}): {str(e)}")
            evaluation['available'] = False
            evaluation['error'] = str(e)
        
        return evaluation
    
    async def _get_product_info_from_supplier(self, supplier: Wholesaler, order_item: OrderItem) -> Dict:
        """공급업체로부터 상품 정보 조회"""
        # 실제로는 각 공급업체 API를 호출해야 함
        # 여기서는 가상의 데이터를 생성
        
        base_price = order_item.unit_price * Decimal('0.7')  # 판매가의 70%를 공급가로 가정
        
        # 공급업체별 가격 변동 시뮬레이션
        price_variations = {
            'domeggook': Decimal('0.95'),    # 5% 할인
            'ownerclan': Decimal('1.0'),     # 기준가
            'zentrade': Decimal('0.98')      # 2% 할인
        }
        
        supplier_type = supplier.wholesaler_type.lower()
        price_multiplier = price_variations.get(supplier_type, Decimal('1.0'))
        
        return {
            'sku': order_item.sku,
            'product_name': order_item.product_name,
            'unit_price': (base_price * price_multiplier).quantize(Decimal('0.01')),
            'available': True,
            'stock': 100,  # 가상의 재고량
            'lead_time_days': 1 if supplier_type == 'domeggook' else 2,
            'shipping_cost': Decimal('2500') if supplier_type == 'zentrade' else Decimal('3000')
        }
    
    async def _evaluate_delivery_capability(self, supplier: Wholesaler, order: Order) -> Dict:
        """배송 능력 평가"""
        # 공급업체별 배송 정보 (실제로는 API에서 조회)
        delivery_info = {
            'domeggook': {
                'estimated_days': 2,
                'shipping_cost': Decimal('3000'),
                'express_available': True,
                'tracking_available': True
            },
            'ownerclan': {
                'estimated_days': 3,
                'shipping_cost': Decimal('3000'),
                'express_available': False,
                'tracking_available': True
            },
            'zentrade': {
                'estimated_days': 2,
                'shipping_cost': Decimal('2500'),
                'express_available': True,
                'tracking_available': True
            }
        }
        
        supplier_type = supplier.wholesaler_type.lower()
        return delivery_info.get(supplier_type, {
            'estimated_days': 3,
            'shipping_cost': Decimal('3000'),
            'express_available': False,
            'tracking_available': True
        })
    
    async def _calculate_reliability_score(self, supplier: Wholesaler) -> float:
        """공급업체 신뢰도 점수 계산"""
        # 실제로는 과거 주문 데이터를 분석해야 함
        # 여기서는 가상의 점수를 생성
        
        reliability_scores = {
            'domeggook': 0.92,  # 92점
            'ownerclan': 0.85,  # 85점
            'zentrade': 0.88    # 88점
        }
        
        supplier_type = supplier.wholesaler_type.lower()
        return reliability_scores.get(supplier_type, 0.80)
    
    async def _calculate_supplier_margin(self, customer_price: Decimal, evaluation: Dict) -> Dict:
        """공급업체별 마진 계산"""
        supplier_cost = evaluation['total_cost']
        delivery_info = evaluation.get('delivery_info', {})
        shipping_cost = delivery_info.get('shipping_cost', Decimal('0'))
        
        return await self.margin_calculator.calculate_margin(
            customer_price=customer_price,
            supplier_price=supplier_cost,
            shipping_cost=shipping_cost,
            platform_fee_rate=Decimal('3.0')  # 플랫폼 수수료 3%
        )
    
    async def _calculate_total_score(self, evaluation: Dict) -> float:
        """종합 점수 계산"""
        criteria = self.selection_criteria
        
        # 마진 점수 (0-100)
        margin_rate = float(evaluation.get('margin_info', {}).get('margin_rate', 0))
        margin_score = min(margin_rate * 3, 100)  # 마진율 * 3 (최대 100점)
        
        # 신뢰도 점수 (0-100)
        reliability_score = evaluation['reliability_score'] * 100
        
        # 배송 점수 (0-100)
        delivery_days = evaluation.get('delivery_info', {}).get('estimated_days', 5)
        delivery_score = max(100 - (delivery_days - 1) * 20, 20)  # 빠를수록 높은 점수
        
        # 가격 점수 (0-100) - 낮은 비용일수록 높은 점수
        cost_ratio = float(evaluation['total_cost']) / 100000  # 임의의 기준값
        price_score = max(100 - cost_ratio * 50, 20)
        
        # 가중 평균 계산
        total_score = (
            margin_score * criteria.margin_weight +
            reliability_score * criteria.reliability_weight +
            delivery_score * criteria.delivery_weight +
            price_score * criteria.price_weight
        )
        
        return round(total_score, 2)
    
    async def _select_optimal_supplier(self, evaluations: List[Dict]) -> Dict:
        """최적 공급업체 선택"""
        # 종합 점수 기준으로 정렬
        evaluations.sort(key=lambda x: x['total_score'], reverse=True)
        
        best_supplier = evaluations[0]
        logger.info(f"선택된 공급업체: {best_supplier['supplier']['name']} (점수: {best_supplier['total_score']})")
        
        return best_supplier
    
    async def _update_dropshipping_order(self, dropshipping_order: DropshippingOrder, supplier_eval: Dict):
        """드롭쉬핑 주문에 선택된 공급업체 정보 업데이트"""
        try:
            # 공급업체 ID 설정
            supplier_id = supplier_eval['supplier']['id']
            dropshipping_order.supplier_id = supplier_id
            
            # 마진 정보 업데이트
            margin_info = supplier_eval['margin_info']
            dropshipping_order.supplier_price = margin_info['supplier_price']
            dropshipping_order.margin_amount = margin_info['margin_amount']
            dropshipping_order.margin_rate = margin_info['margin_rate']
            
            # 배송 정보 업데이트
            delivery_info = supplier_eval['delivery_info']
            if delivery_info.get('estimated_days'):
                estimated_delivery = datetime.utcnow() + timedelta(days=delivery_info['estimated_days'])
                dropshipping_order.estimated_delivery_date = estimated_delivery
            
            self.db.commit()
            
            logger.info(f"드롭쉬핑 주문 업데이트 완료: 공급업체 {supplier_eval['supplier']['name']}")
            
        except Exception as e:
            logger.error(f"드롭쉬핑 주문 업데이트 중 오류: {str(e)}")
            self.db.rollback()
            raise
    
    async def compare_suppliers(self, order_id: str) -> Dict:
        """공급업체 비교 분석"""
        try:
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {
                    'success': False,
                    'message': '주문을 찾을 수 없습니다'
                }
            
            dropshipping_order = self.db.query(DropshippingOrder).filter(
                DropshippingOrder.order_id == order.id
            ).first()
            
            if not dropshipping_order:
                return {
                    'success': False,
                    'message': '드롭쉬핑 주문을 찾을 수 없습니다'
                }
            
            # 모든 가능한 공급업체 평가
            available_suppliers = await self._get_available_suppliers(order)
            comparisons = []
            
            for supplier in available_suppliers:
                evaluation = await self._evaluate_supplier(order, supplier)
                if evaluation['available']:
                    margin_info = await self._calculate_supplier_margin(
                        dropshipping_order.customer_price, 
                        evaluation
                    )
                    evaluation['margin_info'] = margin_info
                    evaluation['total_score'] = await self._calculate_total_score(evaluation)
                    comparisons.append(evaluation)
            
            # 점수순으로 정렬
            comparisons.sort(key=lambda x: x['total_score'], reverse=True)
            
            return {
                'success': True,
                'order_id': order_id,
                'customer_price': float(dropshipping_order.customer_price),
                'supplier_comparisons': [
                    {
                        'supplier_name': comp['supplier']['name'],
                        'supplier_id': comp['supplier']['id'],
                        'total_score': comp['total_score'],
                        'margin_rate': float(comp['margin_info']['margin_rate']),
                        'margin_amount': float(comp['margin_info']['margin_amount']),
                        'total_cost': float(comp['total_cost']),
                        'delivery_days': comp['delivery_info'].get('estimated_days', 0),
                        'reliability_score': comp['reliability_score']
                    }
                    for comp in comparisons
                ],
                'recommendation': {
                    'supplier_name': comparisons[0]['supplier']['name'],
                    'reason': f"최고 점수 ({comparisons[0]['total_score']}점)"
                } if comparisons else None
            }
            
        except Exception as e:
            logger.error(f"공급업체 비교 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'공급업체 비교 중 오류 발생: {str(e)}'
            }
    
    async def update_selection_criteria(self, criteria: Dict) -> Dict:
        """선택 기준 업데이트"""
        try:
            if 'margin_weight' in criteria:
                self.selection_criteria.margin_weight = criteria['margin_weight']
            if 'reliability_weight' in criteria:
                self.selection_criteria.reliability_weight = criteria['reliability_weight']
            if 'delivery_weight' in criteria:
                self.selection_criteria.delivery_weight = criteria['delivery_weight']
            if 'price_weight' in criteria:
                self.selection_criteria.price_weight = criteria['price_weight']
            
            # 가중치 합이 1.0이 되도록 정규화
            total_weight = (
                self.selection_criteria.margin_weight +
                self.selection_criteria.reliability_weight +
                self.selection_criteria.delivery_weight +
                self.selection_criteria.price_weight
            )
            
            if total_weight != 1.0:
                self.selection_criteria.margin_weight /= total_weight
                self.selection_criteria.reliability_weight /= total_weight
                self.selection_criteria.delivery_weight /= total_weight
                self.selection_criteria.price_weight /= total_weight
            
            return {
                'success': True,
                'message': '선택 기준이 업데이트되었습니다',
                'criteria': {
                    'margin_weight': self.selection_criteria.margin_weight,
                    'reliability_weight': self.selection_criteria.reliability_weight,
                    'delivery_weight': self.selection_criteria.delivery_weight,
                    'price_weight': self.selection_criteria.price_weight
                }
            }
            
        except Exception as e:
            logger.error(f"선택 기준 업데이트 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'선택 기준 업데이트 중 오류 발생: {str(e)}'
            }