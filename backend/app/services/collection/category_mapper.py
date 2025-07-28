"""
도매처 카테고리 매핑 및 표준화 서비스
각 도매처의 카테고리를 통합 카테고리로 매핑
"""
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

from ...models.collected_product import WholesalerSource


class StandardCategory(Enum):
    """표준 카테고리"""
    # 패션
    FASHION_WOMEN = "패션/여성의류"
    FASHION_MEN = "패션/남성의류"
    FASHION_KIDS = "패션/아동의류"
    FASHION_ACCESSORIES = "패션/액세서리"
    FASHION_BAGS = "패션/가방"
    FASHION_SHOES = "패션/신발"
    
    # 뷰티
    BEAUTY_SKINCARE = "뷰티/스킨케어"
    BEAUTY_MAKEUP = "뷰티/메이크업"
    BEAUTY_PERFUME = "뷰티/향수"
    BEAUTY_HAIR = "뷰티/헤어케어"
    BEAUTY_BODY = "뷰티/바디케어"
    
    # 전자제품
    ELECTRONICS_MOBILE = "전자제품/모바일"
    ELECTRONICS_COMPUTER = "전자제품/컴퓨터"
    ELECTRONICS_AUDIO = "전자제품/오디오"
    ELECTRONICS_HOME = "전자제품/가전"
    ELECTRONICS_GAMING = "전자제품/게임"
    
    # 생활/가정
    LIVING_KITCHEN = "생활/주방"
    LIVING_FURNITURE = "생활/가구"
    LIVING_DECOR = "생활/인테리어"
    LIVING_BEDDING = "생활/침구"
    LIVING_CLEANING = "생활/청소"
    
    # 식품
    FOOD_FRESH = "식품/신선식품"
    FOOD_PROCESSED = "식품/가공식품"
    FOOD_BEVERAGE = "식품/음료"
    FOOD_HEALTH = "식품/건강식품"
    FOOD_SNACK = "식품/과자/간식"
    
    # 스포츠/레저
    SPORTS_FITNESS = "스포츠/피트니스"
    SPORTS_OUTDOOR = "스포츠/아웃도어"
    SPORTS_EQUIPMENT = "스포츠/운동기구"
    LEISURE_CAMPING = "레저/캠핑"
    LEISURE_TRAVEL = "레저/여행"
    
    # 기타
    BOOKS = "도서/문구"
    TOYS = "완구/취미"
    PET = "반려동물"
    CAR = "자동차용품"
    OTHER = "기타"


