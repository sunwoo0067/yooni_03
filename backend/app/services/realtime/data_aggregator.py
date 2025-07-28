"""
데이터 집계 서비스
실시간 대시보드를 위한 데이터 집계 및 최적화
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import asyncio
from collections import defaultdict
import numpy as np

from app.models.product import Product
from app.models.order_core import Order, OrderItem
from app.models.inventory import Inventory
from app.models.platform import Platform
from app.models.keyword import KeywordPerformance
from app.models.user import User
from app.services.cache_service import CacheService
from app.services.realtime.websocket_manager import connection_manager
from app.services.realtime.event_processor import event_processor, EventType
from app.core.logging import logger
from app.core.database import get_db


class DataAggregator:
    """데이터 집계 서비스"""
    
    def __init__(self):
        self.cache = CacheService()
        self.aggregation_intervals = {
            "realtime": 10,      # 10초
            "minute": 60,        # 1분
            "hourly": 3600,      # 1시간
            "daily": 86400       # 24시간
        }
        
    async def start_aggregation_tasks(self) -> None:
        """집계 작업 시작"""
        try:
            # 각 간격별로 집계 작업 시작
            tasks = [
                self._run_realtime_aggregation(),
                self._run_minute_aggregation(),
                self._run_hourly_aggregation(),
                self._run_daily_aggregation()
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"집계 작업 시작 실패: {str(e)}")
            
    async def _run_realtime_aggregation(self) -> None:
        """실시간 집계 (10초마다)"""
        while True:
            try:
                await self._aggregate_realtime_data()
                await asyncio.sleep(self.aggregation_intervals["realtime"])
            except Exception as e:
                logger.error(f"실시간 집계 실패: {str(e)}")
                await asyncio.sleep(60)  # 에러 시 1분 대기
                
    async def _run_minute_aggregation(self) -> None:
        """분 단위 집계"""
        while True:
            try:
                await self._aggregate_minute_data()
                await asyncio.sleep(self.aggregation_intervals["minute"])
            except Exception as e:
                logger.error(f"분 단위 집계 실패: {str(e)}")
                await asyncio.sleep(300)  # 에러 시 5분 대기
                
    async def _run_hourly_aggregation(self) -> None:
        """시간 단위 집계"""
        while True:
            try:
                await self._aggregate_hourly_data()
                await asyncio.sleep(self.aggregation_intervals["hourly"])
            except Exception as e:
                logger.error(f"시간 단위 집계 실패: {str(e)}")
                await asyncio.sleep(1800)  # 에러 시 30분 대기
                
    async def _run_daily_aggregation(self) -> None:
        """일 단위 집계"""
        while True:
            try:
                await self._aggregate_daily_data()
                await asyncio.sleep(self.aggregation_intervals["daily"])
            except Exception as e:
                logger.error(f"일 단위 집계 실패: {str(e)}")
                await asyncio.sleep(3600)  # 에러 시 1시간 대기
                
    async def _aggregate_realtime_data(self) -> None:
        """실시간 데이터 집계"""
        async for db in get_db():
            try:
                # 활성 사용자 목록 (현재 연결된 사용자)
                active_users = connection_manager.active_connections.keys()
                
                for user_id in active_users:
                    # 최근 10초간의 데이터 집계
                    now = datetime.now()
                    ten_seconds_ago = now - timedelta(seconds=10)
                    
                    # 실시간 매출
                    sales_data = await self._get_realtime_sales(
                        db, user_id, ten_seconds_ago, now
                    )
                    
                    # 실시간 주문
                    order_data = await self._get_realtime_orders(
                        db, user_id, ten_seconds_ago, now
                    )
                    
                    # 데이터 업데이트
                    if sales_data or order_data:
                        update_data = {
                            "sales": sales_data,
                            "orders": order_data,
                            "timestamp": now.isoformat()
                        }
                        
                        # WebSocket으로 푸시
                        await connection_manager.broadcast_dashboard_update(
                            user_id, "realtime", update_data
                        )
                        
                        # 캐시 업데이트
                        cache_key = f"realtime:dashboard:{user_id}"
                        await self.cache.set(cache_key, update_data, ttl=60)
                        
            except Exception as e:
                logger.error(f"실시간 데이터 집계 실패: {str(e)}")
                
    async def _aggregate_minute_data(self) -> None:
        """분 단위 데이터 집계"""
        async for db in get_db():
            try:
                # 모든 활성 사용자에 대해 집계
                users = db.query(User.id).filter(User.is_active == True).all()
                
                for user in users:
                    user_id = user.id
                    
                    # 최근 1분간의 데이터 집계
                    now = datetime.now()
                    one_minute_ago = now - timedelta(minutes=1)
                    
                    # 분당 매출/주문 추이
                    minute_stats = await self._calculate_minute_statistics(
                        db, user_id, one_minute_ago, now
                    )
                    
                    # 캐시 업데이트
                    cache_key = f"stats:minute:{user_id}:{now.strftime('%Y%m%d%H%M')}"
                    await self.cache.set(cache_key, minute_stats, ttl=3600)  # 1시간 보관
                    
                    # 이상 패턴 감지
                    anomalies = await self._detect_anomalies(minute_stats, "minute", user_id)
                    if anomalies:
                        await self._handle_anomalies(user_id, anomalies)
                        
            except Exception as e:
                logger.error(f"분 단위 데이터 집계 실패: {str(e)}")
                
    async def _aggregate_hourly_data(self) -> None:
        """시간 단위 데이터 집계"""
        async for db in get_db():
            try:
                # 현재 시간
                now = datetime.now()
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                previous_hour = current_hour - timedelta(hours=1)
                
                # 모든 활성 사용자에 대해 집계
                users = db.query(User.id).filter(User.is_active == True).all()
                
                for user in users:
                    user_id = user.id
                    
                    # 시간별 통계
                    hourly_stats = await self._calculate_hourly_statistics(
                        db, user_id, previous_hour, current_hour
                    )
                    
                    # 캐시 업데이트
                    cache_key = f"stats:hourly:{user_id}:{previous_hour.strftime('%Y%m%d%H')}"
                    await self.cache.set(cache_key, hourly_stats, ttl=86400)  # 24시간 보관
                    
                    # 시간별 리포트 생성
                    await self._generate_hourly_report(user_id, hourly_stats)
                    
                    # 트렌드 감지
                    trends = await self._detect_trends(hourly_stats, "hourly", user_id)
                    if trends:
                        await self._handle_trends(user_id, trends)
                        
            except Exception as e:
                logger.error(f"시간 단위 데이터 집계 실패: {str(e)}")
                
    async def _aggregate_daily_data(self) -> None:
        """일 단위 데이터 집계"""
        async for db in get_db():
            try:
                # 어제 날짜
                yesterday = datetime.now().date() - timedelta(days=1)
                start_date = datetime.combine(yesterday, datetime.min.time())
                end_date = datetime.combine(yesterday, datetime.max.time())
                
                # 모든 활성 사용자에 대해 집계
                users = db.query(User.id).filter(User.is_active == True).all()
                
                for user in users:
                    user_id = user.id
                    
                    # 일별 통계
                    daily_stats = await self._calculate_daily_statistics(
                        db, user_id, start_date, end_date
                    )
                    
                    # 캐시 업데이트 (장기 보관)
                    cache_key = f"stats:daily:{user_id}:{yesterday.strftime('%Y%m%d')}"
                    await self.cache.set(cache_key, daily_stats, ttl=2592000)  # 30일 보관
                    
                    # 일일 리포트 생성
                    await self._generate_daily_summary(user_id, daily_stats)
                    
                    # 주요 성과 지표 업데이트
                    await self._update_kpi_metrics(user_id, daily_stats)
                    
            except Exception as e:
                logger.error(f"일 단위 데이터 집계 실패: {str(e)}")
                
    async def _get_realtime_sales(
        self,
        db: Session,
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """실시간 매출 데이터"""
        try:
            result = db.query(
                func.sum(OrderItem.price * OrderItem.quantity).label('total'),
                func.count(Order.id).label('count')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_time,
                Order.created_at <= end_time,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            ).first()
            
            return {
                "total": float(result.total or 0),
                "count": result.count or 0,
                "period_seconds": 10
            }
            
        except Exception as e:
            logger.error(f"실시간 매출 조회 실패: {str(e)}")
            return {"total": 0, "count": 0, "period_seconds": 10}
            
    async def _get_realtime_orders(
        self,
        db: Session,
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """실시간 주문 데이터"""
        try:
            orders = db.query(Order).filter(
                Order.user_id == user_id,
                Order.created_at >= start_time,
                Order.created_at <= end_time
            ).order_by(Order.created_at.desc()).limit(10).all()
            
            order_list = []
            for order in orders:
                order_list.append({
                    "id": order.id,
                    "platform": order.platform.name if order.platform else "Unknown",
                    "status": order.status,
                    "total_amount": float(order.total_amount),
                    "created_at": order.created_at.isoformat()
                })
                
            return order_list
            
        except Exception as e:
            logger.error(f"실시간 주문 조회 실패: {str(e)}")
            return []
            
    async def _calculate_minute_statistics(
        self,
        db: Session,
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """분당 통계 계산"""
        try:
            # 매출 통계
            sales_stats = db.query(
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue'),
                func.count(Order.id).label('order_count'),
                func.avg(OrderItem.price * OrderItem.quantity).label('avg_order_value')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_time,
                Order.created_at <= end_time,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            ).first()
            
            # 플랫폼별 분포
            platform_stats = db.query(
                Platform.name,
                func.count(Order.id).label('count')
            ).join(
                Order, Platform.id == Order.platform_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_time,
                Order.created_at <= end_time
            ).group_by(Platform.name).all()
            
            return {
                "revenue": float(sales_stats.revenue or 0),
                "order_count": sales_stats.order_count or 0,
                "avg_order_value": float(sales_stats.avg_order_value or 0),
                "platform_distribution": {
                    p.name: p.count for p in platform_stats
                },
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"분당 통계 계산 실패: {str(e)}")
            return {}
            
    async def _calculate_hourly_statistics(
        self,
        db: Session,
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """시간별 통계 계산"""
        try:
            # 기본 통계
            stats = await self._calculate_minute_statistics(
                db, user_id, start_time, end_time
            )
            
            # 상품별 판매 TOP 10
            top_products = db.query(
                Product.name,
                Product.sku,
                func.sum(OrderItem.quantity).label('quantity'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_time,
                Order.created_at <= end_time,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            ).group_by(
                Product.name, Product.sku
            ).order_by(
                func.sum(OrderItem.price * OrderItem.quantity).desc()
            ).limit(10).all()
            
            stats["top_products"] = [
                {
                    "name": p.name,
                    "sku": p.sku,
                    "quantity": p.quantity,
                    "revenue": float(p.revenue)
                }
                for p in top_products
            ]
            
            # 재고 현황
            low_stock = db.query(
                func.count(Inventory.id).label('count')
            ).join(
                Product, Inventory.product_id == Product.id
            ).filter(
                Product.user_id == user_id,
                Inventory.quantity <= Inventory.min_quantity,
                Inventory.is_active == True
            ).scalar()
            
            stats["low_stock_count"] = low_stock or 0
            
            return stats
            
        except Exception as e:
            logger.error(f"시간별 통계 계산 실패: {str(e)}")
            return {}
            
    async def _calculate_daily_statistics(
        self,
        db: Session,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """일별 통계 계산"""
        try:
            # 시간별 통계 + 추가 분석
            stats = await self._calculate_hourly_statistics(
                db, user_id, start_date, end_date
            )
            
            # 시간대별 매출 분포
            hourly_sales = db.query(
                func.extract('hour', Order.created_at).label('hour'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            ).group_by('hour').all()
            
            stats["hourly_distribution"] = {
                int(h.hour): float(h.revenue) for h in hourly_sales
            }
            
            # 카테고리별 성과
            category_stats = db.query(
                Product.category,
                func.sum(OrderItem.quantity).label('quantity'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            ).group_by(Product.category).all()
            
            stats["category_performance"] = [
                {
                    "category": c.category,
                    "quantity": c.quantity,
                    "revenue": float(c.revenue)
                }
                for c in category_stats
            ]
            
            # 주문 처리 시간 분석
            processing_times = db.query(
                Order.status,
                func.avg(
                    func.extract('epoch', Order.updated_at - Order.created_at)
                ).label('avg_time')
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_(['processing', 'shipped', 'delivered'])
            ).group_by(Order.status).all()
            
            stats["processing_times"] = {
                p.status: round(p.avg_time / 3600, 1)  # 시간 단위
                for p in processing_times
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"일별 통계 계산 실패: {str(e)}")
            return {}
            
    async def _detect_anomalies(
        self,
        current_stats: Dict[str, Any],
        interval: str,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """이상 패턴 감지"""
        try:
            anomalies = []
            
            # 과거 데이터와 비교
            historical_data = await self._get_historical_data(user_id, interval, 10)
            
            if not historical_data:
                return anomalies
                
            # 통계적 이상치 감지
            revenues = [d.get("revenue", 0) for d in historical_data]
            if revenues:
                mean_revenue = np.mean(revenues)
                std_revenue = np.std(revenues)
                current_revenue = current_stats.get("revenue", 0)
                
                # Z-score 계산
                if std_revenue > 0:
                    z_score = (current_revenue - mean_revenue) / std_revenue
                    
                    # 이상치 판정 (Z-score > 3 또는 < -3)
                    if abs(z_score) > 3:
                        anomaly_type = "spike" if z_score > 0 else "drop"
                        anomalies.append({
                            "type": anomaly_type,
                            "metric": "revenue",
                            "value": current_revenue,
                            "expected": mean_revenue,
                            "z_score": z_score,
                            "severity": "high" if abs(z_score) > 4 else "medium"
                        })
                        
            # 주문 수 이상치 검사
            order_counts = [d.get("order_count", 0) for d in historical_data]
            if order_counts:
                mean_orders = np.mean(order_counts)
                current_orders = current_stats.get("order_count", 0)
                
                # 급격한 변화 감지
                if mean_orders > 0:
                    change_rate = (current_orders - mean_orders) / mean_orders
                    if abs(change_rate) > 0.5:  # 50% 이상 변화
                        anomalies.append({
                            "type": "order_anomaly",
                            "metric": "order_count",
                            "value": current_orders,
                            "expected": mean_orders,
                            "change_rate": change_rate,
                            "severity": "medium"
                        })
                        
            return anomalies
            
        except Exception as e:
            logger.error(f"이상 패턴 감지 실패: {str(e)}")
            return []
            
    async def _detect_trends(
        self,
        current_stats: Dict[str, Any],
        interval: str,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """트렌드 감지"""
        try:
            trends = []
            
            # 과거 데이터 조회
            historical_data = await self._get_historical_data(user_id, interval, 24)
            
            if len(historical_data) < 3:
                return trends
                
            # 매출 트렌드 분석
            revenues = [d.get("revenue", 0) for d in historical_data]
            revenues.append(current_stats.get("revenue", 0))
            
            # 이동 평균 계산
            if len(revenues) >= 3:
                ma_3 = np.mean(revenues[-3:])
                ma_12 = np.mean(revenues[-12:]) if len(revenues) >= 12 else ma_3
                
                # 상승/하락 트렌드 감지
                if ma_3 > ma_12 * 1.1:  # 10% 이상 상승
                    trends.append({
                        "type": "revenue_uptrend",
                        "strength": "strong" if ma_3 > ma_12 * 1.2 else "moderate",
                        "current_ma": ma_3,
                        "baseline_ma": ma_12,
                        "growth_rate": (ma_3 - ma_12) / ma_12
                    })
                elif ma_3 < ma_12 * 0.9:  # 10% 이상 하락
                    trends.append({
                        "type": "revenue_downtrend",
                        "strength": "strong" if ma_3 < ma_12 * 0.8 else "moderate",
                        "current_ma": ma_3,
                        "baseline_ma": ma_12,
                        "decline_rate": (ma_12 - ma_3) / ma_12
                    })
                    
            # 상품 트렌드 분석
            if "top_products" in current_stats:
                for product in current_stats["top_products"][:3]:
                    # 급상승 상품 감지
                    product_history = await self._get_product_history(
                        user_id, product["sku"], interval, 7
                    )
                    
                    if product_history:
                        avg_quantity = np.mean([p.get("quantity", 0) for p in product_history])
                        current_quantity = product["quantity"]
                        
                        if avg_quantity > 0 and current_quantity > avg_quantity * 1.5:
                            trends.append({
                                "type": "product_trending",
                                "product": product["name"],
                                "sku": product["sku"],
                                "current_sales": current_quantity,
                                "average_sales": avg_quantity,
                                "growth_rate": (current_quantity - avg_quantity) / avg_quantity
                            })
                            
            return trends
            
        except Exception as e:
            logger.error(f"트렌드 감지 실패: {str(e)}")
            return []
            
    async def _handle_anomalies(
        self,
        user_id: int,
        anomalies: List[Dict[str, Any]]
    ) -> None:
        """이상 패턴 처리"""
        try:
            for anomaly in anomalies:
                # 이벤트 생성
                event_data = {
                    "anomaly": anomaly,
                    "detected_at": datetime.now().isoformat()
                }
                
                # 심각도에 따른 처리
                if anomaly["severity"] == "high":
                    # 즉시 알림
                    notification = {
                        "type": "warning",
                        "title": "이상 패턴 감지",
                        "message": f"{anomaly['metric']}에서 비정상적인 {anomaly['type']}이 감지되었습니다.",
                        "data": anomaly,
                        "priority": "high"
                    }
                    
                    await connection_manager.send_notification(user_id, notification)
                    
                # 로그 기록
                logger.warning(f"이상 패턴 감지: user_id={user_id}, anomaly={anomaly}")
                
        except Exception as e:
            logger.error(f"이상 패턴 처리 실패: {str(e)}")
            
    async def _handle_trends(
        self,
        user_id: int,
        trends: List[Dict[str, Any]]
    ) -> None:
        """트렌드 처리"""
        try:
            for trend in trends:
                # 트렌드 타입별 처리
                if trend["type"] == "product_trending":
                    # 급상승 상품 이벤트
                    await event_processor.process_event(
                        EventType.PRODUCT_TRENDING,
                        user_id,
                        {"trending": trend},
                        None
                    )
                    
                elif trend["type"] in ["revenue_uptrend", "revenue_downtrend"]:
                    # 매출 트렌드 알림
                    trend_direction = "상승" if "uptrend" in trend["type"] else "하락"
                    notification = {
                        "type": "info",
                        "title": f"매출 {trend_direction} 트렌드",
                        "message": f"매출이 {trend_direction} 추세를 보이고 있습니다.",
                        "data": trend,
                        "priority": "medium"
                    }
                    
                    await connection_manager.send_notification(user_id, notification)
                    
        except Exception as e:
            logger.error(f"트렌드 처리 실패: {str(e)}")
            
    async def _generate_hourly_report(
        self,
        user_id: int,
        stats: Dict[str, Any]
    ) -> None:
        """시간별 리포트 생성"""
        try:
            # 간단한 시간별 요약 생성
            report = {
                "type": "hourly_summary",
                "stats": stats,
                "generated_at": datetime.now().isoformat()
            }
            
            # 캐시에 저장
            cache_key = f"report:hourly:{user_id}:{datetime.now().strftime('%Y%m%d%H')}"
            await self.cache.set(cache_key, report, ttl=86400)
            
        except Exception as e:
            logger.error(f"시간별 리포트 생성 실패: {str(e)}")
            
    async def _generate_daily_summary(
        self,
        user_id: int,
        stats: Dict[str, Any]
    ) -> None:
        """일일 요약 생성"""
        try:
            # 일일 요약 알림
            notification = {
                "type": "info",
                "title": "일일 판매 요약",
                "message": f"어제 총 매출: {stats.get('revenue', 0):,.0f}원, 주문: {stats.get('order_count', 0)}건",
                "data": stats,
                "priority": "low"
            }
            
            await connection_manager.send_notification(user_id, notification)
            
        except Exception as e:
            logger.error(f"일일 요약 생성 실패: {str(e)}")
            
    async def _update_kpi_metrics(
        self,
        user_id: int,
        daily_stats: Dict[str, Any]
    ) -> None:
        """KPI 지표 업데이트"""
        try:
            # 월간 KPI 계산
            today = datetime.now().date()
            month_start = today.replace(day=1)
            
            # 월간 누적 데이터 조회
            monthly_data = []
            for day in range(1, today.day + 1):
                date_str = f"{today.year}{today.month:02d}{day:02d}"
                cache_key = f"stats:daily:{user_id}:{date_str}"
                day_stats = await self.cache.get(cache_key)
                if day_stats:
                    monthly_data.append(day_stats)
                    
            # KPI 계산
            if monthly_data:
                total_revenue = sum(d.get("revenue", 0) for d in monthly_data)
                total_orders = sum(d.get("order_count", 0) for d in monthly_data)
                avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
                
                kpi_metrics = {
                    "monthly_revenue": total_revenue,
                    "monthly_orders": total_orders,
                    "average_order_value": avg_order_value,
                    "daily_average_revenue": total_revenue / len(monthly_data),
                    "best_day_revenue": max(d.get("revenue", 0) for d in monthly_data),
                    "updated_at": datetime.now().isoformat()
                }
                
                # KPI 캐시 업데이트
                cache_key = f"kpi:monthly:{user_id}:{today.strftime('%Y%m')}"
                await self.cache.set(cache_key, kpi_metrics, ttl=2592000)  # 30일
                
        except Exception as e:
            logger.error(f"KPI 지표 업데이트 실패: {str(e)}")
            
    async def _get_historical_data(
        self,
        user_id: int,
        interval: str,
        count: int
    ) -> List[Dict[str, Any]]:
        """과거 데이터 조회"""
        try:
            historical_data = []
            
            if interval == "minute":
                # 최근 N분 데이터
                now = datetime.now()
                for i in range(1, count + 1):
                    time_str = (now - timedelta(minutes=i)).strftime('%Y%m%d%H%M')
                    cache_key = f"stats:minute:{user_id}:{time_str}"
                    data = await self.cache.get(cache_key)
                    if data:
                        historical_data.append(data)
                        
            elif interval == "hourly":
                # 최근 N시간 데이터
                now = datetime.now()
                for i in range(1, count + 1):
                    time_str = (now - timedelta(hours=i)).strftime('%Y%m%d%H')
                    cache_key = f"stats:hourly:{user_id}:{time_str}"
                    data = await self.cache.get(cache_key)
                    if data:
                        historical_data.append(data)
                        
            return historical_data
            
        except Exception as e:
            logger.error(f"과거 데이터 조회 실패: {str(e)}")
            return []
            
    async def _get_product_history(
        self,
        user_id: int,
        sku: str,
        interval: str,
        days: int
    ) -> List[Dict[str, Any]]:
        """상품 판매 이력 조회"""
        try:
            # 캐시에서 상품별 데이터 조회
            # 실제로는 더 정교한 상품별 추적 필요
            return []
            
        except Exception as e:
            logger.error(f"상품 이력 조회 실패: {str(e)}")
            return []


# 전역 데이터 집계기 인스턴스
data_aggregator = DataAggregator()