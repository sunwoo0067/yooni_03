"""
대시보드 데이터 서비스
실시간 매출, 주문, 재고 현황 데이터 제공
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import asyncio
from decimal import Decimal

from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.inventory import Inventory
from app.models.platform import Platform
from app.models.keyword import KeywordPerformance
from app.core.database import get_db
from app.services.cache_service import CacheService
from app.core.logging import logger


class DashboardService:
    """대시보드 데이터 서비스"""
    
    def __init__(self):
        self.cache = CacheService()
        self.cache_ttl = 60  # 1분 캐시
        
    async def get_overview(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]] = None,
        date_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """대시보드 개요 데이터 조회"""
        try:
            # 캐시 키 생성
            cache_key = f"dashboard:overview:{user_id}:{platform_ids}:{date_range}"
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data
                
            # 날짜 범위 설정
            if not date_range:
                end_date = datetime.now()
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                date_range = {"start": start_date, "end": end_date}
                
            # 병렬로 데이터 조회
            tasks = [
                self._get_sales_summary(db, user_id, platform_ids, date_range),
                self._get_order_summary(db, user_id, platform_ids, date_range),
                self._get_inventory_summary(db, user_id, platform_ids),
                self._get_top_products(db, user_id, platform_ids, date_range),
                self._get_platform_performance(db, user_id, platform_ids, date_range)
            ]
            
            results = await asyncio.gather(*tasks)
            
            overview_data = {
                "sales": results[0],
                "orders": results[1],
                "inventory": results[2],
                "top_products": results[3],
                "platform_performance": results[4],
                "last_updated": datetime.now().isoformat()
            }
            
            # 캐시 저장
            await self.cache.set(cache_key, overview_data, self.cache_ttl)
            
            return overview_data
            
        except Exception as e:
            logger.error(f"대시보드 개요 조회 실패: {str(e)}")
            raise
            
    async def _get_sales_summary(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """매출 요약 데이터"""
        try:
            # 기본 쿼리
            query = db.query(
                func.sum(OrderItem.price * OrderItem.quantity).label('total_sales'),
                func.count(Order.id).label('order_count'),
                func.avg(OrderItem.price * OrderItem.quantity).label('avg_order_value')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            result = query.first()
            
            # 전일 대비 비교
            yesterday_range = {
                "start": date_range["start"] - timedelta(days=1),
                "end": date_range["end"] - timedelta(days=1)
            }
            
            yesterday_query = db.query(
                func.sum(OrderItem.price * OrderItem.quantity).label('total_sales')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= yesterday_range["start"],
                Order.created_at <= yesterday_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                yesterday_query = yesterday_query.filter(Order.platform_id.in_(platform_ids))
                
            yesterday_result = yesterday_query.first()
            
            # 성장률 계산
            growth_rate = 0
            if yesterday_result.total_sales and result.total_sales:
                growth_rate = ((result.total_sales - yesterday_result.total_sales) / 
                             yesterday_result.total_sales * 100)
                
            return {
                "total_sales": float(result.total_sales or 0),
                "order_count": result.order_count or 0,
                "avg_order_value": float(result.avg_order_value or 0),
                "growth_rate": float(growth_rate),
                "currency": "KRW"
            }
            
        except Exception as e:
            logger.error(f"매출 요약 조회 실패: {str(e)}")
            return {
                "total_sales": 0,
                "order_count": 0,
                "avg_order_value": 0,
                "growth_rate": 0,
                "currency": "KRW"
            }
            
    async def _get_order_summary(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """주문 요약 데이터"""
        try:
            # 상태별 주문 수
            status_query = db.query(
                Order.status,
                func.count(Order.id).label('count')
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"]
            )
            
            if platform_ids:
                status_query = status_query.filter(Order.platform_id.in_(platform_ids))
                
            status_results = status_query.group_by(Order.status).all()
            
            status_summary = {
                "pending": 0,
                "processing": 0,
                "shipped": 0,
                "delivered": 0,
                "cancelled": 0
            }
            
            for status, count in status_results:
                if status in status_summary:
                    status_summary[status] = count
                    
            # 평균 처리 시간 계산
            processing_time_query = db.query(
                func.avg(
                    func.extract('epoch', Order.updated_at - Order.created_at)
                ).label('avg_processing_time')
            ).filter(
                Order.user_id == user_id,
                Order.status == 'processing',
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"]
            )
            
            if platform_ids:
                processing_time_query = processing_time_query.filter(
                    Order.platform_id.in_(platform_ids)
                )
                
            processing_time_result = processing_time_query.first()
            avg_processing_time = processing_time_result.avg_processing_time or 0
            
            return {
                "status_summary": status_summary,
                "total_orders": sum(status_summary.values()),
                "avg_processing_time_hours": round(avg_processing_time / 3600, 1),
                "pending_orders": status_summary["pending"],
                "processing_rate": round(
                    (status_summary["processing"] + status_summary["shipped"] + 
                     status_summary["delivered"]) / sum(status_summary.values()) * 100
                    if sum(status_summary.values()) > 0 else 0, 1
                )
            }
            
        except Exception as e:
            logger.error(f"주문 요약 조회 실패: {str(e)}")
            return {
                "status_summary": {},
                "total_orders": 0,
                "avg_processing_time_hours": 0,
                "pending_orders": 0,
                "processing_rate": 0
            }
            
    async def _get_inventory_summary(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        """재고 요약 데이터"""
        try:
            # 재고 현황
            inventory_query = db.query(
                func.count(Inventory.id).label('total_skus'),
                func.sum(Inventory.quantity).label('total_quantity'),
                func.sum(
                    func.case(
                        (Inventory.quantity == 0, 1),
                        else_=0
                    )
                ).label('out_of_stock'),
                func.sum(
                    func.case(
                        (Inventory.quantity <= Inventory.min_quantity, 1),
                        else_=0
                    )
                ).label('low_stock')
            ).join(
                Product, Inventory.product_id == Product.id
            ).filter(
                Product.user_id == user_id,
                Inventory.is_active == True
            )
            
            if platform_ids:
                inventory_query = inventory_query.filter(
                    Inventory.platform_id.in_(platform_ids)
                )
                
            result = inventory_query.first()
            
            # 재고 가치 계산
            value_query = db.query(
                func.sum(Inventory.quantity * Product.cost).label('inventory_value')
            ).join(
                Product, Inventory.product_id == Product.id
            ).filter(
                Product.user_id == user_id,
                Inventory.is_active == True
            )
            
            if platform_ids:
                value_query = value_query.filter(
                    Inventory.platform_id.in_(platform_ids)
                )
                
            value_result = value_query.first()
            
            return {
                "total_skus": result.total_skus or 0,
                "total_quantity": result.total_quantity or 0,
                "out_of_stock": result.out_of_stock or 0,
                "low_stock": result.low_stock or 0,
                "inventory_value": float(value_result.inventory_value or 0),
                "stock_health_score": self._calculate_stock_health_score(result)
            }
            
        except Exception as e:
            logger.error(f"재고 요약 조회 실패: {str(e)}")
            return {
                "total_skus": 0,
                "total_quantity": 0,
                "out_of_stock": 0,
                "low_stock": 0,
                "inventory_value": 0,
                "stock_health_score": 0
            }
            
    async def _get_top_products(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """베스트셀러 상품"""
        try:
            query = db.query(
                Product.id,
                Product.name,
                Product.sku,
                func.sum(OrderItem.quantity).label('total_quantity'),
                func.sum(OrderItem.price * OrderItem.quantity).label('total_revenue')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Product.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            results = query.group_by(
                Product.id, Product.name, Product.sku
            ).order_by(
                func.sum(OrderItem.price * OrderItem.quantity).desc()
            ).limit(limit).all()
            
            top_products = []
            for product in results:
                top_products.append({
                    "product_id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "quantity_sold": product.total_quantity,
                    "revenue": float(product.total_revenue),
                    "rank": len(top_products) + 1
                })
                
            return top_products
            
        except Exception as e:
            logger.error(f"베스트셀러 조회 실패: {str(e)}")
            return []
            
    async def _get_platform_performance(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> List[Dict[str, Any]]:
        """플랫폼별 성과"""
        try:
            query = db.query(
                Platform.id,
                Platform.name,
                Platform.type,
                func.count(Order.id).label('order_count'),
                func.sum(OrderItem.price * OrderItem.quantity).label('total_revenue')
            ).join(
                Order, Platform.id == Order.platform_id
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Platform.id.in_(platform_ids))
                
            results = query.group_by(
                Platform.id, Platform.name, Platform.type
            ).all()
            
            platform_performance = []
            total_revenue = sum(p.total_revenue or 0 for p in results)
            
            for platform in results:
                revenue = float(platform.total_revenue or 0)
                platform_performance.append({
                    "platform_id": platform.id,
                    "name": platform.name,
                    "type": platform.type,
                    "order_count": platform.order_count,
                    "revenue": revenue,
                    "revenue_share": round(revenue / total_revenue * 100, 1) if total_revenue > 0 else 0
                })
                
            return platform_performance
            
        except Exception as e:
            logger.error(f"플랫폼 성과 조회 실패: {str(e)}")
            return []
            
    def _calculate_stock_health_score(self, inventory_data) -> float:
        """재고 건전성 점수 계산"""
        try:
            if not inventory_data.total_skus:
                return 0
                
            # 품절 비율 (낮을수록 좋음)
            out_of_stock_ratio = (inventory_data.out_of_stock or 0) / inventory_data.total_skus
            
            # 재고 부족 비율 (낮을수록 좋음)
            low_stock_ratio = (inventory_data.low_stock or 0) / inventory_data.total_skus
            
            # 점수 계산 (100점 만점)
            score = 100 - (out_of_stock_ratio * 50) - (low_stock_ratio * 30)
            
            return max(0, min(100, score))
            
        except Exception:
            return 0
            
    async def get_sales_analytics(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]] = None,
        date_range: Optional[Dict[str, datetime]] = None,
        group_by: str = "hour"  # hour, day, week, month
    ) -> Dict[str, Any]:
        """매출 분석 데이터"""
        try:
            # 날짜 범위 설정
            if not date_range:
                end_date = datetime.now()
                if group_by == "hour":
                    start_date = end_date - timedelta(days=1)
                elif group_by == "day":
                    start_date = end_date - timedelta(days=30)
                elif group_by == "week":
                    start_date = end_date - timedelta(days=90)
                else:  # month
                    start_date = end_date - timedelta(days=365)
                date_range = {"start": start_date, "end": end_date}
                
            # 시간 단위별 집계
            time_format = self._get_time_format(group_by)
            
            query = db.query(
                func.to_char(Order.created_at, time_format).label('time_period'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue'),
                func.count(Order.id).label('order_count')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            results = query.group_by('time_period').order_by('time_period').all()
            
            # 데이터 포맷팅
            time_series = []
            for result in results:
                time_series.append({
                    "period": result.time_period,
                    "revenue": float(result.revenue or 0),
                    "order_count": result.order_count
                })
                
            # 통계 계산
            revenues = [r.revenue for r in results if r.revenue]
            total_revenue = sum(revenues)
            avg_revenue = total_revenue / len(revenues) if revenues else 0
            
            return {
                "time_series": time_series,
                "summary": {
                    "total_revenue": total_revenue,
                    "average_revenue": avg_revenue,
                    "peak_revenue": max(revenues) if revenues else 0,
                    "total_orders": sum(r.order_count for r in results)
                },
                "group_by": group_by
            }
            
        except Exception as e:
            logger.error(f"매출 분석 조회 실패: {str(e)}")
            raise
            
    def _get_time_format(self, group_by: str) -> str:
        """시간 그룹 포맷"""
        formats = {
            "hour": "YYYY-MM-DD HH24:00",
            "day": "YYYY-MM-DD",
            "week": "YYYY-WW",
            "month": "YYYY-MM"
        }
        return formats.get(group_by, "YYYY-MM-DD")
        
    async def get_order_analytics(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]] = None,
        date_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """주문 분석 데이터"""
        try:
            if not date_range:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                date_range = {"start": start_date, "end": end_date}
                
            # 시간대별 주문 패턴
            hourly_query = db.query(
                func.extract('hour', Order.created_at).label('hour'),
                func.count(Order.id).label('order_count')
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"]
            )
            
            if platform_ids:
                hourly_query = hourly_query.filter(Order.platform_id.in_(platform_ids))
                
            hourly_results = hourly_query.group_by('hour').all()
            
            # 요일별 주문 패턴
            daily_query = db.query(
                func.extract('dow', Order.created_at).label('day_of_week'),
                func.count(Order.id).label('order_count')
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"]
            )
            
            if platform_ids:
                daily_query = daily_query.filter(Order.platform_id.in_(platform_ids))
                
            daily_results = daily_query.group_by('day_of_week').all()
            
            # 배송 시간 분석
            delivery_query = db.query(
                func.avg(
                    func.extract('epoch', Order.updated_at - Order.created_at)
                ).label('avg_delivery_time')
            ).filter(
                Order.user_id == user_id,
                Order.status == 'delivered',
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"]
            )
            
            if platform_ids:
                delivery_query = delivery_query.filter(Order.platform_id.in_(platform_ids))
                
            delivery_result = delivery_query.first()
            
            return {
                "hourly_pattern": [
                    {"hour": h.hour, "orders": h.order_count} 
                    for h in hourly_results
                ],
                "daily_pattern": [
                    {"day": self._get_day_name(d.day_of_week), "orders": d.order_count} 
                    for d in daily_results
                ],
                "average_delivery_days": round(
                    (delivery_result.avg_delivery_time or 0) / 86400, 1
                )
            }
            
        except Exception as e:
            logger.error(f"주문 분석 조회 실패: {str(e)}")
            raise
            
    def _get_day_name(self, day_number: int) -> str:
        """요일 이름 반환"""
        days = ["일", "월", "화", "수", "목", "금", "토"]
        return days[int(day_number)]
        
    async def get_product_performance(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]] = None,
        date_range: Optional[Dict[str, datetime]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """상품 성과 분석"""
        try:
            if not date_range:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                date_range = {"start": start_date, "end": end_date}
                
            # 상품별 성과
            product_query = db.query(
                Product.id,
                Product.name,
                Product.sku,
                Product.category,
                func.sum(OrderItem.quantity).label('quantity_sold'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue'),
                func.avg(OrderItem.price).label('avg_price'),
                func.count(func.distinct(Order.id)).label('order_count')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Product.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                product_query = product_query.filter(Order.platform_id.in_(platform_ids))
                
            product_results = product_query.group_by(
                Product.id, Product.name, Product.sku, Product.category
            ).order_by(
                func.sum(OrderItem.price * OrderItem.quantity).desc()
            ).limit(limit).all()
            
            # 카테고리별 성과
            category_query = db.query(
                Product.category,
                func.sum(OrderItem.quantity).label('quantity_sold'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).filter(
                Product.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                category_query = category_query.filter(Order.platform_id.in_(platform_ids))
                
            category_results = category_query.group_by(Product.category).all()
            
            # 데이터 포맷팅
            products = []
            for p in product_results:
                products.append({
                    "product_id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "category": p.category,
                    "quantity_sold": p.quantity_sold,
                    "revenue": float(p.revenue),
                    "avg_price": float(p.avg_price),
                    "order_count": p.order_count,
                    "conversion_rate": self._calculate_conversion_rate(p)
                })
                
            categories = []
            total_category_revenue = sum(c.revenue or 0 for c in category_results)
            for c in category_results:
                revenue = float(c.revenue or 0)
                categories.append({
                    "category": c.category,
                    "quantity_sold": c.quantity_sold,
                    "revenue": revenue,
                    "revenue_share": round(revenue / total_category_revenue * 100, 1) if total_category_revenue > 0 else 0
                })
                
            return {
                "products": products,
                "categories": categories,
                "total_products": len(products),
                "date_range": {
                    "start": date_range["start"].isoformat(),
                    "end": date_range["end"].isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"상품 성과 조회 실패: {str(e)}")
            raise
            
    def _calculate_conversion_rate(self, product_data) -> float:
        """전환율 계산 (임시)"""
        # 실제로는 조회수 대비 구매수로 계산해야 함
        # 현재는 임의의 값 반환
        return round(product_data.order_count / 100 * 100, 1) if product_data.order_count else 0