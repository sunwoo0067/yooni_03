"""
주문 관리 API 엔드포인트
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    platform_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """주문 목록 조회"""
    # 임시 응답 데이터
    mock_orders = [
        {
            "id": 1,
            "order_number": "ORD-2025-0001",
            "platform": "쿠팡",
            "customer_name": "김철수",
            "total_amount": 75000,
            "status": "processing",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": 2,
            "order_number": "ORD-2025-0002",
            "platform": "네이버",
            "customer_name": "이영희",
            "total_amount": 120000,
            "status": "shipped",
            "created_at": datetime.now().isoformat()
        }
    ]
    
    return {
        "items": mock_orders,
        "total": 2,
        "page": page,
        "page_size": page_size,
        "pages": 1
    }


@router.get("/{order_id}")
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """주문 상세 조회"""
    return {
        "id": order_id,
        "order_number": f"ORD-2025-{order_id:04d}",
        "platform": "쿠팡",
        "customer": {
            "name": "김철수",
            "phone": "010-1234-5678",
            "address": "서울시 강남구 테헤란로 123"
        },
        "items": [
            {
                "product_name": "무선 이어폰",
                "quantity": 1,
                "price": 75000
            }
        ],
        "total_amount": 75000,
        "status": "processing",
        "created_at": datetime.now().isoformat()
    }


@router.post("/sync")
async def sync_orders(platform_id: Optional[int] = None, db: Session = Depends(get_db)):
    """플랫폼 주문 동기화"""
    return {
        "message": "주문 동기화가 시작되었습니다",
        "platform_id": platform_id,
        "started_at": datetime.now().isoformat()
    }


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """주문 상태 업데이트"""
    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(400, f"유효하지 않은 상태입니다. 가능한 값: {valid_statuses}")
    
    return {
        "id": order_id,
        "status": status,
        "updated_at": datetime.now().isoformat()
    }