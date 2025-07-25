"""Gemini Flash 2.5 API service for cloud-based AI tasks."""

import os
import asyncio
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from datetime import datetime
import json
import logging

from app.core.config import settings
from app.models.ai import AITaskType, AIResponse

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Gemini Flash 2.5 서비스
    - 실시간 트렌드 분석
    - 경쟁사 분석
    - 시장 동향 파악
    - 복잡한 추론 작업
    """
    
    def __init__(self):
        """Initialize Gemini service with API key."""
        self.api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD18ntyKoXp7QQhgd_xe4dDqfC_yVTtnrY")
        genai.configure(api_key=self.api_key)
        
        # Gemini Flash 2.5 모델 초기화
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # 생성 설정
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=4096,
        )
        
        logger.info("Gemini Flash 2.5 service initialized")
    
    async def analyze_market_trends(self, 
                                  category: str, 
                                  keywords: List[str],
                                  region: str = "전체") -> Dict[str, Any]:
        """시장 트렌드 분석"""
        try:
            prompt = f"""
            온라인 쇼핑 전문가로서 다음 카테고리의 최신 트렌드를 분석해주세요:
            
            카테고리: {category}
            키워드: {', '.join(keywords)}
            지역: {region}
            
            다음 항목들을 포함하여 분석해주세요:
            1. 현재 인기 상품 트렌드
            2. 검색량 급상승 키워드
            3. 계절적 요인
            4. 가격대별 선호도
            5. 타겟 고객층 특성
            6. 향후 3개월 예상 트렌드
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            
            # JSON 파싱 시도
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                # JSON 파싱 실패시 텍스트 그대로 반환
                result = {"analysis": response.text}
            
            return {
                "status": "success",
                "task_type": "market_trends",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Market trend analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_competition(self,
                                product_name: str,
                                category: str,
                                price_range: Dict[str, float]) -> Dict[str, Any]:
        """경쟁사 분석"""
        try:
            prompt = f"""
            온라인 셀러 전문가로서 다음 상품의 경쟁 상황을 분석해주세요:
            
            상품명: {product_name}
            카테고리: {category}
            가격대: {price_range.get('min', 0)}원 ~ {price_range.get('max', 0)}원
            
            다음 항목들을 포함하여 분석해주세요:
            1. 주요 경쟁 상품 (상위 5개)
            2. 각 경쟁사의 강점과 약점
            3. 가격 포지셔닝 전략
            4. 차별화 포인트 제안
            5. 마케팅 전략 제안
            6. 예상 시장 점유율
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                result = {"analysis": response.text}
            
            return {
                "status": "success",
                "task_type": "competition_analysis",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Competition analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_marketing_content(self,
                                       product_info: Dict[str, Any],
                                       content_type: str = "description") -> Dict[str, Any]:
        """마케팅 콘텐츠 생성"""
        try:
            prompt = f"""
            전문 카피라이터로서 다음 상품의 {content_type}을 작성해주세요:
            
            상품 정보:
            - 이름: {product_info.get('name', '')}
            - 카테고리: {product_info.get('category', '')}
            - 가격: {product_info.get('price', '')}원
            - 주요 특징: {product_info.get('features', [])}
            - 타겟 고객: {product_info.get('target_audience', '')}
            
            요구사항:
            1. SEO 최적화된 키워드 포함
            2. 구매 욕구를 자극하는 표현
            3. 신뢰감을 주는 톤
            4. 모바일 환경에 최적화된 길이
            5. 이모지 적절히 활용
            
            다음 형식으로 작성해주세요:
            - 짧은 버전 (50자 이내)
            - 중간 버전 (200자 이내)
            - 긴 버전 (500자 이내)
            - 추천 해시태그 (10개)
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                result = {"content": response.text}
            
            return {
                "status": "success",
                "task_type": "marketing_content",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Marketing content generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def predict_demand(self,
                           product_category: str,
                           historical_data: List[Dict[str, Any]],
                           external_factors: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """수요 예측"""
        try:
            prompt = f"""
            데이터 분석 전문가로서 다음 상품의 수요를 예측해주세요:
            
            카테고리: {product_category}
            
            과거 판매 데이터:
            {json.dumps(historical_data[-10:], ensure_ascii=False, indent=2)}
            
            외부 요인:
            {json.dumps(external_factors or {}, ensure_ascii=False, indent=2)}
            
            다음 항목들을 포함하여 예측해주세요:
            1. 향후 7일간 일별 예상 판매량
            2. 향후 30일간 주별 예상 판매량
            3. 수요 변동 요인 분석
            4. 재고 관리 제안
            5. 최적 판매 시점
            6. 리스크 요인
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                result = {"prediction": response.text}
            
            return {
                "status": "success",
                "task_type": "demand_prediction",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Demand prediction failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_customer_reviews(self,
                                     reviews: List[Dict[str, Any]],
                                     product_info: Dict[str, Any]) -> Dict[str, Any]:
        """고객 리뷰 분석"""
        try:
            # 리뷰 샘플링 (최대 20개)
            sample_reviews = reviews[:20] if len(reviews) > 20 else reviews
            
            prompt = f"""
            고객 리뷰 분석 전문가로서 다음 상품의 리뷰를 분석해주세요:
            
            상품 정보:
            {json.dumps(product_info, ensure_ascii=False, indent=2)}
            
            고객 리뷰:
            {json.dumps(sample_reviews, ensure_ascii=False, indent=2)}
            
            다음 항목들을 분석해주세요:
            1. 전반적인 감성 분석 (긍정/부정 비율)
            2. 주요 장점 (Top 5)
            3. 주요 단점 (Top 5)
            4. 자주 언급되는 키워드
            5. 개선 제안사항
            6. 타겟 고객층 인사이트
            7. 상품 설명 개선 포인트
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=self.generation_config
            )
            
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                result = {"analysis": response.text}
            
            return {
                "status": "success",
                "task_type": "review_analysis",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Review analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_model_status(self) -> Dict[str, Any]:
        """모델 상태 확인"""
        try:
            # 간단한 테스트 프롬프트로 모델 상태 확인
            test_response = await asyncio.to_thread(
                self.model.generate_content,
                "상태 확인: 현재 시간을 알려주세요.",
                generation_config=genai.types.GenerationConfig(max_output_tokens=50)
            )
            
            return {
                "service": "Gemini Flash 2.5",
                "status": "active" if test_response.text else "inactive",
                "model": "gemini-2.0-flash-exp",
                "api_key_configured": bool(self.api_key),
                "last_check": datetime.utcnow().isoformat(),
                "capabilities": [
                    "market_trends",
                    "competition_analysis",
                    "marketing_content",
                    "demand_prediction",
                    "review_analysis"
                ]
            }
            
        except Exception as e:
            logger.error(f"Model status check failed: {str(e)}")
            return {
                "service": "Gemini Flash 2.5",
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }