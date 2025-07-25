"""
마켓별 가이드라인 적용 시스템

목표: 각 마켓플레이스의 가이드라인을 자동으로 적용
방법: 마켓별 규칙 엔진 + 자동 검증
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.product_processing import MarketGuideline
from app.models.product import Product


class MarketGuidelineManager:
    """마켓별 가이드라인 관리자"""
    
    def __init__(self, db: Session):
        self.db = db
        self._initialize_default_guidelines()
    
    def _initialize_default_guidelines(self):
        """기본 가이드라인 초기화"""
        
        default_guidelines = {
            "coupang": {
                "image_specs": {
                    "width": 780,
                    "height": 780,
                    "format": ["jpg", "png"],
                    "max_size_mb": 10,
                    "min_size_mb": 0.1,
                    "dpi": 72,
                    "color_mode": "RGB",
                    "aspect_ratio": "1:1",
                    "background": "white_preferred"
                },
                "naming_rules": {
                    "max_length": 40,
                    "min_length": 10,
                    "required_elements": ["제품명"],
                    "forbidden_chars": ["♥", "★", "◆", "♦", "♠", "♣"],
                    "forbidden_patterns": [r'\d+원', r'무료배송', r'당일배송'],
                    "preferred_patterns": ["프리미엄", "고품질", "추천"],
                    "case_sensitivity": False
                },
                "description_rules": {
                    "max_length": 2000,
                    "min_length": 100,
                    "required_sections": ["제품소개", "주요특징"],
                    "forbidden_content": ["타 쇼핑몰 언급", "연락처", "외부링크"],
                    "html_allowed": True,
                    "image_in_description": True
                },
                "prohibited_keywords": [
                    "최저가", "덤핑", "짝퉁", "가품", "B급", "하자상품",
                    "중고", "리퍼", "전시상품"
                ],
                "required_fields": {
                    "brand": True,
                    "model_number": False,
                    "manufacturer": True,
                    "origin_country": True,
                    "warranty": False
                },
                "special_rules": {
                    "color_correction_allowed": True,
                    "text_overlay_limited": True,
                    "promotion_badge_allowed": False,
                    "comparison_chart_allowed": True
                }
            },
            "naver": {
                "image_specs": {
                    "width": 640,
                    "height": 640,
                    "format": ["jpg", "png", "gif"],
                    "max_size_mb": 20,
                    "min_size_mb": 0.1,
                    "dpi": 72,
                    "color_mode": "RGB",
                    "aspect_ratio": ["1:1", "4:3"],
                    "background": "any"
                },
                "naming_rules": {
                    "max_length": 50,
                    "min_length": 15,
                    "required_elements": ["제품명", "브랜드"],
                    "forbidden_chars": ["※", "◎", "●", "■"],
                    "forbidden_patterns": [r'가짜', r'모조품'],
                    "preferred_patterns": ["정품", "국내배송", "브랜드"],
                    "case_sensitivity": False
                },
                "description_rules": {
                    "max_length": 3000,
                    "min_length": 200,
                    "required_sections": ["상품정보", "배송정보", "교환반품"],
                    "forbidden_content": ["과장광고", "의료효능"],
                    "html_allowed": True,
                    "image_in_description": True
                },
                "prohibited_keywords": [
                    "가짜", "모조", "임의", "복제품", "불법"
                ],
                "required_fields": {
                    "brand": True,
                    "model_number": True,
                    "manufacturer": True,
                    "origin_country": True,
                    "warranty": True
                },
                "special_rules": {
                    "color_correction_allowed": True,
                    "text_overlay_allowed": True,
                    "promotion_badge_allowed": True,
                    "comparison_chart_allowed": True,
                    "four_split_image_allowed": True
                }
            },
            "11st": {
                "image_specs": {
                    "width": 1000,
                    "height": 1000,
                    "format": ["jpg", "png"],
                    "max_size_mb": 5,
                    "min_size_mb": 0.1,
                    "dpi": 96,
                    "color_mode": "RGB",
                    "aspect_ratio": "1:1",
                    "background": "white_preferred"
                },
                "naming_rules": {
                    "max_length": 35,
                    "min_length": 10,
                    "required_elements": ["제품명"],
                    "forbidden_chars": ["♣", "♠", "◐", "◑"],
                    "forbidden_patterns": [r'복제품', r'불법'],
                    "preferred_patterns": ["혜택", "적립", "무료", "빠른"],
                    "case_sensitivity": False
                },
                "description_rules": {
                    "max_length": 1500,
                    "min_length": 100,
                    "required_sections": ["상품설명"],
                    "forbidden_content": ["허위정보", "과대광고"],
                    "html_allowed": False,
                    "image_in_description": False
                },
                "prohibited_keywords": [
                    "복제품", "불법", "해적판"
                ],
                "required_fields": {
                    "brand": False,
                    "model_number": False,
                    "manufacturer": False,
                    "origin_country": True,
                    "warranty": False
                },
                "special_rules": {
                    "color_correction_allowed": False,
                    "text_overlay_limited": True,
                    "promotion_badge_allowed": True,
                    "comparison_chart_allowed": False,
                    "zoom_view_required": True
                }
            }
        }
        
        # 데이터베이스에 기본 가이드라인 저장 (없는 경우만)
        for marketplace, guidelines in default_guidelines.items():
            existing = self.db.query(MarketGuideline).filter(
                MarketGuideline.marketplace == marketplace
            ).first()
            
            if not existing:
                guideline = MarketGuideline(
                    marketplace=marketplace,
                    image_specs=guidelines["image_specs"],
                    naming_rules=guidelines["naming_rules"],
                    description_rules=guidelines["description_rules"],
                    prohibited_keywords=guidelines["prohibited_keywords"],
                    required_fields=guidelines["required_fields"],
                    guidelines_version="1.0",
                    is_active=True,
                    created_at=datetime.now()
                )
                self.db.add(guideline)
        
        self.db.commit()
    
    def get_guidelines(self, marketplace: str) -> Optional[Dict]:
        """마켓 가이드라인 조회"""
        
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
                "required_fields": guideline.required_fields or {},
                "version": guideline.guidelines_version
            }
        
        return None
    
    def validate_product_name(self, name: str, marketplace: str) -> Dict[str, Any]:
        """상품명 가이드라인 검증"""
        
        guidelines = self.get_guidelines(marketplace)
        if not guidelines:
            return {"valid": False, "error": "가이드라인을 찾을 수 없습니다"}
        
        naming_rules = guidelines["naming_rules"]
        violations = []
        
        # 길이 검증
        if len(name) > naming_rules.get("max_length", 50):
            violations.append(f"상품명이 최대 길이({naming_rules['max_length']}자)를 초과했습니다")
        
        if len(name) < naming_rules.get("min_length", 5):
            violations.append(f"상품명이 최소 길이({naming_rules['min_length']}자)보다 짧습니다")
        
        # 금지 문자 검증
        forbidden_chars = naming_rules.get("forbidden_chars", [])
        for char in forbidden_chars:
            if char in name:
                violations.append(f"금지된 문자가 포함되어 있습니다: {char}")
        
        # 금지 패턴 검증
        forbidden_patterns = naming_rules.get("forbidden_patterns", [])
        for pattern in forbidden_patterns:
            if re.search(pattern, name):
                violations.append(f"금지된 패턴이 포함되어 있습니다: {pattern}")
        
        # 금지 키워드 검증
        prohibited_keywords = guidelines.get("prohibited_keywords", [])
        for keyword in prohibited_keywords:
            if keyword in name:
                violations.append(f"금지된 키워드가 포함되어 있습니다: {keyword}")
        
        # 필수 요소 검증
        required_elements = naming_rules.get("required_elements", [])
        # 실제로는 더 정교한 검증이 필요하지만, 여기서는 간단히 구현
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "suggestions": self._generate_name_suggestions(name, naming_rules, marketplace)
        }
    
    def validate_product_description(self, description: str, marketplace: str) -> Dict[str, Any]:
        """상품 설명 가이드라인 검증"""
        
        guidelines = self.get_guidelines(marketplace)
        if not guidelines:
            return {"valid": False, "error": "가이드라인을 찾을 수 없습니다"}
        
        description_rules = guidelines["description_rules"]
        violations = []
        
        # 길이 검증
        if len(description) > description_rules.get("max_length", 2000):
            violations.append(f"설명이 최대 길이({description_rules['max_length']}자)를 초과했습니다")
        
        if len(description) < description_rules.get("min_length", 100):
            violations.append(f"설명이 최소 길이({description_rules['min_length']}자)보다 짧습니다")
        
        # 금지 콘텐츠 검증
        forbidden_content = description_rules.get("forbidden_content", [])
        for content in forbidden_content:
            if content in description:
                violations.append(f"금지된 내용이 포함되어 있습니다: {content}")
        
        # HTML 사용 검증
        html_allowed = description_rules.get("html_allowed", False)
        if not html_allowed and self._contains_html(description):
            violations.append("HTML 태그 사용이 허용되지 않습니다")
        
        # 필수 섹션 검증
        required_sections = description_rules.get("required_sections", [])
        missing_sections = []
        for section in required_sections:
            if section not in description:
                missing_sections.append(section)
        
        if missing_sections:
            violations.append(f"필수 섹션이 누락되었습니다: {', '.join(missing_sections)}")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "missing_sections": missing_sections,
            "suggestions": self._generate_description_suggestions(description, description_rules)
        }
    
    def validate_image_specs(self, image_info: Dict, marketplace: str) -> Dict[str, Any]:
        """이미지 규격 가이드라인 검증"""
        
        guidelines = self.get_guidelines(marketplace)
        if not guidelines:
            return {"valid": False, "error": "가이드라인을 찾을 수 없습니다"}
        
        image_specs = guidelines["image_specs"]
        violations = []
        
        # 크기 검증
        width = image_info.get("width", 0)
        height = image_info.get("height", 0)
        
        required_width = image_specs.get("width", 800)
        required_height = image_specs.get("height", 800)
        
        if width != required_width or height != required_height:
            violations.append(f"이미지 크기가 규격에 맞지 않습니다. 요구사항: {required_width}x{required_height}, 현재: {width}x{height}")
        
        # 파일 크기 검증
        file_size_mb = image_info.get("file_size_mb", 0)
        max_size = image_specs.get("max_size_mb", 10)
        min_size = image_specs.get("min_size_mb", 0.1)
        
        if file_size_mb > max_size:
            violations.append(f"파일 크기가 제한을 초과했습니다. 최대: {max_size}MB, 현재: {file_size_mb}MB")
        
        if file_size_mb < min_size:
            violations.append(f"파일 크기가 너무 작습니다. 최소: {min_size}MB, 현재: {file_size_mb}MB")
        
        # 파일 형식 검증
        file_format = image_info.get("format", "").lower()
        allowed_formats = image_specs.get("format", ["jpg", "png"])
        
        if file_format not in allowed_formats:
            violations.append(f"지원되지 않는 파일 형식입니다. 허용: {allowed_formats}, 현재: {file_format}")
        
        # 비율 검증
        aspect_ratio = image_specs.get("aspect_ratio")
        if aspect_ratio and width > 0 and height > 0:
            current_ratio = width / height
            
            if isinstance(aspect_ratio, str):
                if aspect_ratio == "1:1" and abs(current_ratio - 1.0) > 0.01:
                    violations.append("이미지 비율이 1:1이 아닙니다")
                elif aspect_ratio == "4:3" and abs(current_ratio - 4/3) > 0.01:
                    violations.append("이미지 비율이 4:3이 아닙니다")
            elif isinstance(aspect_ratio, list):
                valid_ratio = False
                for ratio_str in aspect_ratio:
                    if ratio_str == "1:1" and abs(current_ratio - 1.0) <= 0.01:
                        valid_ratio = True
                        break
                    elif ratio_str == "4:3" and abs(current_ratio - 4/3) <= 0.01:
                        valid_ratio = True
                        break
                
                if not valid_ratio:
                    violations.append(f"이미지 비율이 허용된 비율과 맞지 않습니다. 허용: {aspect_ratio}")
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "optimization_suggestions": self._generate_image_optimization_suggestions(
                image_info, image_specs, marketplace
            )
        }
    
    def apply_automatic_fixes(self, product_data: Dict, marketplace: str) -> Dict[str, Any]:
        """자동 수정 적용"""
        
        guidelines = self.get_guidelines(marketplace)
        if not guidelines:
            return {"success": False, "error": "가이드라인을 찾을 수 없습니다"}
        
        fixes_applied = []
        fixed_data = product_data.copy()
        
        # 상품명 자동 수정
        if "name" in product_data:
            name_result = self._auto_fix_name(
                product_data["name"], guidelines["naming_rules"], marketplace
            )
            if name_result["modified"]:
                fixed_data["name"] = name_result["fixed_name"]
                fixes_applied.append(f"상품명 수정: {name_result['changes']}")
        
        # 설명 자동 수정
        if "description" in product_data:
            desc_result = self._auto_fix_description(
                product_data["description"], guidelines["description_rules"]
            )
            if desc_result["modified"]:
                fixed_data["description"] = desc_result["fixed_description"]
                fixes_applied.append(f"설명 수정: {desc_result['changes']}")
        
        return {
            "success": True,
            "fixed_data": fixed_data,
            "fixes_applied": fixes_applied,
            "manual_review_needed": self._check_manual_review_needed(fixed_data, guidelines)
        }
    
    def _generate_name_suggestions(self, name: str, naming_rules: Dict, marketplace: str) -> List[str]:
        """상품명 개선 제안"""
        
        suggestions = []
        
        # 길이 조정
        max_length = naming_rules.get("max_length", 50)
        if len(name) > max_length:
            truncated = name[:max_length-3] + "..."
            suggestions.append(f"길이 단축: {truncated}")
        
        # 금지 문자 제거
        forbidden_chars = naming_rules.get("forbidden_chars", [])
        cleaned_name = name
        for char in forbidden_chars:
            cleaned_name = cleaned_name.replace(char, "")
        
        if cleaned_name != name:
            suggestions.append(f"금지 문자 제거: {cleaned_name}")
        
        # 마켓별 선호 표현 추가
        preferred_patterns = naming_rules.get("preferred_patterns", [])
        if preferred_patterns and marketplace == "coupang":
            suggestions.append(f"프리미엄 {name}")
            suggestions.append(f"고품질 {name} 추천")
        elif preferred_patterns and marketplace == "naver":
            suggestions.append(f"정품 {name} 국내배송")
            suggestions.append(f"브랜드 {name} 인증")
        elif preferred_patterns and marketplace == "11st":
            suggestions.append(f"혜택 {name} 적립")
            suggestions.append(f"빠른배송 {name}")
        
        return suggestions[:3]  # 최대 3개 제안
    
    def _generate_description_suggestions(self, description: str, description_rules: Dict) -> List[str]:
        """설명 개선 제안"""
        
        suggestions = []
        
        # 길이 조정
        max_length = description_rules.get("max_length", 2000)
        min_length = description_rules.get("min_length", 100)
        
        if len(description) > max_length:
            suggestions.append(f"설명을 {max_length}자 이내로 단축하세요")
        elif len(description) < min_length:
            suggestions.append(f"설명을 {min_length}자 이상으로 확장하세요")
        
        # 필수 섹션 추가
        required_sections = description_rules.get("required_sections", [])
        for section in required_sections:
            if section not in description:
                suggestions.append(f"'{section}' 섹션을 추가하세요")
        
        return suggestions
    
    def _generate_image_optimization_suggestions(
        self, 
        image_info: Dict, 
        image_specs: Dict, 
        marketplace: str
    ) -> List[str]:
        """이미지 최적화 제안"""
        
        suggestions = []
        
        # 크기 조정
        current_width = image_info.get("width", 0)
        current_height = image_info.get("height", 0)
        required_width = image_specs.get("width", 800)
        required_height = image_specs.get("height", 800)
        
        if current_width != required_width or current_height != required_height:
            suggestions.append(f"이미지 크기를 {required_width}x{required_height}로 조정하세요")
        
        # 파일 크기 최적화
        file_size_mb = image_info.get("file_size_mb", 0)
        max_size = image_specs.get("max_size_mb", 10)
        
        if file_size_mb > max_size:
            suggestions.append(f"파일 크기를 {max_size}MB 이하로 압축하세요")
        
        # 형식 변환
        current_format = image_info.get("format", "").lower()
        allowed_formats = image_specs.get("format", ["jpg"])
        
        if current_format not in allowed_formats:
            suggestions.append(f"파일 형식을 {allowed_formats[0]}로 변환하세요")
        
        # 마켓별 특수 제안
        if marketplace == "coupang":
            suggestions.append("색상 보정을 통해 이미지 품질을 향상시키세요")
        elif marketplace == "naver":
            suggestions.append("4분할 이미지 구성을 고려해보세요")
        elif marketplace == "11st":
            suggestions.append("확대보기를 위한 고해상도 이미지를 준비하세요")
        
        return suggestions
    
    def _auto_fix_name(self, name: str, naming_rules: Dict, marketplace: str) -> Dict[str, Any]:
        """상품명 자동 수정"""
        
        fixed_name = name
        changes = []
        
        # 길이 조정
        max_length = naming_rules.get("max_length", 50)
        if len(fixed_name) > max_length:
            fixed_name = fixed_name[:max_length-3] + "..."
            changes.append("길이 단축")
        
        # 금지 문자 제거
        forbidden_chars = naming_rules.get("forbidden_chars", [])
        for char in forbidden_chars:
            if char in fixed_name:
                fixed_name = fixed_name.replace(char, "")
                changes.append(f"'{char}' 문자 제거")
        
        # 금지 패턴 제거
        forbidden_patterns = naming_rules.get("forbidden_patterns", [])
        for pattern in forbidden_patterns:
            if re.search(pattern, fixed_name):
                fixed_name = re.sub(pattern, "", fixed_name)
                changes.append(f"금지 패턴 제거")
        
        # 공백 정리
        fixed_name = re.sub(r'\s+', ' ', fixed_name).strip()
        
        return {
            "modified": fixed_name != name,
            "fixed_name": fixed_name,
            "changes": ", ".join(changes)
        }
    
    def _auto_fix_description(self, description: str, description_rules: Dict) -> Dict[str, Any]:
        """설명 자동 수정"""
        
        fixed_description = description
        changes = []
        
        # 길이 조정 (간단히 구현)
        max_length = description_rules.get("max_length", 2000)
        if len(fixed_description) > max_length:
            fixed_description = fixed_description[:max_length-3] + "..."
            changes.append("길이 단축")
        
        # 금지 콘텐츠 제거
        forbidden_content = description_rules.get("forbidden_content", [])
        for content in forbidden_content:
            if content in fixed_description:
                fixed_description = fixed_description.replace(content, "[수정됨]")
                changes.append(f"'{content}' 내용 수정")
        
        return {
            "modified": fixed_description != description,
            "fixed_description": fixed_description,
            "changes": ", ".join(changes)
        }
    
    def _contains_html(self, text: str) -> bool:
        """HTML 태그 포함 여부 검사"""
        html_pattern = r'<[^>]+>'
        return bool(re.search(html_pattern, text))
    
    def _check_manual_review_needed(self, product_data: Dict, guidelines: Dict) -> List[str]:
        """수동 검토 필요 사항 확인"""
        
        review_items = []
        
        # 복잡한 규칙들은 수동 검토 필요
        if "description" in product_data:
            required_sections = guidelines.get("description_rules", {}).get("required_sections", [])
            if required_sections:
                review_items.append("필수 섹션 포함 여부 확인")
        
        # 브랜드, 모델번호 등 정확성 검증
        required_fields = guidelines.get("required_fields", {})
        for field, required in required_fields.items():
            if required and field not in product_data:
                review_items.append(f"{field} 정보 확인 필요")
        
        return review_items
    
    def update_guidelines(self, marketplace: str, new_guidelines: Dict) -> bool:
        """가이드라인 업데이트"""
        
        try:
            guideline = self.db.query(MarketGuideline).filter(
                MarketGuideline.marketplace == marketplace
            ).first()
            
            if guideline:
                guideline.image_specs = new_guidelines.get("image_specs", guideline.image_specs)
                guideline.naming_rules = new_guidelines.get("naming_rules", guideline.naming_rules)
                guideline.description_rules = new_guidelines.get("description_rules", guideline.description_rules)
                guideline.prohibited_keywords = new_guidelines.get("prohibited_keywords", guideline.prohibited_keywords)
                guideline.required_fields = new_guidelines.get("required_fields", guideline.required_fields)
                guideline.guidelines_version = new_guidelines.get("version", str(float(guideline.guidelines_version) + 0.1))
                guideline.updated_at = datetime.now()
            else:
                guideline = MarketGuideline(
                    marketplace=marketplace,
                    image_specs=new_guidelines.get("image_specs", {}),
                    naming_rules=new_guidelines.get("naming_rules", {}),
                    description_rules=new_guidelines.get("description_rules", {}),
                    prohibited_keywords=new_guidelines.get("prohibited_keywords", []),
                    required_fields=new_guidelines.get("required_fields", {}),
                    guidelines_version=new_guidelines.get("version", "1.0"),
                    is_active=True,
                    created_at=datetime.now()
                )
                self.db.add(guideline)
            
            self.db.commit()
            return True
            
        except Exception as e:
            print(f"가이드라인 업데이트 오류: {e}")
            self.db.rollback()
            return False