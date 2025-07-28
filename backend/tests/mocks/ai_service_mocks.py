"""
Mock implementations for AI services
"""
import asyncio
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, Mock
from decimal import Decimal
from datetime import datetime, timedelta
import json
import random


class MockGeminiService:
    """Mock Google Gemini AI service for testing"""
    
    def __init__(self):
        self.api_key = "test_gemini_api_key"
        self.model = "gemini-pro"
        self.session = AsyncMock()
        
    async def generate_content(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Mock content generation"""
        # Simulate different responses based on prompt content
        if "상품 설명" in prompt or "product description" in prompt.lower():
            return {
                "text": """이 제품은 뛰어난 품질과 실용성을 겸비한 프리미엄 상품입니다. 
                엄선된 소재로 제작되어 내구성이 뛰어나며, 세련된 디자인으로 어떤 공간에도 잘 어울립니다. 
                사용자의 편의를 고려한 인체공학적 설계로 편안한 사용감을 제공하며, 
                간편한 관리와 유지보수로 오랫동안 사용할 수 있습니다. 
                합리적인 가격으로 최고의 가치를 경험해보세요.""",
                "confidence": 0.92,
                "model_version": "gemini-pro-001",
                "tokens_used": 156,
                "generation_time": 1.2
            }
        
        elif "키워드" in prompt or "keyword" in prompt.lower():
            return {
                "text": "프리미엄, 고품질, 내구성, 실용적, 세련된디자인, 편안함, 합리적가격, 베스트셀러, 인기상품, 추천제품",
                "confidence": 0.89,
                "model_version": "gemini-pro-001",
                "tokens_used": 45,
                "generation_time": 0.8
            }
        
        elif "가격 분석" in prompt or "price analysis" in prompt.lower():
            return {
                "text": """시장 분석 결과, 해당 카테고리의 평균 가격은 25,000-35,000원 범위입니다. 
                경쟁 제품 대비 20% 저렴한 가격으로 설정하면 가격 경쟁력을 확보할 수 있으며, 
                마진율 30-40%를 고려할 때 적정 판매가는 28,000원을 추천합니다. 
                할인 이벤트 시 25,000원까지 가능하며, 이는 소비자 구매 심리를 자극할 수 있는 가격대입니다.""",
                "confidence": 0.87,
                "model_version": "gemini-pro-001",
                "tokens_used": 198,
                "generation_time": 1.5
            }
        
        else:
            return {
                "text": f"AI가 생성한 응답: {prompt[:50]}... 에 대한 분석 결과입니다.",
                "confidence": 0.85,
                "model_version": "gemini-pro-001",
                "tokens_used": 75,
                "generation_time": 1.0
            }
    
    async def analyze_market_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock market analysis"""
        category = product_data.get("category", "일반")
        price = product_data.get("price", 20000)
        
        # Simulate market analysis based on category
        trend_score = random.randint(70, 95)
        demand_level = "높음" if trend_score > 85 else "보통" if trend_score > 75 else "낮음"
        
        return {
            "trend_analysis": {
                "trend": "상승" if trend_score > 80 else "안정",
                "score": trend_score,
                "demand_level": demand_level,
                "seasonality": "연중" if category in ["생활용품", "주방용품"] else "계절성",
                "growth_rate": f"{random.randint(5, 25)}%"
            },
            "competition_analysis": {
                "competitor_count": random.randint(50, 200),
                "average_price": price * random.uniform(0.8, 1.3),
                "price_advantage": random.choice(["높음", "보통", "낮음"]),
                "differentiation_score": random.randint(60, 90)
            },
            "recommendations": [
                "키워드 최적화를 통한 검색 노출 개선",
                "경쟁가 대비 5-10% 할인된 가격 설정",
                "고품질 상품 이미지 활용",
                "고객 리뷰 관리 강화",
                "배송 서비스 차별화"
            ],
            "optimal_price_range": {
                "min": int(price * 0.85),
                "max": int(price * 1.15),
                "recommended": int(price * 0.95)
            },
            "analysis_date": datetime.utcnow().isoformat(),
            "confidence": 0.88
        }
    
    async def optimize_pricing(self, product_data: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock price optimization"""
        current_price = product_data.get("price", 20000)
        cost = product_data.get("cost", current_price * 0.5)
        
        # Calculate optimized price
        market_avg = market_data.get("competition_analysis", {}).get("average_price", current_price)
        optimal_price = int(market_avg * random.uniform(0.9, 1.1))
        
        margin = (optimal_price - cost) / optimal_price * 100
        
        return {
            "current_price": current_price,
            "suggested_price": optimal_price,
            "price_change": optimal_price - current_price,
            "price_change_percent": round((optimal_price - current_price) / current_price * 100, 2),
            "margin_rate": round(margin, 2),
            "confidence": random.uniform(0.85, 0.95),
            "reasoning": [
                f"시장 평균가 {market_avg:,}원 대비 적정 수준",
                f"목표 마진율 {margin:.1f}% 달성",
                "경쟁력 있는 가격으로 판매량 증대 기대",
                "수익성과 경쟁력의 균형 확보"
            ],
            "risk_assessment": {
                "price_sensitivity": random.choice(["높음", "보통", "낮음"]),
                "margin_risk": "낮음" if margin > 30 else "보통" if margin > 20 else "높음",
                "competition_risk": random.choice(["낮음", "보통", "높음"])
            },
            "optimization_date": datetime.utcnow().isoformat()
        }
    
    async def generate_product_tags(self, product_data: Dict[str, Any]) -> List[str]:
        """Mock product tag generation"""
        category = product_data.get("category", "일반")
        name = product_data.get("name", "")
        
        base_tags = ["인기상품", "베스트", "추천", "고품질", "프리미엄"]
        
        category_tags = {
            "보석": ["액세서리", "쥬얼리", "선물", "럭셔리", "패션"],
            "주방용품": ["쿠킹", "요리", "주방", "생활용품", "실용적"],
            "생활용품": ["홈데코", "정리정돈", "편리함", "실용성", "필수템"]
        }
        
        specific_tags = category_tags.get(category, ["실용적", "편리함", "필수템"])
        
        # Combine and return random selection
        all_tags = base_tags + specific_tags
        return random.sample(all_tags, min(8, len(all_tags)))


class MockOllamaService:
    """Mock Ollama local LLM service for testing"""
    
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model = "llama2"
        self.session = AsyncMock()
        
    async def generate(self, prompt: str, model: str = "llama2", **kwargs) -> Dict[str, Any]:
        """Mock local LLM generation"""
        return {
            "model": model,
            "created_at": datetime.utcnow().isoformat(),
            "response": f"로컬 AI 모델 {model}로 생성된 응답: {prompt[:100]}...",
            "done": True,
            "context": [1, 2, 3, 4, 5],  # Mock context tokens
            "total_duration": 2500000000,  # 2.5 seconds in nanoseconds
            "load_duration": 500000000,    # 0.5 seconds
            "prompt_eval_count": 26,
            "prompt_eval_duration": 800000000,
            "eval_count": 298,
            "eval_duration": 1200000000
        }
    
    async def list_models(self) -> Dict[str, Any]:
        """Mock model listing"""
        return {
            "models": [
                {
                    "name": "llama2",
                    "modified_at": datetime.utcnow().isoformat(),
                    "size": 3826793677,
                    "digest": "78e26419b446"
                },
                {
                    "name": "codellama",
                    "modified_at": datetime.utcnow().isoformat(),
                    "size": 3826793677,
                    "digest": "8fdf8f752f6e"
                }
            ]
        }
    
    async def embeddings(self, prompt: str, model: str = "llama2") -> Dict[str, Any]:
        """Mock embedding generation"""
        # Generate mock embedding vector
        embedding = [random.uniform(-1, 1) for _ in range(4096)]
        
        return {
            "embedding": embedding,
            "model": model,
            "prompt": prompt
        }


class MockLangChainService:
    """Mock LangChain service for testing"""
    
    def __init__(self):
        self.llm = MockOllamaService()
        self.chains = {}
        
    async def create_chain(self, chain_type: str, **kwargs) -> str:
        """Mock chain creation"""
        chain_id = f"chain_{chain_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.chains[chain_id] = {
            "type": chain_type,
            "config": kwargs,
            "created_at": datetime.utcnow().isoformat()
        }
        return chain_id
    
    async def run_chain(self, chain_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock chain execution"""
        if chain_id not in self.chains:
            raise ValueError(f"Chain {chain_id} not found")
        
        chain_info = self.chains[chain_id]
        chain_type = chain_info["type"]
        
        # Mock different chain types
        if chain_type == "product_analysis":
            return {
                "chain_id": chain_id,
                "result": {
                    "analysis": "상품 분석 완료",
                    "score": random.randint(70, 95),
                    "recommendations": [
                        "이미지 품질 개선",
                        "설명 보완",
                        "가격 최적화"
                    ]
                },
                "steps": [
                    {"step": "데이터 수집", "status": "completed"},
                    {"step": "AI 분석", "status": "completed"},
                    {"step": "결과 생성", "status": "completed"}
                ],
                "execution_time": 3.5,
                "tokens_used": 234
            }
        
        elif chain_type == "market_research":
            return {
                "chain_id": chain_id,
                "result": {
                    "market_size": f"{random.randint(100, 1000)}억원",
                    "growth_rate": f"{random.randint(5, 25)}%",
                    "key_trends": [
                        "온라인 판매 증가",
                        "개인화 서비스 확대",
                        "친환경 제품 선호"
                    ],
                    "opportunities": [
                        "틈새 시장 진입",
                        "차별화된 서비스",
                        "브랜드 포지셔닝"
                    ]
                },
                "confidence": random.uniform(0.8, 0.95),
                "data_sources": ["네이버 쇼핑", "쿠팡", "11번가"],
                "execution_time": 5.2
            }
        
        else:
            return {
                "chain_id": chain_id,
                "result": f"Mock result for {chain_type}",
                "execution_time": random.uniform(1.0, 5.0)
            }
    
    async def get_chain_history(self, chain_id: str) -> List[Dict[str, Any]]:
        """Mock chain execution history"""
        return [
            {
                "execution_id": f"exec_{i}",
                "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                "input_data": {"test": f"input_{i}"},
                "result": {"test": f"result_{i}"},
                "execution_time": random.uniform(1.0, 5.0),
                "status": "completed"
            }
            for i in range(5)
        ]


class MockAIServiceManager:
    """Mock AI service manager for coordinating all AI services"""
    
    def __init__(self):
        self.gemini = MockGeminiService()
        self.ollama = MockOllamaService()
        self.langchain = MockLangChainService()
        self.active_service = "gemini"
        
    async def switch_service(self, service_name: str) -> Dict[str, Any]:
        """Switch between AI services"""
        if service_name not in ["gemini", "ollama", "langchain"]:
            raise ValueError(f"Unknown service: {service_name}")
        
        self.active_service = service_name
        return {
            "switched_to": service_name,
            "status": "active",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def generate_with_fallback(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate content with fallback mechanism"""
        try:
            # Try primary service (Gemini)
            if self.active_service == "gemini":
                result = await self.gemini.generate_content(prompt, **kwargs)
                result["service_used"] = "gemini"
                return result
        except Exception:
            pass
        
        try:
            # Fallback to Ollama
            result = await self.ollama.generate(prompt, **kwargs)
            result["service_used"] = "ollama"
            return result
        except Exception:
            pass
        
        # Final fallback - simple response
        return {
            "text": f"기본 AI 응답: {prompt[:50]}...",
            "service_used": "fallback",
            "confidence": 0.5,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def batch_process(self, prompts: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Process multiple prompts in batch"""
        results = []
        for i, prompt in enumerate(prompts):
            result = await self.generate_with_fallback(prompt, **kwargs)
            result["batch_index"] = i
            results.append(result)
            
            # Simulate processing delay
            await asyncio.sleep(0.1)
        
        return results
    
    async def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all AI services"""
        return {
            "gemini": {
                "status": "available",
                "model": "gemini-pro",
                "last_used": datetime.utcnow().isoformat(),
                "requests_today": random.randint(50, 200)
            },
            "ollama": {
                "status": "available",
                "model": "llama2",
                "last_used": datetime.utcnow().isoformat(),
                "local_model": True
            },
            "langchain": {
                "status": "available",
                "active_chains": len(self.langchain.chains),
                "last_used": datetime.utcnow().isoformat()
            }
        }