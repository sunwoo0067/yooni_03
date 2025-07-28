"""
Operations Dashboard Service
Handles all dashboard-related business logic
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, distinct, case
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
from collections import defaultdict
import pandas as pd
import io
import uuid

from app.models.order_core import Order, OrderStatus
from app.models.product import Product
from app.models.platform_account import PlatformAccount, PlatformType
from app.models.user import User
from app.models.ai_log import AILog
from app.models.inventory import Inventory
from app.models.collected_product import CollectedProduct
from app.core.config import settings
from app.services.monitoring.metrics_collector import MetricsCollector
from app.services.monitoring.health_checker import HealthChecker
from app.services.monitoring.alert_manager import AlertManager
from app.services.cache.cache_service import CacheService
from app.schemas.dashboard import (
    DashboardMetrics,
    SystemHealth,
    BusinessMetrics,
    PerformanceMetrics,
    AlertResponse,
    LogEntry,
    RealtimeMetrics
)

class OperationsDashboardService:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self.cache_service = CacheService()
        self.redis_client = None
        
    async def _get_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
        
    async def get_dashboard_metrics(
        self,
        db: AsyncSession,
        period: str,
        user_id: int
    ) -> DashboardMetrics:
        """Get comprehensive dashboard metrics"""
        # Calculate time range
        now = datetime.utcnow()
        period_map = {
            "1h": timedelta(hours=1),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        start_date = now - period_map.get(period, timedelta(days=1))
        
        # Get various metrics in parallel
        tasks = [
            self._get_order_metrics(db, start_date, now, user_id),
            self._get_product_metrics(db, start_date, now, user_id),
            self._get_revenue_metrics(db, start_date, now, user_id),
            self._get_platform_metrics(db, start_date, now, user_id),
            self._get_ai_usage_metrics(db, start_date, now, user_id),
            self._get_inventory_metrics(db, user_id),
            self._get_error_rate(start_date, now),
            self._get_api_performance_metrics(start_date, now)
        ]
        
        results = await asyncio.gather(*tasks)
        
        return DashboardMetrics(
            period=period,
            timestamp=now,
            orders=results[0],
            products=results[1],
            revenue=results[2],
            platforms=results[3],
            ai_usage=results[4],
            inventory=results[5],
            error_rate=results[6],
            api_performance=results[7],
            alerts_count=await self.alert_manager.get_active_alerts_count()
        )
        
    async def _get_order_metrics(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> Dict[str, Any]:
        """Get order-related metrics"""
        # Total orders
        total_query = select(func.count(Order.id)).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        total_result = await db.execute(total_query)
        total_orders = total_result.scalar() or 0
        
        # Orders by status
        status_query = select(
            Order.status,
            func.count(Order.id)
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        ).group_by(Order.status)
        
        status_result = await db.execute(status_query)
        orders_by_status = {row[0]: row[1] for row in status_result}
        
        # Calculate growth rate
        prev_start = start_date - (end_date - start_date)
        prev_query = select(func.count(Order.id)).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= prev_start,
                Order.created_at < start_date
            )
        )
        prev_result = await db.execute(prev_query)
        prev_orders = prev_result.scalar() or 0
        
        growth_rate = 0
        if prev_orders > 0:
            growth_rate = ((total_orders - prev_orders) / prev_orders) * 100
            
        return {
            "total": total_orders,
            "by_status": orders_by_status,
            "growth_rate": round(growth_rate, 2),
            "pending": orders_by_status.get(OrderStatus.PENDING, 0),
            "processing": orders_by_status.get(OrderStatus.PROCESSING, 0),
            "shipped": orders_by_status.get(OrderStatus.SHIPPED, 0),
            "delivered": orders_by_status.get(OrderStatus.DELIVERED, 0),
            "cancelled": orders_by_status.get(OrderStatus.CANCELLED, 0)
        }
        
    async def _get_product_metrics(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> Dict[str, Any]:
        """Get product-related metrics"""
        # Active products
        active_query = select(func.count(Product.id)).where(
            and_(
                Product.user_id == user_id,
                Product.is_active == True
            )
        )
        active_result = await db.execute(active_query)
        active_products = active_result.scalar() or 0
        
        # New products in period
        new_query = select(func.count(Product.id)).where(
            and_(
                Product.user_id == user_id,
                Product.created_at >= start_date,
                Product.created_at <= end_date
            )
        )
        new_result = await db.execute(new_query)
        new_products = new_result.scalar() or 0
        
        # Out of stock products
        oos_query = select(func.count(distinct(Product.id))).select_from(
            Product
        ).join(
            Inventory
        ).where(
            and_(
                Product.user_id == user_id,
                Product.is_active == True,
                Inventory.available_quantity <= 0
            )
        )
        oos_result = await db.execute(oos_query)
        out_of_stock = oos_result.scalar() or 0
        
        # Low stock products (< 10 units)
        low_stock_query = select(func.count(distinct(Product.id))).select_from(
            Product
        ).join(
            Inventory
        ).where(
            and_(
                Product.user_id == user_id,
                Product.is_active == True,
                Inventory.available_quantity > 0,
                Inventory.available_quantity < 10
            )
        )
        low_stock_result = await db.execute(low_stock_query)
        low_stock = low_stock_result.scalar() or 0
        
        return {
            "active": active_products,
            "new": new_products,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "total": active_products
        }
        
    async def _get_revenue_metrics(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> Dict[str, Any]:
        """Get revenue-related metrics"""
        # Total revenue
        revenue_query = select(
            func.sum(Order.total_amount)
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_([
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        )
        revenue_result = await db.execute(revenue_query)
        total_revenue = float(revenue_result.scalar() or 0)
        
        # Average order value
        aov_query = select(
            func.avg(Order.total_amount)
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_([
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        )
        aov_result = await db.execute(aov_query)
        avg_order_value = float(aov_result.scalar() or 0)
        
        # Calculate growth
        prev_start = start_date - (end_date - start_date)
        prev_revenue_query = select(
            func.sum(Order.total_amount)
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= prev_start,
                Order.created_at < start_date,
                Order.status.in_([
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        )
        prev_revenue_result = await db.execute(prev_revenue_query)
        prev_revenue = float(prev_revenue_result.scalar() or 0)
        
        growth_rate = 0
        if prev_revenue > 0:
            growth_rate = ((total_revenue - prev_revenue) / prev_revenue) * 100
            
        return {
            "total": round(total_revenue, 2),
            "average_order_value": round(avg_order_value, 2),
            "growth_rate": round(growth_rate, 2),
            "currency": "KRW"
        }
        
    async def _get_platform_metrics(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> Dict[str, Any]:
        """Get platform-specific metrics"""
        # Orders by platform
        platform_query = select(
            Order.platform_type,
            func.count(Order.id),
            func.sum(Order.total_amount)
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        ).group_by(Order.platform_type)
        
        platform_result = await db.execute(platform_query)
        
        platform_data = {}
        for row in platform_result:
            platform_data[row[0]] = {
                "orders": row[1],
                "revenue": float(row[2] or 0)
            }
            
        # Active accounts by platform
        accounts_query = select(
            PlatformAccount.platform_type,
            func.count(PlatformAccount.id)
        ).where(
            and_(
                PlatformAccount.user_id == user_id,
                PlatformAccount.is_active == True
            )
        ).group_by(PlatformAccount.platform_type)
        
        accounts_result = await db.execute(accounts_query)
        
        for row in accounts_result:
            if row[0] in platform_data:
                platform_data[row[0]]["active_accounts"] = row[1]
            else:
                platform_data[row[0]] = {
                    "orders": 0,
                    "revenue": 0,
                    "active_accounts": row[1]
                }
                
        return platform_data
        
    async def _get_ai_usage_metrics(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> Dict[str, Any]:
        """Get AI usage metrics"""
        # Total AI calls
        ai_query = select(
            AILog.service_type,
            func.count(AILog.id),
            func.sum(AILog.tokens_used),
            func.avg(AILog.response_time)
        ).where(
            and_(
                AILog.user_id == user_id,
                AILog.created_at >= start_date,
                AILog.created_at <= end_date
            )
        ).group_by(AILog.service_type)
        
        ai_result = await db.execute(ai_query)
        
        ai_metrics = {
            "total_calls": 0,
            "total_tokens": 0,
            "by_service": {}
        }
        
        for row in ai_result:
            service_type = row[0]
            calls = row[1]
            tokens = row[2] or 0
            avg_response_time = row[3] or 0
            
            ai_metrics["total_calls"] += calls
            ai_metrics["total_tokens"] += tokens
            ai_metrics["by_service"][service_type] = {
                "calls": calls,
                "tokens": tokens,
                "avg_response_time": round(avg_response_time, 2)
            }
            
        return ai_metrics
        
    async def _get_inventory_metrics(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:
        """Get inventory metrics"""
        # Total inventory value
        inventory_query = select(
            func.sum(Inventory.available_quantity * Product.price)
        ).select_from(
            Inventory
        ).join(
            Product
        ).where(
            Product.user_id == user_id
        )
        
        inventory_result = await db.execute(inventory_query)
        total_value = float(inventory_result.scalar() or 0)
        
        # Total SKUs
        sku_query = select(
            func.count(distinct(Inventory.product_id))
        ).select_from(
            Inventory
        ).join(
            Product
        ).where(
            Product.user_id == user_id
        )
        
        sku_result = await db.execute(sku_query)
        total_skus = sku_result.scalar() or 0
        
        return {
            "total_value": round(total_value, 2),
            "total_skus": total_skus,
            "currency": "KRW"
        }
        
    async def _get_error_rate(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Get error rate from metrics"""
        redis_client = await self._get_redis()
        
        # Get error count from redis metrics
        error_key = f"metrics:errors:{start_date.date()}"
        total_key = f"metrics:requests:{start_date.date()}"
        
        errors = await redis_client.get(error_key) or 0
        total = await redis_client.get(total_key) or 1
        
        if int(total) > 0:
            return round((int(errors) / int(total)) * 100, 2)
        return 0.0
        
    async def _get_api_performance_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get API performance metrics"""
        redis_client = await self._get_redis()
        
        # Get average response time
        response_times = []
        for i in range(10):  # Last 10 data points
            key = f"metrics:response_time:{i}"
            value = await redis_client.get(key)
            if value:
                response_times.append(float(value))
                
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "avg_response_time": round(avg_response_time, 2),
            "uptime": 99.9,  # This would come from monitoring service
            "requests_per_minute": await self._get_rpm()
        }
        
    async def _get_rpm(self) -> int:
        """Get requests per minute"""
        redis_client = await self._get_redis()
        rpm = await redis_client.get("metrics:rpm") or 0
        return int(rpm)
        
    async def get_system_health(self, db: AsyncSession) -> SystemHealth:
        """Get comprehensive system health status"""
        health_data = await self.health_checker.check_all_services(db)
        
        return SystemHealth(
            status=health_data["status"],
            services=health_data["services"],
            database=health_data["database"],
            redis=health_data["redis"],
            external_apis=health_data["external_apis"],
            last_check=datetime.utcnow()
        )
        
    async def get_business_metrics(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> BusinessMetrics:
        """Get detailed business metrics"""
        # Daily revenue and orders
        daily_query = select(
            func.date(Order.created_at).label('date'),
            func.count(Order.id).label('orders'),
            func.sum(Order.total_amount).label('revenue')
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_([
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        ).group_by(func.date(Order.created_at))
        
        daily_result = await db.execute(daily_query)
        
        daily_data = []
        for row in daily_result:
            daily_data.append({
                "date": row.date.isoformat(),
                "orders": row.orders,
                "revenue": float(row.revenue)
            })
            
        # Top categories
        category_query = select(
            Product.category,
            func.count(distinct(Order.id)).label('orders'),
            func.sum(Order.total_amount).label('revenue')
        ).select_from(
            Order
        ).join(
            Product, Order.product_id == Product.id
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        ).group_by(Product.category).order_by(
            func.sum(Order.total_amount).desc()
        ).limit(10)
        
        category_result = await db.execute(category_query)
        
        top_categories = []
        for row in category_result:
            top_categories.append({
                "category": row.category,
                "orders": row.orders,
                "revenue": float(row.revenue)
            })
            
        # Customer metrics
        unique_customers = await db.execute(
            select(func.count(distinct(Order.customer_email))).where(
                and_(
                    Order.user_id == user_id,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
        )
        customer_count = unique_customers.scalar() or 0
        
        # Repeat customer rate
        repeat_query = select(
            func.count(distinct(Order.customer_email))
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        ).group_by(Order.customer_email).having(
            func.count(Order.id) > 1
        )
        
        repeat_result = await db.execute(repeat_query)
        repeat_customers = len(repeat_result.all())
        
        repeat_rate = 0
        if customer_count > 0:
            repeat_rate = (repeat_customers / customer_count) * 100
            
        return BusinessMetrics(
            daily_revenue=daily_data,
            top_categories=top_categories,
            customer_metrics={
                "total_customers": customer_count,
                "repeat_rate": round(repeat_rate, 2),
                "new_customers": customer_count - repeat_customers
            },
            conversion_rate=await self._calculate_conversion_rate(db, start_date, end_date, user_id)
        )
        
    async def _calculate_conversion_rate(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> float:
        """Calculate conversion rate"""
        # This would typically come from analytics service
        # For now, return a mock value
        return 3.5
        
    async def get_performance_metrics(
        self,
        db: AsyncSession,
        service: Optional[str] = None
    ) -> PerformanceMetrics:
        """Get performance metrics"""
        metrics = await self.metrics_collector.get_performance_metrics(service)
        
        return PerformanceMetrics(
            response_times=metrics["response_times"],
            error_rates=metrics["error_rates"],
            throughput=metrics["throughput"],
            resource_usage=metrics["resource_usage"],
            service_specific=metrics.get("service_specific", {})
        )
        
    async def get_alerts(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[AlertResponse]:
        """Get system alerts"""
        alerts = await self.alert_manager.get_alerts(
            status=status,
            severity=severity,
            limit=limit
        )
        
        return [
            AlertResponse(
                id=alert["id"],
                type=alert["type"],
                severity=alert["severity"],
                message=alert["message"],
                source=alert["source"],
                status=alert["status"],
                created_at=alert["created_at"],
                acknowledged_at=alert.get("acknowledged_at"),
                resolved_at=alert.get("resolved_at"),
                metadata=alert.get("metadata", {})
            )
            for alert in alerts
        ]
        
    async def acknowledge_alert(
        self,
        db: AsyncSession,
        alert_id: str,
        user_id: int
    ):
        """Acknowledge an alert"""
        await self.alert_manager.acknowledge_alert(alert_id, user_id)
        
    async def get_logs(
        self,
        db: AsyncSession,
        service: Optional[str] = None,
        level: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LogEntry]:
        """Get aggregated logs"""
        # This would typically integrate with a log aggregation service
        # For now, return mock data
        logs = []
        
        # In production, this would query from ElasticSearch or similar
        for i in range(min(limit, 10)):
            logs.append(
                LogEntry(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow() - timedelta(minutes=i),
                    service=service or "backend",
                    level=level or "INFO",
                    message=f"Sample log message {i}",
                    metadata={
                        "request_id": str(uuid.uuid4()),
                        "user_id": "123"
                    }
                )
            )
            
        return logs
        
    async def export_data(
        self,
        db: AsyncSession,
        data_type: str,
        format: str,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> Dict[str, Any]:
        """Export dashboard data"""
        # Get data based on type
        if data_type == "orders":
            data = await self._export_orders(db, start_date, end_date, user_id)
        elif data_type == "products":
            data = await self._export_products(db, start_date, end_date, user_id)
        elif data_type == "revenue":
            data = await self._export_revenue(db, start_date, end_date, user_id)
        else:
            raise ValueError(f"Unknown data type: {data_type}")
            
        # Convert to requested format
        if format == "csv":
            output = self._to_csv(data)
            content_type = "text/csv"
        elif format == "excel":
            output = self._to_excel(data)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format == "json":
            output = json.dumps(data, default=str)
            content_type = "application/json"
        else:
            raise ValueError(f"Unknown format: {format}")
            
        # Store file and generate download URL
        file_id = str(uuid.uuid4())
        filename = f"{data_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        # In production, this would upload to S3 or similar
        redis_client = await self._get_redis()
        await redis_client.setex(
            f"export:{file_id}",
            3600,  # 1 hour expiration
            output
        )
        
        return {
            "url": f"/api/v1/dashboard/download/{file_id}",
            "filename": filename,
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }
        
    async def _export_orders(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> List[Dict]:
        """Export order data"""
        query = select(Order).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        ).options(selectinload(Order.items))
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        data = []
        for order in orders:
            data.append({
                "order_id": order.id,
                "order_number": order.order_number,
                "platform": order.platform_type,
                "status": order.status,
                "total_amount": order.total_amount,
                "created_at": order.created_at,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "items_count": len(order.items)
            })
            
        return data
        
    async def _export_products(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> List[Dict]:
        """Export product data"""
        query = select(Product).where(
            and_(
                Product.user_id == user_id,
                Product.created_at >= start_date,
                Product.created_at <= end_date
            )
        ).options(selectinload(Product.inventory))
        
        result = await db.execute(query)
        products = result.scalars().all()
        
        data = []
        for product in products:
            inventory = product.inventory[0] if product.inventory else None
            data.append({
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "cost": product.cost,
                "margin": product.price - product.cost if product.cost else 0,
                "stock": inventory.available_quantity if inventory else 0,
                "is_active": product.is_active,
                "created_at": product.created_at
            })
            
        return data
        
    async def _export_revenue(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        user_id: int
    ) -> List[Dict]:
        """Export revenue data"""
        query = select(
            func.date(Order.created_at).label('date'),
            Order.platform_type,
            func.count(Order.id).label('orders'),
            func.sum(Order.total_amount).label('revenue'),
            func.avg(Order.total_amount).label('avg_order_value')
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status.in_([
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        ).group_by(
            func.date(Order.created_at),
            Order.platform_type
        )
        
        result = await db.execute(query)
        
        data = []
        for row in result:
            data.append({
                "date": row.date.isoformat(),
                "platform": row.platform_type,
                "orders": row.orders,
                "revenue": float(row.revenue),
                "avg_order_value": float(row.avg_order_value)
            })
            
        return data
        
    def _to_csv(self, data: List[Dict]) -> str:
        """Convert data to CSV"""
        if not data:
            return ""
            
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
        
    def _to_excel(self, data: List[Dict]) -> bytes:
        """Convert data to Excel"""
        if not data:
            return b""
            
        df = pd.DataFrame(data)
        output = io.BytesIO()
        df.to_excel(output, index=False)
        return output.getvalue()
        
    async def get_realtime_metrics(self, db: AsyncSession) -> RealtimeMetrics:
        """Get real-time metrics for WebSocket updates"""
        redis_client = await self._get_redis()
        
        # Get current metrics
        current_rpm = await redis_client.get("metrics:rpm") or 0
        current_active_users = await redis_client.get("metrics:active_users") or 0
        current_error_rate = await redis_client.get("metrics:error_rate") or 0
        
        # Get recent order count
        recent_orders = await db.execute(
            select(func.count(Order.id)).where(
                Order.created_at >= datetime.utcnow() - timedelta(minutes=5)
            )
        )
        order_count = recent_orders.scalar() or 0
        
        return RealtimeMetrics(
            timestamp=datetime.utcnow(),
            requests_per_minute=int(current_rpm),
            active_users=int(current_active_users),
            recent_orders=order_count,
            error_rate=float(current_error_rate),
            system_status="healthy"  # This would come from health checker
        )
        
    async def get_metrics_history(
        self,
        db: AsyncSession,
        metric_type: str,
        period: str,
        interval: str
    ) -> List[Dict[str, Any]]:
        """Get historical metrics data for charts"""
        # Calculate time points based on period and interval
        now = datetime.utcnow()
        period_map = {
            "1h": timedelta(hours=1),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        interval_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1)
        }
        
        start_time = now - period_map.get(period, timedelta(days=1))
        interval_delta = interval_map.get(interval, timedelta(minutes=5))
        
        data_points = []
        current_time = start_time
        
        while current_time <= now:
            # Get metric value for this time point
            value = await self._get_metric_at_time(db, metric_type, current_time)
            data_points.append({
                "timestamp": current_time.isoformat(),
                "value": value
            })
            current_time += interval_delta
            
        return data_points
        
    async def _get_metric_at_time(
        self,
        db: AsyncSession,
        metric_type: str,
        timestamp: datetime
    ) -> float:
        """Get metric value at specific time"""
        # This would query from time-series database
        # For now, return mock data
        import random
        
        if metric_type == "orders":
            return random.randint(10, 100)
        elif metric_type == "revenue":
            return random.uniform(100000, 1000000)
        elif metric_type == "response_time":
            return random.uniform(50, 200)
        else:
            return 0
            
    async def get_top_products(
        self,
        db: AsyncSession,
        limit: int,
        metric: str,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Get top performing products"""
        if metric == "revenue":
            order_by = func.sum(Order.total_amount).desc()
        elif metric == "orders":
            order_by = func.count(Order.id).desc()
        else:
            order_by = func.count(Order.id).desc()
            
        query = select(
            Product.id,
            Product.name,
            Product.sku,
            Product.category,
            Product.price,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_revenue')
        ).select_from(
            Product
        ).join(
            Order, Order.product_id == Product.id
        ).where(
            and_(
                Product.user_id == user_id,
                Order.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).group_by(
            Product.id,
            Product.name,
            Product.sku,
            Product.category,
            Product.price
        ).order_by(order_by).limit(limit)
        
        result = await db.execute(query)
        
        products = []
        for row in result:
            products.append({
                "id": row.id,
                "name": row.name,
                "sku": row.sku,
                "category": row.category,
                "price": float(row.price),
                "orders": row.order_count,
                "revenue": float(row.total_revenue)
            })
            
        return products
        
    async def get_revenue_breakdown(
        self,
        db: AsyncSession,
        period: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Get revenue breakdown by various dimensions"""
        period_map = {
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90)
        }
        
        start_date = datetime.utcnow() - period_map.get(period, timedelta(days=30))
        
        # By platform
        platform_query = select(
            Order.platform_type,
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders')
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.status.in_([
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        ).group_by(Order.platform_type)
        
        platform_result = await db.execute(platform_query)
        
        by_platform = []
        for row in platform_result:
            by_platform.append({
                "platform": row.platform_type,
                "revenue": float(row.revenue),
                "orders": row.orders
            })
            
        # By category
        category_query = select(
            Product.category,
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders')
        ).select_from(
            Order
        ).join(
            Product, Order.product_id == Product.id
        ).where(
            and_(
                Order.user_id == user_id,
                Order.created_at >= start_date,
                Order.status.in_([
                    OrderStatus.PROCESSING,
                    OrderStatus.SHIPPED,
                    OrderStatus.DELIVERED
                ])
            )
        ).group_by(Product.category)
        
        category_result = await db.execute(category_query)
        
        by_category = []
        for row in category_result:
            by_category.append({
                "category": row.category,
                "revenue": float(row.revenue),
                "orders": row.orders
            })
            
        return {
            "by_platform": by_platform,
            "by_category": by_category,
            "period": period
        }