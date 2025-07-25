"""
소싱 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from ....core.deps import get_db
from ....services.sourcing.smart_sourcing_engine import SmartSourcingEngine
from ....services.sourcing.market_data_collector import MarketDataCollector
from ....services.sourcing.trend_analyzer import TrendAnalyzer
from ....services.sourcing.ai_product_analyzer import AIProductAnalyzer
from ....models.market import MarketProduct, MarketCategory
from ....models.trend import TrendKeyword, KeywordAnalysis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze/comprehensive")
async def run_comprehensive_sourcing_analysis(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    종합 소싱 분석 실행
    - 마켓 데이터 수집
    - 트렌드 분석
    - AI 기반 상품 분석
    - 복합 소싱 추천
    """
    try:
        engine = SmartSourcingEngine(db, logger)
        
        # 백그라운드에서 분석 실행
        background_tasks.add_task(engine.run_comprehensive_sourcing)
        
        return {
            "message": "종합 소싱 분석이 시작되었습니다",
            "status": "started",
            "estimated_duration": "15-20분"
        }
    except Exception as e:
        logger.error(f"종합 소싱 분석 시작 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/results")
async def get_sourcing_analysis_results(
    limit: int = Query(default=20, le=100),
    category: Optional[str] = Query(default=None),
    min_score: Optional[float] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    최근 소싱 분석 결과 조회
    """
    try:
        # KeywordAnalysis에서 최근 분석 결과 가져오기
        query = db.query(KeywordAnalysis).order_by(KeywordAnalysis.analyzed_at.desc())
        
        if category:
            query = query.filter(KeywordAnalysis.category == category)
        if min_score:
            query = query.filter(KeywordAnalysis.overall_score >= min_score)
            
        results = query.limit(limit).all()
        
        return {
            "total_results": len(results),
            "analyses": [
                {
                    "id": analysis.id,
                    "keyword": analysis.keyword,
                    "category": analysis.category,
                    "overall_score": analysis.overall_score,
                    "potential_score": analysis.potential_score,
                    "risk_score": analysis.risk_score,
                    "ai_recommendation": analysis.ai_recommendation,
                    "confidence_level": analysis.confidence_level,
                    "analyzed_at": analysis.analyzed_at
                }
                for analysis in results
            ]
        }
    except Exception as e:
        logger.error(f"소싱 분석 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/collect")
async def collect_market_data(
    marketplaces: List[str] = Query(default=["coupang", "naver", "11st"]),
    categories: Optional[List[str]] = Query(default=None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    마켓플레이스 데이터 수집
    """
    try:
        async with MarketDataCollector(db, logger) as collector:
            if background_tasks:
                background_tasks.add_task(collector.collect_all_markets)
                return {
                    "message": "마켓 데이터 수집이 시작되었습니다",
                    "marketplaces": marketplaces,
                    "status": "started"
                }
            else:
                results = await collector.collect_all_markets()
                return {
                    "message": "마켓 데이터 수집 완료",
                    "results": results
                }
    except Exception as e:
        logger.error(f"마켓 데이터 수집 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/bestsellers")
async def get_market_bestsellers(
    marketplace: str = Query(..., description="마켓플레이스 (coupang, naver, 11st)"),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db)
):
    """
    마켓플레이스 베스트셀러 조회
    """
    try:
        query = db.query(MarketProduct).filter(
            MarketProduct.marketplace == marketplace
        ).order_by(MarketProduct.rank)
        
        if category:
            query = query.filter(MarketProduct.category == category)
            
        products = query.limit(limit).all()
        
        return {
            "marketplace": marketplace,
            "category": category,
            "total_products": len(products),
            "products": [
                {
                    "id": product.id,
                    "rank": product.rank,
                    "name": product.product_name,
                    "price": product.price,
                    "category": product.category,
                    "review_count": product.review_count,
                    "rating": product.rating,
                    "collected_at": product.collected_at
                }
                for product in products
            ]
        }
    except Exception as e:
        logger.error(f"베스트셀러 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trends/analyze")
