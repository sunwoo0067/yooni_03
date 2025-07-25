"""
Category mapping utilities for different platforms
"""
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class PlatformType(str, Enum):
    COUPANG = "coupang"
    NAVER = "naver"
    GMARKET_11ST = "gmarket_11st"
    SMARTSTORE = "smartstore"


# Internal category structure
INTERNAL_CATEGORIES = {
    "electronics": {
        "name": "전자제품",
        "subcategories": {
            "smartphones": "스마트폰",
            "tablets": "태블릿",
            "laptops": "노트북",
            "computers": "데스크톱",
            "audio": "오디오",
            "cameras": "카메라",
            "accessories": "전자제품 액세서리"
        }
    },
    "fashion": {
        "name": "패션",
        "subcategories": {
            "mens_clothing": "남성의류",
            "womens_clothing": "여성의류",
            "shoes": "신발",
            "bags": "가방",
            "accessories": "패션 액세서리",
            "watches": "시계",
            "jewelry": "주얼리"
        }
    },
    "home_living": {
        "name": "홈리빙",
        "subcategories": {
            "furniture": "가구",
            "bedding": "침구",
            "kitchen": "주방용품",
            "bathroom": "욕실용품",
            "interior": "인테리어",
            "appliances": "생활가전",
            "storage": "수납정리"
        }
    },
    "beauty": {
        "name": "뷰티",
        "subcategories": {
            "skincare": "스킨케어",
            "makeup": "메이크업",
            "hair": "헤어케어",
            "body": "바디케어",
            "fragrance": "향수",
            "tools": "뷰티툴",
            "mens": "남성화장품"
        }
    },
    "health": {
        "name": "건강",
        "subcategories": {
            "supplements": "건강식품",
            "medical": "의료용품",
            "fitness": "운동용품",
            "diet": "다이어트",
            "hygiene": "위생용품"
        }
    },
    "food": {
        "name": "식품",
        "subcategories": {
            "snacks": "과자·간식",
            "beverages": "음료",
            "fresh": "신선식품",
            "frozen": "냉동식품",
            "instant": "즉석식품",
            "condiments": "조미료",
            "health_food": "건강식품"
        }
    },
    "sports": {
        "name": "스포츠",
        "subcategories": {
            "outdoor": "아웃도어",
            "fitness": "피트니스",
            "team_sports": "구기종목",
            "water_sports": "수상스포츠",
            "winter_sports": "겨울스포츠",
            "equipment": "스포츠용품"
        }
    },
    "toys": {
        "name": "완구",
        "subcategories": {
            "educational": "교육완구",
            "dolls": "인형",
            "blocks": "블록",
            "outdoor_toys": "야외완구",
            "electronic_toys": "전자완구",
            "crafts": "만들기"
        }
    },
    "books": {
        "name": "도서",
        "subcategories": {
            "fiction": "소설",
            "non_fiction": "비소설",
            "education": "교육도서",
            "children": "아동도서",
            "comics": "만화",
            "magazines": "잡지"
        }
    },
    "automotive": {
        "name": "자동차용품",
        "subcategories": {
            "accessories": "자동차 액세서리",
            "maintenance": "정비용품",
            "electronics": "자동차 전자제품",
            "tires": "타이어",
            "oils": "오일류"
        }
    }
}


# Platform-specific category mappings
COUPANG_CATEGORY_MAPPING = {
    "electronics > smartphones": ("196176", "휴대폰"),
    "electronics > tablets": ("194176", "태블릿PC"),
    "electronics > laptops": ("186764", "노트북"),
    "electronics > computers": ("186276", "데스크탑"),
    "electronics > audio": ("197756", "이어폰/헤드폰"),
    "electronics > cameras": ("194364", "디지털카메라"),
    "fashion > mens_clothing": ("115", "남성의류"),
    "fashion > womens_clothing": ("113", "여성의류"),
    "fashion > shoes": ("300", "신발"),
    "fashion > bags": ("1001", "가방/잡화"),
    "home_living > furniture": ("17779", "가구"),
    "home_living > bedding": ("17963", "침구"),
    "home_living > kitchen": ("31454", "주방용품"),
    "beauty > skincare": ("76", "스킨케어"),
    "beauty > makeup": ("77", "메이크업"),
    "health > supplements": ("409382", "건강식품"),
    "food > snacks": ("194020", "과자/간식"),
    "food > beverages": ("194026", "음료"),
    "sports > outdoor": ("35937", "아웃도어"),
    "toys > educational": ("30155", "교육완구"),
    "books > fiction": ("2911", "소설"),
    "automotive > accessories": ("36711", "자동차용품")
}


