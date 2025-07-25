"""
AI 상품명 생성기

목표: 카탈로그, 아임템위너 등 가격비교 사이트 회피
방법: 베스트셀러 패턴 분석 + AI 생성
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.product_processing import (
    ProductNameGeneration, 
    BestsellerPattern, 
    ProcessingCostTracking,
    MarketGuideline
)
from app.models.product import Product
from app.services.ai.ai_manager import AIManager
from app.services.ai.ollama_service import OllamaService
from app.core.config import settings


class ProductNameProcessor:
    """AI 기반 상품명 생성기"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_manager = AIManager()
        self.ollama_service = OllamaService()
        
        # 시간대별 AI 모델 선택 (비용 최적화)
        self.current_hour = datetime.now().hour
        self.is_night_time = 22 <= self.current_hour or self.current_hour <= 6
        
    async def analyze_bestseller_patterns(self, marketplace: str, category: str) -> Dict:
        """베스트셀러 상품명 패턴 분석"""
        
        # 기존 패턴 조회
        existing_patterns = self.db.query(BestsellerPattern).filter(
            and_(
                BestsellerPattern.marketplace == marketplace,
                BestsellerPattern.category == category,
                BestsellerPattern.last_analyzed > datetime.now() - timedelta(days=7)
            )
        ).all()
        
        if existing_patterns:
            # 최근 분석된 패턴이 있으면 사용
            return {
                "patterns": [p.pattern_data for p in existing_patterns],
                "effectiveness_scores": [p.effectiveness_score for p in existing_patterns]
            }
        
        # 새로운 패턴 분석
        bestseller_analysis_prompt = f"""
        {marketplace} 마켓플레이스의 {category} 카테고리에서 베스트셀러 상품명 패턴을 분석해주세요.

        다음 요소들을 중점적으로 분석:
        1. 키워드 사용 패턴
        2. 길이와 구조
        3. 감정적 표현
        4. 숫자와 특수문자 사용
        5. 가격비교 회피 전략

        분석 결과를 JSON 형태로 반환:
        {{
            "keyword_patterns": ["패턴1", "패턴2"],
            "length_range": {{"min": 10, "max": 50}},
            "emotional_triggers": ["단어1", "단어2"],
            "avoid_keywords": ["회피할키워드1", "회피할키워드2"],
            "structure_templates": ["템플릿1", "템플릿2"]
        }}
        """
        
        try:
            if self.is_night_time:
                # 야간: 로컬 모델 사용 (비용 절약)
                analysis_result = await self.ollama_service.generate_text(
                    bestseller_analysis_prompt,
                    model="llama3.1:8b"
                )
                ai_model_used = "ollama_llama3.1_8b"
                cost = 0.0
            else:
                # 주간: GPT-4o-mini 사용 (정확도 우선)
                analysis_result = await self.ai_manager.generate_text(
                    bestseller_analysis_prompt,
                    model="gpt-4o-mini"
                )
                ai_model_used = "gpt-4o-mini"
                cost = 0.002  # 예상 비용
            
            # JSON 파싱
            try:
                pattern_data = json.loads(analysis_result)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본 패턴 사용
                pattern_data = self._get_default_patterns(marketplace)
            
            # 패턴 저장
            new_pattern = BestsellerPattern(
                marketplace=marketplace,
                category=category,
                pattern_type="name_structure",
                pattern_data=pattern_data,
                effectiveness_score=8.5,  # 초기값
                last_analyzed=datetime.now()
            )
            self.db.add(new_pattern)
            
            # 비용 추적
            await self._track_processing_cost(
                "pattern_analysis", ai_model_used, 1, cost
            )
            
            self.db.commit()
            
            return {
                "patterns": [pattern_data],
                "effectiveness_scores": [8.5]
            }
            
        except Exception as e:
            print(f"패턴 분석 오류: {e}")
            return {
                "patterns": [self._get_default_patterns(marketplace)],
                "effectiveness_scores": [7.0]
            }
    
    async def generate_optimized_names(
        self, 
        product: Product, 
        marketplace: str, 
        target_count: int = 5
    ) -> List[str]:
        """AI 기반 최적화된 상품명 생성"""
        
        # 베스트셀러 패턴 분석
        patterns = await self.analyze_bestseller_patterns(
            marketplace, 
            product.category_path or "기본"
        )
        
        # 마켓 가이드라인 조회
        guidelines = await self.get_market_guidelines(marketplace)
        
        # 상품명 생성 프롬프트
        generation_prompt = f"""
        다음 상품에 대해 {marketplace}에 최적화된 상품명을 {target_count}개 생성해주세요.

        원본 상품 정보:
        - 이름: {product.name}
        - 브랜드: {product.brand or '없음'}
        - 카테고리: {product.category_path or '없음'}
        - 설명: {product.description[:200] if product.description else '없음'}

        베스트셀러 패턴:
        {json.dumps(patterns, ensure_ascii=False, indent=2)}

        마켓 가이드라인:
        - 최대 길이: {guidelines.get('naming_rules', {}).get('max_length', 50)}글자
        - 금지 키워드: {guidelines.get('prohibited_keywords', [])}
        - 필수 포함 요소: {guidelines.get('naming_rules', {}).get('required_elements', [])}

        생성 규칙:
        1. 가격비교 사이트 회피를 위한 독창적 표현 사용
        2. 검색 최적화를 위한 핵심 키워드 포함
        3. 감정적 어필 요소 추가
        4. 마켓별 가이드라인 준수
        5. 베스트셀러 패턴 적용

        결과를 JSON 배열 형태로 반환:
        ["상품명1", "상품명2", "상품명3", "상품명4", "상품명5"]
        """
        
        try:
            if self.is_night_time:
                # 야간: 로컬 모델 사용
                result = await self.ollama_service.generate_text(
                    generation_prompt,
                    model="llama3.1:8b"
                )
                ai_model_used = "ollama_llama3.1_8b"
                cost = 0.0
            else:
                # 주간: GPT-4o-mini 사용
                result = await self.ai_manager.generate_text(
                    generation_prompt,
                    model="gpt-4o-mini"
                )
                ai_model_used = "gpt-4o-mini"
                cost = 0.003
            
            # JSON 파싱
            try:
                generated_names = json.loads(result)
                if not isinstance(generated_names, list):
                    generated_names = [str(generated_names)]
            except json.JSONDecodeError:
                # 파싱 실패 시 텍스트에서 추출
                generated_names = self._extract_names_from_text(result)
            
            # 가이드라인 적용 검증
            validated_names = []
            for name in generated_names:
                if self._validate_name_guidelines(name, guidelines):
                    validated_names.append(name)
            
            # 충분한 이름이 생성되지 않았으면 기본 전략 사용
            if len(validated_names) < target_count:
                fallback_names = self._generate_fallback_names(product, marketplace)
                validated_names.extend(fallback_names[:target_count - len(validated_names)])
            
            # 생성 이력 저장
            name_generation = ProductNameGeneration(
                product_id=product.id,
                original_name=product.name,
                generated_names=validated_names,
                marketplace=marketplace,
                generation_strategy="ai_bestseller_pattern",
                ai_model_used=ai_model_used,
                generation_cost=Decimal(str(cost)),
                created_at=datetime.now()
            )
            self.db.add(name_generation)
            
            # 비용 추적
            await self._track_processing_cost(
                "name_generation", ai_model_used, 1, cost
            )
            
            self.db.commit()
            
            return validated_names[:target_count]
            
        except Exception as e:
            print(f"상품명 생성 오류: {e}")
            return self._generate_fallback_names(product, marketplace)[:target_count]
    
    async def apply_market_guidelines(self, names: List[str], marketplace: str) -> List[str]:
        """마켓별 가이드라인 적용"""
        
        guidelines = await self.get_market_guidelines(marketplace)
        validated_names = []
        
        for name in names:
            if self._validate_name_guidelines(name, guidelines):
                validated_names.append(name)
            else:
                # 가이드라인에 맞게 수정
                modified_name = self._fix_name_guidelines(name, guidelines)
                if modified_name:
                    validated_names.append(modified_name)
        
        return validated_names
    
    async def avoid_price_comparison(self, names: List[str]) -> List[str]:
        """가격비교 사이트 회피 로직"""
        
        # 가격비교 사이트에서 자주 사용되는 패턴들
        avoid_patterns = [
            r'\d+원',  # 가격 표시
            r'최저가',
            r'특가',
            r'할인',
            r'세일',
            r'무료배송',
            r'당일배송',
            r'정품',
            r'공식',
            r'브랜드명\s*공식'
        ]
        
        creative_names = []
        for name in names:
            # 패턴 탐지 및 대체
            modified_name = name
            for pattern in avoid_patterns:
                if re.search(pattern, modified_name):
                    # 창의적 표현으로 대체
                    modified_name = self._replace_with_creative_expression(
                        modified_name, pattern
                    )
            
            creative_names.append(modified_name)
        
        return creative_names
    
    async def get_market_guidelines(self, marketplace: str) -> Dict:
        """마켓별 가이드라인 조회"""
        
        guideline = self.db.query(MarketGuideline).filter(
            and_(
                MarketGuideline.marketplace == marketplace,
                MarketGuideline.is_active == True
            )
        ).first()
        
        if guideline:
            return {
                "image_specs": guideline.image_specs,
                "naming_rules": guideline.naming_rules,
                "description_rules": guideline.description_rules,
                "prohibited_keywords": guideline.prohibited_keywords or [],
                "required_fields": guideline.required_fields or []
            }
        
        # 기본 가이드라인 반환
        return self._get_default_guidelines(marketplace)
    
    def _get_default_patterns(self, marketplace: str) -> Dict:
        """기본 베스트셀러 패턴"""
        patterns = {
            "coupang": {
                "keyword_patterns": ["프리미엄", "고품질", "인기", "추천"],
                "length_range": {"min": 15, "max": 40},
                "emotional_triggers": ["특별한", "완벽한", "최고의", "믿을 수 있는"],
                "avoid_keywords": ["최저가", "특가", "할인"],
                "structure_templates": [
                    "[감정표현] [브랜드] [제품명] [특징]",
                    "[특징] [제품명] [용도] [품질표현]"
                ]
            },
            "naver": {
                "keyword_patterns": ["국내", "정품", "인증", "브랜드"],
                "length_range": {"min": 20, "max": 50},
                "emotional_triggers": ["안전한", "검증된", "신뢰할 수 있는", "품질보장"],
                "avoid_keywords": ["최저가", "공동구매", "묶음할인"],
                "structure_templates": [
                    "[브랜드] [제품명] [인증표시] [특징]",
                    "[품질표현] [제품명] [용도] [보장사항]"
                ]
            },
            "11st": {
                "keyword_patterns": ["혜택", "적립", "무료", "빠른"],
                "length_range": {"min": 10, "max": 35},
                "emotional_triggers": ["득템", "초이득", "강추", "인기폭발"],
                "avoid_keywords": ["특가", "반값", "덤핑"],
                "structure_templates": [
                    "[혜택표현] [제품명] [특징] [추천]",
                    "[인기표현] [브랜드] [제품명] [혜택]"
                ]
            }
        }
        return patterns.get(marketplace, patterns["coupang"])
    
    def _get_default_guidelines(self, marketplace: str) -> Dict:
        """기본 마켓 가이드라인"""
        guidelines = {
            "coupang": {
                "naming_rules": {
                    "max_length": 40,
                    "required_elements": ["제품명", "브랜드"],
                    "forbidden_chars": ["♥", "★", "◆"]
                },
                "prohibited_keywords": ["최저가", "덤핑", "짝퉁"],
                "image_specs": {
                    "width": 780,
                    "height": 780,
                    "format": ["jpg", "png"],
                    "max_size_mb": 10
                }
            },
            "naver": {
                "naming_rules": {
                    "max_length": 50,
                    "required_elements": ["제품명"],
                    "forbidden_chars": ["※", "◎"]
                },
                "prohibited_keywords": ["가짜", "모조", "임의"],
                "image_specs": {
                    "width": 640,
                    "height": 640,
                    "format": ["jpg", "png", "gif"],
                    "max_size_mb": 20
                }
            },
            "11st": {
                "naming_rules": {
                    "max_length": 35,
                    "required_elements": ["제품명"],
                    "forbidden_chars": ["♣", "♠"]
                },
                "prohibited_keywords": ["복제품", "불법"],
                "image_specs": {
                    "width": 1000,
                    "height": 1000,
                    "format": ["jpg", "png"],
                    "max_size_mb": 5,
                    "dpi": 96
                }
            }
        }
        return guidelines.get(marketplace, guidelines["coupang"])
    
    def _validate_name_guidelines(self, name: str, guidelines: Dict) -> bool:
        """상품명 가이드라인 검증"""
        naming_rules = guidelines.get("naming_rules", {})
        prohibited_keywords = guidelines.get("prohibited_keywords", [])
        
        # 길이 검증
        max_length = naming_rules.get("max_length", 50)
        if len(name) > max_length:
            return False
        
        # 금지 키워드 검증
        for keyword in prohibited_keywords:
            if keyword in name:
                return False
        
        # 금지 문자 검증
        forbidden_chars = naming_rules.get("forbidden_chars", [])
        for char in forbidden_chars:
            if char in name:
                return False
        
        return True
    
    def _fix_name_guidelines(self, name: str, guidelines: Dict) -> Optional[str]:
        """가이드라인에 맞게 상품명 수정"""
        naming_rules = guidelines.get("naming_rules", {})
        prohibited_keywords = guidelines.get("prohibited_keywords", [])
        
        modified_name = name
        
        # 길이 조정
        max_length = naming_rules.get("max_length", 50)
        if len(modified_name) > max_length:
            modified_name = modified_name[:max_length-3] + "..."
        
        # 금지 키워드 제거
        for keyword in prohibited_keywords:
            modified_name = modified_name.replace(keyword, "")
        
        # 금지 문자 제거
        forbidden_chars = naming_rules.get("forbidden_chars", [])
        for char in forbidden_chars:
            modified_name = modified_name.replace(char, "")
        
        # 공백 정리
        modified_name = re.sub(r'\s+', ' ', modified_name).strip()
        
        return modified_name if modified_name else None
    
    def _extract_names_from_text(self, text: str) -> List[str]:
        """텍스트에서 상품명 추출"""
        # 다양한 패턴으로 상품명 추출 시도
        patterns = [
            r'"([^"]+)"',  # 따옴표로 둘러싸인 텍스트
            r'[0-9]+\.\s*(.+)',  # 번호가 매겨진 리스트
            r'-\s*(.+)',  # 대시로 시작하는 리스트
        ]
        
        names = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            names.extend(matches)
        
        # 중복 제거 및 정리
        unique_names = []
        for name in names:
            cleaned_name = name.strip()
            if cleaned_name and len(cleaned_name) > 5 and cleaned_name not in unique_names:
                unique_names.append(cleaned_name)
        
        return unique_names[:5]
    
    def _generate_fallback_names(self, product: Product, marketplace: str) -> List[str]:
        """기본 상품명 생성 (AI 실패 시 대체)"""
        base_name = product.name
        brand = product.brand or ""
        
        templates = {
            "coupang": [
                f"프리미엄 {brand} {base_name}",
                f"고품질 {base_name} 추천상품",
                f"인기 {brand} {base_name} 특가",
                f"완벽한 {base_name} 최고품질",
                f"믿을 수 있는 {brand} {base_name}"
            ],
            "naver": [
                f"정품 {brand} {base_name} 국내배송",
                f"인증된 {base_name} 품질보장",
                f"안전한 {brand} {base_name} 정식수입",
                f"검증된 {base_name} 브랜드정품",
                f"신뢰할 수 있는 {brand} {base_name}"
            ],
            "11st": [
                f"득템 {brand} {base_name} 혜택",
                f"인기폭발 {base_name} 강추",
                f"초이득 {brand} {base_name} 적립",
                f"빠른배송 {base_name} 무료혜택",
                f"강추템 {brand} {base_name} 인기"
            ]
        }
        
        return templates.get(marketplace, templates["coupang"])
    
    def _replace_with_creative_expression(self, name: str, pattern: str) -> str:
        """창의적 표현으로 패턴 대체"""
        replacements = {
            r'\d+원': '가성비 최고',
            r'최저가': '합리적 가격',
            r'특가': '한정혜택',
            r'할인': '특별가',
            r'세일': '기획전',
            r'무료배송': '배송비없음',
            r'당일배송': '빠른배송',
            r'정품': '정식제품',
            r'공식': '브랜드',
        }
        
        for old_pattern, replacement in replacements.items():
            if re.search(old_pattern, pattern):
                name = re.sub(pattern, replacement, name)
                break
        
        return name
    
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