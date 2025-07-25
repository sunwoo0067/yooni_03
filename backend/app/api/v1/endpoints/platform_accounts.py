"""
API endpoints for platform account management
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ....services.database.database import get_db
from ....services.platform_account_service import get_platform_account_service
from ....schemas.platform_account import (
    PlatformAccountCreate,
    PlatformAccountUpdate,
    PlatformAccountResponse,
    PlatformAccountSummary,
    PlatformAccountConnectionTest,
    PlatformInfo,
    PlatformAccountStats,
    BulkOperationRequest,
    BulkOperationResponse,
    PlatformSyncLogResponse,
    AccountStatusEnum
)
from ....models.platform_account import AccountStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get current user ID (placeholder - implement based on your auth system)
async def get_current_user_id() -> UUID:
    """Get current authenticated user ID"""
    # TODO: Implement actual authentication logic
    # This is a placeholder that should be replaced with your auth system
    from uuid import uuid4
    return uuid4()  # Replace with actual user ID from JWT token or session


@router.post("/", response_model=PlatformAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_platform_account(
    account_data: PlatformAccountCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a new platform account
    
    - **platform_type**: Platform type (coupang, naver, 11st, etc.)
    - **account_name**: Display name for the account
    - **account_id**: Platform-specific account identifier
    - **credentials**: Platform-specific authentication credentials
    - **Additional settings**: Various configuration options
    """
    try:
        service = get_platform_account_service(db)
        account, connection_success = await service.create_account(current_user_id, account_data)
        
        # Schedule a health check in the background
        background_tasks.add_task(
            schedule_health_check,
            str(account.id),
            str(current_user_id)
        )
        
        # Convert to response model
        response = PlatformAccountResponse.from_orm(account)
        response.has_credentials = True
        response.credentials_status = "valid" if connection_success else "invalid"
        
        return response
        
    except ValueError as e:
        logger.error(f"Failed to create platform account: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating platform account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create platform account"
        )


@router.get("/", response_model=List[PlatformAccountSummary])
async def get_platform_accounts(
    platform_type: Optional[str] = Query(None, description="Filter by platform type"),
    status: Optional[AccountStatusEnum] = Query(None, description="Filter by account status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get list of platform accounts for the current user
    
    - **platform_type**: Optional filter by platform type
    - **status**: Optional filter by account status
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    """
    try:
        service = get_platform_account_service(db)
        
        # Convert status enum to model enum if provided
        status_filter = AccountStatus(status.value) if status else None
        
        accounts = service.get_user_accounts(
            current_user_id, platform_type, status_filter, skip, limit
        )
        
        return [PlatformAccountSummary.from_orm(account) for account in accounts]
        
    except Exception as e:
        logger.error(f"Failed to get platform accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform accounts"
        )


@router.get("/{account_id}", response_model=PlatformAccountResponse)
async def get_platform_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get a specific platform account by ID
    
    - **account_id**: UUID of the platform account
    """
    try:
        service = get_platform_account_service(db)
        account = service.get_account(account_id, current_user_id)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform account not found"
            )
        
        response = PlatformAccountResponse.from_orm(account)
        response.has_credentials = bool(account.api_key or account.api_secret)
        response.credentials_status = "configured" if response.has_credentials else "missing"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get platform account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform account"
        )


@router.put("/{account_id}", response_model=PlatformAccountResponse)
async def update_platform_account(
    account_id: UUID,
    update_data: PlatformAccountUpdate,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update a platform account
    
    - **account_id**: UUID of the platform account to update
    - **Update fields**: Any combination of updatable fields
    """
    try:
        service = get_platform_account_service(db)
        account = service.update_account(account_id, current_user_id, update_data)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform account not found"
            )
        
        response = PlatformAccountResponse.from_orm(account)
        response.has_credentials = bool(account.api_key or account.api_secret)
        response.credentials_status = "configured" if response.has_credentials else "missing"
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Failed to update platform account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating platform account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update platform account"
        )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a platform account
    
    - **account_id**: UUID of the platform account to delete
    
    **Warning**: This will permanently delete the account and all associated data.
    """
    try:
        service = get_platform_account_service(db)
        success = service.delete_account(account_id, current_user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform account not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete platform account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete platform account"
        )


@router.post("/{account_id}/test", response_model=PlatformAccountConnectionTest)
async def test_platform_account_connection(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Test connection to a platform account
    
    - **account_id**: UUID of the platform account to test
    
    This endpoint will attempt to connect to the platform API using the stored credentials
    and return the connection status along with performance metrics.
    """
    try:
        service = get_platform_account_service(db)
        test_result = await service.test_connection(account_id, current_user_id)
        
        return test_result
        
    except Exception as e:
        logger.error(f"Failed to test platform account connection {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test platform connection"
        )


@router.get("/platforms/supported", response_model=List[PlatformInfo])
async def get_supported_platforms(
    db: Session = Depends(get_db)
):
    """
    Get list of supported platforms with their configuration requirements
    
    Returns information about all supported e-commerce platforms including:
    - Required credentials
    - API documentation links
    - Rate limits and quotas
    - Supported features
    """
    try:
        service = get_platform_account_service(db)
        platforms = service.get_supported_platforms()
        
        return platforms
        
    except Exception as e:
        logger.error(f"Failed to get supported platforms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supported platforms"
        )


@router.get("/statistics/summary", response_model=PlatformAccountStats)
async def get_account_statistics(
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get comprehensive statistics for user's platform accounts
    
    Returns:
    - Total number of accounts
    - Account status breakdown
    - Platform distribution
    - Health status summary
    """
    try:
        service = get_platform_account_service(db)
        stats = service.get_user_account_statistics(current_user_id)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get account statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account statistics"
        )


@router.post("/bulk/test-connections", response_model=BulkOperationResponse)
async def bulk_test_connections(
    request: BulkOperationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Test connections for multiple platform accounts
    
    - **account_ids**: List of account UUIDs to test
    
    This operation may take some time depending on the number of accounts
    and platform response times.
    """
    try:
        if request.operation != "test_connections":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid operation. Expected 'test_connections'"
            )
        
        service = get_platform_account_service(db)
        account_ids = [UUID(id_str) for id_str in request.account_ids]
        
        result = await service.bulk_test_connections(account_ids, current_user_id)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to bulk test connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test platform connections"
        )


@router.post("/bulk/update-sync-settings", response_model=BulkOperationResponse)
async def bulk_update_sync_settings(
    request: BulkOperationRequest,
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Bulk update synchronization settings for multiple accounts
    
    - **account_ids**: List of account UUIDs to update
    - **parameters**: Dictionary containing sync settings:
      - sync_enabled: boolean
      - auto_pricing_enabled: boolean (optional)
      - auto_inventory_sync: boolean (optional)
    """
    try:
        if request.operation != "update_sync_settings":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid operation. Expected 'update_sync_settings'"
            )
        
        if not request.parameters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parameters required for sync settings update"
            )
        
        sync_enabled = request.parameters.get("sync_enabled")
        if sync_enabled is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sync_enabled parameter is required"
            )
        
        service = get_platform_account_service(db)
        account_ids = [UUID(id_str) for id_str in request.account_ids]
        
        result = service.bulk_update_sync_settings(
            account_ids,
            current_user_id,
            sync_enabled,
            request.parameters.get("auto_pricing_enabled"),
            request.parameters.get("auto_inventory_sync")
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request data: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk update sync settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update sync settings"
        )


@router.post("/health-check/run")
async def run_health_checks(
    background_tasks: BackgroundTasks,
    all_users: bool = Query(False, description="Run health checks for all users (admin only)"),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Trigger health checks for platform accounts
    
    - **all_users**: If true, run health checks for all users (requires admin privileges)
    
    Health checks will be performed in the background and results will be
    stored in the account health status fields.
    """
    try:
        # Add health check task to background
        if all_users:
            # TODO: Add admin privilege check
            background_tasks.add_task(perform_health_checks, None)
            return {"message": "Health checks scheduled for all users"}
        else:
            background_tasks.add_task(perform_health_checks, str(current_user_id))
            return {"message": "Health checks scheduled for your accounts"}
        
    except Exception as e:
        logger.error(f"Failed to schedule health checks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule health checks"
        )


@router.get("/{account_id}/sync-logs", response_model=List[PlatformSyncLogResponse])
async def get_sync_logs(
    account_id: UUID,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of logs to return"),
    db: Session = Depends(get_db),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get synchronization logs for a platform account
    
    - **account_id**: UUID of the platform account
    - **limit**: Maximum number of log entries to return
    """
    try:
        service = get_platform_account_service(db)
        
        # Verify account ownership
        account = service.get_account(account_id, current_user_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Platform account not found"
            )
        
        # Get sync logs
        sync_logs = service.sync_log_crud.get_recent_sync_logs(account_id, limit)
        
        # Convert to response models
        response_logs = []
        for log in sync_logs:
            response_log = PlatformSyncLogResponse.from_orm(log)
            response_log.success_rate = log.calculate_success_rate()
            response_logs.append(response_log)
        
        return response_logs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync logs for account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync logs"
        )


# Background task functions
async def schedule_health_check(account_id: str, user_id: str):
    """Background task to schedule a health check"""
    try:
        # This would typically be implemented with a task queue like Celery
        # For now, we'll just log the scheduling
        logger.info(f"Health check scheduled for account {account_id}")
        
        # In a real implementation, you would:
        # 1. Add the task to a queue
        # 2. Have a worker process handle the health check
        # 3. Update the account status based on results
        
    except Exception as e:
        logger.error(f"Failed to schedule health check: {e}")


async def perform_health_checks(user_id: Optional[str]):
    """Background task to perform health checks"""
    try:
        # This would be implemented with proper task queue handling
        logger.info(f"Performing health checks for user {user_id if user_id else 'all users'}")
        
        # In a real implementation:
        # 1. Get database session
        # 2. Get platform account service
        # 3. Call service.perform_health_checks()
        # 4. Handle results and notifications
        
    except Exception as e:
        logger.error(f"Health check task failed: {e}")


# Error handlers for common exceptions
# Note: APIRouter doesn't support exception_handler decorator
# These are handled at the app level in main.py