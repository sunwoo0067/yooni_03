"""
API router configuration with V2 endpoints.
V2 엔드포인트가 포함된 API 라우터 구성.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    products_v2,
    orders_v2,
    benchmark_dashboard
)

# V2 API 라우터
api_router_v2 = APIRouter()

# V2 엔드포인트 등록
api_router_v2.include_router(
    products_v2.router,
    prefix="/products",
    tags=["products-v2"]
)

api_router_v2.include_router(
    orders_v2.router,
    prefix="/orders",
    tags=["orders-v2"]
)

api_router_v2.include_router(
    benchmark_dashboard.router,
    prefix="/benchmarks",
    tags=["benchmarks"]
)