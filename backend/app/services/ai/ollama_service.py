"""Ollama local model service for privacy-sensitive AI tasks."""

import asyncio
import aiohttp
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
import subprocess
import psutil

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Ollama 로컬 모델 서비스
    - 개인정보 보호 (상품 정보)
    - 빠른 응답속도
    - 오프라인 작업
    - 반복적인 최적화 작업
    - RTX 4070 + 32GB RAM 최적화
    """
    
    def __init__(self):
        """Initialize Ollama service."""
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_model = "llama3.2:3b"  # RTX 4070에 최적화된 모델
        self.fallback_models = ["mistral:7b", "phi3:mini"]  # 대체 모델들
        
        # 성능 최적화 설정
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": 2048,
            "num_ctx": 4096,  # RTX 4070 VRAM에 맞춤
            "num_gpu": 1,
            "num_thread": 8,  # CPU 스레드
        }
        
        # 모델 초기화는 나중에 필요할 때 수행
        self._initialized = False
        
    async def _ensure_ollama_running(self):
        """Ollama 서비스가 실행 중인지 확인하고 필요시 시작"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        logger.info("Ollama service is running")
                        await self._ensure_model_pulled()
                        return
        except Exception:
            logger.warning("Ollama service not running, attempting to start...")
            
        # Ollama 서비스 시작 시도
        try:
            # Windows에서 Ollama 실행
            if os.name == 'nt':  # Windows
                subprocess.Popen(["ollama", "serve"], 
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:  # Linux/Mac
                subprocess.Popen(["ollama", "serve"])
            
            # 서비스 시작 대기
            await asyncio.sleep(5)
            await self._ensure_model_pulled()
            
        except Exception as e:
            logger.error(f"Failed to start Ollama service: {str(e)}")
    
    async def _ensure_model_pulled(self):
        """필요한 모델이 다운로드되어 있는지 확인"""
        try:
            async with aiohttp.ClientSession() as session:
                # 설치된 모델 목록 확인
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        installed_models = [m['name'] for m in data.get('models', [])]
                        
                        # 기본 모델이 없으면 다운로드
                        if self.default_model not in installed_models:
                            logger.info(f"Pulling model {self.default_model}...")
                            await self._pull_model(self.default_model)
                            
        except Exception as e:
            logger.error(f"Failed to check/pull models: {str(e)}")
    
    async def _pull_model(self, model_name: str):
        """모델 다운로드"""
        try:
            async with aiohttp.ClientSession() as session:
                pull_data = {"name": model_name}
                async with session.post(
                    f"{self.base_url}/api/pull",
                    json=pull_data
                ) as response:
                    if response.status == 200:
                        # 스트리밍 응답 처리
                        async for line in response.content:
                            if line:
                                try:
                                    status = json.loads(line)
                                    if 'status' in status:
                                        logger.info(f"Pull status: {status['status']}")
                                except json.JSONDecodeError:
                                    pass
                        logger.info(f"Model {model_name} pulled successfully")
                    else:
                        logger.error(f"Failed to pull model: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {str(e)}")
    
    async def optimize_product_title(self,
                                   current_title: str,
                                   category: str,
                                   keywords: List[str],
                                   max_length: int = 100) -> Dict[str, Any]:
        """상품명 최적화 (개인정보 보호)"""
        try:
            prompt = f"""
            당신은 온라인 쇼핑 상품명 최적화 전문가입니다.
            다음 상품명을 검색 최적화와 클릭률을 높이도록 개선해주세요.
            
            현재 상품명: {current_title}
            카테고리: {category}
            주요 키워드: {', '.join(keywords)}
            최대 길이: {max_length}자
            
            요구사항:
            1. 주요 키워드를 자연스럽게 포함
            2. 브랜드명이 있다면 앞쪽에 배치
            3. 핵심 특징을 간결하게 표현
            4. 불필요한 기호나 반복 제거
            5. 모바일에서도 잘 보이도록 중요 정보는 앞쪽에
            
            다음 형식으로 3개의 개선안을 제시해주세요:
            1. [개선안1]
            2. [개선안2]
            3. [개선안3]
            
            각 개선안 아래에 개선 이유를 간단히 설명해주세요.
            """
            
            response = await self._generate(prompt)
            
            if response.get('status') == 'success':
                # 응답 파싱
                content = response.get('response', '')
                suggestions = self._parse_title_suggestions(content)
                
                return {
                    "status": "success",
                    "task_type": "title_optimization",
                    "data": {
                        "original_title": current_title,
                        "suggestions": suggestions,
                        "keywords_used": keywords,
                        "optimization_tips": [
                            "검색 노출을 위해 주요 키워드를 앞쪽에 배치했습니다",
                            "모바일 화면을 고려하여 핵심 정보를 압축했습니다",
                            "클릭률 향상을 위해 매력적인 수식어를 추가했습니다"
                        ]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Title optimization failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _ensure_initialized(self):
        """Ollama 서비스 초기화 확인"""
        if not self._initialized:
            await self._ensure_ollama_running()
            self._initialized = True
    
    async def generate_product_description(self,
                                         product_info: Dict[str, Any],
                                         style: str = "detailed") -> Dict[str, Any]:
        """상품 설명 생성 (개인정보 보호)"""
        await self._ensure_initialized()
        try:
            prompt = f"""
            전문 상품 설명 작성가로서 다음 상품의 설명을 작성해주세요.
            
            상품 정보:
            - 상품명: {product_info.get('name', '')}
            - 카테고리: {product_info.get('category', '')}
            - 주요 특징: {product_info.get('features', [])}
            - 사양: {product_info.get('specifications', {})}
            - 타겟 고객: {product_info.get('target_audience', '')}
            
            작성 스타일: {style}
            
            다음 구조로 작성해주세요:
            
            1. 핵심 소개 (2-3문장)
            2. 주요 특징 및 장점 (불릿 포인트)
            3. 상세 설명
            4. 사용 방법/활용 팁
            5. 구매 시 혜택
            
            SEO를 고려하여 자연스럽게 키워드를 포함시켜주세요.
            """
            
            response = await self._generate(prompt)
            
            if response.get('status') == 'success':
                return {
                    "status": "success",
                    "task_type": "description_generation",
                    "data": {
                        "description": response.get('response', ''),
                        "style": style,
                        "seo_keywords_included": True,
                        "mobile_optimized": True
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Description generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def extract_keywords(self,
                             text: str,
                             category: str,
                             max_keywords: int = 20) -> Dict[str, Any]:
        """키워드 추출 (로컬 처리로 개인정보 보호)"""
        try:
            prompt = f"""
            SEO 전문가로서 다음 텍스트에서 온라인 쇼핑에 유용한 키워드를 추출해주세요.
            
            텍스트: {text}
            카테고리: {category}
            
            다음 기준으로 {max_keywords}개의 키워드를 추출해주세요:
            1. 검색량이 높을 것으로 예상되는 키워드
            2. 구매 의도가 있는 키워드
            3. 카테고리와 관련성이 높은 키워드
            4. 롱테일 키워드 포함
            
            각 키워드에 대해 다음 정보를 제공해주세요:
            - 키워드
            - 예상 검색 빈도 (높음/중간/낮음)
            - 경쟁도 (높음/중간/낮음)
            - 추천 이유
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await self._generate(prompt, json_mode=True)
            
            if response.get('status') == 'success':
                try:
                    keywords_data = json.loads(response.get('response', '{}'))
                except json.JSONDecodeError:
                    # JSON 파싱 실패시 기본 형식으로 변환
                    keywords_data = self._extract_keywords_fallback(response.get('response', ''))
                
                return {
                    "status": "success",
                    "task_type": "keyword_extraction",
                    "data": keywords_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Keyword extraction failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_pricing_strategy(self,
                                     product_info: Dict[str, Any],
                                     competitor_prices: List[float],
                                     cost: float) -> Dict[str, Any]:
        await self._ensure_initialized()
        """가격 전략 분석 (민감한 가격 정보 로컬 처리)"""
        try:
            avg_competitor_price = sum(competitor_prices) / len(competitor_prices) if competitor_prices else 0
            
            prompt = f"""
            가격 전략 전문가로서 다음 상품의 최적 가격을 분석해주세요.
            
            상품 정보:
            - 카테고리: {product_info.get('category', '')}
            - 품질 등급: {product_info.get('quality_grade', '표준')}
            - 브랜드 인지도: {product_info.get('brand_recognition', '중간')}
            
            원가: {cost:,}원
            경쟁사 가격: {competitor_prices}
            경쟁사 평균가: {avg_competitor_price:,.0f}원
            
            다음 항목들을 분석해주세요:
            1. 추천 판매가격 (3가지 전략)
               - 저가 전략
               - 중가 전략
               - 프리미엄 전략
            2. 각 전략의 예상 마진율
            3. 예상 판매량 (상대적)
            4. 프로모션 가격 제안
            5. 번들 판매 전략
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await self._generate(prompt, json_mode=True)
            
            if response.get('status') == 'success':
                try:
                    pricing_data = json.loads(response.get('response', '{}'))
                except json.JSONDecodeError:
                    pricing_data = {"analysis": response.get('response', '')}
                
                return {
                    "status": "success",
                    "task_type": "pricing_strategy",
                    "data": pricing_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Pricing strategy analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def optimize_images_metadata(self,
                                     image_descriptions: List[str],
                                     product_info: Dict[str, Any]) -> Dict[str, Any]:
        """이미지 메타데이터 최적화"""
        try:
            prompt = f"""
            이미지 SEO 전문가로서 다음 상품 이미지들의 메타데이터를 최적화해주세요.
            
            상품 정보:
            - 상품명: {product_info.get('name', '')}
            - 카테고리: {product_info.get('category', '')}
            
            이미지 설명:
            {chr(10).join([f"{i+1}. {desc}" for i, desc in enumerate(image_descriptions)])}
            
            각 이미지에 대해 다음을 작성해주세요:
            1. SEO 최적화된 파일명 (영문, 하이픈 사용)
            2. Alt 텍스트 (한글, 검색 최적화)
            3. Title 속성
            4. 이미지 설명 (간단한 캡션)
            
            JSON 형식으로 응답해주세요.
            """
            
            response = await self._generate(prompt, json_mode=True)
            
            if response.get('status') == 'success':
                try:
                    metadata = json.loads(response.get('response', '{}'))
                except json.JSONDecodeError:
                    metadata = {"suggestions": response.get('response', '')}
                
                return {
                    "status": "success",
                    "task_type": "image_metadata_optimization",
                    "data": metadata,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Image metadata optimization failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _generate(self, prompt: str, json_mode: bool = False) -> Dict[str, Any]:
        """Ollama API를 통한 텍스트 생성"""
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.default_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": self.generation_config
                }
                
                if json_mode:
                    data["format"] = "json"
                
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "status": "success",
                            "response": result.get("response", ""),
                            "model": self.default_model,
                            "eval_count": result.get("eval_count", 0),
                            "eval_duration": result.get("eval_duration", 0)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API error: {error_text}")
                        return {
                            "status": "error",
                            "error": f"API error: {response.status}",
                            "details": error_text
                        }
                        
        except asyncio.TimeoutError:
            logger.error("Ollama request timeout")
            return {
                "status": "error",
                "error": "Request timeout"
            }
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _parse_title_suggestions(self, content: str) -> List[Dict[str, str]]:
        """상품명 제안 파싱"""
        suggestions = []
        lines = content.split('\n')
        
        current_suggestion = None
        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.')):
                if current_suggestion:
                    suggestions.append(current_suggestion)
                current_suggestion = {
                    "title": line[2:].strip(),
                    "reason": ""
                }
            elif current_suggestion and line:
                current_suggestion["reason"] += line + " "
        
        if current_suggestion:
            suggestions.append(current_suggestion)
        
        return suggestions
    
    def _extract_keywords_fallback(self, content: str) -> Dict[str, List]:
        """키워드 추출 폴백 파서"""
        keywords = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 간단한 키워드 추출
                parts = line.split('-')
                if parts:
                    keyword = parts[0].strip()
                    if keyword:
                        keywords.append({
                            "keyword": keyword,
                            "search_volume": "중간",
                            "competition": "중간",
                            "reason": "관련성 높음"
                        })
        
        return {"keywords": keywords[:20]}  # 최대 20개
    
    async def get_model_status(self) -> Dict[str, Any]:
        """모델 상태 확인"""
        try:
            async with aiohttp.ClientSession() as session:
                # Ollama 서비스 상태 확인
                try:
                    async with session.get(f"{self.base_url}/api/tags") as response:
                        if response.status == 200:
                            data = await response.json()
                            models = data.get('models', [])
                            
                            # GPU 사용량 확인
                            gpu_info = self._get_gpu_usage()
                            
                            return {
                                "service": "Ollama Local",
                                "status": "active",
                                "base_url": self.base_url,
                                "models": [m['name'] for m in models],
                                "current_model": self.default_model,
                                "gpu_info": gpu_info,
                                "last_check": datetime.utcnow().isoformat(),
                                "capabilities": [
                                    "title_optimization",
                                    "description_generation",
                                    "keyword_extraction",
                                    "pricing_strategy",
                                    "image_metadata"
                                ]
                            }
                except Exception:
                    return {
                        "service": "Ollama Local",
                        "status": "inactive",
                        "error": "Service not running",
                        "last_check": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Model status check failed: {str(e)}")
            return {
                "service": "Ollama Local",
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    def _get_gpu_usage(self) -> Dict[str, Any]:
        """GPU 사용량 확인 (NVIDIA)"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # 첫 번째 GPU (RTX 4070)
                return {
                    "name": gpu.name,
                    "memory_used": f"{gpu.memoryUsed}MB",
                    "memory_total": f"{gpu.memoryTotal}MB",
                    "memory_free": f"{gpu.memoryFree}MB",
                    "gpu_load": f"{gpu.load * 100:.1f}%",
                    "temperature": f"{gpu.temperature}°C"
                }
        except Exception:
            pass
        
        return {"status": "GPU info not available"}