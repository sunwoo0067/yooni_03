"""AI related models and schemas."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum


class AITaskType(str, Enum):
    """AI 작업 유형"""
    OPTIMIZE_PRODUCT = "optimize_product"
    GENERATE_KEYWORDS = "generate_keywords"
    ANALYZE_PRICE = "analyze_price"
    PREDICT_DEMAND = "predict_demand"
    ANALYZE_COMPETITION = "analyze_competition"
    GENERATE_DESCRIPTION = "generate_description"
    ANALYZE_MARKET = "analyze_market"
    ANALYZE_REVIEWS = "analyze_reviews"


class AIProvider(str, Enum):
    """AI 제공자"""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    LANGCHAIN = "langchain"
    AUTO = "auto"


class ProductOptimizationRequest(BaseModel):
    """상품 최적화 요청"""
    name: str = Field(..., description="상품명")
    category: str = Field(..., description="카테고리")
    features: List[str] = Field(default=[], description="주요 특징")
    keywords: Optional[List[str]] = Field(default=[], description="키워드")
    target_platform: Optional[str] = Field(default="general", description="타겟 플랫폼")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO, description="AI 제공자")


class KeywordGenerationRequest(BaseModel):
    """키워드 생성 요청"""
    text: str = Field(..., description="분석할 텍스트")
    category: str = Field(..., description="카테고리")
    max_keywords: Optional[int] = Field(default=20, description="최대 키워드 수")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO)


class PriceAnalysisRequest(BaseModel):
    """가격 분석 요청"""
    product_info: Dict[str, Any] = Field(..., description="상품 정보")
    competitor_prices: List[float] = Field(..., description="경쟁사 가격")
    cost: float = Field(..., description="원가")
    target_margin: Optional[float] = Field(default=0.3, description="목표 마진")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO)


class DemandPredictionRequest(BaseModel):
    """수요 예측 요청"""
    product_category: str = Field(..., description="상품 카테고리")
    historical_data: List[Dict[str, Any]] = Field(..., description="과거 판매 데이터")
    external_factors: Optional[Dict[str, Any]] = Field(default={}, description="외부 요인")
    forecast_days: Optional[int] = Field(default=7, description="예측 일수")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO)


class CompetitionAnalysisRequest(BaseModel):
    """경쟁사 분석 요청"""
    product_name: str = Field(..., description="상품명")
    category: str = Field(..., description="카테고리")
    price_range: Dict[str, float] = Field(..., description="가격 범위")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO)


class DescriptionGenerationRequest(BaseModel):
    """상품 설명 생성 요청"""
    product_info: Dict[str, Any] = Field(..., description="상품 정보")
    style: Optional[str] = Field(default="detailed", description="작성 스타일")
    platform: Optional[str] = Field(default="general", description="플랫폼")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO)


class MarketAnalysisRequest(BaseModel):
    """시장 분석 요청"""
    category: str = Field(..., description="카테고리")
    keywords: List[str] = Field(..., description="키워드")
    region: Optional[str] = Field(default="전체", description="지역")
    period: Optional[str] = Field(default="recent", description="분석 기간")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO)


class ReviewAnalysisRequest(BaseModel):
    """리뷰 분석 요청"""
    reviews: List[Dict[str, Any]] = Field(..., description="리뷰 데이터")
    product_info: Dict[str, Any] = Field(..., description="상품 정보")
    provider: Optional[AIProvider] = Field(default=AIProvider.AUTO)


class BatchTaskRequest(BaseModel):
    """배치 작업 요청"""
    tasks: List[Dict[str, Any]] = Field(..., description="작업 목록")
    max_concurrent: Optional[int] = Field(default=5, description="최대 동시 실행 수")


class FeedbackRequest(BaseModel):
    """피드백 요청"""
    task_id: str = Field(..., description="작업 ID")
    rating: int = Field(..., ge=1, le=5, description="평점 (1-5)")
    feedback: Optional[str] = Field(default="", description="피드백 내용")
    improvement_data: Optional[Dict[str, Any]] = Field(default={}, description="개선 데이터")


class AIResponse(BaseModel):
    """AI 응답 기본 모델"""
    status: str = Field(..., description="응답 상태")
    task_type: Optional[str] = Field(default=None, description="작업 유형")
    data: Optional[Dict[str, Any]] = Field(default={}, description="응답 데이터")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    provider: Optional[str] = Field(default=None, description="사용된 AI 제공자")


class ModelStatus(BaseModel):
    """모델 상태"""
    service: str = Field(..., description="서비스 이름")
    status: str = Field(..., description="상태")
    model: Optional[str] = Field(default=None, description="모델 이름")
    capabilities: Optional[List[str]] = Field(default=[], description="지원 기능")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    last_check: str = Field(..., description="마지막 확인 시간")
    additional_info: Optional[Dict[str, Any]] = Field(default={}, description="추가 정보")


class LearningDataSubmission(BaseModel):
    """학습 데이터 제출"""
    product_id: str = Field(..., description="상품 ID")
    timestamp: datetime = Field(..., description="판매 시간")
    quantity: int = Field(..., ge=0, description="판매 수량")
    price: float = Field(..., gt=0, description="판매 가격")
    category: str = Field(..., description="카테고리")
    keywords: List[str] = Field(..., description="사용된 키워드")
    platform: str = Field(..., description="판매 플랫폼")
    promotion: bool = Field(default=False, description="프로모션 여부")


class OptimizationResult(BaseModel):
    """최적화 결과"""
    original: Dict[str, Any] = Field(..., description="원본 데이터")
    optimized: Dict[str, Any] = Field(..., description="최적화된 데이터")
    improvements: List[str] = Field(..., description="개선 사항")
    metrics: Optional[Dict[str, float]] = Field(default={}, description="성능 지표")


class PredictionResult(BaseModel):
    """예측 결과"""
    predictions: List[Dict[str, Any]] = Field(..., description="예측 값")
    confidence_intervals: Optional[List[Tuple[float, float]]] = Field(default=[], description="신뢰 구간")
    feature_importance: Optional[Dict[str, float]] = Field(default={}, description="특징 중요도")
    recommendations: List[str] = Field(..., description="추천 사항")


class AnalysisResult(BaseModel):
    """분석 결과"""
    summary: Dict[str, Any] = Field(..., description="요약")
    insights: List[str] = Field(..., description="인사이트")
    opportunities: Optional[List[str]] = Field(default=[], description="기회")
    threats: Optional[List[str]] = Field(default=[], description="위협")
    action_items: List[str] = Field(..., description="실행 항목")