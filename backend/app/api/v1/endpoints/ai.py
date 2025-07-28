"""AI API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.models.ai import (
    ProductOptimizationRequest,
    KeywordGenerationRequest,
    PriceAnalysisRequest,
    DemandPredictionRequest,
    CompetitionAnalysisRequest,
    DescriptionGenerationRequest,
    MarketAnalysisRequest,
    ReviewAnalysisRequest,
    BatchTaskRequest,
    FeedbackRequest,
    LearningDataSubmission,
    AIResponse,
    ModelStatus,
    OptimizationResult,
    PredictionResult,
    AnalysisResult
)
from app.services.ai.ai_manager import AIManager
from app.utils.ai.learning_engine import LearningEngine, SalesData
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# AI 서비스 인스턴스 (싱글톤)
ai_manager = AIManager()
learning_engine = LearningEngine()


@router.post("/optimize-product", response_model=AIResponse)
async def optimize_product(
    request: ProductOptimizationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    상품 정보 최적화
    - 상품명 최적화
    - 키워드 추천
    - 설명 개선
    """
    try:
        result = await ai_manager.optimize_product(
            product_data={
                "name": request.name,
                "category": request.category,
                "features": request.features,
                "keywords": request.keywords,
                "platform": request.target_platform
            },
            provider=request.provider
        )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Product optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-keywords", response_model=AIResponse)