NAVER_CATEGORY_MAPPING = {
    "electronics > smartphones": ("50000003", "휴대폰"),
    "electronics > tablets": ("50000004", "태블릿PC"),
    "electronics > laptops": ("50000001", "노트북/PC"),
    "electronics > audio": ("50000006", "음향기기"),
    "electronics > cameras": ("50000007", "카메라/캠코더"),
    "fashion > mens_clothing": ("50000008", "남성패션"),
    "fashion > womens_clothing": ("50000009", "여성패션"),
    "fashion > shoes": ("50000010", "신발"),
    "fashion > bags": ("50000011", "가방/지갑/잡화"),
    "home_living > furniture": ("50000012", "가구/인테리어"),
    "home_living > kitchen": ("50000013", "생활/건강"),
    "beauty > skincare": ("50000014", "화장품/미용"),
    "health > supplements": ("50000015", "식품"),
    "sports > outdoor": ("50000016", "스포츠/레저"),
    "toys > educational": ("50000017", "출산/육아"),
    "books > fiction": ("50000018", "도서/음반/DVD"),
    "automotive > accessories": ("50000019", "자동차용품")
}


GMARKET_11ST_CATEGORY_MAPPING = {
    "electronics > smartphones": ("400001001", "스마트폰"),
    "electronics > tablets": ("400001002", "태블릿"),
    "electronics > laptops": ("400002001", "노트북"),
    "electronics > computers": ("400002002", "데스크톱"),
    "electronics > audio": ("400003001", "오디오"),
    "electronics > cameras": ("400004001", "디지털카메라"),
    "fashion > mens_clothing": ("300001001", "남성의류"),
    "fashion > womens_clothing": ("300002001", "여성의류"),
    "fashion > shoes": ("300003001", "신발"),
    "fashion > bags": ("300004001", "가방"),
    "home_living > furniture": ("200001001", "가구"),
    "home_living > kitchen": ("200002001", "주방용품"),
    "beauty > skincare": ("100001001", "스킨케어"),
    "beauty > makeup": ("100001002", "메이크업"),
    "health > supplements": ("500001001", "건강식품"),
    "food > snacks": ("600001001", "과자"),
    "sports > outdoor": ("700001001", "아웃도어"),
    "toys > educational": ("800001001", "완구"),
    "books > fiction": ("900001001", "도서"),
    "automotive > accessories": ("950001001", "자동차용품")
}


SMARTSTORE_CATEGORY_MAPPING = {
    "electronics > smartphones": ("50001851", "휴대폰"),
    "electronics > tablets": ("50001852", "태블릿PC"),
    "electronics > laptops": ("50001853", "노트북"),
    "electronics > computers": ("50001854", "데스크톱"),
    "electronics > audio": ("50001855", "음향기기"),
    "electronics > cameras": ("50001856", "카메라"),
    "fashion > mens_clothing": ("50001001", "남성의류"),
    "fashion > womens_clothing": ("50001002", "여성의류"),
    "fashion > shoes": ("50001003", "신발"),
    "fashion > bags": ("50001004", "가방/잡화"),
    "home_living > furniture": ("50002001", "가구/인테리어"),
    "home_living > kitchen": ("50002002", "주방용품"),
    "beauty > skincare": ("50003001", "스킨케어"),
    "beauty > makeup": ("50003002", "메이크업"),
    "health > supplements": ("50004001", "건강기능식품"),
    "food > snacks": ("50005001", "과자/간식"),
    "sports > outdoor": ("50006001", "스포츠/레저"),
    "toys > educational": ("50007001", "완구/취미"),
    "books > fiction": ("50008001", "도서"),
    "automotive > accessories": ("50009001", "자동차용품")
}


def get_platform_mapping(platform: PlatformType) -> Dict[str, Tuple[str, str]]:
    """Get category mapping for specific platform"""
    mappings = {
        PlatformType.COUPANG: COUPANG_CATEGORY_MAPPING,
        PlatformType.NAVER: NAVER_CATEGORY_MAPPING,
        PlatformType.GMARKET_11ST: GMARKET_11ST_CATEGORY_MAPPING,
        PlatformType.SMARTSTORE: SMARTSTORE_CATEGORY_MAPPING
    }
    return mappings.get(platform, {})


