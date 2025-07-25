"""
Pipeline API endpoints
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ....api.v1.dependencies.database import get_db
from ....services.pipeline.workflow_orchestrator import WorkflowOrchestrator
from ....services.pipeline.state_manager import StateManager
from ....services.pipeline.progress_tracker import ProgressTracker
from ....services.analytics.performance_analyzer import PerformanceAnalyzer
from ....services.analytics.sales_data_collector import SalesDataCollector
from ....models.pipeline import (
    PipelineExecution, PipelineStep, WorkflowTemplate, 
    PipelineAlert, PipelineSchedule
)
from ....models.sales_analytics import SalesAnalytics, MarketplaceSession
from pydantic import BaseModel


class WorkflowStartRequest(BaseModel):
    workflow_name: str
    product_ids: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps_config: Dict[str, Any]
    default_config: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class DataCollectionRequest(BaseModel):
    marketplace: str
    account_ids: Optional[List[str]] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    data_types: Optional[List[str]] = None


router = APIRouter()


@router.post("/workflows/start")
async def start_workflow(
    request: WorkflowStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a new workflow execution"""
    
    try:
        orchestrator = WorkflowOrchestrator(db)
        
        execution_id = await orchestrator.start_workflow(
            workflow_name=request.workflow_name,
            product_ids=request.product_ids,
            config=request.config
        )
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "message": f"Workflow '{request.workflow_name}' started successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.get("/workflows/{execution_id}/status")
async def get_workflow_status(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get workflow execution status"""
    
    try:
        orchestrator = WorkflowOrchestrator(db)
        status_info = await orchestrator.get_execution_status(execution_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow execution not found"
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )


@router.post("/workflows/{execution_id}/pause")
async def pause_workflow(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Pause workflow execution"""
    
    try:
        orchestrator = WorkflowOrchestrator(db)
        await orchestrator.pause_workflow(execution_id)
        
        return {"status": "paused", "execution_id": execution_id}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause workflow: {str(e)}"
        )


@router.post("/workflows/{execution_id}/resume")
async def resume_workflow(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Resume paused workflow"""
    
    try:
        orchestrator = WorkflowOrchestrator(db)
        await orchestrator.resume_workflow(execution_id)
        
        return {"status": "resumed", "execution_id": execution_id}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume workflow: {str(e)}"
        )


@router.post("/workflows/{execution_id}/cancel")
async def cancel_workflow(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel workflow execution"""
    
    try:
        orchestrator = WorkflowOrchestrator(db)
        await orchestrator.cancel_workflow(execution_id)
        
        return {"status": "cancelled", "execution_id": execution_id}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {str(e)}"
        )


@router.get("/workflows/{execution_id}/progress")
async def get_workflow_progress(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed workflow progress"""
    
    try:
        tracker = ProgressTracker(db)
        
        # Get overall progress
        progress_summary = await tracker.get_progress_summary(execution_id)
        
        # Get step progress
        # This would need the step names from the execution
        
        # Get product progress
        product_progress = await tracker.get_product_progress(execution_id)
        
        # Check for bottlenecks
        bottlenecks = await tracker.predict_bottlenecks(execution_id)
        
        return {
            "execution_id": execution_id,
            "summary": progress_summary,
            "product_progress": product_progress,
            "bottlenecks": bottlenecks
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow progress: {str(e)}"
        )


@router.get("/workflows")
async def list_workflows(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List workflow executions"""
    
    try:
        query = select(PipelineExecution).order_by(desc(PipelineExecution.started_at))
        
        if status_filter:
            query = query.where(PipelineExecution.status == status_filter)
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        executions = result.scalars().all()
        
        return {
            "executions": [
                {
                    "id": str(execution.workflow_id),
                    "workflow_name": execution.workflow_name,
                    "status": execution.status,
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                    "progress": execution.calculate_progress(),
                    "success_rate": execution.calculate_success_rate(),
                    "products_processed": execution.products_processed
                }
                for execution in executions
            ],
            "total": len(executions),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}"
        )


