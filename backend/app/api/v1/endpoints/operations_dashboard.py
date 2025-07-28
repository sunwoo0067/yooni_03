"""
Operations Dashboard API endpoints
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, distinct
from sqlalchemy.orm import selectinload

from app.services.database.database import get_db
from app.api.v1.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.order_core import Order
from app.models.product import Product
from app.models.platform_account import PlatformAccount
from app.models.ai_log import AILog
from app.services.monitoring.metrics_collector import MetricsCollector
from app.services.dashboard.operations_dashboard_service import OperationsDashboardService
from app.services.realtime.dashboard_websocket_manager import dashboard_ws_manager
from app.core.config import settings
from app.schemas.dashboard import (
    DashboardMetrics,
    SystemHealth,
    BusinessMetrics,
    PerformanceMetrics,
    AlertResponse,
    LogEntry,
    ExportRequest
)

router = APIRouter()
metrics_collector = MetricsCollector()
dashboard_service = OperationsDashboardService()

@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    period: str = Query("24h", description="Time period: 1h, 24h, 7d, 30d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive dashboard metrics"""
    try:
        metrics = await dashboard_service.get_dashboard_metrics(db, period, current_user.id)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=SystemHealth)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get system health status"""
    try:
        health = await dashboard_service.get_system_health(db)
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/business-metrics", response_model=BusinessMetrics)
async def get_business_metrics(
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get business metrics for specified date range"""
    try:
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        metrics = await dashboard_service.get_business_metrics(
            db, start_date, end_date, current_user.id
        )
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    service: Optional[str] = Query(None, description="Specific service to monitor"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get performance metrics"""
    try:
        metrics = await dashboard_service.get_performance_metrics(db, service)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status: active, resolved, acknowledged"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, warning, info"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get system alerts"""
    try:
        alerts = await dashboard_service.get_alerts(db, status, severity, limit)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Acknowledge an alert"""
    try:
        await dashboard_service.acknowledge_alert(db, alert_id, current_user.id)
        return {"message": "Alert acknowledged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs", response_model=List[LogEntry])
async def get_logs(
    service: Optional[str] = Query(None),
    level: Optional[str] = Query(None, description="Log level: DEBUG, INFO, WARNING, ERROR"),
    search: Optional[str] = Query(None, description="Search in log messages"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get aggregated logs"""
    try:
        logs = await dashboard_service.get_logs(
            db, service, level, search, limit, offset
        )
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export")
async def export_dashboard_data(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export dashboard data in various formats"""
    try:
        export_data = await dashboard_service.export_data(
            db,
            request.data_type,
            request.format,
            request.start_date,
            request.end_date,
            current_user.id
        )
        
        return {
            "download_url": export_data["url"],
            "filename": export_data["filename"],
            "expires_at": export_data["expires_at"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time dashboard updates"""
    connection_id = await dashboard_ws_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Send real-time metrics every 5 seconds
            metrics = await dashboard_service.get_realtime_metrics(db)
            await dashboard_ws_manager.send_dashboard_update(user_id, metrics)
            
            # Handle incoming messages
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "subscribe":
                    # Handle subscription to specific metrics
                    metrics_to_subscribe = data.get("metrics", [])
                    await dashboard_ws_manager.subscribe_to_metrics(connection_id, metrics_to_subscribe)
                    
                elif data.get("type") == "unsubscribe":
                    # Handle unsubscription
                    metrics_to_unsubscribe = data.get("metrics", [])
                    await dashboard_ws_manager.unsubscribe_from_metrics(connection_id, metrics_to_unsubscribe)
                    
                elif data.get("type") == "refresh":
                    # Force refresh of specific data
                    refresh_type = data.get("refresh_type")
                    if refresh_type == "metrics":
                        metrics = await dashboard_service.get_realtime_metrics(db)
                        await dashboard_ws_manager.send_dashboard_update(user_id, metrics)
                    elif refresh_type == "health":
                        health = await dashboard_service.get_system_health(db)
                        await dashboard_ws_manager.send_dashboard_update(user_id, {"health": health})
                        
            except:
                pass
                
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        await dashboard_ws_manager.disconnect(connection_id)
    except Exception as e:
        await dashboard_ws_manager.disconnect(connection_id)
        raise e

@router.get("/metrics/history")
async def get_metrics_history(
    metric_type: str = Query(..., description="Metric type to retrieve"),
    period: str = Query("24h", description="Time period"),
    interval: str = Query("5m", description="Data point interval"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get historical metrics data for charts"""
    try:
        history = await dashboard_service.get_metrics_history(
            db, metric_type, period, interval
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-products")
async def get_top_products(
    limit: int = Query(10, ge=1, le=50),
    metric: str = Query("revenue", description="Metric to sort by: revenue, orders, views"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get top performing products"""
    try:
        products = await dashboard_service.get_top_products(
            db, limit, metric, current_user.id
        )
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/revenue-breakdown")
async def get_revenue_breakdown(
    period: str = Query("30d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get revenue breakdown by platform, category, etc."""
    try:
        breakdown = await dashboard_service.get_revenue_breakdown(
            db, period, current_user.id
        )
        return breakdown
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import asyncio