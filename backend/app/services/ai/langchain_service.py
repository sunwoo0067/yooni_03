"""LangChain service for multi-model workflows and chain management."""

import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# Optional AI dependencies - 설치되지 않은 경우 기본 동작으로 fallback
try:
    from langchain.chains import LLMChain, SequentialChain
    from langchain.prompts import PromptTemplate, ChatPromptTemplate
    from langchain.memory import ConversationBufferWindowMemory
    from langchain.schema import BaseMessage, HumanMessage, AIMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_community.llms import Ollama
    from langchain.callbacks.manager import CallbackManagerForChainRun
    from langchain.agents import AgentExecutor, create_structured_chat_agent
    from langchain.tools import Tool, StructuredTool
    from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangChain modules not available: {e}. Using fallback implementation.")
    LANGCHAIN_AVAILABLE = False
    # Dummy classes for fallback
    class LLMChain: pass
    class SequentialChain: pass
    class PromptTemplate: pass
    class ChatPromptTemplate: pass
    class ConversationBufferWindowMemory: pass
    class BaseMessage: pass
    class HumanMessage: pass
    class AIMessage: pass
    class ChatGoogleGenerativeAI: pass
    class Ollama: pass
    class CallbackManagerForChainRun: pass
    class AgentExecutor: pass
    class Tool: pass
    class StructuredTool: pass
    class JsonOutputParser: 
        def parse(self, text): return {}
    class PydanticOutputParser: 
        def parse(self, text): return {}
    def create_structured_chat_agent(*args, **kwargs): return None
from pydantic import BaseModel, Field

from app.services.ai.gemini_service import GeminiService
from app.services.ai.ollama_service import OllamaService
from app.core.cache import cache_result

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """AI 작업 유형"""
    OPTIMIZE_PRODUCT = "optimize_product"
    MARKET_ANALYSIS = "market_analysis"
    PRICING_STRATEGY = "pricing_strategy"
    CONTENT_GENERATION = "content_generation"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    DEMAND_PREDICTION = "demand_prediction"
    CUSTOMER_INSIGHTS = "customer_insights"


class ProductOptimizationOutput(BaseModel):
    """상품 최적화 출력 스키마"""
    optimized_title: str = Field(description="최적화된 상품명")
    keywords: List[str] = Field(description="추천 키워드 목록")
    description: str = Field(description="상품 설명")
    selling_points: List[str] = Field(description="주요 판매 포인트")
    target_audience: str = Field(description="타겟 고객층")
    seo_score: float = Field(description="SEO 점수 (0-100)")


class MarketAnalysisOutput(BaseModel):
    """시장 분석 출력 스키마"""
    market_trends: List[str] = Field(description="현재 시장 트렌드")
    opportunities: List[str] = Field(description="시장 기회")
    threats: List[str] = Field(description="위협 요소")
    recommendations: List[str] = Field(description="추천 전략")
    growth_potential: float = Field(description="성장 잠재력 (0-100)")


