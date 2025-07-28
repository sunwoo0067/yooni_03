"""API endpoints for platform synchronization."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.database import get_db
from app.models.user import User
from app.models.platform_account import PlatformType
from app.services.sync.sync_manager import SyncManager
from app.services.platform_account_service import PlatformAccountService

router = APIRouter()


# Request/Response Models
class SyncProductsRequest(BaseModel):
    """Request model for product synchronization."""
    platform_account_ids: Optional[List[int]] = Field(
        None,
        description="Specific platform account IDs to sync. If not provided, syncs all active accounts."
    )
    product_ids: Optional[List[int]] = Field(
        None,
        description="Specific product IDs to sync. If not provided, syncs all products."
    )


class SyncOrdersRequest(BaseModel):
    """Request model for order synchronization."""
    platform_account_ids: Optional[List[int]] = Field(
        None,
        description="Specific platform account IDs to sync. If not provided, syncs all active accounts."
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Start date for order sync. Defaults to 7 days ago."
    )
    end_date: Optional[datetime] = Field(
        None,
        description="End date for order sync. Defaults to now."
    )


class SyncInventoryRequest(BaseModel):
    """Request model for inventory synchronization."""
    platform_account_ids: Optional[List[int]] = Field(
        None,
        description="Specific platform account IDs to sync. If not provided, syncs all active accounts."
    )
    product_ids: Optional[List[int]] = Field(
        None,
        description="Specific product IDs to sync. If not provided, syncs all products."
    )
    auto_disable_out_of_stock: bool = Field(
        True,
        description="Automatically disable products that are out of stock"
    )


class TestConnectionRequest(BaseModel):
    """Request model for testing platform connection."""
    platform: PlatformType = Field(..., description="Platform type")
    account_id: int = Field(..., description="Platform account ID")


class ScheduleSyncRequest(BaseModel):
    """Request model for scheduling automatic synchronization."""
    interval_minutes: int = Field(
        60,
        ge=15,
        le=1440,
        description="Sync interval in minutes (15 min to 24 hours)"
    )
    sync_types: List[str] = Field(
        ["products", "orders", "inventory"],
        description="Types of sync to perform"
    )
    active_hours: Optional[Dict[str, int]] = Field(
        None,
        description="Active hours for sync (e.g., {'start': 9, 'end': 18})"
    )


class WebhookRequest(BaseModel):
    """Request model for platform webhooks."""
    platform: PlatformType = Field(..., description="Platform type")
    event_type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Webhook payload")


# Endpoints
@router.post("/products", summary="Sync products across platforms")
async def sync_products(
    request: SyncProductsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Synchronize products across all configured platforms.
    
    This endpoint:
    - Syncs local products to platforms (create/update)
    - Syncs platform products to local database
    - Updates product mappings
    """
    sync_manager = SyncManager(db)
    
    # Get platform accounts
    if request.platform_account_ids:
        platform_accounts = []
        for account_id in request.platform_account_ids:
            account = await PlatformAccountService.get_account(db, account_id, current_user.id)
            if account and account.is_active:
                platform_accounts.append(account)
    else:
        platform_accounts = None
    
    # Start sync in background
    background_tasks.add_task(
        sync_manager.sync_products,
        current_user.id,
        platform_accounts
    )
    
    return {
        "message": "Product synchronization started",
        "sync_type": "products",
        "platform_accounts": len(platform_accounts) if platform_accounts else "all"
    }