def map_internal_to_platform_category(
    internal_category_path: str,
    platform: PlatformType
) -> Optional[Tuple[str, str]]:
    """Map internal category to platform-specific category"""
    platform_mapping = get_platform_mapping(platform)
    
    # Try exact match first
    if internal_category_path in platform_mapping:
        return platform_mapping[internal_category_path]
    
    # Try partial matches (find closest match)
    path_parts = internal_category_path.lower().split(' > ')
    
    for mapped_path, (category_id, category_name) in platform_mapping.items():
        mapped_parts = mapped_path.lower().split(' > ')
        
        # Check if there's overlap in category parts
        if any(part in mapped_parts for part in path_parts):
            return (category_id, category_name)
    
    return None


def suggest_categories_for_product(
    product_name: str,
    product_description: Optional[str] = None,
    brand: Optional[str] = None
) -> List[str]:
    """Suggest internal categories based on product information"""
    suggestions = []
    
    # Convert to lowercase for matching
    text_to_analyze = f"{product_name} {product_description or ''} {brand or ''}".lower()
    
    # Define keywords for each category
    category_keywords = {
        "electronics > smartphones": ["폰", "phone", "스마트폰", "아이폰", "갤럭시", "핸드폰"],
        "electronics > tablets": ["태블릿", "tablet", "아이패드", "ipad"],
        "electronics > laptops": ["노트북", "laptop", "맥북", "macbook", "울트라북"],
        "electronics > computers": ["데스크톱", "desktop", "pc", "컴퓨터"],
        "electronics > audio": ["이어폰", "헤드폰", "스피커", "earphone", "headphone", "speaker"],
        "electronics > cameras": ["카메라", "camera", "캠코더", "camcorder"],
        "fashion > mens_clothing": ["남성", "남자", "mens", "men", "셔츠", "바지", "정장"],
        "fashion > womens_clothing": ["여성", "여자", "womens", "women", "원피스", "블라우스", "치마"],
        "fashion > shoes": ["신발", "shoes", "운동화", "구두", "부츠", "슬리퍼"],
        "fashion > bags": ["가방", "bag", "백팩", "지갑", "wallet", "핸드백"],
        "home_living > furniture": ["가구", "furniture", "의자", "테이블", "침대", "소파"],
        "home_living > kitchen": ["주방", "kitchen", "그릇", "냄비", "프라이팬"],
        "beauty > skincare": ["스킨케어", "skincare", "로션", "크림", "세럼", "토너"],
        "beauty > makeup": ["메이크업", "makeup", "립스틱", "파운데이션", "아이섀도"],
        "health > supplements": ["건강식품", "supplement", "비타민", "영양제", "프로틴"],
        "food > snacks": ["과자", "snack", "간식", "쿠키", "초콜릿"],
        "food > beverages": ["음료", "beverage", "커피", "차", "주스"],
        "sports > outdoor": ["아웃도어", "outdoor", "등산", "캠핑", "텐트"],
        "toys > educational": ["완구", "toy", "교육", "퍼즐", "블록"]
    }
    
    # Score each category based on keyword matches
    category_scores = {}
    
    for category, keywords in category_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in text_to_analyze:
                score += 1
        
        if score > 0:
            category_scores[category] = score
    
    # Sort by score and return top suggestions
    sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    suggestions = [category for category, score in sorted_categories[:5]]
    
    return suggestions


def get_category_hierarchy(category_path: str) -> List[str]:
    """Get category hierarchy as a list"""
    return category_path.split(' > ')


def get_parent_category(category_path: str) -> Optional[str]:
    """Get parent category path"""
    parts = category_path.split(' > ')
    if len(parts) <= 1:
        return None
    
    return ' > '.join(parts[:-1])


def get_category_level(category_path: str) -> int:
    """Get category level (depth)"""
    return len(category_path.split(' > '))


def get_all_internal_categories() -> Dict[str, str]:
    """Get all internal categories as flat dict"""
    categories = {}
    
    for main_key, main_data in INTERNAL_CATEGORIES.items():
        main_path = main_key
        categories[main_path] = main_data["name"]
        
        for sub_key, sub_name in main_data["subcategories"].items():
            sub_path = f"{main_key} > {sub_key}"
            categories[sub_path] = sub_name
    
    return categories


def validate_category_path(category_path: str) -> bool:
    """Validate if category path exists in internal categories"""
    all_categories = get_all_internal_categories()
    return category_path in all_categories


def get_category_display_name(category_path: str) -> str:
    """Get display name for category path"""
    all_categories = get_all_internal_categories()
    return all_categories.get(category_path, category_path)