async def analyze_trends(
    keywords: Optional[List[str]] = Query(default=None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    트렌드 분석 실행
    """
    try:
        analyzer = TrendAnalyzer(db, logger)
        
        if background_tasks:
            background_tasks.add_task(analyzer.analyze_trends, keywords)
            return {
                "message": "트렌드 분석이 시작되었습니다",
                "keywords": keywords or "기본 키워드",
                "status": "started"
            }
        else:
            results = await analyzer.analyze_trends(keywords)
            return {
                "message": "트렌드 분석 완료",
                "results": results
            }
    except Exception as e:
        logger.error(f"트렌드 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/rising")
async def get_rising_trends(
    platform: str = Query(default="google", description="플랫폼 (google, naver)"),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """
    급상승 트렌드 키워드 조회
    """
    try:
        query = db.query(TrendKeyword).filter(
            TrendKeyword.platform == platform,
            TrendKeyword.trend_direction == "rising"
        ).order_by(TrendKeyword.trend_score.desc())
        
        if category:
            query = query.filter(TrendKeyword.category == category)
            
        trends = query.limit(limit).all()
        
        return {
            "platform": platform,
            "category": category,
            "total_trends": len(trends),
            "rising_keywords": [
                {
                    "id": trend.id,
                    "keyword": trend.keyword,
                    "category": trend.category,
                    "trend_score": trend.trend_score,
                    "rise_percentage": trend.rise_percentage,
                    "search_volume": trend.search_volume,
                    "competition_level": trend.competition_level,
                    "analyzed_at": trend.analyzed_at
                }
                for trend in trends
            ]
        }
    except Exception as e:
        logger.error(f"급상승 트렌드 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/product")
async def analyze_product_potential(
    product_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    특정 상품의 AI 분석
    """
    try:
        analyzer = AIProductAnalyzer(db, logger)
        analysis = await analyzer.analyze_product_potential(product_data)
        
        return {
            "message": "상품 분석 완료",
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"상품 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/categories")
async def get_category_recommendations(
    limit: int = Query(default=10, le=20),
    min_confidence: float = Query(default=0.6, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    AI 추천 카테고리 조회
    """
    try:
        # 최근 트렌드 분석을 기반으로 카테고리 추천 생성
        analyzer = TrendAnalyzer(db, logger)
        
        # 모의 트렌드 결과로 카테고리 추천 (실제로는 저장된 분석 결과 사용)
        mock_trend_results = {
            'google_trends': {'keyword_trends': {}},
            'rising_keywords': [],
            'seasonal_keywords': []
        }
        
        recommendations = await analyzer.recommend_categories(mock_trend_results)
        
        # 신뢰도 필터링
        filtered_recommendations = [
            rec for rec in recommendations 
            if rec.get('confidence', 0) >= min_confidence
        ][:limit]
        
        return {
            "total_recommendations": len(filtered_recommendations),
            "min_confidence": min_confidence,
            "recommendations": filtered_recommendations
        }
    except Exception as e:
        logger.error(f"카테고리 추천 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/overview")
async def get_sourcing_dashboard(
    db: Session = Depends(get_db)
):
    """
    소싱 대시보드 개요
    """
    try:
        # 전체 통계
        total_market_products = db.query(MarketProduct).count()
        total_trend_keywords = db.query(TrendKeyword).count()
        total_analyses = db.query(KeywordAnalysis).count()
        
        # 최근 분석 결과 (상위 5개)
        recent_analyses = db.query(KeywordAnalysis).order_by(
            KeywordAnalysis.analyzed_at.desc()
        ).limit(5).all()
        
        # 급상승 키워드 (상위 5개)
        rising_keywords = db.query(TrendKeyword).filter(
            TrendKeyword.trend_direction == "rising"
        ).order_by(TrendKeyword.trend_score.desc()).limit(5).all()
        
        # 카테고리별 통계
        category_stats = db.query(MarketProduct.category).distinct().count()
        
        return {
            "overview": {
                "total_market_products": total_market_products,
                "total_trend_keywords": total_trend_keywords,
                "total_analyses": total_analyses,
                "active_categories": category_stats
            },
            "recent_analyses": [
                {
                    "keyword": analysis.keyword,
                    "overall_score": analysis.overall_score,
                    "ai_recommendation": analysis.ai_recommendation,
                    "analyzed_at": analysis.analyzed_at
                }
                for analysis in recent_analyses
            ],
            "rising_keywords": [
                {
                    "keyword": keyword.keyword,
                    "trend_score": keyword.trend_score,
                    "category": keyword.category,
                    "platform": keyword.platform
                }
                for keyword in rising_keywords
            ]
        }
    except Exception as e:
        logger.error(f"소싱 대시보드 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_sourcing_status():
    """
    소싱 시스템 상태 확인
    """
    return {
        "status": "active",
        "services": {
            "market_data_collector": "ready",
            "trend_analyzer": "ready", 
            "ai_product_analyzer": "ready",
            "smart_sourcing_engine": "ready"
        },
        "version": "1.0.0"
    }