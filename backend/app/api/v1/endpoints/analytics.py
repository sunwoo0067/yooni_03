"""
분석 및 대시보드 API 엔드포인트
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.dependencies.database import get_db

router = APIRouter()


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    period: str = Query("week", regex="^(day|week|month|year)$"),
    db: Session = Depends(get_db)
):
    """대시보드 데이터 조회"""
    # 임시 대시보드 데이터
    return {
        "period": period,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_revenue": 15234500,
            "revenue_change": 12.5,
            "total_orders": 342,
            "orders_change": 8.3,
            "total_customers": 1250,
            "customers_change": 5.2,
            "total_products": 485,
            "products_change": -2.1
        },
        "revenue_trend": [
            {"date": "2025-07-19", "value": 2100000},
            {"date": "2025-07-20", "value": 2350000},
            {"date": "2025-07-21", "value": 1980000},
            {"date": "2025-07-22", "value": 2450000},
            {"date": "2025-07-23", "value": 2680000},
            {"date": "2025-07-24", "value": 2120000},
            {"date": "2025-07-25", "value": 1554500}
        ],
        "category_sales": [
            {"category": "전자제품", "value": 5680000, "percentage": 37.3},
            {"category": "패션", "value": 3450000, "percentage": 22.6},
            {"category": "생활용품", "value": 2890000, "percentage": 19.0},
            {"category": "뷰티", "value": 1980000, "percentage": 13.0},
            {"category": "기타", "value": 1234500, "percentage": 8.1}
        ],
        "platform_orders": [
            {"platform": "쿠팡", "orders": 145, "revenue": 6890000},
            {"platform": "네이버", "orders": 98, "revenue": 4560000},
            {"platform": "11번가", "orders": 67, "revenue": 2340000},
            {"platform": "기타", "orders": 32, "revenue": 1444500}
        ],
        "top_products": [
            {"id": 1, "name": "무선 이어폰 Pro", "sales": 89, "revenue": 3560000},
            {"id": 2, "name": "스마트 워치", "sales": 67, "revenue": 2680000},
            {"id": 3, "name": "미니 가습기", "sales": 125, "revenue": 1875000}
        ],
        "recent_activities": [
            {
                "type": "order",
                "message": "새 주문 #ORD-2025-0342",
                "timestamp": datetime.now().isoformat()
            },
            {
                "type": "product",
                "message": "재고 부족: 무선 이어폰 Pro",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat()
            },
            {
                "type": "sync",
                "message": "쿠팡 상품 동기화 완료",
                "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat()
            }
        ]
    }


@router.get("/sales", response_model=Dict[str, Any])
async def get_sales_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db)
):
    """매출 분석 데이터"""
    return {
        "period": {
            "start": start_date or (datetime.now() - timedelta(days=30)).isoformat(),
            "end": end_date or datetime.now().isoformat()
        },
        "group_by": group_by,
        "total_revenue": 45678900,
        "average_order_value": 133500,
        "data": [
            {"date": "2025-07-01", "revenue": 1520000, "orders": 12},
            {"date": "2025-07-02", "revenue": 1890000, "orders": 15},
            # ... 더 많은 데이터
        ]
    }


@router.get("/products/performance", response_model=List[Dict[str, Any]])
async def get_product_performance(
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("revenue", regex="^(revenue|quantity|profit_margin)$"),
    db: Session = Depends(get_db)
):
    """상품 성과 분석"""
    return [
        {
            "product_id": 1,
            "name": "무선 이어폰 Pro",
            "revenue": 3560000,
            "quantity_sold": 89,
            "profit_margin": 35.2,
            "conversion_rate": 12.5,
            "return_rate": 2.1
        },
        {
            "product_id": 2,
            "name": "스마트 워치",
            "revenue": 2680000,
            "quantity_sold": 67,
            "profit_margin": 42.1,
            "conversion_rate": 10.8,
            "return_rate": 1.5
        }
    ]


@router.get("/customers/insights", response_model=Dict[str, Any])
async def get_customer_insights(db: Session = Depends(get_db)):
    """고객 인사이트"""
    return {
        "total_customers": 1250,
        "new_customers_this_month": 156,
        "returning_customer_rate": 68.5,
        "average_lifetime_value": 456000,
        "top_customer_segments": [
            {"segment": "VIP", "count": 125, "revenue_contribution": 4560000},
            {"segment": "Regular", "count": 680, "revenue_contribution": 8900000},
            {"segment": "New", "count": 445, "revenue_contribution": 1774500}
        ]
    }