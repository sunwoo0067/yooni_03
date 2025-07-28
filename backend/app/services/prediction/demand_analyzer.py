"""
드롭쉬핑 수요 분석 서비스

고객 구매 패턴, 시장 수요 변화, 계절성 트렌드 분석
데이터 기반 재고 및 가격 전략 수립 지원
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.services.database.database import get_db


class DemandTrend(Enum):
    """수요 트렌드"""
    INCREASING = "increasing"    # 증가
    STABLE = "stable"           # 안정
    DECREASING = "decreasing"   # 감소
    VOLATILE = "volatile"       # 변동성 높음


@dataclass
class DemandAnalysis:
    """수요 분석 결과"""
    product_id: int
    current_demand_score: float      # 현재 수요 점수 (0-100)
    trend: DemandTrend              # 수요 트렌드
    weekly_pattern: Dict[str, float] # 요일별 수요 패턴
    monthly_pattern: Dict[int, float] # 월별 수요 패턴
    seasonal_index: float           # 계절성 지수
    price_elasticity: float         # 가격 탄력성
    peak_demand_period: str         # 피크 수요 시기
    demand_volatility: float        # 수요 변동성
    growth_rate: float              # 수요 성장률
    recommendations: List[str]      # 권장사항


class DemandAnalyzer:
    """수요 분석기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analysis_period_days = 90  # 분석 기간
        
    async def analyze_product_demand(self, product_id: int) -> DemandAnalysis:
        """개별 상품 수요 분석"""
        try:
            self.logger.info(f"수요 분석 시작 - 상품 {product_id}")
            
            # 분석 데이터 수집
            data = await self._collect_demand_data(product_id)
            if not data or not data['orders']:
                return self._create_no_data_analysis(product_id)
                
            # 수요 분석 수행
            analysis = await self._perform_demand_analysis(product_id, data)
            
            # 분석 결과 저장
            await self._save_demand_analysis(analysis)
            
            self.logger.info(f"수요 분석 완료 - 상품 {product_id}: "
                           f"수요점수 {analysis.current_demand_score:.1f}, "
                           f"트렌드 {analysis.trend.value}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"수요 분석 실패 - 상품 {product_id}: {e}")
            return self._create_error_analysis(product_id, str(e))
            
    async def _collect_demand_data(self, product_id: int) -> Optional[Dict]:
        """수요 분석 데이터 수집"""
        db = next(get_db())
        try:
            from app.models.product import Product
            from app.models.order_core import Order
            
            # 기본 상품 정보
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
                
            # 주문 데이터 수집
            analysis_start = datetime.now() - timedelta(days=self.analysis_period_days)
            orders = db.query(Order).filter(
                Order.product_id == product_id,
                Order.created_at >= analysis_start,
                Order.status.in_(['completed', 'shipped', 'pending'])
            ).order_by(Order.created_at).all()
            
            # 가격 변동 히스토리
            price_history = await self._get_price_history(product_id)
            
            # 경쟁사 가격 데이터
            competitor_prices = await self._get_competitor_price_history(product)
            
            # 시장 데이터
            market_data = await self._get_market_data(product.category)
            
            return {
                'product': product,
                'orders': orders,
                'price_history': price_history,
                'competitor_prices': competitor_prices,
                'market_data': market_data
            }
            
        finally:
            db.close()
            
    async def _get_price_history(self, product_id: int) -> List[Dict]:
        """가격 변동 히스토리 조회"""
        # 구현 예정: 가격 히스토리 테이블에서 데이터 조회
        # 임시로 가상 데이터 반환
        history = []
        base_price = 50000
        
        for i in range(30):
            date = datetime.now() - timedelta(days=i)
            # 가상의 가격 변동
            price = base_price + (i % 7 - 3) * 1000
            history.append({
                'date': date,
                'price': price
            })
            
        return history
        
    async def _get_competitor_price_history(self, product) -> List[Dict]:
        """경쟁사 가격 히스토리 조회"""
        # 구현 예정: 외부 가격 모니터링 데이터
        return []
        
    async def _get_market_data(self, category: str) -> Dict:
        """시장 데이터 조회"""
        # 구현 예정: 외부 시장 조사 데이터
        return {
            'category_growth_rate': 0.05,
            'market_size': 1000000,
            'competition_level': 'medium'
        }
        
    async def _perform_demand_analysis(self, product_id: int, data: Dict) -> DemandAnalysis:
        """수요 분석 수행"""
        orders = data['orders']
        price_history = data['price_history']
        
        # 현재 수요 점수 계산
        current_demand_score = self._calculate_demand_score(orders)
        
        # 수요 트렌드 분석
        trend = self._analyze_demand_trend(orders)
        
        # 요일별 패턴 분석
        weekly_pattern = self._analyze_weekly_pattern(orders)
        
        # 월별 패턴 분석
        monthly_pattern = self._analyze_monthly_pattern(orders)
        
        # 계절성 지수 계산
        seasonal_index = self._calculate_seasonal_index(orders)
        
        # 가격 탄력성 계산
        price_elasticity = self._calculate_price_elasticity(orders, price_history)
        
        # 피크 수요 시기 분석
        peak_demand_period = self._identify_peak_demand_period(weekly_pattern, monthly_pattern)
        
        # 수요 변동성 계산
        demand_volatility = self._calculate_demand_volatility(orders)
        
        # 수요 성장률 계산
        growth_rate = self._calculate_demand_growth_rate(orders)
        
        # 권장사항 생성
        recommendations = self._generate_demand_recommendations(
            current_demand_score, trend, price_elasticity, demand_volatility
        )
        
        return DemandAnalysis(
            product_id=product_id,
            current_demand_score=current_demand_score,
            trend=trend,
            weekly_pattern=weekly_pattern,
            monthly_pattern=monthly_pattern,
            seasonal_index=seasonal_index,
            price_elasticity=price_elasticity,
            peak_demand_period=peak_demand_period,
            demand_volatility=demand_volatility,
            growth_rate=growth_rate,
            recommendations=recommendations
        )
        
    def _calculate_demand_score(self, orders: List) -> float:
        """현재 수요 점수 계산 (0-100)"""
        if not orders:
            return 0.0
            
        # 최근 30일 주문 수 기반 점수
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_orders = [o for o in orders if o.created_at >= thirty_days_ago]
        
        # 일일 평균 주문 수
        daily_orders = len(recent_orders) / 30
        
        # 0-100 점수로 정규화 (일일 10개 주문 = 100점)
        score = min(100, (daily_orders / 10) * 100)
        
        return round(score, 1)
        
    def _analyze_demand_trend(self, orders: List) -> DemandTrend:
        """수요 트렌드 분석"""
        if len(orders) < 14:
            return DemandTrend.STABLE
            
        # 주 단위로 그룹화
        weekly_sales = {}
        for order in orders:
            week_key = order.created_at.strftime('%Y-W%U')
            weekly_sales[week_key] = weekly_sales.get(week_key, 0) + 1
            
        if len(weekly_sales) < 4:
            return DemandTrend.STABLE
            
        # 최근 4주 데이터로 트렌드 분석
        recent_weeks = sorted(weekly_sales.keys())[-4:]
        weekly_values = [weekly_sales[week] for week in recent_weeks]
        
        # 선형 회귀로 트렌드 계산
        x = np.arange(len(weekly_values))
        if len(weekly_values) > 1:
            slope = np.polyfit(x, weekly_values, 1)[0]
            
            # 변동성 계산
            volatility = np.std(weekly_values) / (np.mean(weekly_values) + 1)
            
            if volatility > 0.5:
                return DemandTrend.VOLATILE
            elif slope > 0.5:
                return DemandTrend.INCREASING
            elif slope < -0.5:
                return DemandTrend.DECREASING
            else:
                return DemandTrend.STABLE
        else:
            return DemandTrend.STABLE
            
    def _analyze_weekly_pattern(self, orders: List) -> Dict[str, float]:
        """요일별 수요 패턴 분석"""
        weekday_counts = {
            'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0,
            'Friday': 0, 'Saturday': 0, 'Sunday': 0
        }
        
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                        'Friday', 'Saturday', 'Sunday']
        
        for order in orders:
            weekday = weekday_names[order.created_at.weekday()]
            weekday_counts[weekday] += 1
            
        total_orders = sum(weekday_counts.values())
        if total_orders == 0:
            return weekday_counts
            
        # 비율로 변환 (평균 = 1.0)
        pattern = {}
        for day, count in weekday_counts.items():
            pattern[day] = round((count / total_orders) * 7, 2)
            
        return pattern
        
    def _analyze_monthly_pattern(self, orders: List) -> Dict[int, float]:
        """월별 수요 패턴 분석"""
        monthly_counts = {i: 0 for i in range(1, 13)}
        
        for order in orders:
            month = order.created_at.month
            monthly_counts[month] += 1
            
        total_orders = sum(monthly_counts.values())
        if total_orders == 0:
            return monthly_counts
            
        # 비율로 변환 (평균 = 1.0)
        pattern = {}
        for month, count in monthly_counts.items():
            pattern[month] = round((count / total_orders) * 12, 2)
            
        return pattern
        
    def _calculate_seasonal_index(self, orders: List) -> float:
        """계절성 지수 계산"""
        if not orders:
            return 1.0
            
        # 현재 월의 수요와 연평균 수요 비교
        current_month = datetime.now().month
        monthly_pattern = self._analyze_monthly_pattern(orders)
        
        return monthly_pattern.get(current_month, 1.0)
        
    def _calculate_price_elasticity(self, orders: List, price_history: List[Dict]) -> float:
        """가격 탄력성 계산"""
        if len(orders) < 20 or len(price_history) < 10:
            return -1.0  # 기본 탄력성
            
        try:
            # 가격과 판매량 데이터 정렬
            price_sales_data = []
            
            for price_point in price_history[-30:]:  # 최근 30일
                date = price_point['date']
                price = price_point['price']
                
                # 해당 날짜 ±3일 범위의 주문 수
                date_orders = [
                    o for o in orders 
                    if abs((o.created_at.date() - date.date()).days) <= 3
                ]
                
                if date_orders:
                    daily_sales = len(date_orders) / 7  # 주간 평균을 일간으로 변환
                    price_sales_data.append((price, daily_sales))
                    
            if len(price_sales_data) < 5:
                return -1.0
                
            # 가격과 판매량의 상관관계 계산
            prices = [p[0] for p in price_sales_data]
            sales = [p[1] for p in price_sales_data]
            
            if len(set(prices)) < 2:  # 가격 변동이 없으면
                return -1.0
                
            # 상관계수 계산
            correlation = np.corrcoef(prices, sales)[0, 1]
            
            # 탄력성 추정 (단순화된 방법)
            if not np.isnan(correlation):
                elasticity = correlation * -2  # 일반적으로 음의 상관관계
                return round(max(-5.0, min(0, elasticity)), 2)
            else:
                return -1.0
                
        except Exception as e:
            self.logger.error(f"가격 탄력성 계산 오류: {e}")
            return -1.0
            
    def _identify_peak_demand_period(self, weekly_pattern: Dict, monthly_pattern: Dict) -> str:
        """피크 수요 시기 식별"""
        # 요일별 피크
        peak_weekday = max(weekly_pattern.items(), key=lambda x: x[1])
        
        # 월별 피크
        peak_month = max(monthly_pattern.items(), key=lambda x: x[1])
        
        month_names = ['', '1월', '2월', '3월', '4월', '5월', '6월',
                      '7월', '8월', '9월', '10월', '11월', '12월']
        
        return f"{peak_weekday[0]}, {month_names[peak_month[0]]}"
        
    def _calculate_demand_volatility(self, orders: List) -> float:
        """수요 변동성 계산"""
        if len(orders) < 14:
            return 0.0
            
        # 일별 주문 수 계산
        daily_sales = {}
        for order in orders:
            date_key = order.created_at.date()
            daily_sales[date_key] = daily_sales.get(date_key, 0) + 1
            
        sales_values = list(daily_sales.values())
        if len(sales_values) < 7:
            return 0.0
            
        # 변동계수 계산 (표준편차 / 평균)
        mean_sales = np.mean(sales_values)
        if mean_sales == 0:
            return 0.0
            
        std_sales = np.std(sales_values)
        volatility = std_sales / mean_sales
        
        return round(volatility, 3)
        
    def _calculate_demand_growth_rate(self, orders: List) -> float:
        """수요 성장률 계산"""
        if len(orders) < 30:
            return 0.0
            
        # 전반기와 후반기 비교
        mid_point = len(orders) // 2
        first_half = orders[:mid_point]
        second_half = orders[mid_point:]
        
        first_half_days = (first_half[-1].created_at - first_half[0].created_at).days + 1
        second_half_days = (second_half[-1].created_at - second_half[0].created_at).days + 1
        
        first_daily_avg = len(first_half) / first_half_days
        second_daily_avg = len(second_half) / second_half_days
        
        if first_daily_avg == 0:
            return 0.0
            
        growth_rate = (second_daily_avg - first_daily_avg) / first_daily_avg
        return round(growth_rate * 100, 1)  # 백분율로 반환
        
    def _generate_demand_recommendations(self, 
                                       demand_score: float,
                                       trend: DemandTrend, 
                                       price_elasticity: float,
                                       volatility: float) -> List[str]:
        """수요 기반 권장사항 생성"""
        recommendations = []
        
        # 수요 점수 기반 권장사항
        if demand_score >= 80:
            recommendations.append("높은 수요 - 재고 증량 및 프로모션 확대 고려")
        elif demand_score >= 60:
            recommendations.append("적정 수요 - 현재 전략 유지")
        elif demand_score >= 30:
            recommendations.append("보통 수요 - 마케팅 강화 필요")
        else:
            recommendations.append("낮은 수요 - 상품 전략 재검토 필요")
            
        # 트렌드 기반 권장사항
        if trend == DemandTrend.INCREASING:
            recommendations.append("수요 증가 트렌드 - 적극적 재고 확보 권장")
        elif trend == DemandTrend.DECREASING:
            recommendations.append("수요 감소 트렌드 - 프로모션 또는 가격 조정 고려")
        elif trend == DemandTrend.VOLATILE:
            recommendations.append("수요 변동성 높음 - 유연한 재고 관리 필요")
            
        # 가격 탄력성 기반 권장사항
        if price_elasticity < -2.0:
            recommendations.append("가격 민감도 높음 - 가격 경쟁력 유지 중요")
        elif price_elasticity > -0.5:
            recommendations.append("가격 민감도 낮음 - 가격 인상 여지 있음")
            
        # 변동성 기반 권장사항
        if volatility > 1.0:
            recommendations.append("수요 변동성 매우 높음 - 안전 재고 확보 필요")
        elif volatility > 0.5:
            recommendations.append("수요 변동성 보통 - 유연한 재고 정책 권장")
            
        return recommendations
        
    def _create_no_data_analysis(self, product_id: int) -> DemandAnalysis:
        """데이터 부족 시 기본 분석"""
        return DemandAnalysis(
            product_id=product_id,
            current_demand_score=0.0,
            trend=DemandTrend.STABLE,
            weekly_pattern={'Monday': 1, 'Tuesday': 1, 'Wednesday': 1, 'Thursday': 1,
                          'Friday': 1, 'Saturday': 1, 'Sunday': 1},
            monthly_pattern={i: 1 for i in range(1, 13)},
            seasonal_index=1.0,
            price_elasticity=-1.0,
            peak_demand_period="데이터 부족",
            demand_volatility=0.0,
            growth_rate=0.0,
            recommendations=["충분한 판매 데이터 수집 필요"]
        )
        
    def _create_error_analysis(self, product_id: int, error_msg: str) -> DemandAnalysis:
        """오류 시 기본 분석"""
        return DemandAnalysis(
            product_id=product_id,
            current_demand_score=0.0,
            trend=DemandTrend.STABLE,
            weekly_pattern={},
            monthly_pattern={},
            seasonal_index=1.0,
            price_elasticity=-1.0,
            peak_demand_period="분석 오류",
            demand_volatility=0.0,
            growth_rate=0.0,
            recommendations=[f"분석 오류: {error_msg}"]
        )
        
    async def _save_demand_analysis(self, analysis: DemandAnalysis):
        """수요 분석 결과 저장"""
        db = next(get_db())
        try:
            from app.models.dropshipping import DemandAnalysisHistory
            
            history = DemandAnalysisHistory(
                product_id=analysis.product_id,
                demand_score=analysis.current_demand_score,
                trend=analysis.trend.value,
                weekly_pattern=str(analysis.weekly_pattern),
                monthly_pattern=str(analysis.monthly_pattern),
                seasonal_index=analysis.seasonal_index,
                price_elasticity=analysis.price_elasticity,
                peak_demand_period=analysis.peak_demand_period,
                demand_volatility=analysis.demand_volatility,
                growth_rate=analysis.growth_rate,
                recommendations=str(analysis.recommendations),
                analyzed_at=datetime.now()
            )
            
            db.add(history)
            db.commit()
            
        finally:
            db.close()
            
    # 분석 리포트 메서드들
    async def analyze_category_demand(self, category: str) -> Dict:
        """카테고리별 수요 분석"""
        db = next(get_db())
        try:
            from app.models.product import Product
            
            products = db.query(Product).filter(
                Product.category == category,
                Product.is_deleted == False
            ).all()
            
            if not products:
                return {"error": f"카테고리 '{category}'에 상품이 없습니다"}
                
            # 카테고리 내 각 상품 분석
            product_analyses = []
            for product in products[:20]:  # 최대 20개 상품만 분석
                analysis = await self.analyze_product_demand(product.id)
                product_analyses.append(analysis)
                
            # 카테고리 전체 통계
            total_demand_score = np.mean([a.current_demand_score for a in product_analyses])
            
            trend_counts = {}
            for analysis in product_analyses:
                trend = analysis.trend.value
                trend_counts[trend] = trend_counts.get(trend, 0) + 1
                
            dominant_trend = max(trend_counts.items(), key=lambda x: x[1])[0]
            
            avg_volatility = np.mean([a.demand_volatility for a in product_analyses])
            avg_growth_rate = np.mean([a.growth_rate for a in product_analyses])
            
            return {
                "category": category,
                "analyzed_products": len(product_analyses),
                "avg_demand_score": round(total_demand_score, 1),
                "dominant_trend": dominant_trend,
                "trend_distribution": trend_counts,
                "avg_volatility": round(avg_volatility, 3),
                "avg_growth_rate": round(avg_growth_rate, 1),
                "top_performers": [
                    {
                        "product_id": a.product_id,
                        "demand_score": a.current_demand_score
                    }
                    for a in sorted(product_analyses, key=lambda x: x.current_demand_score, reverse=True)[:5]
                ]
            }
            
        finally:
            db.close()
            
    async def get_demand_forecast(self, product_id: int, days_ahead: int = 30) -> Dict:
        """수요 예측"""
        try:
            # 현재 수요 분석
            current_analysis = await self.analyze_product_demand(product_id)
            
            # 기본 예측 (단순 모델)
            base_demand = current_analysis.current_demand_score
            
            # 트렌드 적용
            trend_multiplier = 1.0
            if current_analysis.trend == DemandTrend.INCREASING:
                trend_multiplier = 1.0 + (current_analysis.growth_rate / 100) * (days_ahead / 30)
            elif current_analysis.trend == DemandTrend.DECREASING:
                trend_multiplier = 1.0 + (current_analysis.growth_rate / 100) * (days_ahead / 30)
                
            # 계절성 적용
            seasonal_multiplier = current_analysis.seasonal_index
            
            # 예측 수요 점수
            forecasted_demand = base_demand * trend_multiplier * seasonal_multiplier
            forecasted_demand = max(0, min(100, forecasted_demand))
            
            # 신뢰 구간 계산 (변동성 기반)
            confidence_interval = current_analysis.demand_volatility * 10
            lower_bound = max(0, forecasted_demand - confidence_interval)
            upper_bound = min(100, forecasted_demand + confidence_interval)
            
            return {
                "product_id": product_id,
                "forecast_period_days": days_ahead,
                "current_demand_score": current_analysis.current_demand_score,
                "forecasted_demand_score": round(forecasted_demand, 1),
                "confidence_interval": {
                    "lower": round(lower_bound, 1),
                    "upper": round(upper_bound, 1)
                },
                "forecast_factors": {
                    "base_demand": base_demand,
                    "trend_effect": round((trend_multiplier - 1) * 100, 1),
                    "seasonal_effect": round((seasonal_multiplier - 1) * 100, 1)
                },
                "forecast_reliability": "medium" if current_analysis.demand_volatility < 0.5 else "low"
            }
            
        except Exception as e:
            self.logger.error(f"수요 예측 실패 - 상품 {product_id}: {e}")
            return {"error": str(e)}
            
    async def get_demand_insights(self, days_back: int = 30) -> Dict:
        """수요 인사이트 대시보드"""
        db = next(get_db())
        try:
            from app.models.dropshipping import DemandAnalysisHistory
            
            # 최근 분석 결과 조회
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            recent_analyses = db.query(DemandAnalysisHistory).filter(
                DemandAnalysisHistory.analyzed_at >= cutoff_date
            ).all()
            
            if not recent_analyses:
                return {"error": "분석 데이터가 없습니다"}
                
            # 전체 통계
            avg_demand_score = np.mean([a.demand_score for a in recent_analyses])
            
            # 트렌드 분포
            trend_distribution = {}
            for analysis in recent_analyses:
                trend = analysis.trend
                trend_distribution[trend] = trend_distribution.get(trend, 0) + 1
                
            # 성장률 분포
            growth_rates = [a.growth_rate for a in recent_analyses if a.growth_rate is not None]
            avg_growth_rate = np.mean(growth_rates) if growth_rates else 0
            
            # 변동성 분포
            volatilities = [a.demand_volatility for a in recent_analyses if a.demand_volatility is not None]
            avg_volatility = np.mean(volatilities) if volatilities else 0
            
            # 고수요 상품 (상위 10%)
            high_demand_threshold = np.percentile([a.demand_score for a in recent_analyses], 90)
            high_demand_products = [
                a.product_id for a in recent_analyses 
                if a.demand_score >= high_demand_threshold
            ]
            
            # 위험 상품 (수요 감소 + 높은 변동성)
            risk_products = [
                a.product_id for a in recent_analyses
                if a.trend == 'decreasing' and a.demand_volatility > 0.7
            ]
            
            return {
                "analysis_period_days": days_back,
                "total_analyzed_products": len(recent_analyses),
                "avg_demand_score": round(avg_demand_score, 1),
                "trend_distribution": trend_distribution,
                "avg_growth_rate": round(avg_growth_rate, 1),
                "avg_volatility": round(avg_volatility, 3),
                "high_demand_products": len(high_demand_products),
                "risk_products": len(risk_products),
                "insights": {
                    "market_health": "좋음" if avg_demand_score > 60 else "보통" if avg_demand_score > 30 else "나쁨",
                    "overall_trend": max(trend_distribution.items(), key=lambda x: x[1])[0] if trend_distribution else "알 수 없음",
                    "volatility_level": "높음" if avg_volatility > 0.7 else "보통" if avg_volatility > 0.3 else "낮음"
                }
            }
            
        finally:
            db.close()