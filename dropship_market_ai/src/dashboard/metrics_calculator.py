"""Dashboard metrics calculation and aggregation"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case
import structlog

from ..database.models import (
    Product, ProductPerformance, MarketplaceProduct,
    Review, Alert, DashboardMetrics, AIPrediction,
    RotationHistory, MarketOptimization
)

logger = structlog.get_logger()


class MetricsCalculator:
    """Calculate and aggregate metrics for dashboard"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def calculate_daily_metrics(
        self,
        date: Optional[datetime.date] = None
    ) -> Dict[str, Any]:
        """Calculate daily metrics"""
        
        if not date:
            date = datetime.utcnow().date()
        
        metrics = {
            'date': date.isoformat(),
            'type': 'daily',
            'revenue': {},
            'performance': {},
            'products': {},
            'alerts': {}
        }
        
        # Revenue metrics
        revenue_data = await self._calculate_revenue_metrics(date, date)
        metrics['revenue'] = revenue_data
        
        # Performance metrics
        performance_data = await self._calculate_performance_metrics(date, date)
        metrics['performance'] = performance_data
        
        # Product metrics
        product_data = await self._calculate_product_metrics(date)
        metrics['products'] = product_data
        
        # Alert metrics
        alert_data = await self._calculate_alert_metrics(date)
        metrics['alerts'] = alert_data
        
        # Save to database
        await self._save_dashboard_metrics(metrics, 'daily')
        
        return metrics
    
    async def calculate_weekly_metrics(
        self,
        end_date: Optional[datetime.date] = None
    ) -> Dict[str, Any]:
        """Calculate weekly metrics"""
        
        if not end_date:
            end_date = datetime.utcnow().date()
        
        start_date = end_date - timedelta(days=6)
        
        metrics = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'type': 'weekly',
            'revenue': {},
            'performance': {},
            'trends': {},
            'top_performers': {}
        }
        
        # Revenue metrics
        revenue_data = await self._calculate_revenue_metrics(start_date, end_date)
        metrics['revenue'] = revenue_data
        
        # Performance metrics
        performance_data = await self._calculate_performance_metrics(start_date, end_date)
        metrics['performance'] = performance_data
        
        # Trend analysis
        trend_data = await self._calculate_trends(start_date, end_date)
        metrics['trends'] = trend_data
        
        # Top performers
        top_performers = await self._get_top_performers(start_date, end_date)
        metrics['top_performers'] = top_performers
        
        # Save to database
        await self._save_dashboard_metrics(metrics, 'weekly')
        
        return metrics
    
    async def calculate_monthly_metrics(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calculate monthly metrics"""
        
        if not year or not month:
            now = datetime.utcnow()
            year = now.year
            month = now.month
        
        start_date = datetime(year, month, 1).date()
        
        # Calculate end date (last day of month)
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        metrics = {
            'year': year,
            'month': month,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'type': 'monthly',
            'revenue': {},
            'performance': {},
            'growth': {},
            'category_breakdown': {},
            'marketplace_comparison': {}
        }
        
        # Revenue metrics
        revenue_data = await self._calculate_revenue_metrics(start_date, end_date)
        metrics['revenue'] = revenue_data
        
        # Performance metrics
        performance_data = await self._calculate_performance_metrics(start_date, end_date)
        metrics['performance'] = performance_data
        
        # Growth metrics (compare to previous month)
        growth_data = await self._calculate_growth_metrics(year, month)
        metrics['growth'] = growth_data
        
        # Category breakdown
        category_data = await self._get_category_breakdown(start_date, end_date)
        metrics['category_breakdown'] = category_data
        
        # Marketplace comparison
        marketplace_data = await self._get_marketplace_comparison(start_date, end_date)
        metrics['marketplace_comparison'] = marketplace_data
        
        # Save to database
        await self._save_dashboard_metrics(metrics, 'monthly')
        
        return metrics
    
    async def _calculate_revenue_metrics(
        self,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """Calculate revenue-related metrics"""
        
        stmt = select(
            func.sum(ProductPerformance.revenue).label('total_revenue'),
            func.sum(ProductPerformance.profit).label('total_profit'),
            func.sum(ProductPerformance.sales_volume).label('total_sales'),
            func.count(func.distinct(ProductPerformance.product_id)).label('active_products')
        ).where(
            and_(
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        )
        
        result = await self.session.execute(stmt)
        data = result.one()
        
        total_revenue = float(data.total_revenue or 0)
        total_profit = float(data.total_profit or 0)
        total_sales = data.total_sales or 0
        
        return {
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_sales': total_sales,
            'average_order_value': total_revenue / total_sales if total_sales > 0 else 0,
            'profit_margin': total_profit / total_revenue if total_revenue > 0 else 0,
            'active_products': data.active_products or 0
        }
    
    async def _calculate_performance_metrics(
        self,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """Calculate performance metrics"""
        
        stmt = select(
            func.sum(ProductPerformance.views).label('total_views'),
            func.sum(ProductPerformance.clicks).label('total_clicks'),
            func.sum(ProductPerformance.conversions).label('total_conversions'),
            func.avg(ProductPerformance.category_ranking).label('avg_ranking')
        ).where(
            and_(
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        )
        
        result = await self.session.execute(stmt)
        data = result.one()
        
        total_views = data.total_views or 0
        total_clicks = data.total_clicks or 0
        total_conversions = data.total_conversions or 0
        
        return {
            'total_views': total_views,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'click_through_rate': total_clicks / total_views if total_views > 0 else 0,
            'conversion_rate': total_conversions / total_clicks if total_clicks > 0 else 0,
            'average_ranking': float(data.avg_ranking or 0)
        }
    
    async def _calculate_product_metrics(
        self,
        date: datetime.date
    ) -> Dict[str, Any]:
        """Calculate product-related metrics for a specific date"""
        
        # Total active products
        stmt = select(func.count(Product.id)).where(
            Product.status == 'active'
        )
        result = await self.session.execute(stmt)
        total_products = result.scalar() or 0
        
        # Products with sales today
        stmt = select(
            func.count(func.distinct(ProductPerformance.product_id))
        ).where(
            and_(
                ProductPerformance.date == date,
                ProductPerformance.sales_volume > 0
            )
        )
        result = await self.session.execute(stmt)
        products_with_sales = result.scalar() or 0
        
        # New products (created in last 7 days)
        stmt = select(func.count(Product.id)).where(
            Product.created_at >= datetime.combine(date - timedelta(days=7), datetime.min.time())
        )
        result = await self.session.execute(stmt)
        new_products = result.scalar() or 0
        
        # Products needing rotation
        rotation_candidates = await self._count_rotation_candidates()
        
        return {
            'total_active': total_products,
            'with_sales_today': products_with_sales,
            'new_products': new_products,
            'rotation_candidates': rotation_candidates,
            'sales_rate': products_with_sales / total_products if total_products > 0 else 0
        }
    
    async def _calculate_alert_metrics(
        self,
        date: datetime.date
    ) -> Dict[str, Any]:
        """Calculate alert-related metrics"""
        
        # Count alerts by severity
        stmt = select(
            Alert.severity,
            func.count(Alert.id).label('count')
        ).where(
            and_(
                func.date(Alert.created_at) == date,
                Alert.status == 'active'
            )
        ).group_by(Alert.severity)
        
        result = await self.session.execute(stmt)
        severity_counts = {row.severity: row.count for row in result}
        
        # Count alerts by type
        stmt = select(
            Alert.alert_type,
            func.count(Alert.id).label('count')
        ).where(
            func.date(Alert.created_at) == date
        ).group_by(Alert.alert_type)
        
        result = await self.session.execute(stmt)
        type_counts = {row.alert_type: row.count for row in result}
        
        return {
            'total_active': sum(severity_counts.values()),
            'by_severity': severity_counts,
            'by_type': type_counts,
            'critical_count': severity_counts.get('critical', 0),
            'high_priority_count': severity_counts.get('high', 0)
        }
    
    async def _calculate_trends(
        self,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """Calculate trend data"""
        
        # Daily revenue trend
        stmt = select(
            ProductPerformance.date,
            func.sum(ProductPerformance.revenue).label('daily_revenue')
        ).where(
            and_(
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        ).group_by(ProductPerformance.date).order_by(ProductPerformance.date)
        
        result = await self.session.execute(stmt)
        revenue_trend = [
            {
                'date': row.date.isoformat(),
                'revenue': float(row.daily_revenue or 0)
            }
            for row in result
        ]
        
        # Sales volume trend
        stmt = select(
            ProductPerformance.date,
            func.sum(ProductPerformance.sales_volume).label('daily_sales')
        ).where(
            and_(
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        ).group_by(ProductPerformance.date).order_by(ProductPerformance.date)
        
        result = await self.session.execute(stmt)
        sales_trend = [
            {
                'date': row.date.isoformat(),
                'sales': row.daily_sales or 0
            }
            for row in result
        ]
        
        return {
            'revenue_trend': revenue_trend,
            'sales_trend': sales_trend
        }
    
    async def _get_top_performers(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top performing products"""
        
        stmt = select(
            Product,
            func.sum(ProductPerformance.revenue).label('total_revenue'),
            func.sum(ProductPerformance.sales_volume).label('total_sales'),
            func.avg(ProductPerformance.category_ranking).label('avg_ranking')
        ).join(
            ProductPerformance,
            Product.id == ProductPerformance.product_id
        ).where(
            and_(
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        ).group_by(
            Product.id
        ).order_by(
            func.sum(ProductPerformance.revenue).desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        
        top_performers = []
        for product, revenue, sales, ranking in result:
            top_performers.append({
                'product_id': product.id,
                'product_name': product.name,
                'category': product.category,
                'total_revenue': float(revenue or 0),
                'total_sales': sales or 0,
                'average_ranking': float(ranking or 0)
            })
        
        return top_performers
    
    async def _calculate_growth_metrics(
        self,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """Calculate month-over-month growth"""
        
        # Current month data
        current_start = datetime(year, month, 1).date()
        if month == 12:
            current_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            current_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        current_metrics = await self._calculate_revenue_metrics(current_start, current_end)
        
        # Previous month data
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
        
        prev_start = datetime(prev_year, prev_month, 1).date()
        if prev_month == 12:
            prev_end = datetime(prev_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            prev_end = datetime(prev_year, prev_month + 1, 1).date() - timedelta(days=1)
        
        prev_metrics = await self._calculate_revenue_metrics(prev_start, prev_end)
        
        # Calculate growth rates
        revenue_growth = (
            (current_metrics['total_revenue'] - prev_metrics['total_revenue']) / 
            prev_metrics['total_revenue'] * 100
            if prev_metrics['total_revenue'] > 0 else 0
        )
        
        sales_growth = (
            (current_metrics['total_sales'] - prev_metrics['total_sales']) / 
            prev_metrics['total_sales'] * 100
            if prev_metrics['total_sales'] > 0 else 0
        )
        
        return {
            'revenue_growth_rate': revenue_growth,
            'sales_growth_rate': sales_growth,
            'current_month_revenue': current_metrics['total_revenue'],
            'previous_month_revenue': prev_metrics['total_revenue'],
            'current_month_sales': current_metrics['total_sales'],
            'previous_month_sales': prev_metrics['total_sales']
        }
    
    async def _get_category_breakdown(
        self,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> List[Dict[str, Any]]:
        """Get revenue breakdown by category"""
        
        stmt = select(
            Product.category,
            func.sum(ProductPerformance.revenue).label('category_revenue'),
            func.sum(ProductPerformance.sales_volume).label('category_sales'),
            func.count(func.distinct(Product.id)).label('product_count')
        ).join(
            ProductPerformance,
            Product.id == ProductPerformance.product_id
        ).where(
            and_(
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date,
                Product.category.isnot(None)
            )
        ).group_by(
            Product.category
        ).order_by(
            func.sum(ProductPerformance.revenue).desc()
        )
        
        result = await self.session.execute(stmt)
        
        categories = []
        total_revenue = 0
        
        for category, revenue, sales, count in result:
            category_revenue = float(revenue or 0)
            total_revenue += category_revenue
            
            categories.append({
                'category': category,
                'revenue': category_revenue,
                'sales': sales or 0,
                'product_count': count or 0
            })
        
        # Add percentage
        for cat in categories:
            cat['revenue_percentage'] = (
                cat['revenue'] / total_revenue * 100 if total_revenue > 0 else 0
            )
        
        return categories
    
    async def _get_marketplace_comparison(
        self,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> List[Dict[str, Any]]:
        """Compare performance across marketplaces"""
        
        stmt = select(
            ProductPerformance.marketplace,
            func.sum(ProductPerformance.revenue).label('marketplace_revenue'),
            func.sum(ProductPerformance.sales_volume).label('marketplace_sales'),
            func.avg(
                case(
                    (ProductPerformance.clicks > 0,
                     ProductPerformance.conversions * 100.0 / ProductPerformance.clicks),
                    else_=0
                )
            ).label('avg_conversion_rate')
        ).where(
            and_(
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        ).group_by(
            ProductPerformance.marketplace
        ).order_by(
            func.sum(ProductPerformance.revenue).desc()
        )
        
        result = await self.session.execute(stmt)
        
        marketplaces = []
        for marketplace, revenue, sales, conv_rate in result:
            marketplaces.append({
                'marketplace': marketplace,
                'revenue': float(revenue or 0),
                'sales': sales or 0,
                'conversion_rate': float(conv_rate or 0),
                'average_order_value': (
                    float(revenue or 0) / (sales or 1)
                )
            })
        
        return marketplaces
    
    async def _count_rotation_candidates(self) -> int:
        """Count products that need rotation"""
        
        # Simple heuristic: products with low performance in last 7 days
        stmt = select(
            func.count(func.distinct(ProductPerformance.product_id))
        ).where(
            and_(
                ProductPerformance.date >= datetime.utcnow().date() - timedelta(days=7),
                ProductPerformance.category_ranking > 50  # Poor ranking
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def _save_dashboard_metrics(
        self,
        metrics: Dict[str, Any],
        metric_type: str
    ):
        """Save calculated metrics to database"""
        
        metric_date = datetime.utcnow().date()
        if metric_type == 'daily':
            metric_date = datetime.fromisoformat(metrics['date']).date()
        elif metric_type == 'weekly':
            metric_date = datetime.fromisoformat(metrics['end_date']).date()
        elif metric_type == 'monthly':
            metric_date = datetime.fromisoformat(metrics['end_date']).date()
        
        # Check if metrics already exist
        stmt = select(DashboardMetrics).where(
            and_(
                DashboardMetrics.metric_date == metric_date,
                DashboardMetrics.metric_type == metric_type
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing metrics
            existing.total_revenue = metrics['revenue'].get('total_revenue', 0)
            existing.total_profit = metrics['revenue'].get('total_profit', 0)
            existing.total_orders = metrics['revenue'].get('total_sales', 0)
            existing.average_order_value = metrics['revenue'].get('average_order_value', 0)
            existing.conversion_rate = metrics.get('performance', {}).get('conversion_rate', 0)
            existing.marketplace_metrics = metrics.get('marketplace_comparison', [])
            existing.category_metrics = metrics.get('category_breakdown', [])
            existing.top_products = metrics.get('top_performers', [])
            existing.calculated_at = datetime.utcnow()
        else:
            # Create new metrics
            dashboard_metrics = DashboardMetrics(
                metric_date=metric_date,
                metric_type=metric_type,
                total_revenue=metrics['revenue'].get('total_revenue', 0),
                total_profit=metrics['revenue'].get('total_profit', 0),
                total_orders=metrics['revenue'].get('total_sales', 0),
                average_order_value=metrics['revenue'].get('average_order_value', 0),
                conversion_rate=metrics.get('performance', {}).get('conversion_rate', 0),
                marketplace_metrics=metrics.get('marketplace_comparison', []),
                category_metrics=metrics.get('category_breakdown', []),
                top_products=metrics.get('top_performers', [])
            )
            self.session.add(dashboard_metrics)
        
        await self.session.commit()