class LangChainService:
    """
    LangChain 통합 서비스
    - AI 작업 체인 관리
    - 멀티 모델 워크플로우
    - 메모리 및 컨텍스트 관리
    - 자동화된 작업 흐름
    """
    
    def __init__(self):
        """Initialize LangChain service with Gemini and Ollama."""
        # Gemini 모델 초기화
        self.gemini_llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GEMINI_API_KEY", "AIzaSyD18ntyKoXp7QQhgd_xe4dDqfC_yVTtnrY"),
            temperature=0.7,
            max_output_tokens=4096,
            top_p=0.8,
            top_k=40
        )
        
        # Ollama 모델 초기화
        self.ollama_llm = Ollama(
            model="llama3.2:3b",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.7,
            num_predict=2048
        )
        
        # 메모리 초기화 (최근 10개 대화 유지)
        self.memory = ConversationBufferWindowMemory(
            k=10,
            return_messages=True,
            memory_key="chat_history"
        )
        
        # 서비스 인스턴스
        self.gemini_service = GeminiService()
        self.ollama_service = OllamaService()
        
        # 체인 초기화
        self._initialize_chains()
        
        logger.info("LangChain service initialized")
    
    def _initialize_chains(self):
        """각종 체인 초기화"""
        # 상품 최적화 체인
        self.product_optimization_chain = self._create_product_optimization_chain()
        
        # 시장 분석 체인
        self.market_analysis_chain = self._create_market_analysis_chain()
        
        # 가격 전략 체인
        self.pricing_strategy_chain = self._create_pricing_strategy_chain()
        
        # 콘텐츠 생성 체인
        self.content_generation_chain = self._create_content_generation_chain()
    
    def _create_keyword_extraction_chain(self) -> LLMChain:
        """키워드 추출 체인 생성"""
        keyword_prompt = PromptTemplate(
            input_variables=["product_name", "category", "features"],
            template="""
            상품 정보:
            - 상품명: {product_name}
            - 카테고리: {category}
            - 특징: {features}
            
            이 상품에 대한 SEO 최적화된 키워드 20개를 추출해주세요.
            각 키워드는 쉼표로 구분하여 나열해주세요.
            """
        )
        return LLMChain(
            llm=self.ollama_llm,
            prompt=keyword_prompt,
            output_key="keywords"
        )
    
    def _create_trend_analysis_chain(self) -> LLMChain:
        """시장 트렌드 분석 체인 생성"""
        trend_prompt = PromptTemplate(
            input_variables=["category", "keywords"],
            template="""
            카테고리: {category}
            키워드: {keywords}
            
            현재 이 카테고리의 시장 트렌드와 소비자 선호도를 분석하고,
            상품 최적화를 위한 인사이트를 제공해주세요.
            """
        )
        return LLMChain(
            llm=self.gemini_llm,
            prompt=trend_prompt,
            output_key="market_insights"
        )
    
    def _create_optimization_chain(self) -> LLMChain:
        """최종 최적화 체인 생성"""
        optimization_prompt = PromptTemplate(
            input_variables=["product_name", "keywords", "market_insights"],
            template="""
            원본 상품명: {product_name}
            추출된 키워드: {keywords}
            시장 인사이트: {market_insights}
            
            위 정보를 바탕으로 다음을 생성해주세요:
            1. SEO 최적화된 상품명 (100자 이내)
            2. 핵심 판매 포인트 5개
            3. 타겟 고객층 설명
            4. 간단한 상품 설명 (200자)
            
            JSON 형식으로 응답해주세요.
            """
        )
        return LLMChain(
            llm=self.ollama_llm,
            prompt=optimization_prompt,
            output_key="optimization_result"
        )
    
    def _create_product_optimization_chain(self) -> SequentialChain:
        """상품 최적화 체인 생성"""
        # 각 단계별 체인 생성
        keyword_chain = self._create_keyword_extraction_chain()
        trend_chain = self._create_trend_analysis_chain()
        optimization_chain = self._create_optimization_chain()
        
        # 체인 연결
        return SequentialChain(
            chains=[keyword_chain, trend_chain, optimization_chain],
            input_variables=["product_name", "category", "features"],
            output_variables=["keywords", "market_insights", "optimization_result"],
            verbose=True
        )
    
    def _create_competition_analysis_chain(self) -> LLMChain:
        """경쟁사 분석 체인 생성"""
        competition_prompt = PromptTemplate(
            input_variables=["category", "product_type", "price_range"],
            template="""
            카테고리: {category}
            상품 유형: {product_type}
            가격대: {price_range}
            
            이 시장의 주요 경쟁자들과 그들의 전략을 분석해주세요.
            특히 성공적인 판매 전략과 차별화 포인트를 중심으로 분석해주세요.
            """
        )
        return LLMChain(
            llm=self.gemini_llm,
            prompt=competition_prompt,
            output_key="competition_analysis"
        )
    
    def _create_demand_forecast_chain(self) -> LLMChain:
        """수요 예측 체인 생성"""
        demand_prompt = PromptTemplate(
            input_variables=["category", "season", "competition_analysis"],
            template="""
            카테고리: {category}
            현재 시즌: {season}
            경쟁 분석: {competition_analysis}
            
            향후 3개월간의 수요 변화를 예측하고,
            재고 관리 및 가격 전략을 제안해주세요.
            """
        )
        return LLMChain(
            llm=self.ollama_llm,
            prompt=demand_prompt,
            output_key="demand_forecast"
        )
    
    def _create_market_synthesis_chain(self) -> LLMChain:
        """시장 종합 분석 체인 생성"""
        synthesis_prompt = PromptTemplate(
            input_variables=["competition_analysis", "demand_forecast"],
            template="""
            경쟁 분석: {competition_analysis}
            수요 예측: {demand_forecast}
            
            위 분석을 종합하여 다음을 제공해주세요:
            1. 시장 기회 (3-5개)
            2. 위협 요소 (3-5개)
            3. 추천 전략 (5개)
            4. 성장 잠재력 평가 (0-100점)
            
            JSON 형식으로 응답해주세요.
            """
        )
        return LLMChain(
            llm=self.gemini_llm,
            prompt=synthesis_prompt,
            output_key="market_synthesis"
        )
    
    def _create_market_analysis_chain(self) -> SequentialChain:
        """시장 분석 체인 생성"""
        # 각 단계별 체인 생성
        competition_chain = self._create_competition_analysis_chain()
        demand_chain = self._create_demand_forecast_chain()
        synthesis_chain = self._create_market_synthesis_chain()
        
        return SequentialChain(
            chains=[competition_chain, demand_chain, synthesis_chain],
            input_variables=["category", "product_type", "price_range", "season"],
            output_variables=["competition_analysis", "demand_forecast", "market_synthesis"],
            verbose=True
        )
    
    def _create_pricing_strategy_chain(self) -> LLMChain:
        """가격 전략 체인 생성"""
        pricing_prompt = ChatPromptTemplate.from_messages([
            ("system", "당신은 온라인 판매 가격 전략 전문가입니다."),
            ("human", """
            상품 정보:
            - 카테고리: {category}
            - 원가: {cost}원
            - 경쟁사 평균가: {competitor_avg_price}원
            - 품질 등급: {quality_grade}
            - 브랜드 인지도: {brand_recognition}
            
            다음 전략별 가격을 제안해주세요:
            1. 저가 전략 (시장 진입)
            2. 중가 전략 (균형)
            3. 프리미엄 전략 (고품질)
            
            각 전략에 대해:
            - 추천 가격
            - 예상 마진율
            - 예상 판매량 (상대적)
            - 장단점
            
            JSON 형식으로 응답해주세요.
            """)
        ])
        
        return LLMChain(
            llm=self.ollama_llm,  # 가격 정보는 로컬에서 처리
            prompt=pricing_prompt,
            output_key="pricing_strategies"
        )
    
    def _create_content_generation_chain(self) -> SequentialChain:
        """콘텐츠 생성 체인"""
        # Step 1: 상품 특징 분석 (Ollama)
        feature_prompt = PromptTemplate(
            input_variables=["product_info"],
            template="""
            상품 정보: {product_info}
            
            이 상품의 주요 특징과 장점을 분석하여,
            마케팅에 활용할 수 있는 핵심 메시지를 추출해주세요.
            """
        )
        feature_chain = LLMChain(
            llm=self.ollama_llm,
            prompt=feature_prompt,
            output_key="key_features"
        )
        
        # Step 2: 콘텐츠 생성 (Gemini)
        content_prompt = PromptTemplate(
            input_variables=["key_features", "content_type", "target_platform"],
            template="""
            핵심 특징: {key_features}
            콘텐츠 유형: {content_type}
            플랫폼: {target_platform}
            
            위 정보를 바탕으로 {target_platform}에 최적화된 {content_type}을 생성해주세요.
            
            요구사항:
            1. 플랫폼 특성에 맞는 톤과 스타일
            2. SEO 최적화
            3. 구매 전환을 유도하는 CTA 포함
            4. 적절한 이모지 사용
            """
        )
        content_chain = LLMChain(
            llm=self.gemini_llm,
            prompt=content_prompt,
            output_key="generated_content"
        )
        
        return SequentialChain(
            chains=[feature_chain, content_chain],
            input_variables=["product_info", "content_type", "target_platform"],
            output_variables=["key_features", "generated_content"],
            verbose=True
        )
    
    @cache_result(prefix="ai_product_optimization", ttl=3600)  # 1시간 캐싱
    async def optimize_product_workflow(self,
                                      product_data: Dict[str, Any]) -> Dict[str, Any]:
        """상품 최적화 워크플로우 실행"""
        try:
            # 체인 실행
            result = await self._run_chain(
                self.product_optimization_chain,
                {
                    "product_name": product_data.get("name", ""),
                    "category": product_data.get("category", ""),
                    "features": ", ".join(product_data.get("features", []))
                }
            )
            
            # 결과 파싱
            optimization_data = self._parse_json_result(
                result.get("optimization_result", "{}")
            )
            
            # 메모리에 저장
            self.memory.save_context(
                {"input": f"상품 최적화: {product_data.get('name', '')}"},
                {"output": str(optimization_data)}
            )
            
            return {
                "status": "success",
                "task_type": TaskType.OPTIMIZE_PRODUCT,
                "data": {
                    "keywords": result.get("keywords", "").split(", "),
                    "market_insights": result.get("market_insights", ""),
                    "optimization": optimization_data
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Product optimization workflow failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @cache_result(prefix="ai_market_analysis", ttl=7200)  # 2시간 캐싱
    async def analyze_market_workflow(self,
                                    market_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 분석 워크플로우 실행"""
        try:
            # 체인 실행
            result = await self._run_chain(
                self.market_analysis_chain,
                {
                    "category": market_data.get("category", ""),
                    "product_type": market_data.get("product_type", ""),
                    "price_range": f"{market_data.get('min_price', 0)}~{market_data.get('max_price', 0)}원",
                    "season": market_data.get("season", "일반")
                }
            )
            
            # 결과 파싱
            synthesis_data = self._parse_json_result(
                result.get("market_synthesis", "{}")
            )
            
            return {
                "status": "success",
                "task_type": TaskType.MARKET_ANALYSIS,
                "data": {
                    "competition_analysis": result.get("competition_analysis", ""),
                    "demand_forecast": result.get("demand_forecast", ""),
                    "synthesis": synthesis_data
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Market analysis workflow failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @cache_result(prefix="ai_pricing_strategy", ttl=3600)  # 1시간 캐싱
    async def generate_pricing_strategy(self,
                                      pricing_data: Dict[str, Any]) -> Dict[str, Any]:
        """가격 전략 생성"""
        try:
            # 체인 실행
            result = await self._run_chain(
                self.pricing_strategy_chain,
                {
                    "category": pricing_data.get("category", ""),
                    "cost": pricing_data.get("cost", 0),
                    "competitor_avg_price": pricing_data.get("competitor_avg_price", 0),
                    "quality_grade": pricing_data.get("quality_grade", "표준"),
                    "brand_recognition": pricing_data.get("brand_recognition", "중간")
                }
            )
            
            # 결과 파싱
            strategies = self._parse_json_result(
                result.get("pricing_strategies", "{}")
            )
            
            return {
                "status": "success",
                "task_type": TaskType.PRICING_STRATEGY,
                "data": strategies,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Pricing strategy generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_content(self,
                             content_request: Dict[str, Any]) -> Dict[str, Any]:
        """콘텐츠 생성"""
        try:
            # 체인 실행
            result = await self._run_chain(
                self.content_generation_chain,
                {
                    "product_info": json.dumps(
                        content_request.get("product_info", {}),
                        ensure_ascii=False
                    ),
                    "content_type": content_request.get("content_type", "description"),
                    "target_platform": content_request.get("target_platform", "general")
                }
            )
            
            return {
                "status": "success",
                "task_type": TaskType.CONTENT_GENERATION,
                "data": {
                    "key_features": result.get("key_features", ""),
                    "content": result.get("generated_content", "")
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def create_custom_workflow(self,
                                   workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """커스텀 워크플로우 생성 및 실행"""
        try:
            # 워크플로우 스텝 정의
            steps = workflow_config.get("steps", [])
            chains = []
            
            for step in steps:
                if step["type"] == "gemini":
                    llm = self.gemini_llm
                elif step["type"] == "ollama":
                    llm = self.ollama_llm
                else:
                    continue
                
                prompt = PromptTemplate(
                    input_variables=step.get("input_variables", []),
                    template=step.get("template", "")
                )
                
                chain = LLMChain(
                    llm=llm,
                    prompt=prompt,
                    output_key=step.get("output_key", f"step_{len(chains)}")
                )
                chains.append(chain)
            
            # 시퀀셜 체인 생성
            if chains:
                workflow_chain = SequentialChain(
                    chains=chains,
                    input_variables=workflow_config.get("input_variables", []),
                    output_variables=[step.get("output_key", f"step_{i}") 
                                    for i, step in enumerate(steps)],
                    verbose=True
                )
                
                # 체인 실행
                result = await self._run_chain(
                    workflow_chain,
                    workflow_config.get("inputs", {})
                )
                
                return {
                    "status": "success",
                    "task_type": "custom_workflow",
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error": "No valid chains created",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Custom workflow failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _run_chain(self, chain: Union[LLMChain, SequentialChain], 
                        inputs: Dict[str, Any]) -> Dict[str, Any]:
        """체인 실행 헬퍼"""
        try:
            # 동기 체인을 비동기로 실행
            import asyncio
            result = await asyncio.to_thread(chain.run, inputs)
            
            # SequentialChain의 경우 dict 반환, LLMChain의 경우 string 반환
            if isinstance(result, str):
                return {chain.output_key: result}
            return result
            
        except Exception as e:
            logger.error(f"Chain execution failed: {str(e)}")
            raise
    
    def _parse_json_result(self, json_str: str) -> Dict[str, Any]:
        """JSON 결과 파싱"""
        try:
            # JSON 블록 추출 (```json ... ``` 형식 처리)
            if "```json" in json_str:
                start = json_str.find("```json") + 7
                end = json_str.find("```", start)
                json_str = json_str[start:end].strip()
            
            return json.loads(json_str)
        except json.JSONDecodeError:
            # JSON 파싱 실패시 원본 텍스트 반환
            return {"raw_output": json_str}
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 기록 조회"""
        messages = self.memory.chat_memory.messages
        history = []
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        
        return history
    
    def clear_memory(self):
        """메모리 초기화"""
        self.memory.clear()
        logger.info("Conversation memory cleared")
    
    async def get_model_status(self) -> Dict[str, Any]:
        """모델 상태 확인"""
        try:
            # Gemini 상태
            gemini_status = await self.gemini_service.get_model_status()
            
            # Ollama 상태
            ollama_status = await self.ollama_service.get_model_status()
            
            return {
                "service": "LangChain Integration",
                "status": "active",
                "models": {
                    "gemini": gemini_status,
                    "ollama": ollama_status
                },
                "memory": {
                    "messages_count": len(self.memory.chat_memory.messages),
                    "window_size": self.memory.k
                },
                "chains": {
                    "product_optimization": "active",
                    "market_analysis": "active",
                    "pricing_strategy": "active",
                    "content_generation": "active"
                },
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Model status check failed: {str(e)}")
            return {
                "service": "LangChain Integration",
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }