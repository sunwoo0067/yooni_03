"""Dashboard API endpoints"""
from datetime import datetime, date
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db
from ...dashboard.metrics_calculator import MetricsCalculator
from ...dashboard.alert_manager import AlertManager
import yaml
from pathlib import Path

# Load configuration
config_path = Path(__file__).parent.parent.parent.parent / "configs" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

router = APIRouter()


@router.get("/metrics/daily")
async def get_daily_metrics(
    date: Optional[date] = Query(None, description="Date for metrics (defaults to today)"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get daily dashboard metrics"""
    calculator = MetricsCalculator(db)
    metrics = await calculator.calculate_daily_metrics(date)
    return metrics


@router.get("/metrics/weekly")
async def get_weekly_metrics(
    end_date: Optional[date] = Query(None, description="End date for weekly metrics"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get weekly dashboard metrics"""
    calculator = MetricsCalculator(db)
    metrics = await calculator.calculate_weekly_metrics(end_date)
    return metrics


@router.get("/metrics/monthly")
async def get_monthly_metrics(
    year: Optional[int] = Query(None, description="Year"),
    month: Optional[int] = Query(None, description="Month (1-12)"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get monthly dashboard metrics"""
    calculator = MetricsCalculator(db)
    metrics = await calculator.calculate_monthly_metrics(year, month)
    return metrics


@router.get("/alerts/active")
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get active system alerts"""
    from ...database.models import Alert
    from sqlalchemy import select, and_
    
    # Build query
    conditions = [Alert.status == 'active']
    
    if severity:
        conditions.append(Alert.severity == severity)
    
    if alert_type:
        conditions.append(Alert.alert_type == alert_type)
    
    stmt = select(Alert).where(and_(*conditions)).order_by(Alert.created_at.desc())
    
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    
    return {
        'total': len(alerts),
        'alerts': [
            {
                'id': alert.id,
                'type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'product_id': alert.product_id,
                'marketplace': alert.marketplace,
                'created_at': alert.created_at.isoformat(),
                'details': alert.details
            }
            for alert in alerts
        ]
    }


@router.post("/alerts/check")
async def check_alerts(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually trigger alert checks"""
    alert_manager = AlertManager(config, db)
    alerts = await alert_manager.check_all_alerts()
    
    return {
        'checked_at': datetime.utcnow().isoformat(),
        'new_alerts': len(alerts),
        'alerts': [
            {
                'id': alert.id,
                'type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message
            }
            for alert in alerts
        ]
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Acknowledge an alert"""
    alert_manager = AlertManager(config, db)
    await alert_manager.acknowledge_alert(alert_id)
    
    return {'status': 'acknowledged', 'alert_id': alert_id}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Resolve an alert"""
    alert_manager = AlertManager(config, db)
    await alert_manager.resolve_alert(alert_id)
    
    return {'status': 'resolved', 'alert_id': alert_id}


@router.get("/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive dashboard summary"""
    from ...database.models import Product, Alert, ProductPerformance
    from sqlalchemy import select, func, and_
    
    today = datetime.utcnow().date()
    
    # Get product counts
    stmt = select(func.count(Product.id)).where(Product.status == 'active')
    result = await db.execute(stmt)
    total_products = result.scalar() or 0
    
    # Get today's revenue
    stmt = select(
        func.sum(ProductPerformance.revenue),
        func.sum(ProductPerformance.sales_volume)
    ).where(ProductPerformance.date == today)
    result = await db.execute(stmt)
    today_revenue, today_sales = result.one()
    
    # Get active alerts count
    stmt = select(func.count(Alert.id)).where(Alert.status == 'active')
    result = await db.execute(stmt)
    active_alerts = result.scalar() or 0
    
    # Get critical alerts
    stmt = select(func.count(Alert.id)).where(
        and_(
            Alert.status == 'active',
            Alert.severity == 'critical'
        )
    )
    result = await db.execute(stmt)
    critical_alerts = result.scalar() or 0
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'summary': {
            'total_products': total_products,
            'today_revenue': float(today_revenue or 0),
            'today_sales': today_sales or 0,
            'active_alerts': active_alerts,
            'critical_alerts': critical_alerts
        }
    }