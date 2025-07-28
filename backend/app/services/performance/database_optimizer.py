"""
고성능 데이터베이스 최적화 시스템
N+1 쿼리 해결, Eager Loading, 쿼리 최적화
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Type, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy.sql.selectable import Select

from app.models.base import BaseModel
from app.models.product import Product, ProductVariant, PlatformListing
from app.models.order_core import Order, OrderItem
from app.models.user import User
from app.services.performance.cache_manager import cache_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """쿼리 성능 통계"""
    query_type: str
    execution_time: float
    affected_rows: int
    cache_hit: bool = False
    optimized: bool = False


class DatabaseOptimizer:
    """데이터베이스 성능 최적화"""
    
    def __init__(self):
        self.query_stats: List[QueryStats] = []
        self.cache_enabled = True
        self.eager_loading_enabled = True
        
    @asynccontextmanager
    async def track_query(self, query_type: str):
        """쿼리 실행 시간 추적"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.query_stats.append(QueryStats(
                query_type=query_type,
                execution_time=execution_time,
                affected_rows=0,  # 필요시 업데이트
                optimized=True
            ))
            
            if execution_time > 0.05:  # 50ms 이상 걸리는 쿼리 경고
                logger.warning(f"Slow query detected: {query_type} took {execution_time:.3f}s")
    
    async def get_orders_optimized(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """최적화된 주문 목록 조회 (N+1 문제 해결)"""
        
        cache_key = f"orders_optimized:{hash(str(filters))}:{page}:{page_size}"
        
        # 캐시 확인
        if self.cache_enabled:
            cached_result = cache_manager.get(cache_key, namespace="orders")
            if cached_result:
                return cached_result
        
        async with self.track_query("get_orders_optimized"):
            # 1. 단일 쿼리로 모든 관련 데이터 조회 (Eager Loading)
            query = (
                select(Order)
                .options(
                    selectinload(Order.order_items).selectinload(OrderItem.product),
                    joinedload(Order.customer) if hasattr(Order, 'customer') else None
                )
                .filter(self._build_order_filters(filters))
                .order_by(Order.created_at.desc())
            )
            
            # 2. 카운트 쿼리 최적화
            count_query = select(func.count()).select_from(Order).filter(
                self._build_order_filters(filters)
            )
            
            # 3. 병렬 실행
            count_task = db.execute(count_query)
            
            # 4. 페이지네이션
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # 5. 실행
            result = await db.execute(query)
            orders = result.scalars().all()
            
            total = await count_task
            total = total.scalar()
            
            # 6. 응답 구성 (메모리에서 처리)
            order_list = []
            for order in orders:
                # 이미 로드된 관계 사용 (추가 쿼리 없음)
                total_amount = sum(
                    float(item.price * item.quantity) 
                    for item in order.order_items
                )
                
                order_dict = {
                    "id": order.id,
                    "order_number": order.order_number,
                    "platform": order.platform_type,
                    "customer_name": order.customer_name,
                    "customer_phone": order.customer_phone,
                    "total_amount": total_amount,
                    "status": order.status.value,
                    "tracking_number": order.tracking_number,
                    "created_at": order.created_at.isoformat(),
                    "items_count": len(order.order_items),
                    "items": [
                        {
                            "product_name": item.product.name if item.product else "상품 정보 없음",
                            "quantity": item.quantity,
                            "price": float(item.price)
                        }
                        for item in order.order_items
                    ]
                }
                order_list.append(order_dict)
            
            result_data = {
                "items": order_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size
            }
            
            # 캐시 저장
            if self.cache_enabled:
                cache_manager.set(cache_key, result_data, ttl=300, namespace="orders")
            
            return result_data
    
    async def get_products_optimized(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        page: int = 1,
        page_size: int = 20,
        include_variants: bool = False,
        include_listings: bool = False
    ) -> Dict[str, Any]:
        """최적화된 상품 목록 조회"""
        
        cache_key = f"products_optimized:{hash(str(filters))}:{page}:{page_size}:{include_variants}:{include_listings}"
        
        # 캐시 확인
        if self.cache_enabled:
            cached_result = cache_manager.get(cache_key, namespace="products")
            if cached_result:
                return cached_result
        
        async with self.track_query("get_products_optimized"):
            # Eager Loading 옵션 구성
            options = []
            
            if include_variants:
                options.append(selectinload(Product.variants))
            
            if include_listings:
                options.append(
                    selectinload(Product.platform_listings)
                    .selectinload(PlatformListing.platform_account)
                )
            
            # 기본 관계 로딩
            options.extend([
                selectinload(Product.price_history),
                joinedload(Product.platform_account)
            ])
            
            # 메인 쿼리
            query = (
                select(Product)
                .options(*options)
                .filter(self._build_product_filters(filters))
                .order_by(Product.created_at.desc())
            )
            
            # 카운트 쿼리
            count_query = select(func.count()).select_from(Product).filter(
                self._build_product_filters(filters)
            )
            
            # 병렬 실행
            total = await db.scalar(count_query)
            
            # 페이지네이션
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            result = await db.execute(query)
            products = result.scalars().all()
            
            # 응답 구성
            product_list = []
            for product in products:
                product_dict = {
                    "id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "brand": product.brand,
                    "status": product.status.value,
                    "retail_price": float(product.retail_price) if product.retail_price else 0,
                    "stock_quantity": product.stock_quantity,
                    "is_low_stock": product.is_low_stock,
                    "created_at": product.created_at.isoformat(),
                }
                
                if include_variants and product.variants:
                    product_dict["variants"] = [
                        {
                            "id": str(variant.id),
                            "variant_sku": variant.variant_sku,
                            "name": variant.name,
                            "stock_quantity": variant.stock_quantity,
                            "sale_price": float(variant.sale_price) if variant.sale_price else 0
                        }
                        for variant in product.variants
                    ]
                
                if include_listings and product.platform_listings:
                    product_dict["platform_listings"] = [
                        {
                            "id": str(listing.id),
                            "platform": listing.platform_account.platform_type.value if listing.platform_account else "unknown",
                            "listed_price": float(listing.listed_price),
                            "is_published": listing.is_published,
                            "listing_status": listing.listing_status
                        }
                        for listing in product.platform_listings
                    ]
                
                product_list.append(product_dict)
            
            result_data = {
                "items": product_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size
            }
            
            # 캐시 저장
            if self.cache_enabled:
                cache_manager.set(cache_key, result_data, ttl=600, namespace="products")
            
            return result_data
    
    async def bulk_update_stock(
        self,
        db: AsyncSession,
        stock_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """배치 재고 업데이트 (성능 최적화)"""
        
        async with self.track_query("bulk_update_stock"):
            # 1. 모든 상품 ID 수집
            product_ids = [update["product_id"] for update in stock_updates]
            
            # 2. 단일 쿼리로 모든 상품 조회
            query = select(Product).where(Product.id.in_(product_ids))
            result = await db.execute(query)
            products = {str(p.id): p for p in result.scalars().all()}
            
            # 3. 메모리에서 업데이트
            updated_count = 0
            for update in stock_updates:
                product_id = str(update["product_id"])
                if product_id in products:
                    product = products[product_id]
                    product.stock_quantity = update["new_quantity"]
                    updated_count += 1
            
            # 4. 단일 커밋
            await db.commit()
            
            # 5. 캐시 무효화
            cache_manager.flush_namespace("products")
            
            return {
                "success": True,
                "updated_count": updated_count,
                "total_updates": len(stock_updates)
            }
    
    async def get_dashboard_analytics_optimized(
        self,
        db: AsyncSession,
        date_range: Dict[str, Any]
    ) -> Dict[str, Any]:
        """최적화된 대시보드 분석 데이터"""
        
        cache_key = f"dashboard_analytics:{hash(str(date_range))}"
        
        # 캐시 확인
        if self.cache_enabled:
            cached_result = cache_manager.get(cache_key, namespace="analytics")
            if cached_result:
                return cached_result
        
        async with self.track_query("get_dashboard_analytics"):
            # 병렬로 모든 분석 쿼리 실행
            tasks = await asyncio.gather(
                self._get_order_stats(db, date_range),
                self._get_product_stats(db, date_range),
                self._get_revenue_stats(db, date_range),
                self._get_platform_stats(db, date_range),
                return_exceptions=True
            )
            
            order_stats, product_stats, revenue_stats, platform_stats = tasks
            
            result_data = {
                "order_stats": order_stats if not isinstance(order_stats, Exception) else {},
                "product_stats": product_stats if not isinstance(product_stats, Exception) else {},
                "revenue_stats": revenue_stats if not isinstance(revenue_stats, Exception) else {},
                "platform_stats": platform_stats if not isinstance(platform_stats, Exception) else {},
                "generated_at": time.time()
            }
            
            # 캐시 저장 (5분)
            if self.cache_enabled:
                cache_manager.set(cache_key, result_data, ttl=300, namespace="analytics")
            
            return result_data
    
    def _build_order_filters(self, filters: Dict[str, Any]):
        """주문 필터 조건 빌드"""
        conditions = []
        
        if filters.get("status"):
            conditions.append(Order.status == filters["status"])
        
        if filters.get("platform"):
            conditions.append(Order.platform_type == filters["platform"])
        
        if filters.get("date_from"):
            conditions.append(Order.created_at >= filters["date_from"])
        
        if filters.get("date_to"):
            conditions.append(Order.created_at <= filters["date_to"])
        
        return and_(*conditions) if conditions else text("1=1")
    
    def _build_product_filters(self, filters: Dict[str, Any]):
        """상품 필터 조건 빌드"""
        conditions = []
        
        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            conditions.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.sku.ilike(search_term),
                    Product.description.ilike(search_term)
                )
            )
        
        if filters.get("status"):
            if isinstance(filters["status"], list):
                conditions.append(Product.status.in_(filters["status"]))
            else:
                conditions.append(Product.status == filters["status"])
        
        if filters.get("brand"):
            if isinstance(filters["brand"], list):
                conditions.append(Product.brand.in_(filters["brand"]))
            else:
                conditions.append(Product.brand == filters["brand"])
        
        if filters.get("min_price"):
            conditions.append(Product.retail_price >= filters["min_price"])
        
        if filters.get("max_price"):
            conditions.append(Product.retail_price <= filters["max_price"])
        
        if filters.get("low_stock"):
            conditions.append(Product.stock_quantity <= Product.min_stock_level)
        
        if filters.get("out_of_stock"):
            conditions.append(Product.stock_quantity == 0)
        
        return and_(*conditions) if conditions else text("1=1")
    
    async def _get_order_stats(self, db: AsyncSession, date_range: Dict[str, Any]) -> Dict[str, Any]:
        """주문 통계"""
        base_filter = self._build_date_filter("Order", date_range)
        
        # 집계 쿼리
        stats_query = select(
            func.count().label("total_orders"),
            func.sum(
                select(func.sum(OrderItem.price * OrderItem.quantity))
                .where(OrderItem.order_id == Order.id)
                .scalar_subquery()
            ).label("total_revenue"),
            func.avg(
                select(func.sum(OrderItem.price * OrderItem.quantity))
                .where(OrderItem.order_id == Order.id)
                .scalar_subquery()
            ).label("avg_order_value")
        ).where(base_filter)
        
        result = await db.execute(stats_query)
        row = result.first()
        
        return {
            "total_orders": row.total_orders or 0,
            "total_revenue": float(row.total_revenue or 0),
            "avg_order_value": float(row.avg_order_value or 0)
        }
    
    async def _get_product_stats(self, db: AsyncSession, date_range: Dict[str, Any]) -> Dict[str, Any]:
        """상품 통계"""
        base_filter = self._build_date_filter("Product", date_range)
        
        stats_query = select(
            func.count().label("total_products"),
            func.sum(Product.stock_quantity).label("total_stock"),
            func.count().filter(Product.stock_quantity <= Product.min_stock_level).label("low_stock_products"),
            func.count().filter(Product.stock_quantity == 0).label("out_of_stock_products")
        ).where(base_filter)
        
        result = await db.execute(stats_query)
        row = result.first()
        
        return {
            "total_products": row.total_products or 0,
            "total_stock": row.total_stock or 0,
            "low_stock_products": row.low_stock_products or 0,
            "out_of_stock_products": row.out_of_stock_products or 0
        }
    
    async def _get_revenue_stats(self, db: AsyncSession, date_range: Dict[str, Any]) -> Dict[str, Any]:
        """수익 통계"""
        # 일별 수익 추이
        daily_revenue_query = select(
            func.date(Order.created_at).label("date"),
            func.sum(
                select(func.sum(OrderItem.price * OrderItem.quantity))
                .where(OrderItem.order_id == Order.id)
                .scalar_subquery()
            ).label("revenue")
        ).where(
            self._build_date_filter("Order", date_range)
        ).group_by(func.date(Order.created_at)).order_by("date")
        
        result = await db.execute(daily_revenue_query)
        daily_trend = [
            {"date": row.date.isoformat(), "revenue": float(row.revenue or 0)}
            for row in result
        ]
        
        return {"daily_trend": daily_trend}
    
    async def _get_platform_stats(self, db: AsyncSession, date_range: Dict[str, Any]) -> Dict[str, Any]:
        """플랫폼별 통계"""
        platform_query = select(
            Order.platform_type,
            func.count().label("order_count"),
            func.sum(
                select(func.sum(OrderItem.price * OrderItem.quantity))
                .where(OrderItem.order_id == Order.id)
                .scalar_subquery()
            ).label("revenue")
        ).where(
            self._build_date_filter("Order", date_range)
        ).group_by(Order.platform_type)
        
        result = await db.execute(platform_query)
        platform_breakdown = {
            row.platform_type: {
                "order_count": row.order_count or 0,
                "revenue": float(row.revenue or 0)
            }
            for row in result
        }
        
        return {"platform_breakdown": platform_breakdown}
    
    def _build_date_filter(self, model_name: str, date_range: Dict[str, Any]):
        """날짜 필터 생성"""
        model_class = {
            "Order": Order,
            "Product": Product
        }.get(model_name)
        
        if not model_class:
            return text("1=1")
        
        conditions = []
        
        if date_range.get("start_date"):
            conditions.append(model_class.created_at >= date_range["start_date"])
        
        if date_range.get("end_date"):
            conditions.append(model_class.created_at <= date_range["end_date"])
        
        return and_(*conditions) if conditions else text("1=1")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        if not self.query_stats:
            return {"message": "No query statistics available"}
        
        total_queries = len(self.query_stats)
        avg_time = sum(stat.execution_time for stat in self.query_stats) / total_queries
        slow_queries = [stat for stat in self.query_stats if stat.execution_time > 0.05]
        
        return {
            "total_queries": total_queries,
            "average_execution_time": round(avg_time, 4),
            "slow_queries_count": len(slow_queries),
            "slow_queries": [
                {
                    "query_type": stat.query_type,
                    "execution_time": round(stat.execution_time, 4)
                }
                for stat in slow_queries
            ],
            "performance_score": min(10, max(1, 10 - (avg_time * 100)))
        }
    
    def clear_stats(self):
        """통계 초기화"""
        self.query_stats.clear()


# 글로벌 인스턴스
db_optimizer = DatabaseOptimizer()