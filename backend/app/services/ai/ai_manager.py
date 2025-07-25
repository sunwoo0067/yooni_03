"""AI Manager service for orchestrating hybrid AI system."""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
from enum import Enum

from app.services.ai.gemini_service import GeminiService
from app.services.ai.ollama_service import OllamaService
from app.services.ai.langchain_service import LangChainService, TaskType
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """AI 제공자 유형"""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    LANGCHAIN = "langchain"
    AUTO = "auto"  # 자동 선택


class AIManager:
    """
    하이브리드 AI 시스템 매니저
    - Gemini, Ollama, LangChain 통합 관리
    - 작업별 최적 모델 자동 선택
    - 병렬 처리 및 폴백 지원
    - 통합 모니터링 및 로깅
    """
    
    def __init__(self):
        """Initialize AI Manager with all services."""
        self.gemini_service = GeminiService()
        self.ollama_service = OllamaService()
        self.langchain_service = LangChainService()
        
        # 작업별 기본 제공자 매핑
        self.task_provider_mapping = {
            TaskType.OPTIMIZE_PRODUCT: AIProvider.LANGCHAIN,
            TaskType.MARKET_ANALYSIS: AIProvider.LANGCHAIN,
            TaskType.PRICING_STRATEGY: AIProvider.OLLAMA,  # 민감 정보는 로컬
            TaskType.CONTENT_GENERATION: AIProvider.LANGCHAIN,
            TaskType.COMPETITOR_ANALYSIS: AIProvider.GEMINI,  # 실시간 정보
            TaskType.DEMAND_PREDICTION: AIProvider.GEMINI,
            TaskType.CUSTOMER_INSIGHTS: AIProvider.GEMINI,
        }
        
        # 성능 메트릭
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "provider_usage": {
                AIProvider.GEMINI: 0,
                AIProvider.OLLAMA: 0,
                AIProvider.LANGCHAIN: 0
            }
        }
        
        logger.info("AI Manager initialized with all services")
    
    async def optimize_product(self, 
                             product_data: Dict[str, Any],
                             provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """
        상품 최적화 (상품명, 키워드, 설명)
        
        Args:
            product_data: 상품 정보
            provider: AI 제공자 (기본: 자동)
        """
        try:
            self.metrics["total_requests"] += 1
            
            # 제공자 선택
            if provider == AIProvider.AUTO:
                provider = self._select_provider(TaskType.OPTIMIZE_PRODUCT, product_data)
            
            # 워크플로우 실행
            if provider == AIProvider.LANGCHAIN:
                # LangChain 워크플로우 (Gemini + Ollama 조합)
                result = await self.langchain_service.optimize_product_workflow(product_data)
            elif provider == AIProvider.OLLAMA:
                # Ollama 로컬 처리
                title_result = await self.ollama_service.optimize_product_title(
                    current_title=product_data.get("name", ""),
                    category=product_data.get("category", ""),
                    keywords=product_data.get("keywords", [])
                )
                desc_result = await self.ollama_service.generate_product_description(
                    product_info=product_data
                )
                result = self._merge_results([title_result, desc_result])
            else:
                # Gemini 클라우드 처리
                result = await self.gemini_service.generate_marketing_content(
                    product_info=product_data,
                    content_type="full_optimization"
                )
            
            # 메트릭 업데이트
            if result.get("status") == "success":
                self.metrics["successful_requests"] += 1
                self.metrics["provider_usage"][provider] += 1
            else:
                self.metrics["failed_requests"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Product optimization failed: {str(e)}")
            self.metrics["failed_requests"] += 1
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_market(self,
                           category: str,
                           keywords: List[str],
                           region: str = "전체",
                           provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """시장 트렌드 분석"""
        try:
            self.metrics["total_requests"] += 1
            
            if provider == AIProvider.AUTO:
                provider = AIProvider.GEMINI  # 실시간 트렌드는 Gemini
            
            if provider == AIProvider.GEMINI:
                result = await self.gemini_service.analyze_market_trends(
                    category=category,
                    keywords=keywords,
                    region=region
                )
            elif provider == AIProvider.LANGCHAIN:
                result = await self.langchain_service.analyze_market_workflow({
                    "category": category,
                    "product_type": ", ".join(keywords),
                    "min_price": 0,
                    "max_price": 1000000,
                    "season": "current"
                })
            else:
                # Ollama는 실시간 트렌드 분석에 적합하지 않음
                result = {
                    "status": "error",
                    "error": "Market analysis requires online data access"
                }
            
            self._update_metrics(result, provider)
            return result
            
        except Exception as e:
            logger.error(f"Market analysis failed: {str(e)}")
            self.metrics["failed_requests"] += 1
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_keywords(self,
                              text: str,
                              category: str,
                              max_keywords: int = 20,
                              provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """키워드 생성 및 추천"""
        try:
            self.metrics["total_requests"] += 1
            
            if provider == AIProvider.AUTO:
                provider = AIProvider.OLLAMA  # 개인정보 보호를 위해 로컬
            
            if provider == AIProvider.OLLAMA:
                result = await self.ollama_service.extract_keywords(
                    text=text,
                    category=category,
                    max_keywords=max_keywords
                )
            else:
                # Gemini로 폴백
                prompt = f"카테고리 '{category}'의 다음 텍스트에서 SEO 최적화된 키워드 {max_keywords}개를 추출해주세요:\n{text}"
                response = await self.gemini_service.model.generate_content(prompt)
                result = {
                    "status": "success",
                    "task_type": "keyword_generation",
                    "data": {"keywords": response.text.split(", ")[:max_keywords]},
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            self._update_metrics(result, provider)
            return result
            
        except Exception as e:
            logger.error(f"Keyword generation failed: {str(e)}")
            self.metrics["failed_requests"] += 1
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_pricing(self,
                            product_info: Dict[str, Any],
                            competitor_prices: List[float],
                            cost: float,
                            provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """가격 전략 분석"""
        try:
            self.metrics["total_requests"] += 1
            
            if provider == AIProvider.AUTO:
                provider = AIProvider.OLLAMA  # 가격 정보는 로컬 처리
            
            if provider == AIProvider.OLLAMA:
                result = await self.ollama_service.analyze_pricing_strategy(
                    product_info=product_info,
                    competitor_prices=competitor_prices,
                    cost=cost
                )
            elif provider == AIProvider.LANGCHAIN:
                result = await self.langchain_service.generate_pricing_strategy({
                    "category": product_info.get("category", ""),
                    "cost": cost,
                    "competitor_avg_price": sum(competitor_prices) / len(competitor_prices) if competitor_prices else 0,
                    "quality_grade": product_info.get("quality_grade", "표준"),
                    "brand_recognition": product_info.get("brand_recognition", "중간")
                })
            else:
                # Gemini는 민감한 가격 정보 처리 지양
                result = {
                    "status": "error",
                    "error": "Pricing analysis should be done locally for security"
                }
            
            self._update_metrics(result, provider)
            return result
            
        except Exception as e:
            logger.error(f"Pricing analysis failed: {str(e)}")
            self.metrics["failed_requests"] += 1
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def predict_demand(self,
                           product_category: str,
                           historical_data: List[Dict[str, Any]],
                           external_factors: Optional[Dict[str, Any]] = None,
                           provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """수요 예측"""
        try:
            self.metrics["total_requests"] += 1
            
            if provider == AIProvider.AUTO:
                provider = AIProvider.GEMINI  # 복잡한 예측은 Gemini
            
            if provider == AIProvider.GEMINI:
                result = await self.gemini_service.predict_demand(
                    product_category=product_category,
                    historical_data=historical_data,
                    external_factors=external_factors
                )
            else:
                # 간단한 예측은 로컬에서도 가능
                result = {
                    "status": "success",
                    "task_type": "demand_prediction",
                    "data": {
                        "prediction": "Limited prediction available locally",
                        "recommendation": "Use cloud service for better accuracy"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            self._update_metrics(result, provider)
            return result
            
        except Exception as e:
            logger.error(f"Demand prediction failed: {str(e)}")
            self.metrics["failed_requests"] += 1
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_competition(self,
                                product_name: str,
                                category: str,
                                price_range: Dict[str, float],
                                provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """경쟁사 분석"""
        try:
            self.metrics["total_requests"] += 1
            
            if provider == AIProvider.AUTO:
                provider = AIProvider.GEMINI  # 실시간 경쟁사 정보
            
            result = await self.gemini_service.analyze_competition(
                product_name=product_name,
                category=category,
                price_range=price_range
            )
            
            self._update_metrics(result, provider)
            return result
            
        except Exception as e:
            logger.error(f"Competition analysis failed: {str(e)}")
            self.metrics["failed_requests"] += 1
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_description(self,
                                 product_info: Dict[str, Any],
                                 style: str = "detailed",
                                 platform: str = "general",
                                 provider: AIProvider = AIProvider.AUTO) -> Dict[str, Any]:
        """상품 설명 생성"""
        try:
            self.metrics["total_requests"] += 1
            
            if provider == AIProvider.AUTO:
                # 플랫폼별 최적화가 필요하면 LangChain
                provider = AIProvider.LANGCHAIN if platform != "general" else AIProvider.OLLAMA
            
            if provider == AIProvider.LANGCHAIN:
                result = await self.langchain_service.generate_content({
                    "product_info": product_info,
                    "content_type": "description",
                    "target_platform": platform
                })
            elif provider == AIProvider.OLLAMA:
                result = await self.ollama_service.generate_product_description(
                    product_info=product_info,
                    style=style
                )
            else:
                result = await self.gemini_service.generate_marketing_content(
                    product_info=product_info,
                    content_type="description"
                )
            
            self._update_metrics(result, provider)
            return result
            
        except Exception as e:
            logger.error(f"Description generation failed: {str(e)}")
            self.metrics["failed_requests"] += 1
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def batch_process(self,
                          tasks: List[Dict[str, Any]],
                          max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """배치 처리 (병렬 실행)"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_task(task: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                task_type = task.get("type")
                params = task.get("params", {})
                
                if task_type == "optimize_product":
                    return await self.optimize_product(**params)
                elif task_type == "analyze_market":
                    return await self.analyze_market(**params)
                elif task_type == "generate_keywords":
                    return await self.generate_keywords(**params)
                elif task_type == "analyze_pricing":
                    return await self.analyze_pricing(**params)
                elif task_type == "predict_demand":
                    return await self.predict_demand(**params)
                elif task_type == "analyze_competition":
                    return await self.analyze_competition(**params)
                elif task_type == "generate_description":
                    return await self.generate_description(**params)
                else:
                    return {
                        "status": "error",
                        "error": f"Unknown task type: {task_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
        
        # 모든 작업 병렬 실행
        results = await asyncio.gather(
            *[process_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "error",
                    "error": str(result),
                    "task_index": i,
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def learn_from_feedback(self,
                                task_id: str,
                                feedback: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 피드백 학습"""
        try:
            # 피드백 데이터 저장 (추후 학습 엔진과 연동)
            feedback_data = {
                "task_id": task_id,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 여기서는 로깅만, 실제로는 학습 엔진과 연동
            logger.info(f"Feedback received for task {task_id}: {feedback}")
            
            return {
                "status": "success",
                "message": "Feedback recorded successfully",
                "data": feedback_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_all_models_status(self) -> Dict[str, Any]:
        """모든 AI 모델 상태 확인"""
        try:
            # 병렬로 상태 확인
            statuses = await asyncio.gather(
                self.gemini_service.get_model_status(),
                self.ollama_service.get_model_status(),
                self.langchain_service.get_model_status(),
                return_exceptions=True
            )
            
            # 결과 정리
            model_statuses = {}
            services = ["gemini", "ollama", "langchain"]
            
            for i, status in enumerate(statuses):
                if isinstance(status, Exception):
                    model_statuses[services[i]] = {
                        "status": "error",
                        "error": str(status)
                    }
                else:
                    model_statuses[services[i]] = status
            
            return {
                "status": "success",
                "models": model_statuses,
                "metrics": self.metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _select_provider(self, 
                        task_type: TaskType, 
                        data: Dict[str, Any]) -> AIProvider:
        """작업 유형과 데이터에 따라 최적의 제공자 선택"""
        # 기본 매핑 사용
        provider = self.task_provider_mapping.get(task_type, AIProvider.GEMINI)
        
        # 데이터 민감도에 따른 조정
        if self._contains_sensitive_data(data):
            # 민감한 데이터는 로컬 처리
            if provider == AIProvider.GEMINI:
                provider = AIProvider.OLLAMA
        
        # 실시간 데이터 필요 여부
        if self._requires_realtime_data(task_type):
            # 실시간 데이터는 Gemini
            if provider == AIProvider.OLLAMA:
                provider = AIProvider.GEMINI
        
        return provider
    
    def _contains_sensitive_data(self, data: Dict[str, Any]) -> bool:
        """민감한 데이터 포함 여부 확인"""
        sensitive_keys = ["price", "cost", "margin", "profit", "revenue", 
                         "personal_info", "customer_data", "api_key"]
        
        for key in sensitive_keys:
            if key in str(data).lower():
                return True
        return False
    
    def _requires_realtime_data(self, task_type: TaskType) -> bool:
        """실시간 데이터 필요 여부"""
        realtime_tasks = [
            TaskType.MARKET_ANALYSIS,
            TaskType.COMPETITOR_ANALYSIS,
            TaskType.DEMAND_PREDICTION
        ]
        return task_type in realtime_tasks
    
    def _update_metrics(self, result: Dict[str, Any], provider: AIProvider):
        """메트릭 업데이트"""
        if result.get("status") == "success":
            self.metrics["successful_requests"] += 1
            self.metrics["provider_usage"][provider] += 1
        else:
            self.metrics["failed_requests"] += 1
    
    def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """여러 결과 병합"""
        merged = {
            "status": "success",
            "data": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for result in results:
            if result.get("status") == "error":
                return result  # 하나라도 실패하면 실패 반환
            
            # 데이터 병합
            if "data" in result:
                merged["data"].update(result["data"])
        
        return merged