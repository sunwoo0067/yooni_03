"""
재고 동기화 API 엔드포인트
"""
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.database import get_async_db
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.services.sync.real_inventory_sync import real_inventory_sync
from app.core.cache import invalidate_cache

router = APIRouter()


@router.post("/sync-all")
@invalidate_cache("products_list:*")
async def sync_all_inventory(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """전체 재고 동기화"""
    try:
        result = await real_inventory_sync.sync_all_inventory(db)
        return {
            "message": "재고 동기화가 완료되었습니다",
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"재고 동기화 실패: {str(e)}"
        )


@router.post("/sync-critical")
@invalidate_cache("products_list:*")
async def sync_critical_inventory(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """임계 재고 상품 동기화 (재고 10개 이하)"""
    try:
        result = await real_inventory_sync.sync_critical_inventory(db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"임계 재고 동기화 실패: {str(e)}"
        )


@router.post("/sync-product/{product_id}")
@invalidate_cache("product_detail:*")
async def sync_product_inventory(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """특정 상품 재고 동기화"""
    try:
        result = await real_inventory_sync.force_sync_product(db, product_id)
        return {
            "message": "상품 재고가 동기화되었습니다",
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상품 재고 동기화 실패: {str(e)}"
        )


@router.get("/discrepancies")
async def check_inventory_discrepancies(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """재고 불일치 확인"""
    try:
        discrepancies = await real_inventory_sync.check_stock_discrepancy(db)
        
        return {
            "total_discrepancies": len(discrepancies),
            "items": discrepancies,
            "summary": {
                "total_difference": sum(d["difference"] for d in discrepancies),
                "overstock_count": sum(1 for d in discrepancies if d["difference"] < 0),
                "understock_count": sum(1 for d in discrepancies if d["difference"] > 0)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"재고 불일치 확인 실패: {str(e)}"
        )


@router.get("/history/{product_id}")
async def get_inventory_history(
    product_id: int,
    days: int = Query(30, description="조회 기간 (일)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """상품 재고 변경 이력 조회"""
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.models.inventory import InventoryHistory
    
    since_date = datetime.now() - timedelta(days=days)
    
    query = select(InventoryHistory).where(
        InventoryHistory.product_id == product_id,
        InventoryHistory.created_at >= since_date
    ).order_by(InventoryHistory.created_at.desc())
    
    result = await db.execute(query)
    history = result.scalars().all()
    
    return {
        "product_id": product_id,
        "period": {
            "from": since_date.isoformat(),
            "to": datetime.now().isoformat()
        },
        "history": [
            {
                "id": h.id,
                "old_stock": h.old_stock,
                "new_stock": h.new_stock,
                "change_quantity": h.change_quantity,
                "change_source": h.change_source,
                "created_at": h.created_at.isoformat()
            }
            for h in history
        ]
    }


@router.get("/sync-status")
async def get_sync_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """재고 동기화 상태 조회"""
    from datetime import datetime, timedelta
    from sqlalchemy import select, func
    from app.models.inventory import InventoryHistory
    
    # 최근 24시간 동기화 통계
    since_date = datetime.now() - timedelta(hours=24)
    
    # 동기화 횟수
    sync_count_query = select(func.count()).select_from(InventoryHistory).where(
        InventoryHistory.created_at >= since_date,
        InventoryHistory.change_source == "wholesaler_sync"
    )
    sync_count = await db.scalar(sync_count_query)
    
    # 변경된 상품 수
    changed_products_query = select(
        func.count(func.distinct(InventoryHistory.product_id))
    ).where(
        InventoryHistory.created_at >= since_date,
        InventoryHistory.change_quantity != 0
    )
    changed_products = await db.scalar(changed_products_query)
    
    # 마지막 동기화 시간
    last_sync_query = select(
        func.max(InventoryHistory.created_at)
    ).where(
        InventoryHistory.change_source == "wholesaler_sync"
    )
    last_sync = await db.scalar(last_sync_query)
    
    return {
        "status": "active",
        "sync_interval_minutes": 5,
        "statistics": {
            "last_24h_sync_count": sync_count,
            "last_24h_changed_products": changed_products,
            "last_sync_time": last_sync.isoformat() if last_sync else None
        }
    }