"""
통합 주문 관리 API 엔드포인트
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.api.v1.dependencies.database import get_db, get_async_db
from app.core.cache import cache_result, invalidate_cache
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.models.order_core import Order, OrderStatus, OrderItem
from app.models.product import Product
from app.services.order_automation.real_order_processor import real_order_processor
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderListResponse

router = APIRouter()


@router.get("/", response_model=OrderListResponse)
@cache_result(prefix="orders_list", ttl=60)  # 1분 캐싱
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    platform: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """주문 목록 조회"""
    # 쿼리 빌드
    query = select(Order)
    
    # 필터 적용
    filters = []
    if status:
        filters.append(Order.status == status)
    if platform:
        filters.append(Order.platform_type == platform)
    if date_from:
        filters.append(Order.created_at >= date_from)
    if date_to:
        filters.append(Order.created_at <= date_to)
        
    if filters:
        query = query.where(and_(*filters))
        
    # 정렬
    query = query.order_by(Order.created_at.desc())
    
    # 전체 개수 조회
    count_query = select(func.count()).select_from(Order)
    if filters:
        count_query = count_query.where(and_(*filters))
    total = await db.scalar(count_query)
    
    # 페이지네이션
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # 실행
    result = await db.execute(query)
    orders = result.scalars().all()
    
    # 응답 구성
    order_list = []
    for order in orders:
        # 주문 아이템 조회
        items_query = select(OrderItem).where(OrderItem.order_id == order.id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "platform": order.platform_type,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "total_amount": sum(item.price * item.quantity for item in items),
            "status": order.status.value,
            "tracking_number": order.tracking_number,
            "created_at": order.created_at.isoformat(),
            "items_count": len(items)
        }
        order_list.append(order_dict)
    
    return OrderListResponse(
        items=order_list,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{order_id}", response_model=OrderResponse)
@cache_result(prefix="order_detail", ttl=300)  # 5분 캐싱
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """주문 상세 조회"""
    # 주문 조회
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
    # 주문 아이템 조회
    items_query = select(OrderItem).where(OrderItem.order_id == order.id)
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()
    
    # 아이템별 상품 정보 조회
    items_detail = []
    for item in items:
        product = await db.get(Product, item.product_id)
        items_detail.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": product.name if product else "상품 정보 없음",
            "product_sku": product.sku if product else None,
            "quantity": item.quantity,
            "price": float(item.price),
            "subtotal": float(item.price * item.quantity)
        })
    
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        platform=order.platform_type,
        status=order.status.value,
        customer={
            "name": order.customer_name,
            "phone": order.customer_phone,
            "email": order.customer_email,
            "address": order.shipping_address,
            "memo": order.customer_memo
        },
        items=items_detail,
        total_amount=sum(item["subtotal"] for item in items_detail),
        shipping_fee=float(order.shipping_fee) if order.shipping_fee else 0,
        tracking_number=order.tracking_number,
        wholesaler_order_id=order.wholesaler_order_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        internal_memo=order.internal_memo
    )


@router.post("/sync")
@invalidate_cache("orders_list:*")
async def sync_orders(
    platform: Optional[str] = None,
    hours: int = Query(24, description="동기화할 시간 범위 (시간)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """플랫폼 주문 동기화"""
    try:
        from app.services.sync.order_sync import OrderSyncService
        
        sync_service = OrderSyncService()
        
        # 동기화 시작 시간 계산
        since = datetime.now() - timedelta(hours=hours)
        
        # 플랫폼별 또는 전체 동기화
        if platform:
            result = await sync_service.sync_platform_orders(platform, since)
        else:
            result = await sync_service.sync_all_orders(since)
            
        return {
            "message": "주문 동기화가 완료되었습니다",
            "synced_count": result.get("synced_count", 0),
            "errors": result.get("errors", []),
            "started_at": result.get("started_at"),
            "completed_at": result.get("completed_at")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"주문 동기화 실패: {str(e)}"
        )


@router.post("/process-pending")
async def process_pending_orders(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """대기 중인 주문 처리"""
    try:
        results = await real_order_processor.process_new_orders(db)
        
        # 결과 요약
        success_count = sum(1 for r in results if r.status.value == "completed")
        failed_count = sum(1 for r in results if r.status.value == "failed")
        
        return {
            "message": "주문 처리가 완료되었습니다",
            "total_processed": len(results),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": [
                {
                    "order_id": r.order_id,
                    "status": r.status.value,
                    "wholesaler_order_id": r.wholesaler_order_id,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"주문 처리 실패: {str(e)}"
        )


@router.patch("/{order_id}/status")
@invalidate_cache("orders_list:*")
@invalidate_cache("order_detail:*")
async def update_order_status(
    order_id: int,
    status: OrderStatus,
    memo: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """주문 상태 업데이트"""
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
    # 상태 전환 유효성 검사
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
        OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.FAILED, OrderStatus.CANCELLED],
        OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.RETURNED],
        OrderStatus.DELIVERED: [OrderStatus.RETURNED],
        OrderStatus.CANCELLED: [],
        OrderStatus.FAILED: [],
        OrderStatus.RETURNED: []
    }
    
    if status not in valid_transitions.get(order.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"{order.status.value}에서 {status.value}로 변경할 수 없습니다"
        )
    
    # 상태 업데이트
    order.status = status
    order.updated_at = datetime.now()
    
    # 상태별 추가 처리
    if status == OrderStatus.SHIPPED:
        order.shipped_at = datetime.now()
    elif status == OrderStatus.DELIVERED:
        order.delivered_at = datetime.now()
        
    if memo:
        order.internal_memo = (order.internal_memo or "") + f"\n[{datetime.now()}] {memo}"
        
    await db.commit()
    
    return {
        "id": order_id,
        "status": status.value,
        "updated_at": order.updated_at.isoformat(),
        "message": "주문 상태가 업데이트되었습니다"
    }


@router.post("/{order_id}/cancel")
@invalidate_cache("orders_list:*")
@invalidate_cache("order_detail:*")
async def cancel_order(
    order_id: int,
    reason: str = Query(..., description="취소 사유"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """주문 취소"""
    try:
        success = await real_order_processor.cancel_order(db, order_id, reason)
        
        if success:
            return {
                "message": "주문이 취소되었습니다",
                "order_id": order_id,
                "cancelled_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="주문 취소 처리 중 오류가 발생했습니다"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/analytics/summary")
async def get_order_analytics(
    days: int = Query(7, description="분석 기간 (일)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """주문 분석 요약"""
    since_date = datetime.now() - timedelta(days=days)
    
    # 전체 주문 수
    total_query = select(func.count()).select_from(Order).where(
        Order.created_at >= since_date
    )
    total_orders = await db.scalar(total_query)
    
    # 상태별 주문 수
    status_query = select(
        Order.status,
        func.count().label('count')
    ).where(
        Order.created_at >= since_date
    ).group_by(Order.status)
    
    status_result = await db.execute(status_query)
    status_breakdown = {row.status.value: row.count for row in status_result}
    
    # 플랫폼별 주문 수
    platform_query = select(
        Order.platform_type,
        func.count().label('count')
    ).where(
        Order.created_at >= since_date
    ).group_by(Order.platform_type)
    
    platform_result = await db.execute(platform_query)
    platform_breakdown = {row.platform_type: row.count for row in platform_result}
    
    # 일별 주문 추이
    daily_query = select(
        func.date(Order.created_at).label('date'),
        func.count().label('count')
    ).where(
        Order.created_at >= since_date
    ).group_by('date').order_by('date')
    
    daily_result = await db.execute(daily_query)
    daily_trend = [
        {"date": row.date.isoformat(), "count": row.count}
        for row in daily_result
    ]
    
    return {
        "period": {
            "from": since_date.isoformat(),
            "to": datetime.now().isoformat(),
            "days": days
        },
        "summary": {
            "total_orders": total_orders,
            "average_daily": total_orders / days if days > 0 else 0
        },
        "status_breakdown": status_breakdown,
        "platform_breakdown": platform_breakdown,
        "daily_trend": daily_trend
    }


@router.post("/{order_id}/tracking")
@invalidate_cache("order_detail:*")
async def update_tracking_number(
    order_id: int,
    tracking_number: str,
    courier: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """운송장 번호 업데이트"""
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
    order.tracking_number = tracking_number
    if courier:
        order.courier = courier
    order.updated_at = datetime.now()
    
    # 배송 시작으로 상태 변경
    if order.status == OrderStatus.PROCESSING:
        order.status = OrderStatus.SHIPPED
        order.shipped_at = datetime.now()
        
    await db.commit()
    
    return {
        "message": "운송장 번호가 업데이트되었습니다",
        "order_id": order_id,
        "tracking_number": tracking_number,
        "courier": courier
    }