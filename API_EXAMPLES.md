# API 사용 예제집

## 📋 목차
1. [API 개요](#api-개요)
2. [인증 방법](#인증-방법)
3. [상품 수집 API](#상품-수집-api)
4. [AI 소싱 API](#ai-소싱-api)
5. [상품 가공 API](#상품-가공-api)
6. [상품 등록 API](#상품-등록-api)
7. [주문 처리 API](#주문-처리-api)
8. [분석 API](#분석-api)
9. [Python 클라이언트](#python-클라이언트)
10. [curl 예제](#curl-예제)
11. [포스트맨 컬렉션](#포스트맨-컬렉션)

## 🔗 API 개요

### 기본 정보
- **Base URL**: `https://api.dropshipping-system.com/v1`
- **인증 방식**: JWT Bearer Token
- **응답 형식**: JSON
- **Rate Limit**: 1000 requests/hour

### 공통 응답 형식
```json
{
    "success": true,
    "data": {},
    "message": "Success",
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_abc123"
}
```

## 🔐 인증 방법

### 1. API 키 발급
```bash
# 관리자 패널에서 API 키 생성
POST /api/v1/auth/api-keys
```

### 2. JWT 토큰 발급
```python
import requests

def get_access_token(api_key, secret_key):
    url = "https://api.dropshipping-system.com/v1/auth/token"
    data = {
        "api_key": api_key,
        "secret_key": secret_key
    }
    
    response = requests.post(url, json=data)
    return response.json()["data"]["access_token"]

# 사용 예시
token = get_access_token("your_api_key", "your_secret_key")
headers = {"Authorization": f"Bearer {token}"}
```

### 3. 토큰 갱신
```python
def refresh_token(refresh_token):
    url = "https://api.dropshipping-system.com/v1/auth/refresh"
    data = {"refresh_token": refresh_token}
    
    response = requests.post(url, json=data)
    return response.json()["data"]["access_token"]
```

## 📦 상품 수집 API

### 1. 젠트레이드 상품 수집
```python
# 기본 수집
def collect_gentrade_products(category=None, limit=50):
    url = "https://api.dropshipping-system.com/v1/collection/gentrade"
    params = {
        "category": category,
        "limit": limit,
        "sort": "popularity",
        "min_price": 1000,
        "max_price": 100000
    }
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# 사용 예시
products = collect_gentrade_products("생활용품", 100)
print(f"수집된 상품 수: {len(products['data'])}")
```

### 2. 오너클랜 상품 수집
```python
def collect_ownersclan_products(filters=None):
    url = "https://api.dropshipping-system.com/v1/collection/ownersclan"
    data = {
        "filters": filters or {
            "category": "패션",
            "price_range": [10000, 50000],
            "rating_min": 4.0,
            "stock_min": 10
        },
        "limit": 50,
        "offset": 0
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 고급 필터링 예시
advanced_filters = {
    "categories": ["패션", "뷰티"],
    "brands": ["브랜드A", "브랜드B"],
    "discount_min": 20,  # 최소 할인율 20%
    "new_arrivals": True,
    "free_shipping": True
}

products = collect_ownersclan_products(advanced_filters)
```

### 3. 도매꾹 상품 수집
```python
def collect_domemegguk_products(search_query):
    url = "https://api.dropshipping-system.com/v1/collection/domemegguk"
    data = {
        "search_query": search_query,
        "category_filter": ["전자제품", "생활용품"],
        "sort_by": "best_selling",
        "include_options": True,  # 상품 옵션 포함
        "include_reviews": True   # 리뷰 정보 포함
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 키워드 검색 예시
products = collect_domemegguk_products("무선 이어폰")
```

### 4. 일괄 수집 (모든 도매처)
```python
def collect_all_sources(config):
    url = "https://api.dropshipping-system.com/v1/collection/bulk"
    data = {
        "sources": ["gentrade", "ownersclan", "domemegguk"],
        "config": config,
        "merge_duplicates": True,
        "quality_filter": True
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 통합 수집 설정
bulk_config = {
    "target_count": 200,
    "categories": ["생활용품", "패션", "전자제품"],
    "price_range": [5000, 80000],
    "quality_score_min": 70
}

all_products = collect_all_sources(bulk_config)
```

## 🤖 AI 소싱 API

### 1. 마켓 분석
```python
def analyze_market(category, period="30d"):
    url = "https://api.dropshipping-system.com/v1/ai/market-analysis"
    data = {
        "category": category,
        "analysis_period": period,
        "include_competitors": True,
        "include_trends": True,
        "target_platforms": ["coupang", "naver", "11st"]
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 시장 분석 예시
market_data = analyze_market("무선 이어폰", "60d")
print(f"경쟁 강도: {market_data['data']['competition_level']}")
print(f"예상 수익성: {market_data['data']['profitability_score']}")
```

### 2. 트렌드 예측
```python
def predict_trends(products, forecast_days=30):
    url = "https://api.dropshipping-system.com/v1/ai/trend-prediction"
    data = {
        "products": products,
        "forecast_period": forecast_days,
        "include_seasonality": True,
        "include_external_factors": True  # 이벤트, 날씨 등
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 트렌드 예측 예시
product_list = [
    {"id": "prod_001", "category": "생활용품", "name": "접이식 의자"},
    {"id": "prod_002", "category": "전자제품", "name": "블루투스 스피커"}
]

trends = predict_trends(product_list, 45)
for trend in trends['data']:
    print(f"상품: {trend['product_name']}")
    print(f"예상 수요 증가율: {trend['demand_increase']}%")
```

### 3. 상품 점수화
```python
def score_products(products, scoring_weights=None):
    url = "https://api.dropshipping-system.com/v1/ai/product-scoring"
    
    default_weights = {
        "profitability": 0.3,    # 수익성
        "competition": 0.2,      # 경쟁 강도
        "demand": 0.25,          # 수요
        "trend": 0.15,           # 트렌드
        "quality": 0.1           # 품질
    }
    
    data = {
        "products": products,
        "scoring_weights": scoring_weights or default_weights,
        "market_context": {
            "target_margin": 30,  # 목표 마진율 30%
            "risk_tolerance": "medium"
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 점수화 예시
scored_products = score_products(product_list)
top_products = sorted(
    scored_products['data'], 
    key=lambda x: x['total_score'], 
    reverse=True
)[:10]
```

### 4. AI 추천 시스템
```python
def get_ai_recommendations(user_profile):
    url = "https://api.dropshipping-system.com/v1/ai/recommendations"
    data = {
        "user_profile": user_profile,
        "recommendation_count": 20,
        "diversity_factor": 0.3,  # 다양성 30%
        "freshness_factor": 0.2   # 신상품 비중 20%
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 사용자 프로필 기반 추천
seller_profile = {
    "experience_level": "intermediate",
    "preferred_categories": ["생활용품", "패션"],
    "budget_range": [10000, 50000],
    "sales_history": {
        "total_revenue": 1000000,
        "best_category": "생활용품",
        "avg_margin": 25
    }
}

recommendations = get_ai_recommendations(seller_profile)
```

## 🔧 상품 가공 API

### 1. AI 상품명 생성
```python
def generate_product_names(product, variants=3):
    url = "https://api.dropshipping-system.com/v1/processing/name-generation"
    data = {
        "product": product,
        "variants_count": variants,
        "style": "seo_optimized",  # marketing, descriptive, seo_optimized
        "target_platform": "coupang",
        "include_keywords": True,
        "max_length": 50
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 상품명 생성 예시
original_product = {
    "name": "블루투스 무선 이어폰",
    "features": ["노이즈캔슬링", "방수", "장시간 배터리"],
    "category": "전자제품",
    "target_keywords": ["무선이어폰", "블루투스", "노이즈캔슬링"]
}

new_names = generate_product_names(original_product, 5)
print("생성된 상품명들:")
for i, name in enumerate(new_names['data']['variants'], 1):
    print(f"{i}. {name['name']} (SEO점수: {name['seo_score']})")
```

### 2. 이미지 최적화
```python
def optimize_images(image_urls, optimization_type="marketplace"):
    url = "https://api.dropshipping-system.com/v1/processing/image-optimization"
    data = {
        "image_urls": image_urls,
        "optimization_type": optimization_type,  # marketplace, social, mobile
        "target_size": [800, 800],
        "quality": 85,
        "format": "webp",
        "watermark": {
            "enabled": True,
            "text": "우리상점",
            "position": "bottom_right",
            "opacity": 0.7
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 이미지 최적화 예시
original_images = [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg",
    "https://example.com/image3.jpg"
]

optimized = optimize_images(original_images, "marketplace")
print(f"최적화된 이미지 수: {len(optimized['data']['optimized_images'])}")
```

### 3. 상품 설명 생성
```python
def generate_product_description(product_info, template_type="detailed"):
    url = "https://api.dropshipping-system.com/v1/processing/description-generation"
    data = {
        "product_info": product_info,
        "template_type": template_type,  # simple, detailed, marketing
        "include_specifications": True,
        "include_usage_scenarios": True,
        "tone": "professional",  # casual, professional, enthusiastic
        "target_length": 500
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 상품 설명 생성 예시
product_info = {
    "name": "프리미엄 무선 이어폰",
    "features": [
        "액티브 노이즈 캔슬링",
        "IPX7 방수",
        "30시간 재생시간",
        "고음질 코덱 지원"
    ],
    "specifications": {
        "드라이버": "10mm 다이나믹",
        "주파수": "20Hz-20kHz",
        "배터리": "리튬폴리머"
    },
    "category": "전자제품",
    "target_audience": "음악 애호가, 직장인"
}

description = generate_product_description(product_info, "marketing")
print(description['data']['generated_description'])
```

### 4. 카테고리 매핑
```python
def map_categories(source_category, target_platform):
    url = "https://api.dropshipping-system.com/v1/processing/category-mapping"
    data = {
        "source_category": source_category,
        "target_platform": target_platform,
        "include_suggestions": True,
        "confidence_threshold": 0.8
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 카테고리 매핑 예시
mapping = map_categories("생활용품/주방용품/조리도구", "coupang")
print(f"매핑된 카테고리: {mapping['data']['mapped_category']}")
print(f"신뢰도: {mapping['data']['confidence']}")
```

## 🛒 상품 등록 API

### 1. 쿠팡 상품 등록
```python
def register_to_coupang(product_data):
    url = "https://api.dropshipping-system.com/v1/registration/coupang"
    data = {
        "product": product_data,
        "pricing_strategy": "competitive",  # competitive, premium, budget
        "inventory_buffer": 5,  # 재고 버퍼
        "auto_pricing": True,
        "schedule_time": None  # 즉시 등록
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 쿠팡 등록 예시
coupang_product = {
    "name": "프리미엄 무선 이어폰 노이즈캔슬링",
    "description": "고음질 블루투스 이어폰...",
    "category_id": "coupang_category_123",
    "images": ["optimized_image1.jpg", "optimized_image2.jpg"],
    "price": 49000,
    "original_price": 65000,
    "stock_quantity": 50,
    "shipping": {
        "method": "coupang_fulfillment",
        "cost": 0,
        "days": 1
    },
    "attributes": {
        "brand": "우리브랜드",
        "model": "WE-001",
        "color": "블랙",
        "warranty": "1년"
    }
}

result = register_to_coupang(coupang_product)
print(f"등록 결과: {result['data']['status']}")
print(f"상품 ID: {result['data']['product_id']}")
```

### 2. 네이버 스마트스토어 등록
```python
def register_to_naver(product_data):
    url = "https://api.dropshipping-system.com/v1/registration/naver"
    data = {
        "product": product_data,
        "display_settings": {
            "main_exposure": True,
            "mobile_optimized": True,
            "search_tags": ["무선이어폰", "블루투스", "노이즈캔슬링"]
        },
        "promotion": {
            "discount_rate": 15,
            "free_shipping": True,
            "point_rate": 1
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 네이버 등록 예시
naver_product = {
    "name": "[특가] 프리미엄 무선이어폰 IPX7방수",
    "category": "디지털/가전 > 이어폰/헤드폰 > 블루투스이어폰",
    "selling_price": 48000,
    "supply_price": 35000,
    "images": [
        {"url": "main_image.jpg", "type": "main"},
        {"url": "detail1.jpg", "type": "detail"},
        {"url": "detail2.jpg", "type": "detail"}
    ],
    "stock_quantity": 100,
    "product_info": {
        "manufacturer": "우리전자",
        "origin": "중국",
        "material": "ABS, 실리콘"
    }
}

naver_result = register_to_naver(naver_product)
```

### 3. 11번가 등록
```python
def register_to_11st(product_data):
    url = "https://api.dropshipping-system.com/v1/registration/11st"
    data = {
        "product": product_data,
        "marketing": {
            "coupon_applicable": True,
            "point_rate": 2,
            "bulk_discount": [
                {"quantity": 2, "discount": 5},
                {"quantity": 5, "discount": 10}
            ]
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 11번가 등록 예시
elevenst_product = {
    "name": "무선이어폰 블루투스5.0 고음질 노이즈캔슬링",
    "category_code": "1000000123",
    "selling_price": 47000,
    "market_price": 65000,
    "delivery_info": {
        "delivery_company": "CJ대한통운",
        "delivery_fee": 2500,
        "free_delivery_threshold": 30000
    }
}

elevenst_result = register_to_11st(elevenst_product)
```

### 4. 멀티 플랫폼 일괄 등록
```python
def register_to_multiple_platforms(product_data, platforms):
    url = "https://api.dropshipping-system.com/v1/registration/multi-platform"
    data = {
        "product": product_data,
        "target_platforms": platforms,
        "parallel_processing": True,
        "error_handling": "continue",  # stop, continue, retry
        "platform_customization": {
            "coupang": {"pricing_strategy": "competitive"},
            "naver": {"promotion_level": "high"},
            "11st": {"marketing_focus": "discount"}
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 멀티 플랫폼 등록 예시
platforms = ["coupang", "naver", "11st"]
multi_result = register_to_multiple_platforms(coupang_product, platforms)

for platform, result in multi_result['data']['results'].items():
    print(f"{platform}: {result['status']} - {result.get('product_id', 'N/A')}")
```

## 📋 주문 처리 API

### 1. 실시간 주문 모니터링
```python
def monitor_orders(platforms=None, real_time=True):
    url = "https://api.dropshipping-system.com/v1/orders/monitor"
    params = {
        "platforms": platforms or ["coupang", "naver", "11st"],
        "real_time": real_time,
        "status_filter": ["new", "processing"],
        "auto_process": True
    }
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# WebSocket을 통한 실시간 모니터링
import websocket
import json

def on_order_message(ws, message):
    order_data = json.loads(message)
    print(f"새 주문: {order_data['order_id']}")
    # 자동 처리 로직

def start_realtime_monitoring():
    ws_url = "wss://api.dropshipping-system.com/v1/orders/websocket"
    ws = websocket.WebSocketApp(
        ws_url,
        header={"Authorization": f"Bearer {token}"},
        on_message=on_order_message
    )
    ws.run_forever()
```

### 2. 자동 발주 처리
```python
def process_order_automatically(order_id):
    url = f"https://api.dropshipping-system.com/v1/orders/{order_id}/auto-process"
    data = {
        "processing_options": {
            "verify_stock": True,
            "price_check": True,
            "customer_verification": True
        },
        "notification_settings": {
            "customer_update": True,
            "internal_alert": True,
            "supplier_notification": True
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 주문 자동 처리 예시
order_result = process_order_automatically("ORDER_20240101_001")
print(f"처리 상태: {order_result['data']['status']}")
print(f"발주번호: {order_result['data']['supplier_order_id']}")
```

### 3. 배송 추적
```python
def track_delivery(tracking_number, carrier=None):
    url = "https://api.dropshipping-system.com/v1/orders/tracking"
    params = {
        "tracking_number": tracking_number,
        "carrier": carrier,
        "detailed_info": True
    }
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# 배송 추적 예시
tracking_info = track_delivery("1234567890", "cj")
print(f"현재 위치: {tracking_info['data']['current_location']}")
print(f"예상 도착: {tracking_info['data']['estimated_arrival']}")

# 배송 상태 업데이트
def update_delivery_status(order_id, status_update):
    url = f"https://api.dropshipping-system.com/v1/orders/{order_id}/delivery-status"
    response = requests.put(url, headers=headers, json=status_update)
    return response.json()
```

### 4. 정산 처리
```python
def process_settlement(settlement_data):
    url = "https://api.dropshipping-system.com/v1/orders/settlement"
    data = {
        "period": settlement_data["period"],
        "include_fees": True,
        "include_refunds": True,
        "breakdown_by_platform": True,
        "export_format": "excel"  # json, csv, excel
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 정산 처리 예시
settlement_period = {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
}

settlement = process_settlement({"period": settlement_period})
print(f"총 매출: {settlement['data']['total_revenue']:,}원")
print(f"순이익: {settlement['data']['net_profit']:,}원")
```

## 📊 분석 API

### 1. 판매 성과 분석
```python
def analyze_sales_performance(analysis_config):
    url = "https://api.dropshipping-system.com/v1/analytics/sales-performance"
    response = requests.post(url, headers=headers, json=analysis_config)
    return response.json()

# 성과 분석 설정
analysis_config = {
    "period": {
        "start": "2024-01-01",
        "end": "2024-12-31"
    },
    "metrics": [
        "revenue", "profit", "conversion_rate", 
        "customer_acquisition_cost", "lifetime_value"
    ],
    "dimensions": ["platform", "category", "product"],
    "include_forecasting": True
}

performance = analyze_sales_performance(analysis_config)
```

### 2. 상품 성과 분석
```python
def analyze_product_performance(product_ids, metrics):
    url = "https://api.dropshipping-system.com/v1/analytics/product-performance"
    data = {
        "product_ids": product_ids,
        "metrics": metrics,
        "comparison_period": "previous_month",
        "include_ranking": True
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 상품별 성과 분석
top_products = analyze_product_performance(
    product_ids=["PROD_001", "PROD_002", "PROD_003"],
    metrics=["sales_volume", "revenue", "profit_margin", "review_score"]
)
```

### 3. ROI 계산
```python
def calculate_roi(investment_data):
    url = "https://api.dropshipping-system.com/v1/analytics/roi"
    response = requests.post(url, headers=headers, json=investment_data)
    return response.json()

# ROI 계산 예시
roi_data = {
    "investments": [
        {"type": "advertising", "amount": 500000, "period": "2024-01"},
        {"type": "inventory", "amount": 2000000, "period": "2024-01"},
        {"type": "tools", "amount": 100000, "period": "2024-01"}
    ],
    "revenue_period": "2024-01",
    "include_breakdown": True
}

roi_analysis = calculate_roi(roi_data)
print(f"전체 ROI: {roi_analysis['data']['total_roi']}%")
```

## 🐍 Python 클라이언트

### 공식 Python SDK
```python
# pip install dropshipping-automation-sdk

from dropshipping_sdk import DropshippingClient

# 클라이언트 초기화
client = DropshippingClient(
    api_key="your_api_key",
    secret_key="your_secret_key",
    base_url="https://api.dropshipping-system.com/v1"
)

# 상품 수집
products = await client.collection.gentrade.collect(
    category="생활용품",
    limit=50
)

# AI 소싱
recommendations = await client.ai.get_recommendations(
    user_profile={"experience": "intermediate"}
)

# 상품 등록
result = await client.registration.coupang.register(product_data)

# 주문 모니터링
async for order in client.orders.monitor_stream():
    await client.orders.auto_process(order.id)
```

### 비동기 클라이언트 예시
```python
import asyncio
import aiohttp
from typing import List, Dict

class AsyncDropshippingClient:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://api.dropshipping-system.com/v1"
        self.session = None
        self.token = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        async with self.session.post(
            f"{self.base_url}/auth/token",
            json={"api_key": self.api_key, "secret_key": self.secret_key}
        ) as response:
            data = await response.json()
            self.token = data["data"]["access_token"]
    
    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    async def collect_products(self, source: str, **kwargs) -> List[Dict]:
        async with self.session.get(
            f"{self.base_url}/collection/{source}",
            headers=self.headers,
            params=kwargs
        ) as response:
            data = await response.json()
            return data["data"]
    
    async def register_product(self, platform: str, product: Dict) -> Dict:
        async with self.session.post(
            f"{self.base_url}/registration/{platform}",
            headers=self.headers,
            json={"product": product}
        ) as response:
            data = await response.json()
            return data["data"]

# 사용 예시
async def main():
    async with AsyncDropshippingClient("api_key", "secret_key") as client:
        # 병렬 상품 수집
        tasks = [
            client.collect_products("gentrade", category="생활용품"),
            client.collect_products("ownersclan", category="패션"),
            client.collect_products("domemegguk", search="전자제품")
        ]
        
        results = await asyncio.gather(*tasks)
        all_products = [product for result in results for product in result]
        
        print(f"총 수집된 상품: {len(all_products)}개")

asyncio.run(main())
```

## 🌐 curl 예제

### 인증
```bash
# JWT 토큰 발급
curl -X POST https://api.dropshipping-system.com/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "your_api_key",
    "secret_key": "your_secret_key"
  }'

# 응답에서 토큰 추출
export ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### 상품 수집
```bash
# 젠트레이드 상품 수집
curl -X GET "https://api.dropshipping-system.com/v1/collection/gentrade?category=생활용품&limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 오너클랜 상품 수집 (POST)
curl -X POST https://api.dropshipping-system.com/v1/collection/ownersclan \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "category": "패션",
      "price_range": [10000, 50000]
    },
    "limit": 30
  }'
```

### AI 소싱
```bash
# 상품 점수화
curl -X POST https://api.dropshipping-system.com/v1/ai/product-scoring \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {
        "id": "prod_001",
        "name": "무선 이어폰",
        "price": 50000,
        "category": "전자제품"
      }
    ],
    "scoring_weights": {
      "profitability": 0.4,
      "competition": 0.3,
      "demand": 0.3
    }
  }'
```

### 상품 등록
```bash
# 쿠팡 상품 등록
curl -X POST https://api.dropshipping-system.com/v1/registration/coupang \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product": {
      "name": "프리미엄 무선 이어폰",
      "price": 49000,
      "category_id": "123456",
      "images": ["image1.jpg", "image2.jpg"],
      "stock_quantity": 50
    },
    "pricing_strategy": "competitive"
  }'
```

### 주문 모니터링
```bash
# 주문 목록 조회
curl -X GET "https://api.dropshipping-system.com/v1/orders/monitor?platforms=coupang,naver" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 특정 주문 자동 처리
curl -X POST https://api.dropshipping-system.com/v1/orders/ORDER_123/auto-process \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "processing_options": {
      "verify_stock": true,
      "price_check": true
    }
  }'
```

### 분석 데이터
```bash
# 판매 성과 분석
curl -X POST https://api.dropshipping-system.com/v1/analytics/sales-performance \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "period": {
      "start": "2024-01-01",
      "end": "2024-01-31"
    },
    "metrics": ["revenue", "profit", "conversion_rate"],
    "dimensions": ["platform", "category"]
  }'