async def generate_keywords(
    request: KeywordGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """키워드 생성 및 추천"""
    try:
        result = await ai_manager.generate_keywords(
            text=request.text,
            category=request.category,
            max_keywords=request.max_keywords,
            provider=request.provider
        )
        
        # 키워드 점수 계산
        if result.get("status") == "success" and "keywords" in result.get("data", {}):
            keywords = result["data"]["keywords"]
            if isinstance(keywords, list):
                keyword_list = keywords
            else:
                keyword_list = [k.get("keyword", k) for k in keywords if isinstance(k, dict)]
            
            scores = learning_engine.score_keywords(keyword_list)
            result["data"]["keyword_scores"] = scores
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Keyword generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-price", response_model=AIResponse)
async def analyze_price(
    request: PriceAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """가격 전략 분석"""
    try:
        # AI 분석
        result = await ai_manager.analyze_pricing(
            product_info=request.product_info,
            competitor_prices=request.competitor_prices,
            cost=request.cost,
            provider=request.provider
        )
        
        # ML 기반 최적화
        if learning_engine.price_optimizer:
            ml_optimization = await learning_engine.optimize_price(
                product_info=request.product_info,
                cost=request.cost,
                target_margin=request.target_margin
            )
            
            if result.get("status") == "success":
                result["data"]["ml_optimization"] = ml_optimization
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Price analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-demand", response_model=AIResponse)
async def predict_demand(
    request: DemandPredictionRequest,
    current_user: User = Depends(get_current_user)
):
    """수요 예측"""
    try:
        # AI 예측
        result = await ai_manager.predict_demand(
            product_category=request.product_category,
            historical_data=request.historical_data,
            external_factors=request.external_factors,
            provider=request.provider
        )
        
        # ML 예측 추가
        if learning_engine.sales_predictor:
            ml_predictions = await learning_engine.predict_sales(
                product_info={
                    "category": request.product_category,
                    "price": request.historical_data[-1].get("price", 0) if request.historical_data else 0,
                    "keywords": []
                },
                future_days=request.forecast_days
            )
            
            if result.get("status") == "success":
                result["data"]["ml_predictions"] = [
                    {
                        "day": i + 1,
                        "predicted_sales": pred.predicted_sales,
                        "confidence_interval": pred.confidence_interval,
                        "recommendation": pred.recommendation
                    }
                    for i, pred in enumerate(ml_predictions)
                ]
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Demand prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-competition", response_model=AIResponse)
async def analyze_competition(
    request: CompetitionAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """경쟁사 분석"""
    try:
        result = await ai_manager.analyze_competition(
            product_name=request.product_name,
            category=request.category,
            price_range=request.price_range,
            provider=request.provider
        )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Competition analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-description", response_model=AIResponse)
async def generate_description(
    request: DescriptionGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """상품 설명 생성"""
    try:
        result = await ai_manager.generate_description(
            product_info=request.product_info,
            style=request.style,
            platform=request.platform,
            provider=request.provider
        )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Description generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-market", response_model=AIResponse)
async def analyze_market(
    request: MarketAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """시장 분석"""
    try:
        result = await ai_manager.analyze_market(
            category=request.category,
            keywords=request.keywords,
            region=request.region,
            provider=request.provider
        )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Market analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-reviews", response_model=AIResponse)
async def analyze_reviews(
    request: ReviewAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """리뷰 분석"""
    try:
        # Gemini를 사용한 리뷰 분석
        from backend.app.services.ai.gemini_service import GeminiService
        gemini = GeminiService()
        
        result = await gemini.analyze_customer_reviews(
            reviews=request.reviews,
            product_info=request.product_info
        )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Review analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-process", response_model=List[AIResponse])
async def batch_process(
    request: BatchTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """배치 처리"""
    try:
        results = await ai_manager.batch_process(
            tasks=request.tasks,
            max_concurrent=request.max_concurrent
        )
        
        return [AIResponse(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/status", response_model=Dict[str, Any])
async def get_models_status(
    current_user: User = Depends(get_current_user)
):
    """AI 모델 상태 확인"""
    try:
        ai_status = await ai_manager.get_all_models_status()
        ml_status = learning_engine.get_model_performance()
        
        return {
            "ai_models": ai_status,
            "ml_models": ml_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learn-feedback", response_model=AIResponse)
async def submit_feedback(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """피드백 학습"""
    try:
        # 즉시 응답
        result = await ai_manager.learn_from_feedback(
            task_id=request.task_id,
            feedback={
                "rating": request.rating,
                "feedback": request.feedback,
                "improvement_data": request.improvement_data,
                "user_id": current_user.id
            }
        )
        
        # 백그라운드에서 학습 처리
        if request.improvement_data.get("sales_data"):
            background_tasks.add_task(
                process_sales_data,
                request.improvement_data["sales_data"]
            )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Feedback submission failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-sales-data")
async def submit_sales_data(
    data: LearningDataSubmission,
    current_user: User = Depends(get_current_user)
):
    """판매 데이터 제출 (학습용)"""
    try:
        sales_data = SalesData(
            product_id=data.product_id,
            timestamp=data.timestamp,
            quantity=data.quantity,
            price=data.price,
            category=data.category,
            keywords=data.keywords,
            platform=data.platform,
            promotion=data.promotion,
            season=_get_season(data.timestamp),
            day_of_week=data.timestamp.weekday(),
            hour_of_day=data.timestamp.hour
        )
        
        await learning_engine.add_sales_data(sales_data)
        
        return {
            "status": "success",
            "message": "Sales data submitted successfully",
            "buffer_size": len(learning_engine.training_buffer)
        }
        
    except Exception as e:
        logger.error(f"Sales data submission failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ab-test/analyze")
async def analyze_ab_test(
    variant_a_data: List[LearningDataSubmission],
    variant_b_data: List[LearningDataSubmission],
    current_user: User = Depends(get_current_user)
):
    """A/B 테스트 분석"""
    try:
        # 데이터 변환
        a_sales = [
            SalesData(
                product_id=d.product_id,
                timestamp=d.timestamp,
                quantity=d.quantity,
                price=d.price,
                category=d.category,
                keywords=d.keywords,
                platform=d.platform,
                promotion=d.promotion,
                season=_get_season(d.timestamp),
                day_of_week=d.timestamp.weekday(),
                hour_of_day=d.timestamp.hour
            )
            for d in variant_a_data
        ]
        
        b_sales = [
            SalesData(
                product_id=d.product_id,
                timestamp=d.timestamp,
                quantity=d.quantity,
                price=d.price,
                category=d.category,
                keywords=d.keywords,
                platform=d.platform,
                promotion=d.promotion,
                season=_get_season(d.timestamp),
                day_of_week=d.timestamp.weekday(),
                hour_of_day=d.timestamp.hour
            )
            for d in variant_b_data
        ]
        
        result = await learning_engine.analyze_ab_test(a_sales, b_sales)
        
        return result
        
    except Exception as e:
        logger.error(f"A/B test analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 헬퍼 함수
def _get_season(date: datetime) -> str:
    """날짜로부터 계절 추출"""
    month = date.month
    if month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "fall"
    else:
        return "winter"


async def process_sales_data(sales_data: List[Dict[str, Any]]):
    """백그라운드에서 판매 데이터 처리"""
    try:
        for data in sales_data:
            sales_obj = SalesData(
                product_id=data.get("product_id", ""),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
                quantity=data.get("quantity", 0),
                price=data.get("price", 0),
                category=data.get("category", ""),
                keywords=data.get("keywords", []),
                platform=data.get("platform", "general"),
                promotion=data.get("promotion", False),
                season=_get_season(datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat()))),
                day_of_week=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())).weekday(),
                hour_of_day=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())).hour
            )
            
            await learning_engine.add_sales_data(sales_obj)
            
    except Exception as e:
        logger.error(f"Background sales data processing failed: {str(e)}")