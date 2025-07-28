"""
수요 예측 엔진
시계열 분석, 계절성 패턴 감지, 재고 최적화, 트렌드 예측
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import numpy as np
from collections import defaultdict
import calendar

from app.models.product import Product
from app.models.order_core import Order, OrderItem
from app.models.category import Category
from app.core.exceptions import AppException


class DemandForecasting:
    """수요 예측 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def forecast_product_demand(
        self, 
        product_id: int,
        days_ahead: int = 30,
        include_seasonality: bool = True
    ) -> Dict[str, Any]:
        """
        상품별 수요 예측
        
        Args:
            product_id: 상품 ID
            days_ahead: 예측 기간 (일)
            include_seasonality: 계절성 고려 여부
            
        Returns:
            수요 예측 결과
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise AppException("상품을 찾을 수 없습니다", status_code=404)
            
        # 과거 판매 데이터 수집
        historical_data = self._get_historical_sales(product_id, days=180)
        
        if not historical_data:
            return {
                'product_id': product_id,
                'product_name': product.name,
                'forecast_period': days_ahead,
                'error': '판매 이력이 부족하여 예측할 수 없습니다'
            }
            
        # 1. 기본 통계 분석
        basic_stats = self._calculate_basic_statistics(historical_data)
        
        # 2. 트렌드 분석
        trend = self._analyze_trend(historical_data)
        
        # 3. 계절성 분석
        seasonality = self._analyze_seasonality(historical_data) if include_seasonality else None
        
        # 4. 이동 평균 기반 예측
        base_forecast = self._moving_average_forecast(
            historical_data, days_ahead, window=7
        )
        
        # 5. 트렌드 및 계절성 적용
        adjusted_forecast = self._apply_trend_and_seasonality(
            base_forecast, trend, seasonality
        )
        
        # 6. 신뢰 구간 계산
        confidence_intervals = self._calculate_confidence_intervals(
            historical_data, adjusted_forecast
        )
        
        # 7. 재고 권장사항 생성
        inventory_recommendations = self._generate_inventory_recommendations(
            product, adjusted_forecast, basic_stats
        )
        
        return {
            'product_id': product_id,
            'product_name': product.name,
            'forecast_period': days_ahead,
            'current_stock': product.stock,
            'historical_stats': basic_stats,
            'trend': trend,
            'seasonality': seasonality,
            'daily_forecast': adjusted_forecast,
            'total_forecast': sum(adjusted_forecast),
            'confidence_intervals': confidence_intervals,
            'inventory_recommendations': inventory_recommendations,
            'alerts': self._generate_demand_alerts(product, adjusted_forecast)
        }
        
    def _get_historical_sales(self, product_id: int, days: int = 180) -> List[Dict[str, Any]]:
        """과거 판매 데이터 조회"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 일별 판매량 집계
        daily_sales = self.db.query(
            func.date(Order.created_at).label('date'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(OrderItem).filter(
            OrderItem.product_id == product_id,
            Order.created_at >= since_date,
            Order.status == 'completed'
        ).group_by(func.date(Order.created_at)).order_by('date').all()
        
        # 빈 날짜 채우기
        sales_dict = {sale.date: sale.quantity for sale in daily_sales}
        
        result = []
        current_date = since_date.date()
        end_date = datetime.utcnow().date()
        
        while current_date <= end_date:
            result.append({
                'date': current_date,
                'quantity': sales_dict.get(current_date, 0)
            })
            current_date += timedelta(days=1)
            
        return result
        
    def _calculate_basic_statistics(self, historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """기본 통계 계산"""
        quantities = [d['quantity'] for d in historical_data]
        
        return {
            'mean_daily': np.mean(quantities),
            'median_daily': np.median(quantities),
            'std_dev': np.std(quantities),
            'min_daily': np.min(quantities),
            'max_daily': np.max(quantities),
            'zero_sales_days': quantities.count(0),
            'total_period_sales': sum(quantities)
        }
        
    def _analyze_trend(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """트렌드 분석 (간단한 선형 회귀)"""
        if len(historical_data) < 14:
            return {'type': 'insufficient_data'}
            
        # X: 일수, Y: 판매량
        X = np.arange(len(historical_data))
        y = np.array([d['quantity'] for d in historical_data])
        
        # 이동 평균으로 노이즈 제거
        window = 7
        y_smooth = np.convolve(y, np.ones(window)/window, mode='valid')
        X_smooth = X[:len(y_smooth)]
        
        # 선형 회귀
        if len(X_smooth) > 0:
            coefficients = np.polyfit(X_smooth, y_smooth, 1)
            slope = coefficients[0]
            
            # 트렌드 타입 결정
            if abs(slope) < 0.1:
                trend_type = 'stable'
            elif slope > 0:
                trend_type = 'increasing'
            else:
                trend_type = 'decreasing'
                
            # 성장률 계산
            avg_quantity = np.mean(y_smooth)
            if avg_quantity > 0:
                growth_rate = (slope / avg_quantity) * 100
            else:
                growth_rate = 0
                
            return {
                'type': trend_type,
                'slope': slope,
                'daily_growth_rate': growth_rate,
                'weekly_growth_rate': growth_rate * 7
            }
        else:
            return {'type': 'insufficient_data'}
            
    def _analyze_seasonality(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """계절성 분석"""
        if len(historical_data) < 60:
            return {'pattern': 'insufficient_data'}
            
        # 요일별 패턴
        weekday_sales = defaultdict(list)
        for data in historical_data:
            weekday = data['date'].weekday()
            weekday_sales[weekday].append(data['quantity'])
            
        weekday_pattern = {}
        overall_mean = np.mean([d['quantity'] for d in historical_data])
        
        for day in range(7):
            if weekday_sales[day]:
                day_mean = np.mean(weekday_sales[day])
                weekday_pattern[day] = day_mean / overall_mean if overall_mean > 0 else 1.0
            else:
                weekday_pattern[day] = 1.0
                
        # 월별 패턴 (충분한 데이터가 있는 경우)
        monthly_pattern = {}
        if len(historical_data) >= 90:
            monthly_sales = defaultdict(list)
            for data in historical_data:
                month = data['date'].month
                monthly_sales[month].append(data['quantity'])
                
            for month in range(1, 13):
                if monthly_sales[month]:
                    month_mean = np.mean(monthly_sales[month])
                    monthly_pattern[month] = month_mean / overall_mean if overall_mean > 0 else 1.0
                else:
                    monthly_pattern[month] = 1.0
                    
        return {
            'pattern': 'detected',
            'weekday_factors': weekday_pattern,
            'monthly_factors': monthly_pattern if monthly_pattern else None
        }
        
    def _moving_average_forecast(
        self, 
        historical_data: List[Dict[str, Any]], 
        days_ahead: int,
        window: int = 7
    ) -> List[float]:
        """이동 평균 기반 예측"""
        quantities = [d['quantity'] for d in historical_data]
        
        # 최근 데이터로 이동 평균 계산
        if len(quantities) >= window:
            recent_avg = np.mean(quantities[-window:])
        else:
            recent_avg = np.mean(quantities)
            
        # 기본 예측값
        base_forecast = [recent_avg] * days_ahead
        
        return base_forecast
        
    def _apply_trend_and_seasonality(
        self,
        base_forecast: List[float],
        trend: Dict[str, Any],
        seasonality: Optional[Dict[str, Any]]
    ) -> List[float]:
        """트렌드와 계절성 적용"""
        adjusted_forecast = base_forecast.copy()
        
        # 트렌드 적용
        if trend.get('type') in ['increasing', 'decreasing']:
            slope = trend.get('slope', 0)
            for i in range(len(adjusted_forecast)):
                adjusted_forecast[i] += slope * i
                
        # 계절성 적용
        if seasonality and seasonality.get('pattern') == 'detected':
            start_date = datetime.utcnow().date() + timedelta(days=1)
            
            for i in range(len(adjusted_forecast)):
                forecast_date = start_date + timedelta(days=i)
                
                # 요일 계절성
                weekday = forecast_date.weekday()
                weekday_factor = seasonality['weekday_factors'].get(weekday, 1.0)
                adjusted_forecast[i] *= weekday_factor
                
                # 월별 계절성
                if seasonality.get('monthly_factors'):
                    month = forecast_date.month
                    month_factor = seasonality['monthly_factors'].get(month, 1.0)
                    adjusted_forecast[i] *= month_factor
                    
        # 음수 방지
        adjusted_forecast = [max(0, f) for f in adjusted_forecast]
        
        return adjusted_forecast
        
    def _calculate_confidence_intervals(
        self,
        historical_data: List[Dict[str, Any]],
        forecast: List[float]
    ) -> Dict[str, List[float]]:
        """신뢰 구간 계산"""
        quantities = [d['quantity'] for d in historical_data]
        std_dev = np.std(quantities)
        
        # 95% 신뢰 구간 (정규분포 가정)
        z_score = 1.96
        margin = z_score * std_dev
        
        lower_bound = [max(0, f - margin) for f in forecast]
        upper_bound = [f + margin for f in forecast]
        
        return {
            'lower_95': lower_bound,
            'upper_95': upper_bound,
            'margin_of_error': margin
        }
        
    def _generate_inventory_recommendations(
        self,
        product: Product,
        forecast: List[float],
        stats: Dict[str, float]
    ) -> Dict[str, Any]:
        """재고 최적화 권장사항"""
        total_forecast = sum(forecast)
        current_stock = product.stock
        
        # 안전 재고 계산 (표준편차 기반)
        safety_stock = stats['std_dev'] * 2  # 2 표준편차
        
        # 재주문점 계산 (리드타임 7일 가정)
        lead_time = 7
        lead_time_demand = sum(forecast[:lead_time]) if len(forecast) >= lead_time else total_forecast * (lead_time / len(forecast))
        reorder_point = lead_time_demand + safety_stock
        
        # 최적 주문량 (EOQ 간소화 버전)
        daily_demand = stats['mean_daily']
        optimal_order_quantity = daily_demand * 30  # 30일치
        
        # 재고 상태 평가
        days_of_supply = current_stock / daily_demand if daily_demand > 0 else float('inf')
        
        recommendations = {
            'current_stock': current_stock,
            'safety_stock': round(safety_stock),
            'reorder_point': round(reorder_point),
            'optimal_order_quantity': round(optimal_order_quantity),
            'days_of_supply': round(days_of_supply, 1),
            'stock_status': self._evaluate_stock_status(days_of_supply),
            'action_required': self._determine_action(current_stock, reorder_point, days_of_supply)
        }
        
        return recommendations
        
    def _evaluate_stock_status(self, days_of_supply: float) -> str:
        """재고 상태 평가"""
        if days_of_supply < 7:
            return 'critical_low'
        elif days_of_supply < 14:
            return 'low'
        elif days_of_supply < 60:
            return 'optimal'
        elif days_of_supply < 90:
            return 'high'
        else:
            return 'excess'
            
    def _determine_action(self, current_stock: int, reorder_point: float, days_of_supply: float) -> str:
        """필요 조치 결정"""
        if current_stock <= reorder_point:
            return 'immediate_reorder'
        elif days_of_supply < 14:
            return 'prepare_reorder'
        elif days_of_supply > 90:
            return 'reduce_stock'
        else:
            return 'monitor'
            
    def _generate_demand_alerts(self, product: Product, forecast: List[float]) -> List[Dict[str, str]]:
        """수요 예측 알림 생성"""
        alerts = []
        
        # 재고 부족 예상
        cumulative_demand = 0
        for i, daily_forecast in enumerate(forecast):
            cumulative_demand += daily_forecast
            if cumulative_demand > product.stock and not alerts:
                alerts.append({
                    'type': 'stock_out',
                    'severity': 'high',
                    'message': f'{i+1}일 후 재고 소진 예상',
                    'days_until': i+1
                })
                break
                
        # 급격한 수요 증가 예상
        if len(forecast) >= 7:
            week1_avg = np.mean(forecast[:7])
            week2_avg = np.mean(forecast[7:14]) if len(forecast) >= 14 else week1_avg
            
            if week2_avg > week1_avg * 1.5:
                alerts.append({
                    'type': 'demand_spike',
                    'severity': 'medium',
                    'message': '다음 주 수요 급증 예상',
                    'increase_percent': round((week2_avg / week1_avg - 1) * 100)
                })
                
        return alerts
        
    def forecast_category_demand(
        self,
        category: str,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """카테고리별 수요 예측"""
        # 카테고리의 모든 활성 상품
        products = self.db.query(Product).filter(
            Product.category == category,
            Product.is_active == True
        ).all()
        
        if not products:
            raise AppException(f"'{category}' 카테고리에 상품이 없습니다", status_code=404)
            
        category_forecast = {
            'category': category,
            'forecast_period': days_ahead,
            'product_count': len(products),
            'products': [],
            'summary': {
                'total_current_stock': 0,
                'total_forecast_demand': 0,
                'products_needing_reorder': 0,
                'products_with_excess_stock': 0
            }
        }
        
        # 각 상품별 예측
        for product in products:
            try:
                product_forecast = self.forecast_product_demand(
                    product.id, days_ahead, include_seasonality=True
                )
                
                category_forecast['products'].append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'current_stock': product.stock,
                    'total_forecast': product_forecast['total_forecast'],
                    'stock_status': product_forecast['inventory_recommendations']['stock_status'],
                    'action': product_forecast['inventory_recommendations']['action_required']
                })
                
                # 요약 정보 업데이트
                category_forecast['summary']['total_current_stock'] += product.stock
                category_forecast['summary']['total_forecast_demand'] += product_forecast['total_forecast']
                
                if product_forecast['inventory_recommendations']['action_required'] in ['immediate_reorder', 'prepare_reorder']:
                    category_forecast['summary']['products_needing_reorder'] += 1
                elif product_forecast['inventory_recommendations']['stock_status'] == 'excess':
                    category_forecast['summary']['products_with_excess_stock'] += 1
                    
            except Exception as e:
                category_forecast['products'].append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'error': str(e)
                })
                
        # 카테고리 레벨 권장사항
        category_forecast['recommendations'] = self._generate_category_recommendations(
            category_forecast['summary']
        )
        
        return category_forecast
        
    def _generate_category_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """카테고리 레벨 권장사항 생성"""
        recommendations = []
        
        reorder_ratio = summary['products_needing_reorder'] / summary['product_count'] if summary['product_count'] > 0 else 0
        excess_ratio = summary['products_with_excess_stock'] / summary['product_count'] if summary['product_count'] > 0 else 0
        
        if reorder_ratio > 0.3:
            recommendations.append(f"{summary['products_needing_reorder']}개 상품의 재주문이 필요합니다.")
            
        if excess_ratio > 0.3:
            recommendations.append(f"{summary['products_with_excess_stock']}개 상품의 재고가 과다합니다. 프로모션을 고려하세요.")
            
        if summary['total_forecast_demand'] > summary['total_current_stock']:
            shortage = summary['total_forecast_demand'] - summary['total_current_stock']
            recommendations.append(f"예측 기간 동안 약 {shortage:.0f}개의 재고 부족이 예상됩니다.")
            
        return recommendations
        
    def get_demand_trends(self, days: int = 90) -> Dict[str, Any]:
        """전체 수요 트렌드 분석"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 일별 전체 판매량
        daily_sales = self.db.query(
            func.date(Order.created_at).label('date'),
            func.sum(OrderItem.quantity).label('quantity'),
            func.count(distinct(Order.id)).label('order_count')
        ).join(OrderItem).filter(
            Order.created_at >= since_date,
            Order.status == 'completed'
        ).group_by(func.date(Order.created_at)).order_by('date').all()
        
        # 카테고리별 판매 트렌드
        category_sales = self.db.query(
            Product.category,
            func.date(Order.created_at).label('date'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(OrderItem).join(Product).filter(
            Order.created_at >= since_date,
            Order.status == 'completed'
        ).group_by(Product.category, func.date(Order.created_at)).all()
        
        # 데이터 정리
        total_quantities = [s.quantity for s in daily_sales]
        
        # 카테고리별 데이터 정리
        category_trends = defaultdict(lambda: {'dates': [], 'quantities': []})
        for sale in category_sales:
            if sale.category:
                category_trends[sale.category]['dates'].append(sale.date)
                category_trends[sale.category]['quantities'].append(sale.quantity)
                
        # 트렌드 분석
        overall_trend = self._analyze_trend([
            {'date': s.date, 'quantity': s.quantity} for s in daily_sales
        ])
        
        # 상위 성장 카테고리
        growth_rates = {}
        for category, data in category_trends.items():
            if len(data['quantities']) >= 14:
                trend = self._analyze_trend([
                    {'date': data['dates'][i], 'quantity': data['quantities'][i]}
                    for i in range(len(data['dates']))
                ])
                growth_rates[category] = trend.get('weekly_growth_rate', 0)
                
        top_growing = sorted(growth_rates.items(), key=lambda x: x[1], reverse=True)[:5]
        declining = sorted(growth_rates.items(), key=lambda x: x[1])[:5]
        
        return {
            'period_days': days,
            'overall_trend': overall_trend,
            'total_orders': sum(s.order_count for s in daily_sales),
            'total_items_sold': sum(total_quantities),
            'average_daily_items': np.mean(total_quantities) if total_quantities else 0,
            'peak_day': {
                'date': max(daily_sales, key=lambda x: x.quantity).date if daily_sales else None,
                'quantity': max(s.quantity for s in daily_sales) if daily_sales else 0
            },
            'top_growing_categories': [
                {'category': cat, 'growth_rate': rate} for cat, rate in top_growing if rate > 0
            ],
            'declining_categories': [
                {'category': cat, 'growth_rate': rate} for cat, rate in declining if rate < 0
            ]
        }