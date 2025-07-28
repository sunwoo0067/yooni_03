"""
AI 기반 상품 소싱 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from database.connection import get_db
from services.ai.trend_analyzer import TrendAnalyzer
from services.ai.profit_predictor import ProfitPredictor
from services.ai.product_recommender import ProductRecommender
from utils.logger import app_logger

router = APIRouter(prefix="/ai-sourcing", tags=["ai-sourcing"])


@router.get("/trends/market")
async def analyze_market_trends(
    days: int = Query(30, description="분석 기간 (일)"),
    db: Session = Depends(get_db)
):
    """시장 트렌드 분석"""
    try:
        analyzer = TrendAnalyzer(db)
        trends = await analyzer.analyze_market_trends(days=days)
        return trends
    except Exception as e:
        app_logger.error(f"시장 트렌드 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/categories")
async def get_category_trends(db: Session = Depends(get_db)):
    """카테고리별 트렌드 및 추천"""
    try:
        analyzer = TrendAnalyzer(db)
        recommendations = analyzer.get_category_recommendations()
        
        return {
            "status": "success",
            "count": len(recommendations),
            "categories": recommendations,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        app_logger.error(f"카테고리 트렌드 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trends/search")
async def analyze_search_trends(
    keywords: List[str],
    db: Session = Depends(get_db)
):
    """검색 키워드 트렌드 분석"""
    try:
        if not keywords:
            raise HTTPException(status_code=400, detail="키워드를 입력해주세요")
            
        analyzer = TrendAnalyzer(db)
        trends = await analyzer.get_search_trends(keywords)
        return trends
    except Exception as e:
        app_logger.error(f"검색 트렌드 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profit/analyze/{product_code}")
async def analyze_product_profit(
    product_code: str,
    marketplace: str = Query("coupang", description="마켓플레이스"),
    db: Session = Depends(get_db)
):
    """개별 상품 수익성 분석"""
    try:
        from database.models_v2 import WholesaleProduct
        
        # 상품 조회
        product = db.query(WholesaleProduct).filter(
            WholesaleProduct.product_code == product_code
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
        predictor = ProfitPredictor(db)
        analysis = predictor.calculate_profit_potential(product, marketplace)
        
        return {
            "status": "success",
            "product_code": product_code,
            "product_name": product.product_name,
            "analysis": analysis,
            "analyzed_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"수익성 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profit/analyze-batch")
async def analyze_batch_profit(
    product_codes: List[str],
    db: Session = Depends(get_db)
):
    """여러 상품 일괄 수익성 분석"""
    try:
        if not product_codes:
            raise HTTPException(status_code=400, detail="상품 코드를 입력해주세요")
        
        if len(product_codes) > 50:
            raise HTTPException(status_code=400, detail="최대 50개까지 분석 가능합니다")
        
        predictor = ProfitPredictor(db)
        results = predictor.analyze_batch_products(product_codes)
        
        return {
            "status": "success",
            "requested": len(product_codes),
            "analyzed": len(results),
            "results": results,
            "analyzed_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"일괄 수익성 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profit/distribution")
async def get_profit_distribution(
    days: int = Query(30, description="분석 기간 (일)"),
    db: Session = Depends(get_db)
):
    """수익성 분포 분석"""
    try:
        predictor = ProfitPredictor(db)
        distribution = predictor.get_profit_distribution(days=days)
        return distribution
    except Exception as e:
        app_logger.error(f"수익성 분포 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_product_recommendations(
    recommendation_type: str = Query(
        "balanced",
        description="추천 유형: trend(트렌드), profit(수익성), balanced(균형)"
    ),
    limit: int = Query(20, ge=1, le=100, description="추천 상품 수"),
    db: Session = Depends(get_db)
):
    """AI 기반 상품 추천"""
    try:
        if recommendation_type not in ["trend", "profit", "balanced"]:
            raise HTTPException(
                status_code=400,
                detail="추천 유형은 trend, profit, balanced 중 하나여야 합니다"
            )
        
        recommender = ProductRecommender(db)
        recommendations = await recommender.get_recommendations(
            recommendation_type=recommendation_type,
            limit=limit
        )
        
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"상품 추천 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/opportunities")
async def get_category_opportunities(db: Session = Depends(get_db)):
    """카테고리별 사업 기회 분석"""
    try:
        recommender = ProductRecommender(db)
        opportunities = recommender.get_category_opportunities()
        
        return {
            "status": "success",
            "count": len(opportunities),
            "opportunities": opportunities,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        app_logger.error(f"기회 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_ai_dashboard(db: Session = Depends(get_db)):
    """AI 분석 대시보드 데이터"""
    try:
        # 각 분석기 초기화
        trend_analyzer = TrendAnalyzer(db)
        profit_predictor = ProfitPredictor(db)
        recommender = ProductRecommender(db)
        
        # 1. 시장 트렌드 요약
        market_trends = await trend_analyzer.analyze_market_trends(days=7)
        
        # 2. 수익성 분포
        profit_dist = profit_predictor.get_profit_distribution(days=7)
        
        # 3. 상위 추천 상품
        top_recommendations = await recommender.get_recommendations(
            recommendation_type="balanced",
            limit=5
        )
        
        # 4. 카테고리 기회
        opportunities = recommender.get_category_opportunities()[:5]
        
        dashboard_data = {
            "status": "success",
            "summary": {
                "total_trending_products": market_trends.get("total_products", 0),
                "avg_profit_score": profit_dist.get("avg_profit_score", 0),
                "top_recommendations_count": len(top_recommendations.get("recommendations", [])),
                "opportunity_categories": len(opportunities)
            },
            "market_trends_summary": {
                "rising_products": len(market_trends.get("rising_products", [])),
                "stable_products": len(market_trends.get("stable_products", [])),
                "top_category": market_trends.get("category_trends", [{}])[0].get("category")
                if market_trends.get("category_trends") else None
            },
            "profit_summary": profit_dist.get("score_distribution", {}),
            "top_recommendations": top_recommendations.get("recommendations", [])[:3],
            "top_opportunities": opportunities[:3],
            "generated_at": datetime.now().isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        app_logger.error(f"대시보드 데이터 생성 오류: {e}")
        return {
            "status": "error",
            "message": "대시보드 데이터를 생성할 수 없습니다",
            "error": str(e)
        }