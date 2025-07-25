"""
상품 용도 분석기

목표: 제품 용도 변경으로 경쟁력 확보
방법: AI 기반 대체 용도 발굴
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal

import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.product_processing import (
    ProductPurposeAnalysis,
    CompetitorAnalysis,
    ProcessingCostTracking
)
from app.models.product import Product
from app.services.ai.ai_manager import AIManager
from app.services.ai.ollama_service import OllamaService
from app.core.config import settings


class ProductPurposeAnalyzer:
    """AI 기반 상품 용도 분석기"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_manager = AIManager()
        self.ollama_service = OllamaService()
        
        # 시간대별 AI 모델 선택
        self.current_hour = datetime.now().hour
        self.is_night_time = 22 <= self.current_hour or self.current_hour <= 6
    
    async def analyze_alternative_uses(self, product: Product) -> Dict:
        """대체 용도 분석"""
        
        # 제품 정보 수집
        product_info = {
            "name": product.name,
            "description": product.description or "",
            "category": product.category_path or "",
            "brand": product.brand or "",
            "attributes": product.attributes or {}
        }
        
        # AI 분석 프롬프트
        analysis_prompt = f"""
        다음 제품의 대안적 용도를 분석하고 새로운 시장 기회를 발굴해주세요.

        제품 정보:
        - 이름: {product_info['name']}
        - 설명: {product_info['description'][:500]}
        - 카테고리: {product_info['category']}
        - 브랜드: {product_info['brand']}
        - 속성: {json.dumps(product_info['attributes'], ensure_ascii=False)}

        분석 요청사항:
        1. 기존 용도 외의 창의적 활용 방안
        2. 새로운 타겟 고객층 발굴
        3. 계절/상황별 활용 방안
        4. 다른 제품과의 조합 활용
        5. 틈새 시장 기회

        결과를 JSON 형태로 반환:
        {{
            "original_purpose": "기존 주용도",
            "alternative_purposes": [
                {{
                    "purpose": "대체 용도 설명",
                    "target_audience": "타겟 고객층",
                    "market_size": "시장 규모 (small/medium/large)",
                    "competition_level": "경쟁 강도 (low/medium/high)",
                    "seasonal_factor": "계절 요인",
                    "price_advantage": "가격 경쟁력",
                    "marketing_angle": "마케팅 포인트"
                }}
            ],
            "cross_selling_opportunities": [
                {{
                    "product_type": "연관 제품",
                    "combination_benefit": "조합 효과"
                }}
            ],
            "market_positioning": {{
                "differentiation": "차별화 포인트",
                "competitive_advantage": "경쟁 우위",
                "pricing_strategy": "가격 전략"
            }}
        }}
        """
        
        try:
            if self.is_night_time:
                result = await self.ollama_service.generate_text(
                    analysis_prompt, model="llama3.1:8b"
                )
                ai_model_used = "ollama_llama3.1_8b"
                cost = 0.0
            else:
                result = await self.ai_manager.generate_text(
                    analysis_prompt, model="gpt-4o-mini"
                )
                ai_model_used = "gpt-4o-mini"
                cost = 0.004
            
            # JSON 파싱
            try:
                analysis_data = json.loads(result)
            except json.JSONDecodeError:
                # 파싱 실패 시 기본 분석 수행
                analysis_data = await self._perform_basic_analysis(product_info)
            
            # 시장 기회 점수 계산
            market_scores = await self._calculate_market_scores(analysis_data)
            analysis_data["market_scores"] = market_scores
            
            # 분석 결과 저장
            purpose_analysis = ProductPurposeAnalysis(
                product_id=product.id,
                original_purpose=analysis_data.get("original_purpose", "기본 용도"),
                alternative_purposes=analysis_data.get("alternative_purposes", []),
                target_audience=analysis_data.get("market_positioning", {}),
                market_opportunity=market_scores,
                ai_model_used=ai_model_used,
                analysis_cost=Decimal(str(cost)),
                created_at=datetime.now()
            )
            
            self.db.add(purpose_analysis)
            
            # 비용 추적
            await self._track_processing_cost(
                "purpose_analysis", ai_model_used, 1, cost
            )
            
            self.db.commit()
            
            return analysis_data
            
        except Exception as e:
            print(f"용도 분석 오류: {e}")
            return await self._perform_basic_analysis(product_info)
    
    async def generate_new_descriptions(
        self, 
        product: Product, 
        selected_purpose: Dict,
        marketplace: str
    ) -> Dict:
        """새로운 상세페이지 생성"""
        
        description_prompt = f"""
        다음 제품에 대해 새로운 용도에 맞는 상세페이지를 작성해주세요.

        기존 제품 정보:
        - 이름: {product.name}
        - 설명: {product.description or ''}
        - 카테고리: {product.category_path or ''}

        새로운 용도:
        - 목적: {selected_purpose.get('purpose', '')}
        - 타겟 고객: {selected_purpose.get('target_audience', '')}
        - 마케팅 포인트: {selected_purpose.get('marketing_angle', '')}

        마켓플레이스: {marketplace}

        작성 요청사항:
        1. 새로운 용도에 맞는 제품명
        2. 매력적인 상세 설명
        3. 핵심 혜택 포인트
        4. 사용 시나리오
        5. 고객 후기 스타일 문구

        결과를 JSON 형태로 반환:
        {{
            "new_title": "새로운 제품명",
            "detailed_description": "상세 설명",
            "key_benefits": ["혜택1", "혜택2", "혜택3"],
            "usage_scenarios": [
                {{
                    "scenario": "사용 상황",
                    "description": "상황 설명"
                }}
            ],
            "customer_testimonial_style": [
                "고객 후기 스타일 문구1",
                "고객 후기 스타일 문구2"
            ],
            "seo_keywords": ["키워드1", "키워드2", "키워드3"]
        }}
        """
        
        try:
            if self.is_night_time:
                result = await self.ollama_service.generate_text(
                    description_prompt, model="llama3.1:8b"
                )
                ai_model_used = "ollama_llama3.1_8b"
                cost = 0.0
            else:
                result = await self.ai_manager.generate_text(
                    description_prompt, model="gpt-4o-mini"
                )
                ai_model_used = "gpt-4o-mini"
                cost = 0.003
            
            try:
                description_data = json.loads(result)
            except json.JSONDecodeError:
                description_data = await self._generate_basic_description(
                    product, selected_purpose
                )
            
            # 비용 추적
            await self._track_processing_cost(
                "description_generation", ai_model_used, 1, cost
            )
            
            return description_data
            
        except Exception as e:
            print(f"설명 생성 오류: {e}")
            return await self._generate_basic_description(product, selected_purpose)
    
    async def optimize_for_competition(
        self, 
        product: Product, 
        marketplace: str,
        target_keywords: List[str]
    ) -> Dict:
        """경쟁력 최적화"""
        
        # 경쟁사 분석
        competitor_analysis = await self._analyze_competitors(
            product, marketplace, target_keywords
        )
        
        # 최적화 전략 생성
        optimization_prompt = f"""
        경쟁 분석 결과를 바탕으로 제품의 경쟁력을 최적화하는 전략을 제시해주세요.

        제품 정보:
        - 이름: {product.name}
        - 현재 가격: {product.sale_price or product.retail_price}
        - 카테고리: {product.category_path or ''}

        경쟁사 분석:
        {json.dumps(competitor_analysis, ensure_ascii=False, indent=2)}

        타겟 키워드: {target_keywords}
        마켓플레이스: {marketplace}

        최적화 요청사항:
        1. 가격 포지셔닝 전략
        2. 차별화 포인트 강화
        3. 키워드 최적화 방안
        4. 프로모션 전략
        5. 리스크 요소 및 대응책

        결과를 JSON 형태로 반환:
        {{
            "pricing_strategy": {{
                "recommended_price": "추천 가격",
                "price_positioning": "가격 포지셔닝",
                "discount_strategy": "할인 전략"
            }},
            "differentiation": {{
                "unique_selling_points": ["차별화 포인트1", "차별화 포인트2"],
                "competitive_advantages": ["경쟁 우위1", "경쟁 우위2"]
            }},
            "keyword_optimization": {{
                "primary_keywords": ["주요 키워드1", "주요 키워드2"],
                "long_tail_keywords": ["롱테일 키워드1", "롱테일 키워드2"],
                "avoid_keywords": ["피해야 할 키워드1", "피해야 할 키워드2"]
            }},
            "promotion_strategy": {{
                "launch_tactics": ["론칭 전략1", "론칭 전략2"],
                "ongoing_promotions": ["지속 프로모션1", "지속 프로모션2"]
            }},
            "risk_mitigation": {{
                "potential_risks": ["리스크1", "리스크2"],
                "mitigation_plans": ["대응책1", "대응책2"]
            }}
        }}
        """
        
        try:
            if self.is_night_time:
                result = await self.ollama_service.generate_text(
                    optimization_prompt, model="llama3.1:8b"
                )
                ai_model_used = "ollama_llama3.1_8b"
                cost = 0.0
            else:
                result = await self.ai_manager.generate_text(
                    optimization_prompt, model="gpt-4o-mini"
                )
                ai_model_used = "gpt-4o-mini"
                cost = 0.005
            
            try:
                optimization_data = json.loads(result)
            except json.JSONDecodeError:
                optimization_data = await self._generate_basic_optimization(
                    product, competitor_analysis
                )
            
            # 경쟁사 분석 결과 저장
            competitor_analysis_record = CompetitorAnalysis(
                product_id=product.id,
                marketplace=marketplace,
                competitor_products=competitor_analysis.get("competitors", []),
                price_analysis=competitor_analysis.get("price_analysis", {}),
                naming_patterns=competitor_analysis.get("naming_patterns", {}),
                image_strategies=competitor_analysis.get("image_strategies", {}),
                market_gap_opportunities=optimization_data.get("differentiation", {}),
                competitive_advantage=optimization_data.get("promotion_strategy", {}),
                analysis_date=datetime.now()
            )
            
            self.db.add(competitor_analysis_record)
            
            # 비용 추적
            await self._track_processing_cost(
                "competition_optimization", ai_model_used, 1, cost
            )
            
            self.db.commit()
            
            return {
                "competitor_analysis": competitor_analysis,
                "optimization_strategy": optimization_data
            }
            
        except Exception as e:
            print(f"경쟁력 최적화 오류: {e}")
            return {
                "error": str(e),
                "competitor_analysis": competitor_analysis,
                "optimization_strategy": await self._generate_basic_optimization(
                    product, competitor_analysis
                )
            }
    
    async def _perform_basic_analysis(self, product_info: Dict) -> Dict:
        """기본 분석 수행 (AI 실패 시)"""
        
        # 카테고리 기반 대안 용도 추천
        category = product_info.get("category", "").lower()
        
        alternative_uses = []
        
        if "가전" in category or "전자" in category:
            alternative_uses = [
                {
                    "purpose": "업무용 도구로 활용",
                    "target_audience": "재택근무자, 프리랜서",
                    "market_size": "medium",
                    "competition_level": "medium",
                    "seasonal_factor": "연중",
                    "price_advantage": "업무 효율성 대비 저렴",
                    "marketing_angle": "생산성 향상"
                },
                {
                    "purpose": "선물용 아이템",
                    "target_audience": "선물을 찾는 고객",
                    "market_size": "large",
                    "competition_level": "high",
                    "seasonal_factor": "명절, 기념일",
                    "price_advantage": "합리적 선물 가격",
                    "marketing_angle": "실용적 선물"
                }
            ]
        elif "의류" in category or "패션" in category:
            alternative_uses = [
                {
                    "purpose": "코스프레/연출용",
                    "target_audience": "코스플레이어, 연극인",
                    "market_size": "small",
                    "competition_level": "low",
                    "seasonal_factor": "이벤트 시즌",
                    "price_advantage": "전문 의상 대비 저렴",
                    "marketing_angle": "다양한 컨셉 연출"
                }
            ]
        elif "스포츠" in category or "운동" in category:
            alternative_uses = [
                {
                    "purpose": "재활/치료용 보조 도구",
                    "target_audience": "재활 환자, 고령자",
                    "market_size": "medium",
                    "competition_level": "low",
                    "seasonal_factor": "연중",
                    "price_advantage": "의료기기 대비 저렴",
                    "marketing_angle": "건강 관리"
                }
            ]
        else:
            # 일반적인 대안 용도
            alternative_uses = [
                {
                    "purpose": "DIY 프로젝트 재료",
                    "target_audience": "DIY 애호가",
                    "market_size": "medium",
                    "competition_level": "medium",
                    "seasonal_factor": "연중",
                    "price_advantage": "전문 재료 대비 저렴",
                    "marketing_angle": "창의적 활용"
                }
            ]
        
        return {
            "original_purpose": "기본 용도",
            "alternative_purposes": alternative_uses,
            "cross_selling_opportunities": [
                {
                    "product_type": "관련 액세서리",
                    "combination_benefit": "완성도 향상"
                }
            ],
            "market_positioning": {
                "differentiation": "독특한 활용 방안",
                "competitive_advantage": "다목적 활용성",
                "pricing_strategy": "가성비 중심"
            }
        }
    
    async def _calculate_market_scores(self, analysis_data: Dict) -> Dict:
        """시장 기회 점수 계산"""
        
        scores = {}
        
        alternative_purposes = analysis_data.get("alternative_purposes", [])
        
        for i, purpose in enumerate(alternative_purposes):
            # 시장 규모 점수
            market_size = purpose.get("market_size", "medium")
            size_score = {"small": 3, "medium": 6, "large": 9}.get(market_size, 6)
            
            # 경쟁 강도 점수 (낮을수록 좋음)
            competition = purpose.get("competition_level", "medium")
            competition_score = {"low": 9, "medium": 6, "high": 3}.get(competition, 6)
            
            # 종합 점수
            total_score = (size_score + competition_score) / 2
            
            scores[f"purpose_{i}"] = {
                "market_size_score": size_score,
                "competition_score": competition_score,
                "total_score": total_score,
                "recommendation": "high" if total_score >= 7 else "medium" if total_score >= 5 else "low"
            }
        
        return scores
    
    async def _generate_basic_description(
        self, 
        product: Product, 
        selected_purpose: Dict
    ) -> Dict:
        """기본 설명 생성 (AI 실패 시)"""
        
        purpose = selected_purpose.get("purpose", "다목적 활용")
        target_audience = selected_purpose.get("target_audience", "모든 고객")
        
        return {
            "new_title": f"{product.name} - {purpose}",
            "detailed_description": f"이 제품은 {purpose}에 최적화된 제품입니다. {target_audience}에게 특히 추천드립니다.",
            "key_benefits": [
                "다양한 용도로 활용 가능",
                "뛰어난 가성비",
                "간편한 사용법"
            ],
            "usage_scenarios": [
                {
                    "scenario": "일상 사용",
                    "description": "매일 편리하게 활용할 수 있습니다"
                },
                {
                    "scenario": "특별한 상황",
                    "description": "특별한 순간에도 유용합니다"
                }
            ],
            "customer_testimonial_style": [
                "정말 유용한 제품이에요!",
                "가격 대비 만족스럽습니다"
            ],
            "seo_keywords": [
                product.name.split()[0] if product.name else "제품",
                purpose.split()[0] if purpose else "활용",
                "추천"
            ]
        }
    
    async def _analyze_competitors(
        self, 
        product: Product, 
        marketplace: str,
        target_keywords: List[str]
    ) -> Dict:
        """경쟁사 분석"""
        
        # 실제로는 마켓플레이스 API나 크롤링을 통해 경쟁 상품 정보 수집
        # 여기서는 시뮬레이션 데이터 반환
        
        return {
            "competitors": [
                {
                    "name": "경쟁 상품 1",
                    "price": float(product.sale_price or 0) * 1.2 if product.sale_price else 0,
                    "rating": 4.2,
                    "review_count": 156,
                    "keywords": target_keywords[:3]
                },
                {
                    "name": "경쟁 상품 2", 
                    "price": float(product.sale_price or 0) * 0.8 if product.sale_price else 0,
                    "rating": 3.8,
                    "review_count": 89,
                    "keywords": target_keywords[1:4]
                }
            ],
            "price_analysis": {
                "average_price": float(product.sale_price or 0) if product.sale_price else 0,
                "price_range": {
                    "min": float(product.sale_price or 0) * 0.7 if product.sale_price else 0,
                    "max": float(product.sale_price or 0) * 1.5 if product.sale_price else 0
                },
                "price_position": "competitive"
            },
            "naming_patterns": {
                "common_keywords": target_keywords,
                "naming_styles": ["간결형", "설명형", "혜택강조형"]
            },
            "image_strategies": {
                "common_styles": ["라이프스타일", "제품단독", "비교차트"],
                "color_trends": ["밝은톤", "자연색"]
            }
        }
    
    async def _generate_basic_optimization(
        self, 
        product: Product,
        competitor_analysis: Dict
    ) -> Dict:
        """기본 최적화 전략 (AI 실패 시)"""
        
        current_price = float(product.sale_price or product.retail_price or 0)
        avg_competitor_price = competitor_analysis.get("price_analysis", {}).get("average_price", current_price)
        
        return {
            "pricing_strategy": {
                "recommended_price": min(current_price, avg_competitor_price * 0.95),
                "price_positioning": "가성비 중심",
                "discount_strategy": "첫 구매 할인"
            },
            "differentiation": {
                "unique_selling_points": ["독특한 활용 방안", "뛰어난 내구성"],
                "competitive_advantages": ["빠른 배송", "우수한 고객 서비스"]
            },
            "keyword_optimization": {
                "primary_keywords": [product.name.split()[0] if product.name else "제품", "추천"],
                "long_tail_keywords": ["가성비 좋은", "실용적인"],
                "avoid_keywords": ["최저가", "특가"]
            },
            "promotion_strategy": {
                "launch_tactics": ["SNS 마케팅", "인플루언서 협업"],
                "ongoing_promotions": ["리뷰 이벤트", "재구매 할인"]
            },
            "risk_mitigation": {
                "potential_risks": ["가격 경쟁", "리뷰 관리"],
                "mitigation_plans": ["차별화 강화", "고객 만족도 향상"]
            }
        }
    
    async def _track_processing_cost(
        self, 
        processing_type: str, 
        ai_model: str, 
        request_count: int, 
        cost: float
    ):
        """가공 비용 추적"""
        
        today = datetime.now().date()
        
        cost_tracking = self.db.query(ProcessingCostTracking).filter(
            and_(
                ProcessingCostTracking.date == today,
                ProcessingCostTracking.processing_type == processing_type,
                ProcessingCostTracking.ai_model == ai_model
            )
        ).first()
        
        if cost_tracking:
            cost_tracking.total_requests += request_count
            cost_tracking.total_cost += Decimal(str(cost))
            cost_tracking.average_cost_per_request = (
                cost_tracking.total_cost / cost_tracking.total_requests
            )
            cost_tracking.cost_optimization_used = self.is_night_time
        else:
            cost_tracking = ProcessingCostTracking(
                date=datetime.now(),
                processing_type=processing_type,
                ai_model=ai_model,
                total_requests=request_count,
                total_cost=Decimal(str(cost)),
                average_cost_per_request=Decimal(str(cost)),
                cost_optimization_used=self.is_night_time
            )
            self.db.add(cost_tracking)
        
        self.db.commit()