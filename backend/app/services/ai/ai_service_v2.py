"""
Improved AI Service with robust error handling.
강력한 에러 처리가 적용된 개선된 AI 서비스.
"""
from typing import Optional, Dict, Any, List, Union
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio

from app.core.exceptions import ExternalServiceError, ServiceException
from app.core.logging_utils import get_logger, log_execution_time
from app.core.external_api_utils import with_timeout
from app.core.cache_utils import CacheService, cached_result
from app.core.constants import Limits


class AIProvider(ABC):
    """AI 프로바이더 추상 베이스 클래스"""
    
    def __init__(self, name: str, api_key: str):
        self.name = name
        self.api_key = api_key
        self.logger = get_logger(f"AI_{name}")
        
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """텍스트 생성"""
        pass
        
    @abstractmethod
    async def analyze_product(
        self, 
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """상품 분석"""
        pass
        
    @abstractmethod
    async def is_available(self) -> bool:
        """서비스 가용성 확인"""
        pass


class GeminiProvider(AIProvider):
    """Google Gemini 프로바이더"""
    
    def __init__(self, api_key: str):
        super().__init__("Gemini", api_key)
        self._initialize_client()
        
    def _initialize_client(self):
        """클라이언트 초기화"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.logger.info("Gemini client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini: {e}")
            self.model = None
            
    @with_timeout(30)
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Gemini로 텍스트 생성"""
        if not self.model:
            raise ExternalServiceError(
                service_name="Gemini",
                detail="Gemini client not initialized"
            )
            
        try:
            # 동기 호출을 비동기로 변환
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config={
                        "max_output_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
            )
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"Gemini generation failed: {e}")
            raise ExternalServiceError(
                service_name="Gemini",
                detail=str(e)
            )
            
    async def analyze_product(
        self, 
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """상품 분석"""
        prompt = f"""
        다음 상품 정보를 분석해주세요:
        
        상품명: {product_data.get('name')}
        설명: {product_data.get('description')}
        카테고리: {product_data.get('category')}
        가격: {product_data.get('price')}
        
        다음 항목들을 분석해주세요:
        1. 타겟 고객층
        2. 주요 특징 및 장점
        3. 마케팅 포인트
        4. 추천 키워드 (5개)
        5. 예상 판매 전망
        """
        
        try:
            result = await self.generate_text(prompt)
            
            # 결과 파싱 (실제로는 더 정교한 파싱 필요)
            return {
                "analysis_text": result,
                "analyzed_at": datetime.utcnow().isoformat(),
                "provider": self.name
            }
            
        except Exception as e:
            self.logger.error(f"Product analysis failed: {e}")
            raise
            
    async def is_available(self) -> bool:
        """Gemini 서비스 가용성 확인"""
        try:
            await self.generate_text("test", max_tokens=10)
            return True
        except:
            return False


class OllamaProvider(AIProvider):
    """Ollama 로컬 LLM 프로바이더"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__("Ollama", "local")
        self.base_url = base_url
        
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Ollama로 텍스트 생성"""
        # Ollama API 호출 구현
        raise NotImplementedError("Ollama provider implementation needed")
        
    async def analyze_product(
        self, 
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """상품 분석"""
        # Ollama 상품 분석 구현
        raise NotImplementedError("Ollama provider implementation needed")
        
    async def is_available(self) -> bool:
        """Ollama 서비스 가용성 확인"""
        # 로컬 서비스 확인
        return False


class AIServiceV2:
    """
    개선된 AI 서비스 (폴백 지원).
    여러 AI 프로바이더를 관리하고 자동 폴백을 제공합니다.
    """
    
    def __init__(
        self,
        providers: List[AIProvider],
        cache_service: Optional[CacheService] = None
    ):
        self.providers = providers
        self.cache_service = cache_service
        self.logger = get_logger(self.__class__.__name__)
        self._current_provider_index = 0
        
    async def get_available_provider(self) -> Optional[AIProvider]:
        """사용 가능한 프로바이더 찾기"""
        for i, provider in enumerate(self.providers):
            try:
                if await provider.is_available():
                    self._current_provider_index = i
                    return provider
            except Exception as e:
                self.logger.warning(
                    f"Provider {provider.name} availability check failed: {e}"
                )
                continue
                
        return None
        
    @log_execution_time("generate_text")
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        텍스트 생성 (자동 폴백).
        
        Returns:
            {
                "text": "생성된 텍스트",
                "provider": "사용된 프로바이더",
                "cached": bool,
                "generated_at": "timestamp"
            }
        """
        # 캐시 키 생성
        cache_key = None
        if use_cache and self.cache_service:
            cache_key = self.cache_service.make_key(
                "text",
                hashlib.md5(f"{prompt}:{max_tokens}:{temperature}".encode()).hexdigest()
            )
            
            # 캐시 조회
            cached = self.cache_service.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached
                
        # 프로바이더 순회하며 시도
        errors = []
        
        for provider in self.providers:
            try:
                self.logger.info(f"Trying provider: {provider.name}")
                
                text = await provider.generate_text(
                    prompt, 
                    max_tokens, 
                    temperature
                )
                
                result = {
                    "text": text,
                    "provider": provider.name,
                    "cached": False,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                # 캐싱
                if cache_key:
                    self.cache_service.set(cache_key, result, ttl=3600)
                    
                return result
                
            except Exception as e:
                self.logger.error(
                    f"Provider {provider.name} failed",
                    error=e
                )
                errors.append({
                    "provider": provider.name,
                    "error": str(e)
                })
                continue
                
        # 모든 프로바이더 실패
        raise ServiceException(
            "All AI providers failed",
            code="AI_PROVIDERS_UNAVAILABLE",
            details={"errors": errors}
        )
        
    @log_execution_time("analyze_product")
    async def analyze_product(
        self,
        product_data: Dict[str, Any],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """상품 분석 (자동 폴백)"""
        # 캐시 확인
        if use_cache and self.cache_service:
            cache_key = self.cache_service.make_key(
                "product_analysis",
                product_data.get("id", "unknown")
            )
            
            cached = self.cache_service.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached
                
        # 프로바이더 시도
        provider = await self.get_available_provider()
        if not provider:
            raise ServiceException(
                "No AI provider available",
                code="NO_AI_PROVIDER"
            )
            
        try:
            result = await provider.analyze_product(product_data)
            result["cached"] = False
            
            # 캐싱 (24시간)
            if use_cache and self.cache_service and cache_key:
                self.cache_service.set(cache_key, result, ttl=86400)
                
            return result
            
        except Exception as e:
            self.logger.error(f"Product analysis failed: {e}")
            raise ServiceException(
                "Product analysis failed",
                code="PRODUCT_ANALYSIS_FAILED",
                details={"error": str(e)}
            )
            
    async def batch_analyze_products(
        self,
        products: List[Dict[str, Any]],
        batch_size: int = 5,
        delay: float = 1.0
    ) -> List[Dict[str, Any]]:
        """배치 상품 분석"""
        results = []
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            # 배치 처리
            batch_results = await asyncio.gather(
                *[self.analyze_product(p) for p in batch],
                return_exceptions=True
            )
            
            # 결과 처리
            for product, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Failed to analyze product {product.get('id')}: {result}"
                    )
                    results.append({
                        "product_id": product.get("id"),
                        "error": str(result),
                        "status": "failed"
                    })
                else:
                    results.append(result)
                    
            # 다음 배치 전 지연
            if i + batch_size < len(products):
                await asyncio.sleep(delay)
                
        return results
        
    def get_status(self) -> Dict[str, Any]:
        """서비스 상태 조회"""
        return {
            "providers": [
                {
                    "name": p.name,
                    "available": asyncio.create_task(p.is_available())
                }
                for p in self.providers
            ],
            "current_provider": self.providers[self._current_provider_index].name
            if self.providers else None,
            "cache_enabled": bool(self.cache_service)
        }


import hashlib  # 상단에 추가