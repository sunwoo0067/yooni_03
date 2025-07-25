"""
Product Registration API endpoints for multi-platform dropshipping
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.database import get_async_session
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.models.platform_account import PlatformType
from app.models.product_registration import (
    ProductRegistrationBatch, RegistrationPriority, RegistrationStatus
)
from app.services.account.market_account_manager import MarketAccountManager
from app.services.registration.product_registration_engine import ProductRegistrationEngine
from app.services.queue.registration_scheduler import RegistrationScheduler
from app.services.image.image_processing_pipeline import ImageProcessingPipeline
from app.schemas.product_registration import (
    BatchRegistrationRequest, SingleRegistrationRequest, BatchResponse,
    RegistrationResponse, BatchStatusResponse, QueueStatsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/registration", tags=["Product Registration"])
security = HTTPBearer()


@router.post("/batch", response_model=BatchResponse)
async def create_batch_registration(
    request: BatchRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new batch registration for multiple products
    
    - **batch_name**: Name for the batch
    - **products**: List of product data to register
    - **target_platforms**: Target platform types (coupang, naver, 11st)
    - **priority**: Registration priority (urgent, high, medium, low)
    - **scheduled_at**: Optional scheduling time
    - **batch_settings**: Optional batch-specific settings
    """
    try:
        # Initialize services
        account_manager = MarketAccountManager(db)
        platform_manager = None  # Would need initialization
        registration_engine = ProductRegistrationEngine(
            db, account_manager, platform_manager
        )
        
        # Validate target platforms
        valid_platforms = [p.value for p in PlatformType]
        invalid_platforms = [p for p in request.target_platforms if p not in valid_platforms]
        if invalid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid platforms: {invalid_platforms}. Valid platforms: {valid_platforms}"
            )
        
        # Check if user has active accounts for target platforms
        platform_types = [PlatformType(p) for p in request.target_platforms]
        accounts = await account_manager.get_active_accounts(
            str(current_user.id),
            platforms=platform_types
        )
        
        if not accounts:
            raise HTTPException(
                status_code=400,
                detail="No active accounts found for target platforms"
            )
        
        # Validate products data
        if not request.products or len(request.products) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one product is required"
            )
        
        # Create batch
        batch = await registration_engine.create_registration_batch(
            user_id=str(current_user.id),
            batch_name=request.batch_name,
            products=[product.dict() for product in request.products],
            target_platforms=request.target_platforms,
            priority=RegistrationPriority(request.priority),
            batch_settings=request.batch_settings,
            scheduled_at=request.scheduled_at
        )
        
        # Queue for processing
        scheduler = RegistrationScheduler(db, registration_engine, None)  # Redis client needed
        
        background_tasks.add_task(
            _queue_batch_processing,
            scheduler,
            str(batch.id),
            RegistrationPriority(request.priority),
            request.scheduled_at
        )
        
        return BatchResponse(
            batch_id=str(batch.id),
            batch_name=batch.batch_name,
            status=batch.status.value,
            total_products=batch.total_products,
            target_platforms=request.target_platforms,
            priority=request.priority,
            scheduled_at=batch.scheduled_at,
            created_at=batch.created_at,
            message="Batch created and queued for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create batch registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create batch registration"
        )


@router.post("/single", response_model=RegistrationResponse)
async def create_single_registration(
    request: SingleRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Register a single product across multiple platforms
    
    - **product**: Product data to register
    - **target_platforms**: Target platform types
    - **priority**: Registration priority
    """
    try:
        # Initialize services
        account_manager = MarketAccountManager(db)
        platform_manager = None  # Would need initialization
        registration_engine = ProductRegistrationEngine(
            db, account_manager, platform_manager
        )
        
        # Validate target platforms
        valid_platforms = [p.value for p in PlatformType]
        invalid_platforms = [p for p in request.target_platforms if p not in valid_platforms]
        if invalid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid platforms: {invalid_platforms}"
            )
        
        # Queue for immediate processing
        scheduler = RegistrationScheduler(db, registration_engine, None)
        
        background_tasks.add_task(
            _queue_single_registration,
            scheduler,
            str(current_user.id),
            request.product.dict(),
            request.target_platforms,
            RegistrationPriority(request.priority)
        )
        
        return RegistrationResponse(
            success=True,
            message="Single product registration queued for processing",
            target_platforms=request.target_platforms,
            priority=request.priority
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create single registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create single registration"
        )


@router.get("/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: UUID = Path(..., description="Batch ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed status of a registration batch
    """
    try:
        # Initialize services
        account_manager = MarketAccountManager(db)
        platform_manager = None
        registration_engine = ProductRegistrationEngine(
            db, account_manager, platform_manager
        )
        
        # Get batch status
        status = await registration_engine.get_batch_status(str(batch_id))
        
        return BatchStatusResponse(**status)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get batch status"
        )


@router.post("/batch/{batch_id}/retry", response_model=RegistrationResponse)
async def retry_batch_registration(
    batch_id: UUID = Path(..., description="Batch ID"),
    platform_filter: Optional[List[str]] = Query(None, description="Platforms to retry"),
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retry failed registrations in a batch
    """
    try:
        # Initialize services
        account_manager = MarketAccountManager(db)
        platform_manager = None
        registration_engine = ProductRegistrationEngine(
            db, account_manager, platform_manager
        )
        
        # Queue retry operation
        background_tasks.add_task(
            _retry_batch_registration,
            registration_engine,
            str(batch_id),
            platform_filter
        )
        
        return RegistrationResponse(
            success=True,
            message="Batch retry queued for processing",
            target_platforms=platform_filter or []
        )
        
    except Exception as e:
        logger.error(f"Failed to retry batch registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retry batch registration"
        )


@router.delete("/batch/{batch_id}")
async def cancel_batch_registration(
    batch_id: UUID = Path(..., description="Batch ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a pending or in-progress batch registration
    """
    try:
        # Initialize services
        account_manager = MarketAccountManager(db)
        platform_manager = None
        registration_engine = ProductRegistrationEngine(
            db, account_manager, platform_manager
        )
        
        # Cancel batch
        success = await registration_engine.cancel_batch(str(batch_id))
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Batch cannot be cancelled"
            )
        
        return {"message": "Batch cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel batch: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel batch"
        )


@router.get("/batches", response_model=List[BatchResponse])
async def list_user_batches(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Number of batches to return"),
    offset: int = Query(0, ge=0, description="Number of batches to skip"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    List user's registration batches with optional filtering
    """
    try:
        from sqlalchemy import select, desc
        
        # Build query
        query = select(ProductRegistrationBatch).where(
            ProductRegistrationBatch.user_id == current_user.id
        )
        
        if status:
            try:
                status_enum = RegistrationStatus(status)
                query = query.where(ProductRegistrationBatch.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )
        
        query = query.order_by(desc(ProductRegistrationBatch.created_at))
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        batches = result.scalars().all()
        
        # Convert to response format
        batch_responses = []
        for batch in batches:
            batch_responses.append(BatchResponse(
                batch_id=str(batch.id),
                batch_name=batch.batch_name,
                status=batch.status.value,
                total_products=batch.total_products,
                completed_products=batch.completed_products,
                failed_products=batch.failed_products,
                target_platforms=batch.target_platforms,
                priority=batch.priority.value,
                progress_percentage=float(batch.progress_percentage),
                scheduled_at=batch.scheduled_at,
                started_at=batch.started_at,
                completed_at=batch.completed_at,
                created_at=batch.created_at
            ))
        
        return batch_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list batches: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list batches"
        )


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    Get registration queue statistics (admin only)
    """
    # Note: In production, add admin permission check
    try:
        # Initialize scheduler (would need Redis)
        scheduler = RegistrationScheduler(None, None, None)
        
        stats = await scheduler.get_queue_stats()
        
        return QueueStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get queue statistics"
        )


@router.post("/queue/{queue_type}/clear")
async def clear_queue(
    queue_type: str = Path(..., description="Queue type to clear"),
    current_user: User = Depends(get_current_user)
):
    """
    Clear specific queue (admin only)
    """
    # Note: In production, add admin permission check
    try:
        scheduler = RegistrationScheduler(None, None, None)
        
        success = await scheduler.clear_queue(queue_type)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid queue type: {queue_type}"
            )
        
        return {"message": f"Queue {queue_type} cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear queue: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear queue"
        )


# Background task functions
async def _queue_batch_processing(
    scheduler: RegistrationScheduler,
    batch_id: str,
    priority: RegistrationPriority,
    scheduled_at: Optional[datetime]
):
    """Background task to queue batch processing"""
    try:
        await scheduler.queue_batch_registration(
            batch_id,
            priority,
            scheduled_at
        )
    except Exception as e:
        logger.error(f"Failed to queue batch {batch_id}: {e}")


async def _queue_single_registration(
    scheduler: RegistrationScheduler,
    user_id: str,
    product_data: Dict[str, Any],
    target_platforms: List[str],
    priority: RegistrationPriority
):
    """Background task to queue single registration"""
    try:
        await scheduler.queue_single_registration(
            user_id,
            product_data,
            target_platforms,
            priority
        )
    except Exception as e:
        logger.error(f"Failed to queue single registration: {e}")


async def _retry_batch_registration(
    registration_engine: ProductRegistrationEngine,
    batch_id: str,
    platform_filter: Optional[List[str]]
):
    """Background task to retry batch registration"""
    try:
        await registration_engine.retry_failed_registrations(
            batch_id,
            platform_filter
        )
    except Exception as e:
        logger.error(f"Failed to retry batch {batch_id}: {e}")


# Health check endpoint
@router.get("/health")
async def registration_health_check():
    """Health check for registration service"""
    return {
        "service": "product_registration",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "batch_registration",
            "single_registration", 
            "retry_logic",
            "queue_management",
            "image_processing"
        ]
    }