"""
가격 최적화 엔진
경쟁사 가격 분석, 수요 예측 기반 가격 조정, 마진 최적화
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import numpy as np
from decimal import Decimal

from app.models.product import Product
from app.models.order_core import Order, OrderItem
from app.models.price_history import PriceHistory
from app.core.exceptions import AppException


class PriceOptimizer:
    """가격 최적화 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def optimize_product_price(
        self, 
        product_id: int,
        target_margin: Optional[float] = None,
        competitor_prices: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        상품 가격 최적화
        
        Args:
            product_id: 상품 ID
            target_margin: 목표 마진율 (0.0 ~ 1.0)
            competitor_prices: 경쟁사 가격 리스트
            
        Returns:
            최적화된 가격 정보
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise AppException("상품을 찾을 수 없습니다", status_code=404)
            
        # 현재 가격 정보
        current_price = float(product.price)
        cost = float(getattr(product, 'cost', current_price * 0.6))  # 원가가 없으면 가격의 60%로 가정
        
        # 1. 수요 탄력성 분석
        elasticity = self._calculate_price_elasticity(product_id)
        
        # 2. 경쟁사 가격 분석
        competitive_price = self._analyze_competitor_prices(
            current_price, competitor_prices
        )
        
        # 3. 판매 속도 분석
        sales_velocity = self._calculate_sales_velocity(product_id)
        
        # 4. 재고 상황 고려
        inventory_factor = self._calculate_inventory_factor(product)
        
        # 5. 최적 가격 계산
        optimal_price = self._calculate_optimal_price(
            current_price=current_price,
            cost=cost,
            elasticity=elasticity,
            competitive_price=competitive_price,
            sales_velocity=sales_velocity,
            inventory_factor=inventory_factor,
            target_margin=target_margin
        )
        
        # 6. 가격 조정 제한 (급격한 변화 방지)
        max_change_rate = 0.2  # 최대 20% 변경
        if abs(optimal_price - current_price) / current_price > max_change_rate:
            if optimal_price > current_price:
                optimal_price = current_price * (1 + max_change_rate)
            else:
                optimal_price = current_price * (1 - max_change_rate)
                
        # 결과 구성
        margin = (optimal_price - cost) / optimal_price
        revenue_impact = self._estimate_revenue_impact(
            product_id, current_price, optimal_price, elasticity
        )
        
        return {
            'product_id': product_id,
            'product_name': product.name,
            'current_price': current_price,
            'optimal_price': round(optimal_price, 2),
            'price_change': round(optimal_price - current_price, 2),
            'price_change_percent': round((optimal_price - current_price) / current_price * 100, 2),
            'expected_margin': round(margin * 100, 2),
            'revenue_impact_estimate': revenue_impact,
            'factors': {
                'demand_elasticity': round(elasticity, 2),
                'sales_velocity': sales_velocity,
                'inventory_pressure': inventory_factor,
                'competitive_position': 'above' if optimal_price > competitive_price else 'below'
            },
            'recommendations': self._generate_pricing_recommendations(
                product, current_price, optimal_price, margin
            )
        }
        
    def _calculate_price_elasticity(self, product_id: int, days: int = 90) -> float:
        """가격 탄력성 계산"""
        # 최근 가격 변경 이력과 판매량 변화 분석
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 가격 이력 조회
        price_changes = self.db.query(PriceHistory).filter(
            PriceHistory.product_id == product_id,
            PriceHistory.created_at >= since_date
        ).order_by(PriceHistory.created_at).all()
        
        if len(price_changes) < 2:
            # 가격 변경 이력이 부족한 경우 기본값 사용
            return -1.2  # 일반적인 탄력성 값
            
        # 기간별 판매량 계산
        elasticities = []
        for i in range(1, len(price_changes)):
            prev_price = float(price_changes[i-1].price)
            curr_price = float(price_changes[i].price)
            
            # 가격 변경 전후 판매량
            prev_sales = self._get_sales_volume(
                product_id, 
                price_changes[i-1].created_at,
                price_changes[i].created_at
            )
            
            if i < len(price_changes) - 1:
                next_date = price_changes[i+1].created_at
            else:
                next_date = datetime.utcnow()
                
            curr_sales = self._get_sales_volume(
                product_id,
                price_changes[i].created_at,
                next_date
            )
            
            # 탄력성 계산
            if prev_sales > 0 and prev_price != curr_price:
                price_change_rate = (curr_price - prev_price) / prev_price
                quantity_change_rate = (curr_sales - prev_sales) / prev_sales
                
                if price_change_rate != 0:
                    elasticity = quantity_change_rate / price_change_rate
                    elasticities.append(elasticity)
                    
        # 평균 탄력성 반환
        if elasticities:
            return np.mean(elasticities)
        else:
            return -1.2
            
    def _get_sales_volume(
        self, 
        product_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> int:
        """특정 기간 판매량 조회"""
        result = self.db.query(
            func.sum(OrderItem.quantity)
        ).join(Order).filter(
            OrderItem.product_id == product_id,
            Order.created_at >= start_date,
            Order.created_at < end_date,
            Order.status == 'completed'
        ).scalar()
        
        return result or 0
        
    def _analyze_competitor_prices(
        self, 
        current_price: float,
        competitor_prices: Optional[List[float]] = None
    ) -> float:
        """경쟁사 가격 분석"""
        if not competitor_prices:
            # 경쟁사 가격 정보가 없으면 현재 가격 반환
            return current_price
            
        # 이상치 제거 (상위/하위 10%)
        sorted_prices = sorted(competitor_prices)
        trim_count = max(1, len(sorted_prices) // 10)
        trimmed_prices = sorted_prices[trim_count:-trim_count] if len(sorted_prices) > 2 else sorted_prices
        
        # 평균 경쟁사 가격
        avg_competitor_price = np.mean(trimmed_prices)
        
        # 경쟁력 있는 가격 제안 (평균보다 약간 낮게)
        competitive_price = avg_competitor_price * 0.95
        
        return competitive_price
        
    def _calculate_sales_velocity(self, product_id: int, days: int = 30) -> Dict[str, Any]:
        """판매 속도 계산"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 일별 판매량
        daily_sales = self.db.query(
            func.date(Order.created_at).label('date'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(OrderItem).filter(
            OrderItem.product_id == product_id,
            Order.created_at >= since_date,
            Order.status == 'completed'
        ).group_by(func.date(Order.created_at)).all()
        
        if not daily_sales:
            return {
                'average_daily': 0,
                'trend': 'stable',
                'velocity_score': 0
            }
            
        quantities = [s.quantity for s in daily_sales]
        avg_daily = np.mean(quantities)
        
        # 추세 분석 (최근 7일 vs 이전)
        recent_days = 7
        if len(quantities) >= recent_days * 2:
            recent_avg = np.mean(quantities[-recent_days:])
            previous_avg = np.mean(quantities[-recent_days*2:-recent_days])
            
            if recent_avg > previous_avg * 1.2:
                trend = 'increasing'
            elif recent_avg < previous_avg * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
            
        # 속도 점수 (0-1)
        velocity_score = min(1.0, avg_daily / 10)  # 일 10개 판매를 기준으로
        
        return {
            'average_daily': avg_daily,
            'trend': trend,
            'velocity_score': velocity_score
        }
        
    def _calculate_inventory_factor(self, product: Product) -> float:
        """재고 상황에 따른 가격 조정 계수"""
        stock = product.stock
        
        # 재고 회전율 계산
        monthly_sales = self._get_sales_volume(
            product.id,
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        
        if monthly_sales == 0:
            months_of_inventory = float('inf')
        else:
            months_of_inventory = stock / monthly_sales
            
        # 재고 압박 계수 계산
        if months_of_inventory > 6:
            # 재고 과다 - 가격 인하 압력
            return 0.8
        elif months_of_inventory > 3:
            # 적정 재고
            return 1.0
        elif months_of_inventory > 1:
            # 재고 부족 임박
            return 1.1
        else:
            # 재고 부족 - 가격 인상 가능
            return 1.2
            
    def _calculate_optimal_price(
        self,
        current_price: float,
        cost: float,
        elasticity: float,
        competitive_price: float,
        sales_velocity: Dict[str, Any],
        inventory_factor: float,
        target_margin: Optional[float] = None
    ) -> float:
        """최적 가격 계산"""
        # 기본 최적 가격 (수요 탄력성 기반)
        # 가격 = 원가 * (1 + 1/|탄력성|)
        if elasticity != 0:
            markup_factor = 1 + (1 / abs(elasticity))
        else:
            markup_factor = 1.5
            
        elasticity_based_price = cost * markup_factor
        
        # 목표 마진 기반 가격
        if target_margin:
            margin_based_price = cost / (1 - target_margin)
        else:
            margin_based_price = elasticity_based_price
            
        # 경쟁사 가격 고려
        competitive_factor = 0.3  # 경쟁사 가격의 영향도
        
        # 판매 속도 고려
        velocity_adjustment = 1.0
        if sales_velocity['trend'] == 'increasing':
            velocity_adjustment = 1.05  # 수요 증가시 가격 상향
        elif sales_velocity['trend'] == 'decreasing':
            velocity_adjustment = 0.95  # 수요 감소시 가격 하향
            
        # 최종 가격 계산 (가중 평균)
        optimal_price = (
            elasticity_based_price * 0.3 +
            margin_based_price * 0.3 +
            competitive_price * competitive_factor +
            current_price * 0.1  # 현재 가격 안정성
        ) * velocity_adjustment * inventory_factor
        
        # 최소 마진 보장
        min_margin = 0.1  # 최소 10% 마진
        min_price = cost / (1 - min_margin)
        
        return max(optimal_price, min_price)
        
    def _estimate_revenue_impact(
        self,
        product_id: int,
        current_price: float,
        new_price: float,
        elasticity: float
    ) -> Dict[str, Any]:
        """가격 변경의 매출 영향 추정"""
        # 현재 판매량
        current_volume = self._get_sales_volume(
            product_id,
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        
        # 가격 변경률
        price_change_rate = (new_price - current_price) / current_price
        
        # 예상 판매량 변화
        quantity_change_rate = price_change_rate * elasticity
        expected_volume = current_volume * (1 + quantity_change_rate)
        
        # 매출 변화
        current_revenue = current_price * current_volume
        expected_revenue = new_price * expected_volume
        revenue_change = expected_revenue - current_revenue
        
        return {
            'current_monthly_revenue': round(current_revenue, 2),
            'expected_monthly_revenue': round(expected_revenue, 2),
            'revenue_change': round(revenue_change, 2),
            'revenue_change_percent': round(revenue_change / current_revenue * 100, 2) if current_revenue > 0 else 0,
            'volume_change_percent': round(quantity_change_rate * 100, 2)
        }
        
    def _generate_pricing_recommendations(
        self,
        product: Product,
        current_price: float,
        optimal_price: float,
        margin: float
    ) -> List[str]:
        """가격 책정 권장사항 생성"""
        recommendations = []
        
        price_diff_percent = (optimal_price - current_price) / current_price * 100
        
        if abs(price_diff_percent) < 5:
            recommendations.append("현재 가격이 최적 수준에 근접합니다.")
        elif price_diff_percent > 0:
            recommendations.append(f"가격을 {price_diff_percent:.1f}% 인상하여 수익성을 개선할 수 있습니다.")
            if price_diff_percent > 10:
                recommendations.append("단계적 가격 인상을 고려하세요.")
        else:
            recommendations.append(f"가격을 {abs(price_diff_percent):.1f}% 인하하여 판매량을 늘릴 수 있습니다.")
            
        if margin < 0.2:
            recommendations.append("마진율이 낮습니다. 원가 절감 방안을 검토하세요.")
        elif margin > 0.5:
            recommendations.append("높은 마진율을 유지하고 있습니다. 프리미엄 포지셔닝을 강화하세요.")
            
        if product.stock > 100:
            recommendations.append("재고가 많습니다. 프로모션을 통한 재고 소진을 고려하세요.")
            
        return recommendations
        
    def bulk_optimize_prices(
        self,
        category: Optional[str] = None,
        min_margin: float = 0.2
    ) -> List[Dict[str, Any]]:
        """카테고리별 일괄 가격 최적화"""
        # 대상 상품 조회
        query = self.db.query(Product).filter(
            Product.is_active == True,
            Product.stock > 0
        )
        
        if category:
            query = query.filter(Product.category == category)
            
        products = query.all()
        
        results = []
        for product in products:
            try:
                optimization = self.optimize_product_price(
                    product.id,
                    target_margin=min_margin
                )
                results.append(optimization)
            except Exception as e:
                results.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'error': str(e)
                })
                
        # 수익 영향 순으로 정렬
        results.sort(
            key=lambda x: x.get('revenue_impact_estimate', {}).get('revenue_change', 0),
            reverse=True
        )
        
        return results
        
    def get_dynamic_pricing_rules(self, product_id: int) -> Dict[str, Any]:
        """동적 가격 책정 규칙 생성"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise AppException("상품을 찾을 수 없습니다", status_code=404)
            
        # 시간대별 수요 분석
        hourly_demand = self._analyze_hourly_demand(product_id)
        
        # 요일별 수요 분석
        daily_demand = self._analyze_daily_demand(product_id)
        
        # 계절성 분석
        seasonal_factor = self._analyze_seasonality(product_id)
        
        # 동적 가격 규칙 생성
        rules = {
            'product_id': product_id,
            'base_price': float(product.price),
            'time_based_rules': self._generate_time_based_rules(hourly_demand),
            'day_based_rules': self._generate_day_based_rules(daily_demand),
            'seasonal_adjustment': seasonal_factor,
            'inventory_based_rules': self._generate_inventory_based_rules(product),
            'recommended_update_frequency': 'daily'
        }
        
        return rules
        
    def _analyze_hourly_demand(self, product_id: int) -> Dict[int, float]:
        """시간대별 수요 분석"""
        # 최근 30일 시간대별 판매 데이터
        hourly_sales = self.db.query(
            func.extract('hour', Order.created_at).label('hour'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(OrderItem).filter(
            OrderItem.product_id == product_id,
            Order.created_at >= datetime.utcnow() - timedelta(days=30),
            Order.status == 'completed'
        ).group_by('hour').all()
        
        # 시간대별 수요 지수 계산
        total_sales = sum(s.quantity for s in hourly_sales)
        avg_hourly = total_sales / 24 if total_sales > 0 else 1
        
        demand_index = {}
        for sale in hourly_sales:
            demand_index[int(sale.hour)] = sale.quantity / avg_hourly
            
        # 빈 시간대 채우기
        for hour in range(24):
            if hour not in demand_index:
                demand_index[hour] = 0.5  # 데이터가 없는 시간은 낮은 수요로 가정
                
        return demand_index
        
    def _analyze_daily_demand(self, product_id: int) -> Dict[int, float]:
        """요일별 수요 분석"""
        # 최근 12주 요일별 판매 데이터
        daily_sales = self.db.query(
            func.extract('dow', Order.created_at).label('weekday'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(OrderItem).filter(
            OrderItem.product_id == product_id,
            Order.created_at >= datetime.utcnow() - timedelta(weeks=12),
            Order.status == 'completed'
        ).group_by('weekday').all()
        
        total_sales = sum(s.quantity for s in daily_sales)
        avg_daily = total_sales / 7 if total_sales > 0 else 1
        
        demand_index = {}
        for sale in daily_sales:
            demand_index[int(sale.weekday)] = sale.quantity / avg_daily
            
        # 빈 요일 채우기
        for day in range(7):
            if day not in demand_index:
                demand_index[day] = 1.0
                
        return demand_index
        
    def _analyze_seasonality(self, product_id: int) -> Dict[str, float]:
        """계절성 분석"""
        # 간단한 계절성 분석 (실제로는 더 복잡한 시계열 분석 필요)
        return {
            'spring': 1.0,
            'summer': 1.1,
            'fall': 1.0,
            'winter': 0.9
        }
        
    def _generate_time_based_rules(self, hourly_demand: Dict[int, float]) -> List[Dict[str, Any]]:
        """시간대별 가격 규칙 생성"""
        rules = []
        
        for hour, demand_index in hourly_demand.items():
            if demand_index > 1.5:
                # 고수요 시간대
                adjustment = min(1.1, 1 + (demand_index - 1) * 0.05)
                rules.append({
                    'hour': hour,
                    'adjustment': adjustment,
                    'reason': '고수요 시간대'
                })
            elif demand_index < 0.7:
                # 저수요 시간대
                adjustment = max(0.9, 1 - (1 - demand_index) * 0.1)
                rules.append({
                    'hour': hour,
                    'adjustment': adjustment,
                    'reason': '저수요 시간대'
                })
                
        return rules
        
    def _generate_day_based_rules(self, daily_demand: Dict[int, float]) -> List[Dict[str, Any]]:
        """요일별 가격 규칙 생성"""
        day_names = ['월', '화', '수', '목', '금', '토', '일']
        rules = []
        
        for day, demand_index in daily_demand.items():
            if demand_index > 1.2:
                adjustment = min(1.05, 1 + (demand_index - 1) * 0.025)
                rules.append({
                    'day': day,
                    'day_name': day_names[day],
                    'adjustment': adjustment,
                    'reason': '고수요 요일'
                })
            elif demand_index < 0.8:
                adjustment = max(0.95, 1 - (1 - demand_index) * 0.05)
                rules.append({
                    'day': day,
                    'day_name': day_names[day],
                    'adjustment': adjustment,
                    'reason': '저수요 요일'
                })
                
        return rules
        
    def _generate_inventory_based_rules(self, product: Product) -> List[Dict[str, Any]]:
        """재고 기반 가격 규칙 생성"""
        rules = []
        
        # 재고 수준별 규칙
        if product.stock > 200:
            rules.append({
                'condition': 'stock > 200',
                'adjustment': 0.9,
                'reason': '과잉 재고'
            })
        elif product.stock < 20:
            rules.append({
                'condition': 'stock < 20',
                'adjustment': 1.1,
                'reason': '재고 부족'
            })
            
        # 재고 회전율 기반 규칙
        monthly_sales = self._get_sales_volume(
            product.id,
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        
        if monthly_sales > 0:
            months_of_inventory = product.stock / monthly_sales
            if months_of_inventory > 3:
                rules.append({
                    'condition': 'slow_moving',
                    'adjustment': 0.85,
                    'reason': '재고 회전율 낮음'
                })
                
        return rules