```

## 📮 포스트맨 컬렉션

### 컬렉션 구조
```json
{
  "info": {
    "name": "Dropshipping Automation API",
    "description": "Complete API collection for dropshipping automation system",
    "version": "1.0.0"
  },
  "auth": {
    "type": "bearer",
    "bearer": [
      {
        "key": "token",
        "value": "{{ACCESS_TOKEN}}",
        "type": "string"
      }
    ]
  },
  "variable": [
    {
      "key": "BASE_URL",
      "value": "https://api.dropshipping-system.com/v1"
    },
    {
      "key": "ACCESS_TOKEN",
      "value": ""
    }
  ]
}
```

### 환경 변수 설정
```json
{
  "environments": [
    {
      "name": "Development",
      "values": [
        {"key": "BASE_URL", "value": "http://localhost:8000/api/v1"},
        {"key": "API_KEY", "value": "dev_api_key"},
        {"key": "SECRET_KEY", "value": "dev_secret_key"}
      ]
    },
    {
      "name": "Production",
      "values": [
        {"key": "BASE_URL", "value": "https://api.dropshipping-system.com/v1"},
        {"key": "API_KEY", "value": "prod_api_key"},
        {"key": "SECRET_KEY", "value": "prod_secret_key"}
      ]
    }
  ]
}
```

### 사전 요청 스크립트
```javascript
// 자동 토큰 갱신
pm.sendRequest({
    url: pm.environment.get("BASE_URL") + "/auth/token",
    method: 'POST',
    header: {
        'Content-Type': 'application/json'
    },
    body: {
        mode: 'raw',
        raw: JSON.stringify({
            api_key: pm.environment.get("API_KEY"),
            secret_key: pm.environment.get("SECRET_KEY")
        })
    }
}, function (err, response) {
    if (response.code === 200) {
        const token = response.json().data.access_token;
        pm.environment.set("ACCESS_TOKEN", token);
    }
});
```

### 테스트 스크립트
```javascript
// 응답 검증
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has success field", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('success');
    pm.expect(jsonData.success).to.eql(true);
});

pm.test("Response time is less than 2000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000);
});

// 데이터 저장
if (pm.response.code === 200) {
    var responseData = pm.response.json();
    if (responseData.data && responseData.data.product_id) {
        pm.environment.set("LAST_PRODUCT_ID", responseData.data.product_id);
    }
}
```

## 🔍 API 응답 코드

### 성공 응답
- `200` - 성공
- `201` - 생성됨
- `202` - 처리 중 (비동기 작업)

### 클라이언트 오류
- `400` - 잘못된 요청
- `401` - 인증 실패
- `403` - 권한 없음
- `404` - 리소스 없음
- `429` - 요청 한도 초과

### 서버 오류
- `500` - 내부 서버 오류
- `502` - 게이트웨이 오류
- `503` - 서비스 이용 불가

### 사용량 제한
```json
{
  "rate_limit": {
    "limit": 1000,
    "remaining": 987,
    "reset_time": "2024-01-01T13:00:00Z"
  }
}
```

이 API 예제집을 통해 드랍쉬핑 자동화 시스템의 모든 기능을 효과적으로 활용할 수 있습니다. 각 예제는 실제 프로덕션 환경에서 바로 사용할 수 있도록 작성되었습니다.