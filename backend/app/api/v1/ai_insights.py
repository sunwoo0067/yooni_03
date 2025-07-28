"""
AI 인사이트 API 엔드포인트
추천, 가격 최적화, 수요 예측 기능 제공
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.services.ai.recommendation_engine import RecommendationEngine
from app.services.ai.price_optimizer import PriceOptimizer
from app.services.ai.demand_forecasting import DemandForecasting
from app.schemas.base import ResponseModel


router = APIRouter(prefix="/ai", tags=["AI Insights"])


@router.get("/recommendations/user", response_model=ResponseModel)
def get_user_recommendations(
    limit: int = Query(10, ge=1, le=50, description="추천 상품 개수"),
    exclude_purchased: bool = Query(True, description="구매한 상품 제외 여부"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 맞춤 상품 추천
    
    - 구매 이력 기반 추천
    - 유사 사용자의 구매 패턴 분석
    - 인기 상품 추천
    """
    engine = RecommendationEngine(db)
    
    try:
        recommendations = engine.get_user_recommendations(
            user_id=current_user.id,
            limit=limit,
            exclude_purchased=exclude_purchased
        )
        
        # 응답 형식 정리
        result = []
        for rec in recommendations:
            product = rec['product']
            result.append({
                'product_id': product.id,
                'name': product.name,
                'category': product.category,
                'price': float(product.price),
                'image_url': product.image_url,
                'score': round(rec['score'], 2),
                'reason': rec['reason']
            })
            
        return ResponseModel(
            success=True,
            data={
                'recommendations': result,
                'count': len(result)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/product/{product_id}", response_model=ResponseModel)
def get_similar_products(
    product_id: int,
    limit: int = Query(5, ge=1, le=20, description="추천 상품 개수"),
    db: Session = Depends(get_db)
):
    """특정 상품과 유사한 상품 추천"""
    engine = RecommendationEngine(db)
    
    try:
        recommendations = engine.get_product_similarities(
            product_id=product_id,
            limit=limit
        )
        
        result = []
        for rec in recommendations:
            product = rec['product']
            result.append({
                'product_id': product.id,
                'name': product.name,
                'category': product.category,
                'price': float(product.price),
                'image_url': product.image_url,
                'similarity_score': round(rec['score'], 2)
            })
            
        return ResponseModel(
            success=True,
            data={
                'similar_products': result,
                'count': len(result)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/bundle", response_model=ResponseModel)
def get_bundle_recommendations(
    product_ids: List[int],
    limit: int = Query(5, ge=1, le=10, description="추천 상품 개수"),
    db: Session = Depends(get_db)
):
    """함께 구매하면 좋은 상품 추천 (장바구니 기반)"""
    engine = RecommendationEngine(db)
    
    try:
        recommendations = engine.get_bundle_recommendations(
            product_ids=product_ids,
            limit=limit
        )
        
        result = []
        for rec in recommendations:
            product = rec['product']
            result.append({
                'product_id': product.id,
                'name': product.name,
                'category': product.category,
                'price': float(product.price),
                'score': round(rec['score'], 2),
                'reason': rec['reason']
            })
            
        return ResponseModel(
            success=True,
            data={
                'bundle_recommendations': result,
                'count': len(result)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-optimization/product/{product_id}", response_model=ResponseModel)
def optimize_product_price(
    product_id: int,
    target_margin: Optional[float] = Query(None, ge=0.0, le=1.0, description="목표 마진율"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    상품 가격 최적화 분석
    
    관리자 권한 필요
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
    optimizer = PriceOptimizer(db)
    
    try:
        result = optimizer.optimize_product_price(
            product_id=product_id,
            target_margin=target_margin
        )
        
        return ResponseModel(
            success=True,
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-optimization/category", response_model=ResponseModel)
def optimize_category_prices(
    category: Optional[str] = Query(None, description="카테고리"),
    min_margin: float = Query(0.2, ge=0.0, le=1.0, description="최소 마진율"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    카테고리별 일괄 가격 최적화
    
    관리자 권한 필요
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
    optimizer = PriceOptimizer(db)
    
    try:
        results = optimizer.bulk_optimize_prices(
            category=category,
            min_margin=min_margin
        )
        
        # 요약 정보 생성
        summary = {
            'total_products': len(results),
            'price_increases': len([r for r in results if r.get('price_change', 0) > 0]),
            'price_decreases': len([r for r in results if r.get('price_change', 0) < 0]),
            'total_revenue_impact': sum(r.get('revenue_impact_estimate', {}).get('revenue_change', 0) for r in results),
            'errors': len([r for r in results if 'error' in r])
        }
        
        return ResponseModel(
            success=True,
            data={
                'optimizations': results[:20],  # 상위 20개만 반환
                'summary': summary
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-optimization/dynamic-rules/{product_id}", response_model=ResponseModel)
def get_dynamic_pricing_rules(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    동적 가격 책정 규칙 조회
    
    관리자 권한 필요
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
    optimizer = PriceOptimizer(db)
    
    try:
        rules = optimizer.get_dynamic_pricing_rules(product_id)
        
        return ResponseModel(
            success=True,
            data=rules
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demand-forecast/product/{product_id}", response_model=ResponseModel)
def forecast_product_demand(
    product_id: int,
    days_ahead: int = Query(30, ge=7, le=90, description="예측 기간 (일)"),
    include_seasonality: bool = Query(True, description="계절성 고려 여부"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    상품별 수요 예측
    
    관리자 권한 필요
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
    forecaster = DemandForecasting(db)
    
    try:
        forecast = forecaster.forecast_product_demand(
            product_id=product_id,
            days_ahead=days_ahead,
            include_seasonality=include_seasonality
        )
        
        return ResponseModel(
            success=True,
            data=forecast
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demand-forecast/category", response_model=ResponseModel)
def forecast_category_demand(
    category: str,
    days_ahead: int = Query(30, ge=7, le=90, description="예측 기간 (일)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    카테고리별 수요 예측
    
    관리자 권한 필요
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
    forecaster = DemandForecasting(db)
    
    try:
        forecast = forecaster.forecast_category_demand(
            category=category,
            days_ahead=days_ahead
        )
        
        return ResponseModel(
            success=True,
            data=forecast
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demand-trends", response_model=ResponseModel)
def get_demand_trends(
    days: int = Query(90, ge=30, le=365, description="분석 기간 (일)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    전체 수요 트렌드 분석
    
    관리자 권한 필요
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
    forecaster = DemandForecasting(db)
    
    try:
        trends = forecaster.get_demand_trends(days=days)
        
        return ResponseModel(
            success=True,
            data=trends
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", response_model=ResponseModel)
def get_ai_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI 인사이트 대시보드 데이터
    
    관리자 권한 필요
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
    try:
        # 각 엔진 초기화
        recommendation_engine = RecommendationEngine(db)
        price_optimizer = PriceOptimizer(db)
        demand_forecaster = DemandForecasting(db)
        
        # 인기 상품 (전체 사용자 대상)
        popular_products = recommendation_engine._get_popular_recommendations(limit=10)
        
        # 수요 트렌드 (최근 30일)
        demand_trends = demand_forecaster.get_demand_trends(days=30)
        
        # 가격 최적화 기회 (상위 5개)
        price_opportunities = price_optimizer.bulk_optimize_prices(min_margin=0.2)[:5]
        
        dashboard_data = {
            'popular_products': [
                {
                    'product_id': p['product'].id,
                    'name': p['product'].name,
                    'category': p['product'].category,
                    'reason': p['reason']
                } for p in popular_products
            ],
            'demand_summary': {
                'trend': demand_trends['overall_trend']['type'],
                'weekly_growth_rate': demand_trends['overall_trend'].get('weekly_growth_rate', 0),
                'total_orders_30d': demand_trends['total_orders'],
                'avg_daily_items': round(demand_trends['average_daily_items'], 1)
            },
            'price_optimization_opportunities': [
                {
                    'product_id': p['product_id'],
                    'product_name': p['product_name'],
                    'current_price': p['current_price'],
                    'optimal_price': p['optimal_price'],
                    'revenue_impact': p['revenue_impact_estimate']['revenue_change']
                } for p in price_opportunities if 'error' not in p
            ],
            'alerts': []
        }
        
        # 재고 부족 예상 상품 확인
        from app.models.product import Product
        low_stock_products = db.query(Product).filter(
            Product.is_active == True,
            Product.stock < 20
        ).limit(5).all()
        
        for product in low_stock_products:
            dashboard_data['alerts'].append({
                'type': 'low_stock',
                'product_id': product.id,
                'product_name': product.name,
                'current_stock': product.stock,
                'message': f'{product.name} 재고 부족 ({product.stock}개 남음)'
            })
            
        return ResponseModel(
            success=True,
            data=dashboard_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))