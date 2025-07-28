"""
대시보드 분석 서비스
AI 기반 인사이트 및 예측 분석 제공
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import pandas as pd
import asyncio

from app.models.product import Product
from app.models.order_core import Order, OrderItem
from app.models.inventory import Inventory
from app.models.platform import Platform
from app.models.keyword import KeywordPerformance
from app.models.market import MarketTrend
from app.services.cache_service import CacheService
from app.services.ai_service import AIService
from app.core.logging import logger


class AnalyticsService:
    """대시보드 분석 서비스"""
    
    def __init__(self):
        self.cache = CacheService()
        self.ai_service = AIService()
        self.cache_ttl = 300  # 5분 캐시
        
    async def get_ai_insights(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """AI 기반 비즈니스 인사이트"""
        try:
            # 캐시 확인
            cache_key = f"analytics:insights:{user_id}:{platform_ids}"
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data
                
            # 병렬로 인사이트 생성
            tasks = [
                self._generate_sales_insights(db, user_id, platform_ids),
                self._generate_inventory_insights(db, user_id, platform_ids),
                self._generate_product_insights(db, user_id, platform_ids),
                self._generate_market_insights(db, user_id, platform_ids),
                self._generate_action_items(db, user_id, platform_ids)
            ]
            
            results = await asyncio.gather(*tasks)
            
            insights = {
                "sales_insights": results[0],
                "inventory_insights": results[1],
                "product_insights": results[2],
                "market_insights": results[3],
                "action_items": results[4],
                "generated_at": datetime.now().isoformat()
            }
            
            # 캐시 저장
            await self.cache.set(cache_key, insights, self.cache_ttl)
            
            return insights
            
        except Exception as e:
            logger.error(f"AI 인사이트 생성 실패: {str(e)}")
            raise
            
    async def _generate_sales_insights(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """매출 인사이트 생성"""
        try:
            insights = []
            
            # 매출 트렌드 분석
            trend_data = await self._analyze_sales_trend(db, user_id, platform_ids)
            if trend_data["trend"] == "increasing":
                insights.append({
                    "type": "positive",
                    "category": "sales",
                    "title": "매출 상승 추세",
                    "description": f"최근 7일간 매출이 {trend_data['growth_rate']:.1f}% 증가했습니다.",
                    "impact": "high",
                    "data": trend_data
                })
            elif trend_data["trend"] == "decreasing":
                insights.append({
                    "type": "warning",
                    "category": "sales",
                    "title": "매출 하락 주의",
                    "description": f"최근 7일간 매출이 {abs(trend_data['growth_rate']):.1f}% 감소했습니다.",
                    "impact": "high",
                    "data": trend_data
                })
                
            # 피크 시간대 분석
            peak_hours = await self._analyze_peak_hours(db, user_id, platform_ids)
            if peak_hours:
                insights.append({
                    "type": "info",
                    "category": "sales",
                    "title": "주요 판매 시간대",
                    "description": f"오늘 가장 많은 주문이 {peak_hours['peak_hour']}시에 발생했습니다.",
                    "impact": "medium",
                    "data": peak_hours
                })
                
            # 플랫폼별 성과 분석
            platform_performance = await self._analyze_platform_performance(db, user_id, platform_ids)
            if platform_performance["best_platform"]:
                insights.append({
                    "type": "info",
                    "category": "sales",
                    "title": "최우수 판매 채널",
                    "description": f"{platform_performance['best_platform']}에서 가장 높은 매출을 기록했습니다.",
                    "impact": "medium",
                    "data": platform_performance
                })
                
            return insights
            
        except Exception as e:
            logger.error(f"매출 인사이트 생성 실패: {str(e)}")
            return []
            
    async def _generate_inventory_insights(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """재고 인사이트 생성"""
        try:
            insights = []
            
            # 품절 임박 상품
            low_stock_products = await self._find_low_stock_products(db, user_id, platform_ids)
            if low_stock_products:
                insights.append({
                    "type": "warning",
                    "category": "inventory",
                    "title": "재고 부족 경고",
                    "description": f"{len(low_stock_products)}개 상품의 재고가 부족합니다.",
                    "impact": "high",
                    "data": {"products": low_stock_products[:5]}  # 상위 5개만
                })
                
            # 재고 회전율 분석
            turnover_data = await self._analyze_inventory_turnover(db, user_id, platform_ids)
            if turnover_data["slow_moving_products"]:
                insights.append({
                    "type": "warning",
                    "category": "inventory",
                    "title": "저회전 상품 발견",
                    "description": f"{len(turnover_data['slow_moving_products'])}개 상품의 재고 회전이 느립니다.",
                    "impact": "medium",
                    "data": turnover_data
                })
                
            # 최적 재고 수준 제안
            optimal_stock = await self._suggest_optimal_stock_levels(db, user_id, platform_ids)
            if optimal_stock:
                insights.append({
                    "type": "recommendation",
                    "category": "inventory",
                    "title": "재고 최적화 제안",
                    "description": "AI가 분석한 최적 재고 수준을 확인하세요.",
                    "impact": "medium",
                    "data": optimal_stock
                })
                
            return insights
            
        except Exception as e:
            logger.error(f"재고 인사이트 생성 실패: {str(e)}")
            return []
            
    async def _generate_product_insights(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """상품 인사이트 생성"""
        try:
            insights = []
            
            # 급상승 상품
            trending_products = await self._find_trending_products(db, user_id, platform_ids)
            if trending_products:
                insights.append({
                    "type": "positive",
                    "category": "product",
                    "title": "인기 급상승 상품",
                    "description": f"{len(trending_products)}개 상품의 판매가 급증했습니다.",
                    "impact": "high",
                    "data": {"products": trending_products[:3]}
                })
                
            # 키워드 성과 분석
            keyword_performance = await self._analyze_keyword_performance(db, user_id, platform_ids)
            if keyword_performance["top_keywords"]:
                insights.append({
                    "type": "info",
                    "category": "product",
                    "title": "고성과 키워드",
                    "description": "이 키워드들이 높은 전환율을 보이고 있습니다.",
                    "impact": "medium",
                    "data": keyword_performance
                })
                
            # 가격 최적화 제안
            price_optimization = await self._suggest_price_optimization(db, user_id, platform_ids)
            if price_optimization:
                insights.append({
                    "type": "recommendation",
                    "category": "product",
                    "title": "가격 최적화 기회",
                    "description": f"{len(price_optimization)}개 상품의 가격 조정을 고려해보세요.",
                    "impact": "medium",
                    "data": {"suggestions": price_optimization[:3]}
                })
                
            return insights
            
        except Exception as e:
            logger.error(f"상품 인사이트 생성 실패: {str(e)}")
            return []
            
    async def _generate_market_insights(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """시장 인사이트 생성"""
        try:
            insights = []
            
            # 시장 트렌드 분석
            market_trends = await self._analyze_market_trends(db, user_id)
            if market_trends:
                for trend in market_trends[:2]:  # 상위 2개 트렌드
                    insights.append({
                        "type": "opportunity",
                        "category": "market",
                        "title": f"시장 트렌드: {trend['keyword']}",
                        "description": f"'{trend['keyword']}' 관련 상품의 수요가 {trend['growth_rate']:.1f}% 증가했습니다.",
                        "impact": "high",
                        "data": trend
                    })
                    
            # 경쟁사 동향
            competitor_analysis = await self._analyze_competitors(db, user_id, platform_ids)
            if competitor_analysis:
                insights.append({
                    "type": "info",
                    "category": "market",
                    "title": "경쟁사 가격 동향",
                    "description": "주요 경쟁 상품의 가격 변화를 확인하세요.",
                    "impact": "medium",
                    "data": competitor_analysis
                })
                
            return insights
            
        except Exception as e:
            logger.error(f"시장 인사이트 생성 실패: {str(e)}")
            return []
            
    async def _generate_action_items(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """실행 가능한 액션 아이템 생성"""
        try:
            action_items = []
            
            # 재고 보충 필요
            restock_items = await self._get_restock_recommendations(db, user_id, platform_ids)
            for item in restock_items[:3]:
                action_items.append({
                    "priority": "high",
                    "type": "restock",
                    "title": f"{item['product_name']} 재고 보충 필요",
                    "description": f"현재 재고: {item['current_stock']}개, 권장 주문량: {item['recommended_order']}개",
                    "action": "order_inventory",
                    "data": item
                })
                
            # 가격 조정 추천
            price_adjustments = await self._get_price_adjustment_recommendations(db, user_id, platform_ids)
            for item in price_adjustments[:2]:
                action_items.append({
                    "priority": "medium",
                    "type": "price_optimization",
                    "title": f"{item['product_name']} 가격 조정 추천",
                    "description": f"현재 가격: {item['current_price']:,}원 → 권장 가격: {item['recommended_price']:,}원",
                    "action": "update_price",
                    "data": item
                })
                
            # 프로모션 기회
            promotion_opportunities = await self._find_promotion_opportunities(db, user_id, platform_ids)
            for opp in promotion_opportunities[:2]:
                action_items.append({
                    "priority": "medium",
                    "type": "promotion",
                    "title": f"{opp['platform']} 프로모션 참여 추천",
                    "description": opp['description'],
                    "action": "create_promotion",
                    "data": opp
                })
                
            # 우선순위 정렬
            action_items.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])
            
            return action_items
            
        except Exception as e:
            logger.error(f"액션 아이템 생성 실패: {str(e)}")
            return []
            
    async def predict_sales(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]] = None,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """매출 예측"""
        try:
            # 과거 데이터 조회 (최근 90일)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            query = db.query(
                func.date(Order.created_at).label('date'),
                func.sum(OrderItem.price * OrderItem.quantity).label('daily_sales')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            results = query.group_by('date').order_by('date').all()
            
            if len(results) < 30:
                # 데이터 부족
                return {
                    "error": "예측을 위한 충분한 데이터가 없습니다.",
                    "required_days": 30,
                    "available_days": len(results)
                }
                
            # 시계열 데이터 준비
            df = pd.DataFrame(results)
            df['date'] = pd.to_datetime(df['date'])
            df['daily_sales'] = df['daily_sales'].astype(float)
            
            # 특성 엔지니어링
            df['day_of_week'] = df['date'].dt.dayofweek
            df['day_of_month'] = df['date'].dt.day
            df['month'] = df['date'].dt.month
            df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
            
            # 이동 평균 추가
            df['ma_7'] = df['daily_sales'].rolling(window=7, min_periods=1).mean()
            df['ma_30'] = df['daily_sales'].rolling(window=30, min_periods=1).mean()
            
            # 모델 학습
            features = ['days_since_start', 'day_of_week', 'day_of_month', 'month', 'ma_7', 'ma_30']
            X = df[features].fillna(0)
            y = df['daily_sales']
            
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = LinearRegression()
            model.fit(X_scaled, y)
            
            # 예측
            future_dates = pd.date_range(start=end_date + timedelta(days=1), periods=days_ahead)
            future_df = pd.DataFrame({'date': future_dates})
            
            # 미래 데이터 특성 생성
            future_df['day_of_week'] = future_df['date'].dt.dayofweek
            future_df['day_of_month'] = future_df['date'].dt.day
            future_df['month'] = future_df['date'].dt.month
            future_df['days_since_start'] = (future_df['date'] - df['date'].min()).dt.days
            
            # 이동 평균은 최근 값 사용
            future_df['ma_7'] = df['ma_7'].iloc[-1]
            future_df['ma_30'] = df['ma_30'].iloc[-1]
            
            X_future = future_df[features]
            X_future_scaled = scaler.transform(X_future)
            
            predictions = model.predict(X_future_scaled)
            
            # 신뢰 구간 계산 (간단한 방법)
            historical_std = df['daily_sales'].std()
            confidence_interval = 1.96 * historical_std  # 95% 신뢰구간
            
            # 결과 포맷팅
            forecast = []
            for i, date in enumerate(future_dates):
                forecast.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "predicted_sales": max(0, float(predictions[i])),
                    "lower_bound": max(0, float(predictions[i] - confidence_interval)),
                    "upper_bound": float(predictions[i] + confidence_interval)
                })
                
            # 예측 요약
            total_predicted = sum(p['predicted_sales'] for p in forecast)
            avg_predicted = total_predicted / days_ahead
            recent_avg = df['daily_sales'].tail(days_ahead).mean()
            
            return {
                "forecast": forecast,
                "summary": {
                    "total_predicted_sales": total_predicted,
                    "average_daily_sales": avg_predicted,
                    "growth_vs_recent": ((avg_predicted - recent_avg) / recent_avg * 100) if recent_avg > 0 else 0,
                    "confidence_level": 0.95,
                    "model_accuracy": model.score(X_scaled, y)
                },
                "period": {
                    "start": future_dates[0].strftime('%Y-%m-%d'),
                    "end": future_dates[-1].strftime('%Y-%m-%d'),
                    "days": days_ahead
                }
            }
            
        except Exception as e:
            logger.error(f"매출 예측 실패: {str(e)}")
            raise
            
    async def _analyze_sales_trend(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """매출 트렌드 분석"""
        try:
            # 최근 7일 vs 이전 7일 비교
            today = datetime.now()
            week_ago = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)
            
            # 최근 7일 매출
            recent_query = db.query(
                func.sum(OrderItem.price * OrderItem.quantity).label('total_sales')
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= week_ago,
                Order.created_at <= today,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                recent_query = recent_query.filter(Order.platform_id.in_(platform_ids))
                
            recent_sales = recent_query.scalar() or 0
            
            # 이전 7일 매출
            previous_query = db.query(
                func.sum(OrderItem.price * OrderItem.quantity).label('total_sales')
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= two_weeks_ago,
                Order.created_at < week_ago,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                previous_query = previous_query.filter(Order.platform_id.in_(platform_ids))
                
            previous_sales = previous_query.scalar() or 0
            
            # 트렌드 계산
            if previous_sales > 0:
                growth_rate = ((recent_sales - previous_sales) / previous_sales) * 100
            else:
                growth_rate = 100 if recent_sales > 0 else 0
                
            trend = "increasing" if growth_rate > 5 else "decreasing" if growth_rate < -5 else "stable"
            
            return {
                "trend": trend,
                "growth_rate": growth_rate,
                "recent_sales": float(recent_sales),
                "previous_sales": float(previous_sales)
            }
            
        except Exception as e:
            logger.error(f"매출 트렌드 분석 실패: {str(e)}")
            return {"trend": "unknown", "growth_rate": 0}
            
    async def _analyze_peak_hours(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """피크 시간대 분석"""
        try:
            today = datetime.now().date()
            
            query = db.query(
                func.extract('hour', Order.created_at).label('hour'),
                func.count(Order.id).label('order_count')
            ).filter(
                Order.user_id == user_id,
                func.date(Order.created_at) == today
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            results = query.group_by('hour').order_by(func.count(Order.id).desc()).all()
            
            if results:
                peak_hour = int(results[0].hour)
                return {
                    "peak_hour": peak_hour,
                    "order_count": results[0].order_count,
                    "hourly_distribution": [
                        {"hour": int(r.hour), "orders": r.order_count} 
                        for r in results
                    ]
                }
                
            return None
            
        except Exception as e:
            logger.error(f"피크 시간대 분석 실패: {str(e)}")
            return None
            
    async def _analyze_platform_performance(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """플랫폼별 성과 분석"""
        try:
            today = datetime.now().date()
            
            query = db.query(
                Platform.name,
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue')
            ).join(
                Order, Platform.id == Order.platform_id
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                func.date(Order.created_at) == today,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Platform.id.in_(platform_ids))
                
            results = query.group_by(Platform.name).order_by(
                func.sum(OrderItem.price * OrderItem.quantity).desc()
            ).all()
            
            if results:
                return {
                    "best_platform": results[0].name,
                    "best_platform_revenue": float(results[0].revenue),
                    "platform_breakdown": [
                        {"platform": r.name, "revenue": float(r.revenue)} 
                        for r in results
                    ]
                }
                
            return {"best_platform": None}
            
        except Exception as e:
            logger.error(f"플랫폼 성과 분석 실패: {str(e)}")
            return {"best_platform": None}
            
    async def _find_low_stock_products(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """재고 부족 상품 찾기"""
        try:
            query = db.query(
                Product.id,
                Product.name,
                Product.sku,
                Inventory.quantity,
                Inventory.min_quantity,
                Platform.name.label('platform_name')
            ).join(
                Inventory, Product.id == Inventory.product_id
            ).join(
                Platform, Inventory.platform_id == Platform.id
            ).filter(
                Product.user_id == user_id,
                Inventory.quantity <= Inventory.min_quantity,
                Inventory.is_active == True
            )
            
            if platform_ids:
                query = query.filter(Inventory.platform_id.in_(platform_ids))
                
            results = query.order_by(Inventory.quantity).limit(10).all()
            
            low_stock_products = []
            for r in results:
                low_stock_products.append({
                    "product_id": r.id,
                    "name": r.name,
                    "sku": r.sku,
                    "current_stock": r.quantity,
                    "min_stock": r.min_quantity,
                    "platform": r.platform_name,
                    "stock_percentage": round(r.quantity / r.min_quantity * 100, 1) if r.min_quantity > 0 else 0
                })
                
            return low_stock_products
            
        except Exception as e:
            logger.error(f"재고 부족 상품 조회 실패: {str(e)}")
            return []
            
    async def _analyze_inventory_turnover(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """재고 회전율 분석"""
        try:
            # 최근 30일 판매 데이터와 현재 재고 비교
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            query = db.query(
                Product.id,
                Product.name,
                Inventory.quantity.label('current_stock'),
                func.coalesce(func.sum(OrderItem.quantity), 0).label('units_sold')
            ).join(
                Inventory, Product.id == Inventory.product_id
            ).outerjoin(
                OrderItem, Product.id == OrderItem.product_id
            ).outerjoin(
                Order, and_(
                    OrderItem.order_id == Order.id,
                    Order.created_at >= thirty_days_ago,
                    Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
                )
            ).filter(
                Product.user_id == user_id,
                Inventory.is_active == True
            )
            
            if platform_ids:
                query = query.filter(Inventory.platform_id.in_(platform_ids))
                
            results = query.group_by(
                Product.id, Product.name, Inventory.quantity
            ).having(
                Inventory.quantity > 0
            ).all()
            
            slow_moving_products = []
            for r in results:
                if r.current_stock > 0:
                    # 월간 회전율 = 판매량 / 평균 재고
                    turnover_rate = (r.units_sold / r.current_stock) if r.current_stock > 0 else 0
                    
                    if turnover_rate < 0.5:  # 월 0.5회 미만 회전
                        slow_moving_products.append({
                            "product_id": r.id,
                            "name": r.name,
                            "current_stock": r.current_stock,
                            "units_sold_30d": int(r.units_sold),
                            "turnover_rate": round(turnover_rate, 2),
                            "estimated_days_to_sell": round(r.current_stock / (r.units_sold / 30), 0) if r.units_sold > 0 else 999
                        })
                        
            return {
                "slow_moving_products": slow_moving_products[:10],
                "total_slow_moving": len(slow_moving_products)
            }
            
        except Exception as e:
            logger.error(f"재고 회전율 분석 실패: {str(e)}")
            return {"slow_moving_products": [], "total_slow_moving": 0}
            
    async def _suggest_optimal_stock_levels(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """최적 재고 수준 제안"""
        try:
            # 간단한 재고 최적화 로직
            # 실제로는 더 복잡한 알고리즘 필요
            
            suggestions = []
            
            # 베스트셀러 상품의 재고 확인
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            query = db.query(
                Product.id,
                Product.name,
                Inventory.quantity.label('current_stock'),
                func.sum(OrderItem.quantity).label('units_sold'),
                func.avg(OrderItem.quantity).label('avg_order_size')
            ).join(
                Inventory, Product.id == Inventory.product_id
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Product.user_id == user_id,
                Order.created_at >= thirty_days_ago,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            results = query.group_by(
                Product.id, Product.name, Inventory.quantity
            ).having(
                func.sum(OrderItem.quantity) > 10  # 최소 10개 이상 판매된 상품
            ).order_by(
                func.sum(OrderItem.quantity).desc()
            ).limit(5).all()
            
            for r in results:
                # 일일 평균 판매량
                daily_sales = r.units_sold / 30
                
                # 권장 재고 = (일일 판매량 * 리드타임) + 안전재고
                lead_time = 7  # 평균 7일 리드타임 가정
                safety_stock = daily_sales * 3  # 3일치 안전재고
                
                optimal_stock = int((daily_sales * lead_time) + safety_stock)
                
                if abs(optimal_stock - r.current_stock) > r.current_stock * 0.2:  # 20% 이상 차이
                    suggestions.append({
                        "product_id": r.id,
                        "name": r.name,
                        "current_stock": r.current_stock,
                        "optimal_stock": optimal_stock,
                        "adjustment": optimal_stock - r.current_stock,
                        "daily_sales": round(daily_sales, 1)
                    })
                    
            return {
                "suggestions": suggestions,
                "methodology": "평균 일일 판매량 기반 최적화"
            }
            
        except Exception as e:
            logger.error(f"최적 재고 수준 제안 실패: {str(e)}")
            return None
            
    async def _find_trending_products(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """급상승 상품 찾기"""
        try:
            # 최근 7일 vs 이전 7일 비교
            today = datetime.now()
            week_ago = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)
            
            # 최근 7일 판매
            recent = db.query(
                Product.id,
                Product.name,
                func.sum(OrderItem.quantity).label('recent_sales')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Product.user_id == user_id,
                Order.created_at >= week_ago,
                Order.created_at <= today
            )
            
            if platform_ids:
                recent = recent.filter(Order.platform_id.in_(platform_ids))
                
            recent = recent.group_by(Product.id, Product.name).subquery()
            
            # 이전 7일 판매
            previous = db.query(
                Product.id,
                func.sum(OrderItem.quantity).label('previous_sales')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Product.user_id == user_id,
                Order.created_at >= two_weeks_ago,
                Order.created_at < week_ago
            )
            
            if platform_ids:
                previous = previous.filter(Order.platform_id.in_(platform_ids))
                
            previous = previous.group_by(Product.id).subquery()
            
            # 비교
            results = db.query(
                recent.c.id,
                recent.c.name,
                recent.c.recent_sales,
                func.coalesce(previous.c.previous_sales, 0).label('previous_sales')
            ).outerjoin(
                previous, recent.c.id == previous.c.id
            ).all()
            
            trending = []
            for r in results:
                if r.previous_sales > 0:
                    growth_rate = ((r.recent_sales - r.previous_sales) / r.previous_sales) * 100
                else:
                    growth_rate = 100 if r.recent_sales > 5 else 0
                    
                if growth_rate > 50:  # 50% 이상 성장
                    trending.append({
                        "product_id": r.id,
                        "name": r.name,
                        "recent_sales": int(r.recent_sales),
                        "previous_sales": int(r.previous_sales),
                        "growth_rate": round(growth_rate, 1)
                    })
                    
            return sorted(trending, key=lambda x: x['growth_rate'], reverse=True)[:5]
            
        except Exception as e:
            logger.error(f"급상승 상품 조회 실패: {str(e)}")
            return []
            
    async def _analyze_keyword_performance(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """키워드 성과 분석"""
        try:
            # 최근 7일 키워드 성과
            week_ago = datetime.now() - timedelta(days=7)
            
            query = db.query(
                KeywordPerformance.keyword,
                func.sum(KeywordPerformance.impressions).label('total_impressions'),
                func.sum(KeywordPerformance.clicks).label('total_clicks'),
                func.sum(KeywordPerformance.conversions).label('total_conversions')
            ).join(
                Product, KeywordPerformance.product_id == Product.id
            ).filter(
                Product.user_id == user_id,
                KeywordPerformance.date >= week_ago
            )
            
            if platform_ids:
                query = query.filter(KeywordPerformance.platform_id.in_(platform_ids))
                
            results = query.group_by(
                KeywordPerformance.keyword
            ).having(
                func.sum(KeywordPerformance.impressions) > 100  # 최소 노출 수
            ).order_by(
                func.sum(KeywordPerformance.conversions).desc()
            ).limit(10).all()
            
            top_keywords = []
            for r in results:
                ctr = (r.total_clicks / r.total_impressions * 100) if r.total_impressions > 0 else 0
                cvr = (r.total_conversions / r.total_clicks * 100) if r.total_clicks > 0 else 0
                
                top_keywords.append({
                    "keyword": r.keyword,
                    "impressions": r.total_impressions,
                    "clicks": r.total_clicks,
                    "conversions": r.total_conversions,
                    "ctr": round(ctr, 2),
                    "cvr": round(cvr, 2)
                })
                
            return {
                "top_keywords": top_keywords[:5],
                "total_keywords_analyzed": len(results)
            }
            
        except Exception as e:
            logger.error(f"키워드 성과 분석 실패: {str(e)}")
            return {"top_keywords": [], "total_keywords_analyzed": 0}
            
    async def _suggest_price_optimization(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """가격 최적화 제안"""
        try:
            # 간단한 가격 탄력성 분석
            suggestions = []
            
            # 최근 가격 변경 이력과 판매량 변화 분석
            # 실제로는 더 복잡한 알고리즘 필요
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"가격 최적화 제안 실패: {str(e)}")
            return []
            
    async def _analyze_market_trends(
        self,
        db: Session,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """시장 트렌드 분석"""
        try:
            # 최근 시장 트렌드 데이터
            week_ago = datetime.now() - timedelta(days=7)
            
            trends = db.query(
                MarketTrend
            ).filter(
                MarketTrend.created_at >= week_ago,
                MarketTrend.relevance_score > 0.7
            ).order_by(
                MarketTrend.growth_rate.desc()
            ).limit(5).all()
            
            trend_data = []
            for trend in trends:
                trend_data.append({
                    "keyword": trend.keyword,
                    "category": trend.category,
                    "growth_rate": trend.growth_rate,
                    "search_volume": trend.search_volume,
                    "competition": trend.competition_level
                })
                
            return trend_data
            
        except Exception as e:
            logger.error(f"시장 트렌드 분석 실패: {str(e)}")
            return []
            
    async def _analyze_competitors(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """경쟁사 분석"""
        try:
            # 실제로는 외부 API나 크롤링 데이터 활용
            # 여기서는 간단한 예시
            
            return {
                "price_trends": "경쟁사 평균 대비 5% 저렴",
                "market_share": "카테고리 내 3위"
            }
            
        except Exception as e:
            logger.error(f"경쟁사 분석 실패: {str(e)}")
            return None
            
    async def _get_restock_recommendations(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """재고 보충 추천"""
        try:
            # 재고 부족 상품 중 판매량이 높은 상품
            recommendations = []
            
            low_stock = await self._find_low_stock_products(db, user_id, platform_ids)
            
            for product in low_stock[:5]:
                # 일일 평균 판매량 계산
                thirty_days_ago = datetime.now() - timedelta(days=30)
                
                sales_query = db.query(
                    func.sum(OrderItem.quantity).label('total_sales')
                ).join(
                    Order, OrderItem.order_id == Order.id
                ).filter(
                    OrderItem.product_id == product['product_id'],
                    Order.created_at >= thirty_days_ago
                )
                
                result = sales_query.first()
                daily_sales = (result.total_sales or 0) / 30
                
                if daily_sales > 0:
                    # 권장 주문량 계산
                    lead_time = 7
                    safety_days = 5
                    recommended_order = int(daily_sales * (lead_time + safety_days))
                    
                    recommendations.append({
                        "product_id": product['product_id'],
                        "product_name": product['name'],
                        "current_stock": product['current_stock'],
                        "daily_sales": round(daily_sales, 1),
                        "days_until_stockout": int(product['current_stock'] / daily_sales) if daily_sales > 0 else 0,
                        "recommended_order": recommended_order
                    })
                    
            return sorted(recommendations, key=lambda x: x['days_until_stockout'])
            
        except Exception as e:
            logger.error(f"재고 보충 추천 실패: {str(e)}")
            return []
            
    async def _get_price_adjustment_recommendations(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """가격 조정 추천"""
        try:
            # 실제로는 경쟁사 가격, 수요 탄력성 등을 고려
            # 여기서는 간단한 예시
            
            recommendations = []
            
            # 판매량이 낮은 상품 중 가격이 높은 상품
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            query = db.query(
                Product.id,
                Product.name,
                Product.price,
                func.count(OrderItem.id).label('order_count')
            ).outerjoin(
                OrderItem, Product.id == OrderItem.product_id
            ).outerjoin(
                Order, and_(
                    OrderItem.order_id == Order.id,
                    Order.created_at >= thirty_days_ago
                )
            ).filter(
                Product.user_id == user_id
            )
            
            if platform_ids:
                query = query.join(
                    Inventory, Product.id == Inventory.product_id
                ).filter(
                    Inventory.platform_id.in_(platform_ids)
                )
                
            results = query.group_by(
                Product.id, Product.name, Product.price
            ).having(
                func.count(OrderItem.id) < 10  # 판매량이 적은 상품
            ).order_by(
                Product.price.desc()
            ).limit(10).all()
            
            for r in results:
                # 간단한 가격 조정 로직
                if r.order_count < 5:
                    discount_rate = 0.1  # 10% 할인
                else:
                    discount_rate = 0.05  # 5% 할인
                    
                recommended_price = int(r.price * (1 - discount_rate))
                
                recommendations.append({
                    "product_id": r.id,
                    "product_name": r.name,
                    "current_price": r.price,
                    "recommended_price": recommended_price,
                    "discount_percentage": int(discount_rate * 100),
                    "expected_sales_increase": "15-25%"  # 예상치
                })
                
            return recommendations[:5]
            
        except Exception as e:
            logger.error(f"가격 조정 추천 실패: {str(e)}")
            return []
            
    async def _find_promotion_opportunities(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """프로모션 기회 찾기"""
        try:
            opportunities = []
            
            # 플랫폼별 프로모션 기회
            # 실제로는 플랫폼 API에서 정보를 가져와야 함
            
            platforms = db.query(Platform).filter(
                Platform.user_id == user_id,
                Platform.is_active == True
            )
            
            if platform_ids:
                platforms = platforms.filter(Platform.id.in_(platform_ids))
                
            for platform in platforms.all():
                # 예시 프로모션
                if platform.type == "naver":
                    opportunities.append({
                        "platform": platform.name,
                        "type": "event",
                        "title": "네이버 쇼핑 라이브",
                        "description": "라이브 방송을 통한 판매 증대 기회",
                        "expected_benefit": "평균 매출 200% 증가",
                        "deadline": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                    })
                elif platform.type == "coupang":
                    opportunities.append({
                        "platform": platform.name,
                        "type": "discount",
                        "title": "쿠팡 로켓배송 할인",
                        "description": "로켓배송 상품 특별 할인 프로모션",
                        "expected_benefit": "주문량 150% 증가 예상",
                        "deadline": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
                    })
                    
            return opportunities
            
        except Exception as e:
            logger.error(f"프로모션 기회 찾기 실패: {str(e)}")
            return []