def find_similar_categories(category_name: str, limit: int = 5) -> List[str]:
    """Find similar categories by name"""
    all_categories = get_all_internal_categories()
    category_name_lower = category_name.lower()
    
    # Find categories that contain the search term
    matches = []
    for path, name in all_categories.items():
        if category_name_lower in name.lower() or category_name_lower in path.lower():
            matches.append(path)
    
    return matches[:limit]


def get_category_tree_structure() -> Dict[str, Any]:
    """Get category tree structure for UI"""
    tree = {}
    
    for main_key, main_data in INTERNAL_CATEGORIES.items():
        tree[main_key] = {
            "name": main_data["name"],
            "path": main_key,
            "level": 1,
            "children": {}
        }
        
        for sub_key, sub_name in main_data["subcategories"].items():
            tree[main_key]["children"][sub_key] = {
                "name": sub_name,
                "path": f"{main_key} > {sub_key}",
                "level": 2,
                "children": {}
            }
    
    return tree


def get_platform_specific_requirements(platform: PlatformType) -> Dict[str, Any]:
    """Get platform-specific category requirements"""
    requirements = {
        PlatformType.COUPANG: {
            "max_category_depth": 4,
            "required_fields": ["brand", "model"],
            "prohibited_keywords": ["중고", "리퍼", "B급"],
            "description_min_length": 100,
            "image_requirements": {
                "min_images": 3,
                "main_image_size": "1000x1000",
                "formats": ["JPG", "PNG"]
            }
        },
        PlatformType.NAVER: {
            "max_category_depth": 3,
            "required_fields": ["brand", "origin_country"],
            "prohibited_keywords": ["병행수입", "미개봉"],
            "description_min_length": 50,
            "image_requirements": {
                "min_images": 1,
                "main_image_size": "800x800",
                "formats": ["JPG", "PNG", "GIF"]
            }
        },
        PlatformType.GMARKET_11ST: {
            "max_category_depth": 5,
            "required_fields": ["brand"],
            "prohibited_keywords": ["짝퉁", "복제품"],
            "description_min_length": 200,
            "image_requirements": {
                "min_images": 5,
                "main_image_size": "1200x1200",
                "formats": ["JPG", "PNG"]
            }
        },
        PlatformType.SMARTSTORE: {
            "max_category_depth": 3,
            "required_fields": ["brand", "manufacturer"],
            "prohibited_keywords": ["중고", "전시품"],
            "description_min_length": 100,
            "image_requirements": {
                "min_images": 2,
                "main_image_size": "700x700",
                "formats": ["JPG", "PNG"]
            }
        }
    }
    
    return requirements.get(platform, {})


def optimize_category_for_platform(
    internal_category: str,
    platform: PlatformType,
    product_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Optimize category selection for specific platform"""
    platform_category = map_internal_to_platform_category(internal_category, platform)
    requirements = get_platform_specific_requirements(platform)
    
    optimization_result = {
        "platform_category": platform_category,
        "requirements": requirements,
        "recommendations": [],
        "warnings": []
    }
    
    # Check requirements
    if requirements:
        # Check required fields
        for field in requirements.get("required_fields", []):
            if not product_data.get(field):
                optimization_result["warnings"].append(f"Required field '{field}' is missing")
        
        # Check prohibited keywords
        product_text = f"{product_data.get('name', '')} {product_data.get('description', '')}".lower()
        for keyword in requirements.get("prohibited_keywords", []):
            if keyword in product_text:
                optimization_result["warnings"].append(f"Prohibited keyword '{keyword}' found in product")
        
        # Check description length
        description = product_data.get("description", "")
        min_length = requirements.get("description_min_length", 0)
        if len(description) < min_length:
            optimization_result["warnings"].append(f"Description too short (min: {min_length} chars)")
        
        # Check image requirements
        image_reqs = requirements.get("image_requirements", {})
        images = product_data.get("image_urls", [])
        min_images = image_reqs.get("min_images", 1)
        if len(images) < min_images:
            optimization_result["warnings"].append(f"Need at least {min_images} images")
    
    # Add recommendations
    if platform == PlatformType.COUPANG:
        optimization_result["recommendations"].extend([
            "Add detailed specifications",
            "Include size chart if applicable",
            "Use high contrast images"
        ])
    elif platform == PlatformType.NAVER:
        optimization_result["recommendations"].extend([
            "Include origin country information",
            "Add certification marks",
            "Use lifestyle images"
        ])
    
    return optimization_result