class CategoryMapper:
    """카테고리 매핑 서비스"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._init_mapping_rules()
        
    def _init_mapping_rules(self):
        """매핑 규칙 초기화"""
        # 오너클랜 카테고리 매핑
        self.ownerclan_mapping = {
            # 패션
            "여성의류": StandardCategory.FASHION_WOMEN,
            "남성의류": StandardCategory.FASHION_MEN,
            "아동의류": StandardCategory.FASHION_KIDS,
            "여성패션": StandardCategory.FASHION_WOMEN,
            "남성패션": StandardCategory.FASHION_MEN,
            "가방/지갑": StandardCategory.FASHION_BAGS,
            "신발": StandardCategory.FASHION_SHOES,
            "액세서리": StandardCategory.FASHION_ACCESSORIES,
            
            # 뷰티
            "화장품": StandardCategory.BEAUTY_MAKEUP,
            "스킨케어": StandardCategory.BEAUTY_SKINCARE,
            "향수/바디": StandardCategory.BEAUTY_PERFUME,
            "헤어/바디": StandardCategory.BEAUTY_HAIR,
            
            # 전자제품
            "디지털/가전": StandardCategory.ELECTRONICS_HOME,
            "스마트폰": StandardCategory.ELECTRONICS_MOBILE,
            "컴퓨터/노트북": StandardCategory.ELECTRONICS_COMPUTER,
            "음향기기": StandardCategory.ELECTRONICS_AUDIO,
            
            # 생활
            "생활용품": StandardCategory.LIVING_KITCHEN,
            "주방용품": StandardCategory.LIVING_KITCHEN,
            "가구/인테리어": StandardCategory.LIVING_FURNITURE,
            "침구류": StandardCategory.LIVING_BEDDING,
            
            # 식품
            "식품": StandardCategory.FOOD_PROCESSED,
            "건강식품": StandardCategory.FOOD_HEALTH,
            "음료": StandardCategory.FOOD_BEVERAGE,
            
            # 스포츠
            "스포츠/레저": StandardCategory.SPORTS_OUTDOOR,
            "운동용품": StandardCategory.SPORTS_EQUIPMENT,
            "캠핑": StandardCategory.LEISURE_CAMPING,
        }
        
        # 도매매 카테고리 매핑
        self.domeme_mapping = {
            # 패션
            "여성패션잡화": StandardCategory.FASHION_WOMEN,
            "남성패션잡화": StandardCategory.FASHION_MEN,
            "유아동패션": StandardCategory.FASHION_KIDS,
            "가방": StandardCategory.FASHION_BAGS,
            "신발": StandardCategory.FASHION_SHOES,
            "시계/액세서리": StandardCategory.FASHION_ACCESSORIES,
            
            # 뷰티
            "뷰티": StandardCategory.BEAUTY_MAKEUP,
            "화장품/향수": StandardCategory.BEAUTY_PERFUME,
            "바디/헤어": StandardCategory.BEAUTY_BODY,
            
            # 생활
            "생활/주방": StandardCategory.LIVING_KITCHEN,
            "가구": StandardCategory.LIVING_FURNITURE,
            "홈인테리어": StandardCategory.LIVING_DECOR,
            "침구": StandardCategory.LIVING_BEDDING,
            
            # 스포츠
            "스포츠": StandardCategory.SPORTS_FITNESS,
            "아웃도어": StandardCategory.SPORTS_OUTDOOR,
            "캠핑용품": StandardCategory.LEISURE_CAMPING,
        }
        
        # 젠트레이드 카테고리 매핑
        self.gentrade_mapping = {
            # 패션
            "의류": StandardCategory.FASHION_WOMEN,
            "패션잡화": StandardCategory.FASHION_ACCESSORIES,
            "가방/신발": StandardCategory.FASHION_BAGS,
            
            # 뷰티
            "화장품": StandardCategory.BEAUTY_MAKEUP,
            "뷰티/헬스": StandardCategory.BEAUTY_SKINCARE,
            
            # 전자
            "전자제품": StandardCategory.ELECTRONICS_HOME,
            "IT/디지털": StandardCategory.ELECTRONICS_COMPUTER,
            
            # 생활
            "생활용품": StandardCategory.LIVING_KITCHEN,
            "인테리어": StandardCategory.LIVING_DECOR,
            
            # 기타
            "문구/사무": StandardCategory.BOOKS,
            "완구": StandardCategory.TOYS,
        }
        
        # 키워드 기반 매핑 (도매처 구분 없이 사용)
        self.keyword_mapping = {
            # 패션 키워드
            ("원피스", "블라우스", "스커트", "여성"): StandardCategory.FASHION_WOMEN,
            ("셔츠", "바지", "자켓", "남성"): StandardCategory.FASHION_MEN,
            ("아동", "키즈", "유아"): StandardCategory.FASHION_KIDS,
            ("가방", "백팩", "크로스백"): StandardCategory.FASHION_BAGS,
            ("운동화", "구두", "슬리퍼"): StandardCategory.FASHION_SHOES,
            ("목걸이", "반지", "귀걸이", "팔찌"): StandardCategory.FASHION_ACCESSORIES,
            
            # 뷰티 키워드
            ("립스틱", "파운데이션", "아이섀도우"): StandardCategory.BEAUTY_MAKEUP,
            ("스킨", "로션", "크림", "에센스"): StandardCategory.BEAUTY_SKINCARE,
            ("향수", "퍼퓸", "오드뜨왈렛"): StandardCategory.BEAUTY_PERFUME,
            ("샴푸", "린스", "헤어팩"): StandardCategory.BEAUTY_HAIR,
            
            # 전자제품 키워드
            ("스마트폰", "휴대폰", "핸드폰"): StandardCategory.ELECTRONICS_MOBILE,
            ("노트북", "데스크탑", "컴퓨터"): StandardCategory.ELECTRONICS_COMPUTER,
            ("이어폰", "헤드폰", "스피커"): StandardCategory.ELECTRONICS_AUDIO,
            ("TV", "냉장고", "세탁기", "에어컨"): StandardCategory.ELECTRONICS_HOME,
            
            # 생활 키워드
            ("프라이팬", "냄비", "주방"): StandardCategory.LIVING_KITCHEN,
            ("소파", "침대", "책상", "의자"): StandardCategory.LIVING_FURNITURE,
            ("커튼", "러그", "조명"): StandardCategory.LIVING_DECOR,
            ("이불", "베개", "매트리스"): StandardCategory.LIVING_BEDDING,
            
            # 식품 키워드
            ("과자", "쿠키", "초콜릿"): StandardCategory.FOOD_SNACK,
            ("커피", "차", "음료"): StandardCategory.FOOD_BEVERAGE,
            ("비타민", "영양제", "건강"): StandardCategory.FOOD_HEALTH,
            
            # 스포츠 키워드
            ("운동", "피트니스", "요가"): StandardCategory.SPORTS_FITNESS,
            ("등산", "낚시", "아웃도어"): StandardCategory.SPORTS_OUTDOOR,
            ("텐트", "캠핑", "글램핑"): StandardCategory.LEISURE_CAMPING,
        }
        
    def map_category(
        self, 
        source: WholesalerSource, 
        original_category: str,
        product_name: Optional[str] = None
    ) -> Tuple[StandardCategory, float]:
        """
        도매처 카테고리를 표준 카테고리로 매핑
        
        Returns:
            (표준 카테고리, 신뢰도 점수 0-1)
        """
        if not original_category:
            return StandardCategory.OTHER, 0.0
            
        # 1. 도매처별 직접 매핑 시도
        mapping_dict = self._get_mapping_dict(source)
        
        # 정확한 매칭
        if original_category in mapping_dict:
            return mapping_dict[original_category], 1.0
            
        # 부분 매칭
        for key, value in mapping_dict.items():
            if key in original_category or original_category in key:
                return value, 0.8
                
        # 2. 키워드 기반 매핑
        if product_name:
            category, confidence = self._map_by_keywords(
                original_category, product_name
            )
            if category != StandardCategory.OTHER:
                return category, confidence
                
        # 3. 카테고리 텍스트만으로 키워드 매핑
        category, confidence = self._map_by_keywords(original_category, "")
        if category != StandardCategory.OTHER:
            return category, confidence * 0.7  # 낮은 신뢰도
            
        # 4. 매핑 실패
        self.logger.warning(
            f"카테고리 매핑 실패: {source.value} - {original_category}"
        )
        return StandardCategory.OTHER, 0.3
        
    def _get_mapping_dict(self, source: WholesalerSource) -> Dict:
        """도매처별 매핑 딕셔너리 반환"""
        if source == WholesalerSource.OWNERCLAN:
            return self.ownerclan_mapping
        elif source == WholesalerSource.DOMEME:
            return self.domeme_mapping
        elif source == WholesalerSource.GENTRADE:
            return self.gentrade_mapping
        else:
            return {}
            
    def _map_by_keywords(
        self, 
        category_text: str, 
        product_name: str
    ) -> Tuple[StandardCategory, float]:
        """키워드 기반 카테고리 매핑"""
        combined_text = f"{category_text} {product_name}".lower()
        
        best_match = StandardCategory.OTHER
        best_score = 0.0
        
        for keywords, category in self.keyword_mapping.items():
            match_count = sum(1 for keyword in keywords if keyword in combined_text)
            if match_count > 0:
                score = match_count / len(keywords)
                if score > best_score:
                    best_score = score
                    best_match = category
                    
        confidence = min(best_score * 1.2, 1.0)  # 약간의 부스트
        return best_match, confidence
        
    def get_category_hierarchy(self, category: StandardCategory) -> List[str]:
        """카테고리 계층 구조 반환"""
        if category == StandardCategory.OTHER:
            return ["기타"]
            
        parts = category.value.split("/")
        return parts
        
    def get_display_name(self, category: StandardCategory) -> str:
        """표시용 카테고리 이름 반환"""
        return category.value.replace("/", " > ")
        
    def suggest_categories(
        self, 
        product_name: str, 
        description: Optional[str] = None
    ) -> List[Tuple[StandardCategory, float]]:
        """
        상품명과 설명을 기반으로 카테고리 추천
        
        Returns:
            [(카테고리, 신뢰도)] 리스트 (신뢰도 내림차순)
        """
        combined_text = f"{product_name} {description or ''}".lower()
        suggestions = []
        
        # 키워드 매칭으로 점수 계산
        for keywords, category in self.keyword_mapping.items():
            match_count = sum(1 for keyword in keywords if keyword in combined_text)
            if match_count > 0:
                score = match_count / len(keywords)
                suggestions.append((category, score))
                
        # 신뢰도 순으로 정렬
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 3개만 반환
        return suggestions[:3] if suggestions else [(StandardCategory.OTHER, 0.1)]
        
    def get_statistics(self) -> Dict[str, int]:
        """카테고리 매핑 통계"""
        stats = {
            "total_mappings": sum(
                len(mapping) for mapping in [
                    self.ownerclan_mapping,
                    self.domeme_mapping,
                    self.gentrade_mapping
                ]
            ),
            "ownerclan_mappings": len(self.ownerclan_mapping),
            "domeme_mappings": len(self.domeme_mapping),
            "gentrade_mappings": len(self.gentrade_mapping),
            "keyword_groups": len(self.keyword_mapping),
            "standard_categories": len(StandardCategory)
        }
        return stats


# 싱글톤 인스턴스
category_mapper = CategoryMapper()