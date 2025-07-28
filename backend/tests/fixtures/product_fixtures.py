"""
Product-related test fixtures and sample data
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Any
import pytest


@pytest.fixture
def sample_product_data() -> Dict[str, Any]:
    """Basic product data for testing"""
    return {
        "name": "테스트 상품",
        "description": "테스트용 상품 설명입니다.",
        "price": Decimal("25000"),
        "cost": Decimal("12500"),
        "sku": "TEST-001",
        "category": "테스트 카테고리",
        "subcategory": "테스트 서브카테고리",
        "brand": "테스트 브랜드",
        "stock_quantity": 100,
        "min_stock_level": 10,
        "weight": Decimal("0.5"),
        "dimensions": {
            "length": 10.0,
            "width": 8.0,
            "height": 5.0,
            "unit": "cm"
        },
        "images": [
            "https://example.com/test-image-1.jpg",
            "https://example.com/test-image-2.jpg"
        ],
        "tags": ["테스트", "상품", "샘플"],
        "specifications": {
            "material": "테스트 소재",
            "color": "테스트 색상",
            "size": "테스트 사이즈"
        },
        "status": "active",
        "margin_rate": Decimal("0.5"),
        "supplier": "test_supplier",
        "supplier_product_id": "SUPP_TEST_001",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


@pytest.fixture
def sample_collected_products() -> List[Dict[str, Any]]:
    """Sample collected products from wholesalers"""
    return [
        {
            "id": "oc_001",
            "name": "18K 골드 목걸이",
            "description": "고급 18K 골드로 제작된 프리미엄 목걸이",
            "price": 125000,
            "cost": 62500,
            "stock": 15,
            "category": "보석",
            "subcategory": "목걸이",
            "brand": "OwnerClan Premium",
            "sku": "OC-GOLD-001",
            "weight": "15g",
            "material": "18K 골드",
            "images": [
                "https://example.com/gold-necklace-1.jpg",
                "https://example.com/gold-necklace-2.jpg"
            ],
            "specifications": {
                "length": "45cm",
                "clasp": "스프링 클래스프",
                "chain_type": "벤치안 체인"
            },
            "supplier": "ownerclan",
            "supplier_product_id": "OC-PREMIUM-001"
        },
        {
            "id": "zt_001",
            "name": "스테인리스 주방칼 세트",
            "description": "프리미엄 스테인리스 스틸로 제작된 전문가용 주방칼 5종 세트",
            "price": 89000,
            "cost": 44500,
            "stock": 50,
            "category": "주방용품",
            "subcategory": "조리도구",
            "brand": "Zentrade Kitchen",
            "sku": "ZT-KNIFE-001",
            "weight": "1.2kg",
            "material": "스테인리스 스틸",
            "images": [
                "https://example.com/knife-set-1.jpg",
                "https://example.com/knife-set-2.jpg"
            ],
            "specifications": {
                "set_contents": ["식칼", "과도", "빵칼", "유틸리티 나이프", "파링 나이프"],
                "blade_material": "독일산 스테인리스 스틸",
                "handle_material": "에르고노믹 플라스틱"
            },
            "supplier": "zentrade",
            "supplier_product_id": "ZT-KITCHEN-001"
        },
        {
            "id": "dg_001",
            "name": "다기능 청소 도구 세트",
            "description": "일상 청소를 위한 다양한 도구가 포함된 올인원 청소 세트",
            "price": 35000,
            "cost": 17500,
            "stock": 100,
            "category": "생활용품",
            "subcategory": "청소용품",
            "brand": "Domeggook Clean",
            "sku": "DG-CLEAN-001",
            "weight": "800g",
            "material": "플라스틱, 마이크로파이버",
            "images": [
                "https://example.com/clean-set-1.jpg"
            ],
            "specifications": {
                "contents": ["걸레", "스프레이", "브러시", "클리너"],
                "package_size": "30x20x15cm"
            },
            "supplier": "domeggook",
            "supplier_product_id": "DG-CLEAN-001"
        }
    ]


@pytest.fixture
def product_categories() -> List[Dict[str, Any]]:
    """Sample product categories"""
    return [
        {
            "name": "보석",
            "description": "귀금속 및 보석류",
            "subcategories": ["목걸이", "반지", "귀걸이", "팔찌"],
            "commission_rate": 0.15,
            "popular_keywords": ["골드", "실버", "다이아몬드", "진주"]
        },
        {
            "name": "주방용품",
            "description": "조리 및 주방 관련 용품",
            "subcategories": ["조리도구", "조리기구", "식기", "수납용품"],
            "commission_rate": 0.10,
            "popular_keywords": ["스테인리스", "논스틱", "실리콘", "세라믹"]
        },
        {
            "name": "생활용품",
            "description": "일상생활 편의용품",
            "subcategories": ["청소용품", "수납용품", "욕실용품", "세탁용품"],
            "commission_rate": 0.12,
            "popular_keywords": ["다기능", "편리한", "실용적", "친환경"]
        },
        {
            "name": "전자제품",
            "description": "각종 전자기기 및 액세서리",
            "subcategories": ["스마트폰", "태블릿", "액세서리", "가전제품"],
            "commission_rate": 0.08,
            "popular_keywords": ["스마트", "무선", "고성능", "에너지절약"]
        }
    ]


@pytest.fixture
def product_variants() -> List[Dict[str, Any]]:
    """Sample product variants"""
    return [
        {
            "parent_product_id": "TEST-001",
            "variant_type": "color",
            "variant_value": "빨간색",
            "sku": "TEST-001-RED",
            "price_modifier": Decimal("0"),
            "stock_quantity": 50,
            "images": ["https://example.com/test-red.jpg"]
        },
        {
            "parent_product_id": "TEST-001",
            "variant_type": "color",
            "variant_value": "파란색",
            "sku": "TEST-001-BLUE",
            "price_modifier": Decimal("0"),
            "stock_quantity": 30,
            "images": ["https://example.com/test-blue.jpg"]
        },
        {
            "parent_product_id": "TEST-001",
            "variant_type": "size",
            "variant_value": "L",
            "sku": "TEST-001-L",
            "price_modifier": Decimal("5000"),
            "stock_quantity": 20,
            "images": []
        }
    ]


@pytest.fixture
def product_with_ai_enhancement() -> Dict[str, Any]:
    """Product data enhanced by AI"""
    return {
        "name": "프리미엄 스마트 무선 이어폰",
        "original_description": "무선 이어폰",
        "ai_enhanced_description": """혁신적인 노이즈 캔슬링 기술이 적용된 프리미엄 무선 이어폰입니다. 
        최첨단 Bluetooth 5.0 기술로 끊김 없는 연결을 제공하며, 인체공학적 디자인으로 
        장시간 착용해도 편안합니다. IPX7 방수 등급으로 운동이나 야외활동 시에도 안심하고 
        사용할 수 있습니다. 30시간 연속 재생이 가능한 배터리와 급속 충전 기능으로 
        언제나 최고의 음질을 경험하세요.""",
        "ai_generated_keywords": [
            "무선이어폰", "노이즈캔슬링", "블루투스5.0", "방수", "장시간재생", 
            "프리미엄", "고음질", "편안한착용감", "스포츠", "급속충전"
        ],
        "ai_optimized_price": Decimal("89000"),
        "original_price": Decimal("79000"),
        "market_analysis": {
            "trend": "상승",
            "demand_score": 92,
            "competition_level": "중간",
            "recommended_margin": 0.45
        },
        "ai_confidence": 0.94
    }


@pytest.fixture
def bulk_product_data() -> List[Dict[str, Any]]:
    """Bulk product data for performance testing"""
    products = []
    
    categories = ["보석", "주방용품", "생활용품", "전자제품", "의류"]
    brands = ["브랜드A", "브랜드B", "브랜드C", "브랜드D", "브랜드E"]
    
    for i in range(100):
        product = {
            "name": f"대량 테스트 상품 {i+1:03d}",
            "description": f"대량 테스트용 상품 {i+1}입니다. " * 5,
            "price": Decimal(str(10000 + (i * 500))),
            "cost": Decimal(str(5000 + (i * 250))),
            "sku": f"BULK-{i+1:03d}",
            "category": categories[i % len(categories)],
            "brand": brands[i % len(brands)],
            "stock_quantity": 50 + (i % 100),
            "weight": Decimal(str(0.1 + (i % 10) * 0.1)),
            "tags": [f"태그{j}" for j in range(1, 4)],
            "status": "active" if i % 10 != 9 else "inactive"
        }
        products.append(product)
    
    return products


@pytest.fixture
def marketplace_product_mappings() -> Dict[str, Dict[str, Any]]:
    """Sample product mappings to marketplaces"""
    return {
        "coupang": {
            "vendor_item_id": "VI_COUP_001",
            "product_id": "CP_12345",
            "status": "registered",
            "approval_status": "approved",
            "platform_specific_data": {
                "rocket_delivery": True,
                "commission_rate": 0.12,
                "category_code": "HOME_KITCHEN"
            }
        },
        "naver": {
            "channel_product_no": "CH_NAVER_001",
            "product_id": "NV_67890",
            "status": "registered",
            "approval_status": "reviewing",
            "platform_specific_data": {
                "smart_store": True,
                "commission_rate": 0.03,
                "delivery_type": "standard"
            }
        },
        "eleventy": {
            "vendor_item_id": "VI_11ST_001",
            "product_id": "11_54321",
            "status": "registered",
            "approval_status": "approved",
            "platform_specific_data": {
                "commission_rate": 0.035,
                "category_code": "ELECTRONICS"
            }
        }
    }


@pytest.fixture
def product_performance_data() -> Dict[str, Any]:
    """Sample product performance metrics"""
    return {
        "views": 1250,
        "clicks": 89,
        "orders": 12,
        "revenue": Decimal("420000"),
        "profit": Decimal("210000"),
        "conversion_rate": 0.13,
        "average_rating": 4.3,
        "review_count": 8,
        "return_rate": 0.02,
        "platform_breakdown": {
            "coupang": {
                "views": 800,
                "orders": 8,
                "revenue": Decimal("280000")
            },
            "naver": {
                "views": 300,
                "orders": 3,
                "revenue": Decimal("105000")
            },
            "eleventy": {
                "views": 150,
                "orders": 1,
                "revenue": Decimal("35000")
            }
        },
        "period": "last_30_days"
    }


@pytest.fixture
def product_price_history() -> List[Dict[str, Any]]:
    """Sample price history data"""
    from datetime import timedelta
    
    base_date = datetime.utcnow()
    history = []
    
    prices = [25000, 23000, 24000, 26000, 25500, 24500, 25000]
    
    for i, price in enumerate(prices):
        history.append({
            "product_id": "TEST-001",
            "price": Decimal(str(price)),
            "changed_at": base_date - timedelta(days=len(prices)-i),
            "changed_by": "system" if i % 2 == 0 else "admin",
            "reason": "market_adjustment" if i % 2 == 0 else "manual_update"
        })
    
    return history


@pytest.fixture
def product_inventory_alerts() -> List[Dict[str, Any]]:
    """Sample inventory alert data"""
    return [
        {
            "product_id": "TEST-001",
            "sku": "TEST-001",
            "current_stock": 5,
            "min_stock_level": 10,
            "alert_type": "low_stock",
            "severity": "warning",
            "created_at": datetime.utcnow(),
            "resolved": False
        },
        {
            "product_id": "TEST-002",
            "sku": "TEST-002",
            "current_stock": 0,
            "min_stock_level": 5,
            "alert_type": "out_of_stock",
            "severity": "critical",
            "created_at": datetime.utcnow(),
            "resolved": False
        }
    ]