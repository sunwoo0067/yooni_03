"""
드롭쉬핑 배송 예상 시간 계산 서비스
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.order import DropshippingOrder, SupplierOrderStatus
from app.models.wholesaler import Wholesaler
from app.models.product import Product

logger = logging.getLogger(__name__)


class DeliveryEstimator:
    """드롭쉬핑 배송 예상 시간 계산 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_delivery_days = {
            'seoul': 1,      # 서울
            'metro': 2,      # 수도권
            'major': 2,      # 광역시
            'normal': 3,     # 일반 지역
            'remote': 4      # 외곽 지역
        }
        
        # 공급업체별 평균 처리 시간 (일)
        self.supplier_processing_days = {
            'domeggook': 1,
            'ownerclan': 2,
            'zentrade': 1
        }
    
    async def estimate_delivery_time(
        self, 
        dropshipping_order: DropshippingOrder,
        shipping_address: Optional[Dict] = None
    ) -> Dict:
        """
        배송 예상 시간 계산
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            shipping_address: 배송지 정보 (선택)
            
        Returns:
            Dict: 배송 예상 시간 정보
        """
        try:
            order = dropshipping_order.order
            
            # 배송지 정보 추출
            if not shipping_address:
                shipping_address = {
                    'city': order.shipping_city,
                    'state': order.shipping_state,
                    'postal_code': order.shipping_postal_code,
                    'address1': order.shipping_address1
                }
            
            # 1. 공급업체 처리 시간 계산
            supplier_processing_time = await self._calculate_supplier_processing_time(dropshipping_order)
            
            # 2. 배송 지역별 시간 계산
            delivery_time = await self._calculate_delivery_time_by_region(shipping_address)
            
            # 3. 상품별 추가 시간 계산
            product_processing_time = await self._calculate_product_processing_time(dropshipping_order)
            
            # 4. 요일/휴일 조정
            schedule_adjustment = await self._calculate_schedule_adjustment()
            
            # 5. 총 예상 시간 계산
            total_days = (
                supplier_processing_time['days'] + 
                delivery_time['days'] + 
                product_processing_time['days'] + 
                schedule_adjustment['days']
            )
            
            # 최소/최대값 설정
            min_days = max(total_days - 1, 1)
            max_days = total_days + 2
            
            # 예상 날짜 계산
            estimated_ship_date = datetime.utcnow() + timedelta(days=supplier_processing_time['days'])
            estimated_delivery_date = datetime.utcnow() + timedelta(days=total_days)
            
            return {
                'success': True,
                'estimation': {
                    'total_days': total_days,
                    'min_days': min_days,
                    'max_days': max_days,
                    'estimated_ship_date': estimated_ship_date.isoformat(),
                    'estimated_delivery_date': estimated_delivery_date.isoformat()
                },
                'breakdown': {
                    'supplier_processing': supplier_processing_time,
                    'delivery_transit': delivery_time,
                    'product_processing': product_processing_time,
                    'schedule_adjustment': schedule_adjustment
                },
                'region_info': delivery_time.get('region_info', {}),
                'confidence_level': await self._calculate_confidence_level(dropshipping_order),
                'factors': await self._get_estimation_factors(dropshipping_order, shipping_address)
            }
            
        except Exception as e:
            logger.error(f"배송 시간 예상 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 시간 예상 중 오류 발생: {str(e)}'
            }
    
    async def _calculate_supplier_processing_time(self, dropshipping_order: DropshippingOrder) -> Dict:
        """공급업체 처리 시간 계산"""
        try:
            supplier = dropshipping_order.supplier
            if not supplier:
                return {'days': 2, 'description': '공급업체 정보 없음 (기본값)'}
            
            supplier_type = supplier.wholesaler_type.lower() if supplier.wholesaler_type else 'unknown'
            base_days = self.supplier_processing_days.get(supplier_type, 2)
            
            # 과거 데이터 기반 조정
            historical_avg = await self._get_supplier_historical_processing_time(supplier.id)
            if historical_avg:
                adjusted_days = int((base_days + historical_avg) / 2)
            else:
                adjusted_days = base_days
            
            # 재고 상태에 따른 조정
            stock_adjustment = 0
            if dropshipping_order.status == SupplierOrderStatus.OUT_OF_STOCK:
                stock_adjustment = 2  # 품절시 2일 추가
            
            total_days = adjusted_days + stock_adjustment
            
            return {
                'days': total_days,
                'base_days': base_days,
                'historical_avg': historical_avg,
                'stock_adjustment': stock_adjustment,
                'description': f'{supplier.name} 처리 시간',
                'supplier': supplier.name
            }
            
        except Exception as e:
            logger.error(f"공급업체 처리 시간 계산 중 오류: {str(e)}")
            return {'days': 2, 'description': '계산 오류 (기본값)'}
    
    async def _calculate_delivery_time_by_region(self, shipping_address: Dict) -> Dict:
        """배송 지역별 시간 계산"""
        try:
            city = shipping_address.get('city', '').lower()
            state = shipping_address.get('state', '').lower()
            postal_code = shipping_address.get('postal_code', '')
            
            # 지역 분류
            region_type = 'normal'  # 기본값
            region_name = city
            
            # 서울
            if '서울' in city or 'seoul' in city:
                region_type = 'seoul'
                region_name = '서울특별시'
            
            # 수도권 (경기, 인천)
            elif any(area in city for area in ['경기', '인천', 'gyeonggi', 'incheon']):
                region_type = 'metro'
                region_name = '수도권'
            
            # 광역시
            elif any(metro in city for metro in ['부산', '대구', '대전', '광주', '울산', 'busan', 'daegu', 'daejeon', 'gwangju', 'ulsan']):
                region_type = 'major'
                region_name = f'{city} 광역시'
            
            # 제주, 강원 외곽
            elif any(remote in city for remote in ['제주', '강원', 'jeju', 'gangwon']) or any(remote in state for remote in ['제주', '강원']):
                region_type = 'remote'
                region_name = '외곽 지역'
            
            base_days = self.base_delivery_days.get(region_type, 3)
            
            # 우편번호 기반 세부 조정
            postal_adjustment = 0
            if postal_code:
                # 우편번호가 63으로 시작하면 제주
                if postal_code.startswith('63'):
                    postal_adjustment = 1
                    region_type = 'remote'
                    region_name = '제주특별자치도'
            
            total_days = base_days + postal_adjustment
            
            return {
                'days': total_days,
                'base_days': base_days,
                'postal_adjustment': postal_adjustment,
                'region_type': region_type,
                'region_name': region_name,
                'description': f'{region_name} 배송',
                'region_info': {
                    'type': region_type,
                    'name': region_name,
                    'city': city,
                    'postal_code': postal_code
                }
            }
            
        except Exception as e:
            logger.error(f"지역별 배송 시간 계산 중 오류: {str(e)}")
            return {
                'days': 3,
                'description': '계산 오류 (기본값)',
                'region_info': {}
            }
    
    async def _calculate_product_processing_time(self, dropshipping_order: DropshippingOrder) -> Dict:
        """상품별 추가 처리 시간 계산"""
        try:
            order_items = dropshipping_order.order.order_items
            max_processing_days = 0
            processing_details = []
            
            for item in order_items:
                item_days = 0
                item_factors = []
                
                # 상품 속성에 따른 추가 시간
                if item.product_attributes:
                    # 커스텀 옵션이 있는 경우
                    if 'custom' in str(item.product_attributes).lower():
                        item_days += 1
                        item_factors.append('커스텀 옵션')
                    
                    # 대량 주문인 경우
                    if item.quantity > 10:
                        item_days += 1
                        item_factors.append('대량 주문')
                
                # 상품 카테고리별 추가 시간
                if item.product:
                    category = item.product.category or ''
                    if any(special in category.lower() for special in ['전자', 'electronic', '가전']):
                        item_days += 1
                        item_factors.append('전자제품 검수')
                
                processing_details.append({
                    'sku': item.sku,
                    'product_name': item.product_name,
                    'additional_days': item_days,
                    'factors': item_factors
                })
                
                max_processing_days = max(max_processing_days, item_days)
            
            return {
                'days': max_processing_days,
                'description': '상품별 추가 처리 시간',
                'details': processing_details,
                'max_item_processing': max_processing_days
            }
            
        except Exception as e:
            logger.error(f"상품별 처리 시간 계산 중 오류: {str(e)}")
            return {
                'days': 0,
                'description': '계산 오류',
                'details': []
            }
    
    async def _calculate_schedule_adjustment(self) -> Dict:
        """요일/휴일 조정 계산"""
        try:
            now = datetime.utcnow()
            adjustment_days = 0
            adjustment_factors = []
            
            # 주말 조정
            if now.weekday() >= 5:  # 토요일(5), 일요일(6)
                adjustment_days += 1
                adjustment_factors.append('주말 주문')
            
            # 늦은 시간 주문 (오후 6시 이후)
            if now.hour >= 18:
                adjustment_days += 1
                adjustment_factors.append('늦은 시간 주문')
            
            # 연휴 체크 (간단한 구현)
            # 실제로는 공휴일 API를 사용하는 것이 좋음
            if now.month == 1 and now.day <= 3:  # 신정 연휴
                adjustment_days += 2
                adjustment_factors.append('신정 연휴')
            elif now.month == 2 and 10 <= now.day <= 12:  # 설날 추정
                adjustment_days += 3
                adjustment_factors.append('설날 연휴')
            elif now.month == 10 and 3 <= now.day <= 9:  # 추석 추정
                adjustment_days += 3
                adjustment_factors.append('추석 연휴')
            
            return {
                'days': adjustment_days,
                'description': '일정 조정',
                'factors': adjustment_factors,
                'current_datetime': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"일정 조정 계산 중 오류: {str(e)}")
            return {
                'days': 0,
                'description': '계산 오류',
                'factors': []
            }
    
    async def _get_supplier_historical_processing_time(self, supplier_id: str) -> Optional[float]:
        """공급업체 과거 처리 시간 평균 조회"""
        try:
            # 최근 30일 내 완료된 주문들의 처리 시간 평균 계산
            from sqlalchemy import extract
            
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            result = (
                self.db.query(
                    func.avg(
                        extract('epoch', DropshippingOrder.supplier_confirmed_at - DropshippingOrder.supplier_order_date) / 86400
                    ).label('avg_processing_days')
                )
                .filter(
                    and_(
                        DropshippingOrder.supplier_id == supplier_id,
                        DropshippingOrder.supplier_order_date >= thirty_days_ago,
                        DropshippingOrder.supplier_confirmed_at.isnot(None),
                        DropshippingOrder.status.in_([
                            SupplierOrderStatus.CONFIRMED,
                            SupplierOrderStatus.SHIPPED,
                            SupplierOrderStatus.DELIVERED
                        ])
                    )
                )
                .scalar()
            )
            
            return float(result) if result else None
            
        except Exception as e:
            logger.error(f"공급업체 과거 처리 시간 조회 중 오류: {str(e)}")
            return None
    
    async def _calculate_confidence_level(self, dropshipping_order: DropshippingOrder) -> Dict:
        """예상 시간 신뢰도 계산"""
        try:
            confidence_score = 100  # 기본 100%
            confidence_factors = []
            
            # 공급업체 신뢰도
            supplier = dropshipping_order.supplier
            if supplier:
                # 최근 성공률 조회
                success_rate = await self._get_supplier_success_rate(supplier.id)
                if success_rate is not None:
                    if success_rate < 0.8:  # 80% 미만
                        confidence_score -= 20
                        confidence_factors.append(f'공급업체 성공률 낮음 ({success_rate:.1%})')
                    elif success_rate > 0.95:  # 95% 이상
                        confidence_factors.append(f'공급업체 높은 신뢰도 ({success_rate:.1%})')
            
            # 재고 상태
            if dropshipping_order.status == SupplierOrderStatus.OUT_OF_STOCK:
                confidence_score -= 30
                confidence_factors.append('품절 상태')
            
            # 과거 데이터 충분성
            historical_orders = await self._get_historical_orders_count(dropshipping_order.supplier_id)
            if historical_orders < 10:
                confidence_score -= 15
                confidence_factors.append('과거 데이터 부족')
            
            # 특수 상품 여부
            if any('custom' in str(item.product_attributes or '').lower() for item in dropshipping_order.order.order_items):
                confidence_score -= 10
                confidence_factors.append('커스텀 상품 포함')
            
            confidence_level = max(confidence_score, 20)  # 최소 20%
            
            # 신뢰도 등급
            if confidence_level >= 90:
                grade = 'A'
                description = '매우 높음'
            elif confidence_level >= 75:
                grade = 'B'
                description = '높음'
            elif confidence_level >= 60:
                grade = 'C'
                description = '보통'
            else:
                grade = 'D'
                description = '낮음'
            
            return {
                'score': confidence_level,
                'grade': grade,
                'description': description,
                'factors': confidence_factors,
                'recommendation': '예상 시간의 정확도가 높습니다.' if confidence_level >= 80 else 
                                '예상 시간에 여유를 두고 확인하세요.'
            }
            
        except Exception as e:
            logger.error(f"신뢰도 계산 중 오류: {str(e)}")
            return {
                'score': 50,
                'grade': 'C',
                'description': '보통',
                'factors': ['계산 오류'],
                'recommendation': '예상 시간을 참고용으로만 사용하세요.'
            }
    
    async def _get_supplier_success_rate(self, supplier_id: str) -> Optional[float]:
        """공급업체 성공률 조회"""
        try:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            total_orders = (
                self.db.query(DropshippingOrder)
                .filter(
                    and_(
                        DropshippingOrder.supplier_id == supplier_id,
                        DropshippingOrder.created_at >= thirty_days_ago
                    )
                )
                .count()
            )
            
            if total_orders == 0:
                return None
            
            successful_orders = (
                self.db.query(DropshippingOrder)
                .filter(
                    and_(
                        DropshippingOrder.supplier_id == supplier_id,
                        DropshippingOrder.created_at >= thirty_days_ago,
                        DropshippingOrder.status.in_([
                            SupplierOrderStatus.DELIVERED,
                            SupplierOrderStatus.SHIPPED,
                            SupplierOrderStatus.CONFIRMED
                        ])
                    )
                )
                .count()
            )
            
            return successful_orders / total_orders
            
        except Exception as e:
            logger.error(f"공급업체 성공률 조회 중 오류: {str(e)}")
            return None
    
    async def _get_historical_orders_count(self, supplier_id: str) -> int:
        """과거 주문 건수 조회"""
        try:
            return (
                self.db.query(DropshippingOrder)
                .filter(DropshippingOrder.supplier_id == supplier_id)
                .count()
            )
        except Exception as e:
            logger.error(f"과거 주문 건수 조회 중 오류: {str(e)}")
            return 0
    
    async def _get_estimation_factors(self, dropshipping_order: DropshippingOrder, shipping_address: Dict) -> List[str]:
        """예상 시간에 영향을 미치는 요인들"""
        factors = []
        
        try:
            # 공급업체 요인
            if dropshipping_order.supplier:
                factors.append(f'공급업체: {dropshipping_order.supplier.name}')
            
            # 배송지 요인
            city = shipping_address.get('city', '')
            if city:
                factors.append(f'배송지: {city}')
            
            # 상품 요인
            order_items = dropshipping_order.order.order_items
            if len(order_items) > 1:
                factors.append(f'상품 종류: {len(order_items)}개')
            
            total_quantity = sum(item.quantity for item in order_items)
            if total_quantity > 5:
                factors.append(f'총 수량: {total_quantity}개')
            
            # 시간 요인
            now = datetime.utcnow()
            if now.weekday() >= 5:
                factors.append('주말 주문')
            
            if now.hour >= 18:
                factors.append('늦은 시간 주문')
            
            # 특수 상황
            if dropshipping_order.status == SupplierOrderStatus.OUT_OF_STOCK:
                factors.append('품절 상태')
            
        except Exception as e:
            logger.error(f"예상 요인 조회 중 오류: {str(e)}")
            factors.append('일반적인 배송 조건')
        
        return factors
    
    async def get_delivery_performance_report(self, days: int = 30) -> Dict:
        """배송 성과 리포트 생성"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 완료된 주문들 조회
            completed_orders = (
                self.db.query(DropshippingOrder)
                .filter(
                    and_(
                        DropshippingOrder.status == SupplierOrderStatus.DELIVERED,
                        DropshippingOrder.created_at >= start_date,
                        DropshippingOrder.supplier_shipped_at.isnot(None)
                    )
                )
                .all()
            )
            
            if not completed_orders:
                return {
                    'success': True,
                    'message': '해당 기간에 완료된 주문이 없습니다',
                    'period': f'{start_date.date()} ~ {end_date.date()}'
                }
            
            # 실제 배송 시간 계산
            actual_delivery_times = []
            for order in completed_orders:
                if order.supplier_shipped_at and order.created_at:
                    delivery_time = (order.supplier_shipped_at - order.created_at).days
                    actual_delivery_times.append(delivery_time)
            
            # 통계 계산
            avg_delivery_time = sum(actual_delivery_times) / len(actual_delivery_times)
            min_delivery_time = min(actual_delivery_times)
            max_delivery_time = max(actual_delivery_times)
            
            # 공급업체별 성과
            supplier_performance = {}
            for order in completed_orders:
                if order.supplier:
                    supplier_name = order.supplier.name
                    if supplier_name not in supplier_performance:
                        supplier_performance[supplier_name] = []
                    
                    if order.supplier_shipped_at and order.created_at:
                        delivery_time = (order.supplier_shipped_at - order.created_at).days
                        supplier_performance[supplier_name].append(delivery_time)
            
            supplier_stats = {}
            for supplier, times in supplier_performance.items():
                supplier_stats[supplier] = {
                    'order_count': len(times),
                    'avg_delivery_time': sum(times) / len(times),
                    'min_delivery_time': min(times),
                    'max_delivery_time': max(times)
                }
            
            return {
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'overall_performance': {
                    'total_completed_orders': len(completed_orders),
                    'avg_delivery_time_days': round(avg_delivery_time, 1),
                    'min_delivery_time_days': min_delivery_time,
                    'max_delivery_time_days': max_delivery_time,
                    'on_time_delivery_rate': self._calculate_on_time_rate(actual_delivery_times)
                },
                'supplier_performance': supplier_stats,
                'delivery_time_distribution': self._create_delivery_time_distribution(actual_delivery_times)
            }
            
        except Exception as e:
            logger.error(f"배송 성과 리포트 생성 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 성과 리포트 생성 중 오류 발생: {str(e)}'
            }
    
    def _calculate_on_time_rate(self, delivery_times: List[int]) -> float:
        """정시 배송률 계산 (5일 이내)"""
        if not delivery_times:
            return 0.0
        
        on_time_count = sum(1 for time in delivery_times if time <= 5)
        return (on_time_count / len(delivery_times)) * 100
    
    def _create_delivery_time_distribution(self, delivery_times: List[int]) -> Dict:
        """배송 시간 분포 생성"""
        distribution = {
            '1_day': 0,
            '2_days': 0,
            '3_days': 0,
            '4_5_days': 0,
            '6_7_days': 0,
            'over_1_week': 0
        }
        
        for time in delivery_times:
            if time <= 1:
                distribution['1_day'] += 1
            elif time <= 2:
                distribution['2_days'] += 1
            elif time <= 3:
                distribution['3_days'] += 1
            elif time <= 5:
                distribution['4_5_days'] += 1
            elif time <= 7:
                distribution['6_7_days'] += 1
            else:
                distribution['over_1_week'] += 1
        
        return distribution