@router.post("/orders", summary="Sync orders from platforms")
async def sync_orders(
    request: SyncOrdersRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Synchronize orders from all configured platforms.
    
    This endpoint:
    - Fetches new orders from platforms
    - Creates/updates local orders
    - Updates inventory based on orders
    """
    sync_manager = SyncManager(db)
    
    # Get platform accounts
    if request.platform_account_ids:
        platform_accounts = []
        for account_id in request.platform_account_ids:
            account = await PlatformAccountService.get_account(db, account_id, current_user.id)
            if account and account.is_active:
                platform_accounts.append(account)
    else:
        platform_accounts = None
    
    # Set date range
    end_date = request.end_date or datetime.now()
    start_date = request.start_date or (end_date - timedelta(days=7))
    
    # Start sync
    result = await sync_manager.sync_orders(current_user.id, platform_accounts)
    
    return {
        "message": "Order synchronization completed",
        "sync_type": "orders",
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "result": result
    }


@router.post("/inventory", summary="Sync inventory across platforms")
async def sync_inventory(
    request: SyncInventoryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Synchronize inventory levels across all platforms.
    
    This endpoint:
    - Fetches current inventory from all platforms
    - Calculates unified inventory
    - Updates all platforms with synchronized values
    - Optionally disables out-of-stock products
    """
    sync_manager = SyncManager(db)
    
    # Get platform accounts
    if request.platform_account_ids:
        platform_accounts = []
        for account_id in request.platform_account_ids:
            account = await PlatformAccountService.get_account(db, account_id, current_user.id)
            if account and account.is_active:
                platform_accounts.append(account)
    else:
        platform_accounts = None
    
    # Start sync
    result = await sync_manager.sync_inventory(current_user.id, platform_accounts)
    
    # Auto-disable out of stock products if requested
    if request.auto_disable_out_of_stock and result.get("low_stock_alerts"):
        out_of_stock = [p for p in result["low_stock_alerts"] if p["stock_status"] == "out_of_stock"]
        if out_of_stock:
            disable_result = await sync_manager.inventory_sync.auto_disable_out_of_stock(current_user.id)
            result["auto_disabled"] = disable_result
    
    return {
        "message": "Inventory synchronization completed",
        "sync_type": "inventory",
        "result": result
    }


@router.get("/status", summary="Get synchronization status")
async def get_sync_status(
    sync_id: Optional[str] = Query(None, description="Specific sync ID to get status for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the status of synchronization operations.
    
    Returns:
    - Active synchronizations
    - Recent sync history
    - Sync results
    """
    sync_manager = SyncManager(db)
    
    status = await sync_manager.get_sync_status(sync_id)
    
    return {
        "sync_status": status,
        "user_id": current_user.id
    }


@router.post("/platforms/{platform}/test", summary="Test platform connection")
async def test_platform_connection(
    platform: PlatformType,
    request: TestConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Test connection to a specific platform account.
    
    This endpoint verifies:
    - API credentials are valid
    - Platform is accessible
    - Account has proper permissions
    """
    # Verify account ownership
    account = await PlatformAccountService.get_account(db, request.account_id, current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Platform account not found")
    
    if account.platform != platform:
        raise HTTPException(status_code=400, detail="Platform type mismatch")
    
    sync_manager = SyncManager(db)
    
    result = await sync_manager.test_platform_connection(platform, request.account_id)
    
    return result


@router.get("/logs", summary="Get synchronization logs")
async def get_sync_logs(
    start_date: Optional[datetime] = Query(None, description="Start date for logs"),
    end_date: Optional[datetime] = Query(None, description="End date for logs"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    sync_type: Optional[str] = Query(None, description="Filter by sync type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get synchronization logs for debugging and monitoring.
    
    Returns detailed logs of all sync operations including:
    - Timestamps
    - Success/failure status
    - Error messages
    - Affected items
    """
    # This would typically query a sync_logs table
    # For now, return from sync manager's history
    sync_manager = SyncManager(db)
    
    logs = sync_manager._sync_history
    
    # Filter logs based on parameters
    filtered_logs = []
    for log in logs:
        if start_date and log.get("started_at") < start_date:
            continue
        if end_date and log.get("started_at") > end_date:
            continue
        if platform and platform.value not in log.get("platforms", []):
            continue
        if sync_type and sync_type not in log.get("types", []):
            continue
        
        filtered_logs.append(log)
    
    # Limit results
    filtered_logs = filtered_logs[-limit:]
    
    return {
        "logs": filtered_logs,
        "total": len(filtered_logs),
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "platform": platform.value if platform else None,
            "sync_type": sync_type
        }
    }


@router.post("/schedule", summary="Schedule automatic synchronization")
async def schedule_sync(
    request: ScheduleSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule automatic synchronization for the user's platforms.
    
    This sets up periodic sync tasks that will run at the specified interval.
    """
    sync_manager = SyncManager(db)
    
    schedule_config = {
        "interval": request.interval_minutes,
        "sync_types": request.sync_types,
        "active_hours": request.active_hours
    }
    
    result = await sync_manager.schedule_sync(current_user.id, schedule_config)
    
    return {
        "message": "Synchronization scheduled successfully",
        "schedule": result
    }


@router.post("/webhook", summary="Handle platform webhooks")
async def handle_webhook(
    request: WebhookRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle webhooks from e-commerce platforms.
    
    This endpoint processes real-time updates from platforms including:
    - New orders
    - Order status changes
    - Inventory updates
    - Product changes
    """
    sync_manager = SyncManager(db)
    
    # Process webhook based on platform and event type
    if request.event_type.startswith("order"):
        result = await sync_manager.order_sync.process_webhooks(
            request.data,
            request.platform
        )
    else:
        result = {"message": "Webhook received but not processed", "event_type": request.event_type}
    
    return {
        "status": "processed",
        "platform": request.platform.value,
        "event_type": request.event_type,
        "result": result
    }


@router.post("/all", summary="Perform full synchronization")
async def sync_all(
    background_tasks: BackgroundTasks,
    sync_types: Optional[List[str]] = Query(
        None,
        description="Types of sync to perform. If not specified, performs all types."
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform a full synchronization across all platforms and types.
    
    This is a comprehensive sync that includes:
    - Products (bidirectional)
    - Orders (from platforms)
    - Inventory (synchronization)
    
    This operation may take several minutes for large catalogs.
    """
    sync_manager = SyncManager(db)
    
    # Start full sync in background
    background_tasks.add_task(
        sync_manager.sync_all,
        current_user.id,
        sync_types
    )
    
    return {
        "message": "Full synchronization started",
        "sync_types": sync_types or ["products", "orders", "inventory"],
        "status": "processing"
    }