@router.get("/templates")
async def list_workflow_templates(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """List workflow templates"""
    
    try:
        query = select(WorkflowTemplate).order_by(WorkflowTemplate.name)
        
        if active_only:
            query = query.where(WorkflowTemplate.is_active == True)
        
        result = await db.execute(query)
        templates = result.scalars().all()
        
        return {
            "templates": [
                {
                    "id": str(template.id),
                    "name": template.name,
                    "description": template.description,
                    "version": template.version,
                    "category": template.category,
                    "is_active": template.is_active,
                    "usage_count": template.usage_count,
                    "last_used_at": template.last_used_at
                }
                for template in templates
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.post("/templates")
async def create_workflow_template(
    template_data: WorkflowTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new workflow template"""
    
    try:
        template = WorkflowTemplate(
            name=template_data.name,
            description=template_data.description,
            steps_config=template_data.steps_config,
            default_config=template_data.default_config,
            category=template_data.category,
            tags=template_data.tags
        )
        
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        return {
            "id": str(template.id),
            "name": template.name,
            "status": "created"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get("/alerts")
async def get_pipeline_alerts(
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get pipeline alerts"""
    
    try:
        query = select(PipelineAlert).order_by(desc(PipelineAlert.created_at))
        
        if severity:
            query = query.where(PipelineAlert.severity == severity)
        
        if acknowledged is not None:
            query = query.where(PipelineAlert.is_acknowledged == acknowledged)
        
        query = query.limit(limit)
        
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        return {
            "alerts": [
                {
                    "id": str(alert.id),
                    "execution_id": str(alert.execution_id) if alert.execution_id else None,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "message": alert.message,
                    "component": alert.component,
                    "created_at": alert.created_at,
                    "is_acknowledged": alert.is_acknowledged,
                    "acknowledged_by": alert.acknowledged_by
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user: str = Query(..., description="User acknowledging the alert"),
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge an alert"""
    
    try:
        result = await db.execute(
            select(PipelineAlert).where(PipelineAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        alert.acknowledge(user)
        await db.commit()
        
        return {"status": "acknowledged", "alert_id": alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.post("/data-collection/start")
async def start_data_collection(
    request: DataCollectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start marketplace data collection"""
    
    try:
        collector = SalesDataCollector(db)
        
        # Set default date range if not provided
        if not request.date_range_start or not request.date_range_end:
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            date_range = (start_date, end_date)
        else:
            date_range = (request.date_range_start, request.date_range_end)
        
        # Start collection (this would be async in production)
        results = await collector.collect_all_marketplace_data(
            account_ids=request.account_ids,
            date_range=date_range,
            marketplaces=[request.marketplace] if request.marketplace != "all" else None
        )
        
        return {
            "status": "started",
            "date_range": {
                "start": date_range[0],
                "end": date_range[1]
            },
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start data collection: {str(e)}"
        )


@router.get("/data-collection/status")
async def get_data_collection_status(db: AsyncSession = Depends(get_db)):
    """Get data collection status"""
    
    try:
        collector = SalesDataCollector(db)
        status_info = await collector.get_collection_status()
        
        return status_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection status: {str(e)}"
        )


@router.get("/analytics/performance")
async def get_performance_analysis(
    date_range_start: Optional[date] = Query(None),
    date_range_end: Optional[date] = Query(None),
    report_type: str = Query("comprehensive"),
    db: AsyncSession = Depends(get_db)
):
    """Get performance analysis"""
    
    try:
        analyzer = PerformanceAnalyzer(db)
        
        # Set default date range if not provided
        if not date_range_start or not date_range_end:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            date_range = (start_date, end_date)
        else:
            date_range = (date_range_start, date_range_end)
        
        # Generate performance report
        report = await analyzer.generate_performance_report(date_range, report_type)
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance analysis: {str(e)}"
        )


@router.post("/analytics/optimize")
async def optimize_models(db: AsyncSession = Depends(get_db)):
    """Trigger AI model optimization"""
    
    try:
        analyzer = PerformanceAnalyzer(db)
        
        # Run optimization
        optimization_results = await analyzer.optimize_ai_models()
        
        return optimization_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize models: {str(e)}"
        )


@router.get("/dashboard/overview")
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """Get dashboard overview data"""
    
    try:
        # Get recent executions
        recent_executions = await db.execute(
            select(PipelineExecution)
            .where(PipelineExecution.started_at >= datetime.utcnow() - timedelta(hours=24))
            .order_by(desc(PipelineExecution.started_at))
            .limit(10)
        )
        executions = recent_executions.scalars().all()
        
        # Get recent alerts
        recent_alerts = await db.execute(
            select(PipelineAlert)
            .where(
                and_(
                    PipelineAlert.created_at >= datetime.utcnow() - timedelta(hours=24),
                    PipelineAlert.is_acknowledged == False
                )
            )
            .order_by(desc(PipelineAlert.created_at))
            .limit(10)
        )
        alerts = recent_alerts.scalars().all()
        
        # Get collection sessions
        recent_sessions = await db.execute(
            select(MarketplaceSession)
            .where(MarketplaceSession.started_at >= datetime.utcnow() - timedelta(hours=24))
            .order_by(desc(MarketplaceSession.started_at))
            .limit(10)
        )
        sessions = recent_sessions.scalars().all()
        
        # Calculate summary statistics
        total_executions = len(executions)
        active_executions = len([e for e in executions if e.status in ["running", "paused"]])
        failed_executions = len([e for e in executions if e.status == "failed"])
        
        total_products_processed = sum(e.products_processed for e in executions)
        
        return {
            "summary": {
                "total_executions_24h": total_executions,
                "active_executions": active_executions,
                "failed_executions": failed_executions,
                "success_rate": ((total_executions - failed_executions) / total_executions * 100) if total_executions > 0 else 0,
                "total_products_processed": total_products_processed,
                "unacknowledged_alerts": len(alerts),
                "active_collection_sessions": len([s for s in sessions if s.status == "collecting"])
            },
            "recent_executions": [
                {
                    "id": str(execution.workflow_id),
                    "workflow_name": execution.workflow_name,
                    "status": execution.status,
                    "started_at": execution.started_at,
                    "progress": execution.calculate_progress(),
                    "products_processed": execution.products_processed
                }
                for execution in executions
            ],
            "recent_alerts": [
                {
                    "id": str(alert.id),
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "created_at": alert.created_at
                }
                for alert in alerts
            ],
            "collection_sessions": [
                {
                    "id": str(session.id),
                    "marketplace": session.marketplace,
                    "status": session.status,
                    "started_at": session.started_at,
                    "items_collected": session.total_items_collected
                }
                for session in sessions
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard overview: {str(e)}"
        )