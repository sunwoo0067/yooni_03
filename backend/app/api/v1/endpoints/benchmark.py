"""
벤치마크 API 엔드포인트
시장 데이터 조회 및 분석
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.api.v1.dependencies.database import get_db
from app.services.benchmark.benchmark_manager import BenchmarkManager
from app.services.sourcing.smart_sourcing_engine_v2 import SmartSourcingEngine
from app.models.benchmark import BenchmarkProduct

router = APIRouter()


@router.get("/products/search")
async def search_benchmark_products(
    keyword: str = Query(..., description="검색 키워드"),
    category: Optional[str] = Query(None, description="카테고리"),
    min_price: Optional[int] = Query(None, description="최소 가격"),
    max_price: Optional[int] = Query(None, description="최대 가격"),
    market: Optional[str] = Query(None, description="마켓 (coupang, naver, 11st)"),
    limit: int = Query(50, description="결과 수"),
    db: Session = Depends(get_db)
):
    """벤치마크 상품 검색"""
    manager = BenchmarkManager(db)
    
    # 가격 범위 설정
    price_range = None
    if min_price is not None and max_price is not None:
        price_range = (min_price, max_price)
    
    # 유사 상품 검색
    products = await manager.find_similar_products(
        product_name=keyword,
        category=category,
        price_range=price_range
    )
    
    # 마켓 필터링
    if market:
        products = [p for p in products if p.market_type == market]
    
    # 결과 제한
    products = products[:limit]
    
    return {
        "keyword": keyword,
        "total_found": len(products),
        "products": [
            {
                "id": p.id,
                "market": p.market_type,
                "product_id": p.market_product_id,
                "name": p.product_name,
                "brand": p.brand,
                "category": p.main_category,
                "price": p.sale_price,
                "original_price": p.original_price,
                "discount_rate": p.discount_rate,
                "monthly_sales": p.monthly_sales,
                "review_count": p.review_count,
                "rating": p.rating,
                "rank": p.bestseller_rank
            }
            for p in products
        ]
    }


@router.get("/categories/{category}/bestsellers")
async def get_category_bestsellers(
    category: str,
    market: Optional[str] = Query(None, description="특정 마켓만 조회"),
    limit: int = Query(100, description="결과 수"),
    db: Session = Depends(get_db)
):
    """카테고리별 베스트셀러 조회"""
    manager = BenchmarkManager(db)
    
    products = await manager.get_category_bestsellers(
        category=category,
        market_type=market,
        limit=limit
    )
    
    return {
        "category": category,
        "market": market or "all",
        "total": len(products),
        "bestsellers": [
            {
                "rank": p.bestseller_rank,
                "market": p.market_type,
                "name": p.product_name,
                "brand": p.brand,
                "price": p.sale_price,
                "discount_rate": p.discount_rate,
                "monthly_sales": p.monthly_sales,
                "review_count": p.review_count,
                "rating": p.rating
            }
            for p in products
        ]
    }


@router.get("/products/{market}/{product_id}/price-history")
async def get_product_price_history(
    market: str,
    product_id: str,
    days: int = Query(30, description="조회 기간 (일)"),
    db: Session = Depends(get_db)
):
    """상품 가격 변동 이력 조회"""
    manager = BenchmarkManager(db)
    
    history = await manager.get_price_trends(
        product_id=product_id,
        market_type=market,
        days=days
    )
    
    if not history:
        raise HTTPException(status_code=404, detail="가격 이력을 찾을 수 없습니다")
    
    return {
        "market": market,
        "product_id": product_id,
        "period_days": days,
        "price_history": history
    }


@router.get("/insights/market/{category}")
async def get_market_insights(
    category: str,
    db: Session = Depends(get_db)
):
    """카테고리별 시장 인사이트"""
    manager = BenchmarkManager(db)
    
    insights = await manager.get_market_insights(category)
    
    return {
        "category": category,
        "insights": insights
    }


@router.get("/opportunities/trending")
async def get_trending_opportunities(
    days: int = Query(7, description="분석 기간"),
    min_growth: float = Query(20.0, description="최소 성장률"),
    db: Session = Depends(get_db)
):
    """급성장 상품 기회 조회"""
    manager = BenchmarkManager(db)
    
    trending = await manager.get_trending_products(
        days=days,
        min_growth_rate=min_growth
    )
    
    return {
        "analysis_period": days,
        "min_growth_rate": min_growth,
        "total_found": len(trending),
        "opportunities": [
            {
                "product": {
                    "name": item['product'].product_name,
                    "market": item['product'].market_type,
                    "category": item['product'].main_category,
                    "price": item['product'].sale_price,
                    "monthly_sales": item['product'].monthly_sales,
                    "rank": item['product'].bestseller_rank
                },
                "metrics": {
                    "price_volatility": item['price_volatility'],
                    "review_count": item['product'].review_count,
                    "rating": item['product'].rating
                }
            }
            for item in trending[:20]  # 상위 20개만
        ]
    }


@router.post("/analysis/comprehensive")
async def run_comprehensive_analysis(
    db: Session = Depends(get_db)
):
    """종합 소싱 분석 실행"""
    engine = SmartSourcingEngine(db)
    
    try:
        result = await engine.run_comprehensive_sourcing()
        
        return {
            "status": "success",
            "analysis": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실행 실패: {str(e)}")


@router.get("/competitors/{competitor_name}")
async def get_competitor_analysis(
    competitor_name: str,
    db: Session = Depends(get_db)
):
    """경쟁사 분석 데이터 조회"""
    manager = BenchmarkManager(db)
    
    competitor = await manager.get_competitor_analysis(competitor_name)
    
    if not competitor:
        raise HTTPException(status_code=404, detail="경쟁사 정보를 찾을 수 없습니다")
    
    return {
        "competitor": competitor_name,
        "analysis": {
            "market_share": competitor.market_share,
            "total_products": competitor.total_products,
            "average_rating": competitor.average_rating,
            "price_strategy": {
                "average": competitor.avg_price,
                "min": competitor.price_range_min,
                "max": competitor.price_range_max
            },
            "main_categories": competitor.main_categories,
            "monthly_revenue_estimate": competitor.monthly_revenue_estimate,
            "growth_trend": competitor.growth_trend
        }
    }


@router.get("/dashboard/summary")
async def get_benchmark_dashboard(
    db: Session = Depends(get_db)
):
    """벤치마크 대시보드 요약"""
    manager = BenchmarkManager(db)
    
    # 시장 요약 정보
    from sqlalchemy import func
    
    # 전체 통계
    total_products = db.query(func.count(BenchmarkProduct.id)).scalar()
    total_categories = db.query(func.count(func.distinct(BenchmarkProduct.main_category))).scalar()
    
    # 마켓별 분포
    market_stats = db.query(
        BenchmarkProduct.market_type,
        func.count(BenchmarkProduct.id).label('count'),
        func.avg(BenchmarkProduct.sale_price).label('avg_price')
    ).group_by(BenchmarkProduct.market_type).all()
    
    # 최근 급상승 상품
    trending = await manager.get_trending_products(days=3, min_growth_rate=10)
    
    return {
        "overview": {
            "total_products_tracked": total_products,
            "total_categories": total_categories,
            "last_updated": datetime.now()
        },
        "market_distribution": [
            {
                "market": stat.market_type,
                "product_count": stat.count,
                "average_price": int(stat.avg_price) if stat.avg_price else 0
            }
            for stat in market_stats
        ],
        "trending_products": [
            {
                "name": item['product'].product_name,
                "market": item['product'].market_type,
                "category": item['product'].main_category,
                "price": item['product'].sale_price,
                "sales": item['product'].monthly_sales
            }
            for item in trending[:10]
        ]
    }