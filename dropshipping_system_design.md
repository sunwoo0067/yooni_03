# 드랍쉬핑 자동화 시스템 설계

## 1. 시스템 개요

### 1.1 비즈니스 목표
- 일일 주문 처리: 현재 20건 → 목표 100~1000건
- 자동순환 시스템 구축
- 멀티 계정 운영
- AI 기반 가격 최적화

### 1.2 기술 스택
- **백엔드**: Python (FastAPI)
- **데이터베이스**: PostgreSQL + Supabase
- **스케줄러**: Celery + Redis
- **AI/ML**: scikit-learn, TensorFlow
- **웹 스크래핑**: Scrapy, Selenium
- **API 클라이언트**: httpx, aiohttp

## 2. 데이터베이스 스키마

### 2.1 핵심 테이블 구조

```sql
-- 도매처 정보
CREATE TABLE wholesalers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    api_type VARCHAR(50), -- 'api', 'excel', 'scraping'
    api_config JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 원본 상품 데이터 (도매처별 원본 데이터 그대로 저장)
CREATE TABLE raw_products (
    id SERIAL PRIMARY KEY,
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    product_code VARCHAR(200) NOT NULL,
    raw_data JSONB NOT NULL, -- 도매처 원본 데이터 전체
    collected_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(wholesaler_id, product_code)
);

-- 정규화된 상품 마스터
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    master_product_code VARCHAR(200) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    brand VARCHAR(200),
    model_name VARCHAR(200),
    category_id INTEGER REFERENCES categories(id),
    description TEXT,
    specifications JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 상품-도매처 매핑 (가격 정보 포함)
CREATE TABLE product_wholesaler_mapping (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    wholesaler_product_code VARCHAR(200) NOT NULL,
    supply_price DECIMAL(10,2) NOT NULL,
    wholesale_price DECIMAL(10,2),
    retail_price DECIMAL(10,2),
    shipping_fee DECIMAL(10,2) DEFAULT 0,
    stock_status VARCHAR(50),
    is_lowest_price BOOLEAN DEFAULT false,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(wholesaler_id, wholesaler_product_code)
);

-- 이미지 URL 관리
CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    image_type VARCHAR(50), -- 'main', 'sub', 'detail'
    image_url TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 상세페이지 URL 관리
CREATE TABLE product_detail_pages (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    detail_page_url TEXT,
    detail_html TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 표준 카테고리 (쿠팡 기준)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    coupang_category_code VARCHAR(100),
    category_name VARCHAR(200) NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    level INTEGER NOT NULL,
    full_path VARCHAR(500),
    is_active BOOLEAN DEFAULT true
);

-- 도매처-표준 카테고리 매핑
CREATE TABLE category_mapping (
    id SERIAL PRIMARY KEY,
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    wholesaler_category VARCHAR(500),
    standard_category_id INTEGER REFERENCES categories(id),
    confidence_score DECIMAL(3,2) DEFAULT 0.0
);

-- 멀티 계정 관리
CREATE TABLE marketplace_accounts (
    id SERIAL PRIMARY KEY,
    marketplace VARCHAR(50) NOT NULL, -- 'coupang', 'naver', '11st'
    account_name VARCHAR(100) NOT NULL,
    account_config JSONB, -- API keys, credentials
    pricing_policy JSONB, -- 계정별 가격 정책
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 상품 업로드 이력
CREATE TABLE product_listings (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    account_id INTEGER REFERENCES marketplace_accounts(id),
    marketplace_product_id VARCHAR(200),
    listing_price DECIMAL(10,2),
    margin_rate DECIMAL(5,2),
    status VARCHAR(50),
    listed_at TIMESTAMP,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- 주문 관리
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(100) UNIQUE NOT NULL,
    marketplace_order_id VARCHAR(200),
    account_id INTEGER REFERENCES marketplace_accounts(id),
    product_id INTEGER REFERENCES products(id),
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    quantity INTEGER NOT NULL,
    order_price DECIMAL(10,2),
    supply_price DECIMAL(10,2),
    profit DECIMAL(10,2),
    customer_info JSONB,
    order_status VARCHAR(50),
    ordered_at TIMESTAMP,
    shipped_at TIMESTAMP,
    tracking_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 가격 변동 이력
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    change_percentage DECIMAL(5,2),
    detected_at TIMESTAMP DEFAULT NOW()
);

-- 중복 상품 그룹
CREATE TABLE duplicate_product_groups (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(200),
    matching_criteria JSONB, -- 매칭 기준 (상품명 유사도, 이미지 해시 등)
    created_at TIMESTAMP DEFAULT NOW()
);

-- 중복 상품 매핑
CREATE TABLE duplicate_products (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES duplicate_product_groups(id),
    product_id INTEGER REFERENCES products(id),
    similarity_score DECIMAL(3,2),
    is_primary BOOLEAN DEFAULT false
);

-- 시스템 설정
CREATE TABLE system_configs (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 작업 스케줄
CREATE TABLE job_schedules (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50), -- 'collect', 'update', 'sync'
    wholesaler_id INTEGER REFERENCES wholesalers(id),
    schedule_config JSONB, -- cron expression, interval
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- 작업 로그
CREATE TABLE job_logs (
    id SERIAL PRIMARY KEY,
    job_schedule_id INTEGER REFERENCES job_schedules(id),
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_summary JSONB,
    error_message TEXT
);
```

### 2.2 인덱스 전략

```sql
-- 성능 최적화를 위한 인덱스
CREATE INDEX idx_raw_products_wholesaler_updated ON raw_products(wholesaler_id, updated_at);
CREATE INDEX idx_product_mapping_lowest_price ON product_wholesaler_mapping(product_id, is_lowest_price);
CREATE INDEX idx_products_name_trgm ON products USING gin(name gin_trgm_ops); -- 상품명 검색
CREATE INDEX idx_orders_status_date ON orders(order_status, ordered_at);
CREATE INDEX idx_price_history_product_date ON price_history(product_id, detected_at);
```

## 3. 시스템 아키텍처

### 3.1 마이크로서비스 구조

```
dropshipping-system/
├── collector-service/       # 상품 수집 서비스
│   ├── adapters/           # 도매처별 어댑터
│   │   ├── zentrade.py
│   │   ├── ownerclan.py
│   │   ├── domeme.py
│   │   └── excel_adapter.py
│   ├── scheduler.py        # 수집 스케줄러
│   └── api.py
│
├── product-service/        # 상품 관리 서비스
│   ├── duplicate_finder.py # 중복 상품 검색
│   ├── price_optimizer.py  # 가격 최적화
│   ├── category_mapper.py  # 카테고리 매핑
│   └── api.py
│
├── order-service/          # 주문 처리 서비스
│   ├── order_processor.py
│   ├── tracking_updater.py
│   └── api.py
│
├── marketplace-service/    # 마켓플레이스 연동
│   ├── coupang/
│   ├── naver/
│   └── api.py
│
├── ai-service/            # AI/ML 서비스
│   ├── price_predictor.py
│   ├── category_classifier.py
│   ├── duplicate_detector.py
│   └── api.py
│
├── common/                # 공통 모듈
│   ├── database.py
│   ├── models.py
│   ├── utils.py
│   └── config.py
│
└── web-dashboard/         # 관리 대시보드
    └── ...
```

### 3.2 데이터 흐름

```mermaid
graph TB
    A[도매처 API/Excel] --> B[Collector Service]
    B --> C[Raw Products DB]
    C --> D[Product Service]
    D --> E[정규화된 상품 DB]
    E --> F[중복 검사/가격 최적화]
    F --> G[Marketplace Service]
    G --> H[쿠팡/네이버 등]
    H --> I[Order Service]
    I --> J[도매처 발주]
    J --> K[배송 추적]
    
    L[AI Service] --> F
    L --> D
```

## 4. 핵심 기능 구현

### 4.1 도매처별 수집 어댑터

```python
# collectors/adapters/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import asyncio
from datetime import datetime, timedelta

class BaseWholesalerAdapter(ABC):
    def __init__(self, wholesaler_id: int, config: Dict[str, Any]):
        self.wholesaler_id = wholesaler_id
        self.config = config
        
    @abstractmethod
    async def collect_all_products(self) -> List[Dict[str, Any]]:
        """전체 상품 수집"""
        pass
    
    @abstractmethod
    async def collect_recent_products(self, days: int = 30) -> List[Dict[str, Any]]:
        """최근 N일 상품 수집"""
        pass
    
    @abstractmethod
    async def collect_updated_products(self, last_update: datetime) -> List[Dict[str, Any]]:
        """업데이트된 상품만 수집"""
        pass
    
    async def save_raw_products(self, products: List[Dict[str, Any]]):
        """원본 데이터 저장"""
        # DB 저장 로직
        pass

# collectors/adapters/ownerclan.py
class OwnerClanAdapter(BaseWholesalerAdapter):
    def __init__(self, wholesaler_id: int, config: Dict[str, Any]):
        super().__init__(wholesaler_id, config)
        self.jwt_token = None
        self.base_url = "https://api.ownerclan.com"
    
    async def authenticate(self):
        """JWT 토큰 발급"""
        # 인증 로직
        pass
    
    async def collect_all_products(self) -> List[Dict[str, Any]]:
        """오너클랜 2단계 수집"""
        # 1단계: 상품 코드 수집 (1000개씩)
        all_product_codes = []
        page = 1
        while True:
            codes = await self._fetch_product_codes(page, limit=1000)
            if not codes:
                break
            all_product_codes.extend(codes)
            page += 1
        
        # 2단계: 상품 상세 정보 수집 (5000개씩)
        all_products = []
        for i in range(0, len(all_product_codes), 5000):
            batch_codes = all_product_codes[i:i+5000]
            products = await self._fetch_product_details(batch_codes)
            all_products.extend(products)
            
        return all_products
```

### 4.2 중복 상품 검색 엔진

```python
# product_service/duplicate_finder.py
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import imagehash
from PIL import Image
import requests
from io import BytesIO

class DuplicateProductFinder:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=5000
        )
        
    async def find_duplicates(self, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """중복 상품 검색"""
        candidates = []
        
        # 1. 상품명 유사도 검색
        name_similar = await self._find_by_name_similarity(product['name'])
        candidates.extend(name_similar)
        
        # 2. 키워드 기반 검색
        keyword_similar = await self._find_by_keywords(product)
        candidates.extend(keyword_similar)
        
        # 3. 이미지 해시 비교 (옵션)
        if product.get('images'):
            image_similar = await self._find_by_image_hash(product['images'])
            candidates.extend(image_similar)
        
        # 중복 제거 및 점수 계산
        unique_candidates = self._merge_and_score(candidates)
        return unique_candidates
    
    async def _find_by_name_similarity(self, name: str, threshold: float = 0.7):
        """상품명 유사도 기반 검색"""
        # DB에서 모든 상품명 로드 (캐싱 필요)
        all_products = await self._get_all_product_names()
        
        # TF-IDF 벡터화
        names = [p['name'] for p in all_products]
        names.append(name)
        
        tfidf_matrix = self.vectorizer.fit_transform(names)
        similarities = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])
        
        # 유사도 임계값 이상인 상품 반환
        similar_indices = np.where(similarities[0] >= threshold)[0]
        return [all_products[i] for i in similar_indices]
    
    async def _find_by_image_hash(self, image_urls: List[str]):
        """이미지 해시 기반 중복 검색"""
        results = []
        for url in image_urls[:3]:  # 메인 이미지 3개만 비교
            try:
                response = requests.get(url)
                img = Image.open(BytesIO(response.content))
                hash_val = str(imagehash.average_hash(img))
                
                # DB에서 유사한 해시 검색
                similar = await self._query_similar_hashes(hash_val)
                results.extend(similar)
            except:
                continue
                
        return results
```

### 4.3 AI 기반 가격 최적화

```python
# ai_service/price_optimizer.py
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta

class PriceOptimizer:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100)
        self.min_margin = 0.2  # 최소 마진율 20%
        
    async def optimize_price(self, product: Dict[str, Any], 
                           account: Dict[str, Any]) -> Dict[str, Any]:
        """AI 기반 최적 가격 산정"""
        
        # 특성 추출
        features = await self._extract_features(product)
        
        # 가격 예측
        predicted_price = self.model.predict([features])[0]
        
        # 제약 조건 적용
        optimized_price = self._apply_constraints(
            predicted_price,
            product['supply_price'],
            product['category'],
            account['pricing_policy']
        )
        
        return {
            'recommended_price': optimized_price,
            'expected_margin': (optimized_price - product['supply_price']) / optimized_price,
            'confidence': self._calculate_confidence(features)
        }
    
    def _apply_constraints(self, predicted_price: float, 
                          supply_price: float,
                          category: str,
                          policy: Dict) -> float:
        """가격 제약 조건 적용"""
        
        # 최소 마진 보장
        min_price = supply_price * (1 + self.min_margin)
        
        # 카테고리별 마진율 적용
        category_margin = policy.get('category_margins', {}).get(category, 0.25)
        category_price = supply_price * (1 + category_margin)
        
        # 가격 구간별 마진율 적용
        if supply_price < 10000:
            margin = 0.3
        elif supply_price < 50000:
            margin = 0.25
        else:
            margin = 0.2
            
        range_price = supply_price * (1 + margin)
        
        # 최종 가격 결정
        final_price = max(min_price, category_price, range_price, predicted_price)
        
        # 끝자리 조정 (990원, 900원 단위)
        if final_price < 10000:
            final_price = round(final_price / 100) * 100 - 10
        else:
            final_price = round(final_price / 1000) * 1000 - 100
            
        return final_price
```

### 4.4 자동 주문 처리 시스템

```python
# order_service/order_processor.py
class OrderProcessor:
    def __init__(self):
        self.wholesaler_adapters = {}
        
    async def process_order(self, order: Dict[str, Any]):
        """주문 자동 처리"""
        try:
            # 1. 최저가 도매처 선택
            wholesaler = await self._select_best_wholesaler(order['product_id'])
            
            # 2. 도매처별 주문 처리
            if wholesaler['api_type'] == 'api':
                result = await self._process_api_order(wholesaler, order)
            else:
                result = await self._process_excel_order(wholesaler, order)
            
            # 3. 주문 상태 업데이트
            await self._update_order_status(order['id'], 'ordered', result)
            
            # 4. 알림 발송
            await self._send_notification(order, result)
            
        except Exception as e:
            await self._handle_order_error(order, e)
    
    async def _process_api_order(self, wholesaler: Dict, order: Dict):
        """API 주문 처리"""
        adapter = self.wholesaler_adapters[wholesaler['code']]
        
        if wholesaler['code'] == 'ownerclan':
            # 오너클랜 API 주문
            result = await adapter.create_order({
                'product_code': order['wholesaler_product_code'],
                'quantity': order['quantity'],
                'customer_info': order['customer_info']
            })
            
            # 송장 번호 자동 입력
            if result.get('tracking_number'):
                await self._update_marketplace_tracking(
                    order['marketplace_order_id'],
                    result['tracking_number']
                )
                
        return result
```

## 5. 배포 및 운영 전략

### 5.1 Docker Compose 구성

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: dropshipping
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  collector-service:
    build: ./collector-service
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://admin:secure_password@postgres:5432/dropshipping
      REDIS_URL: redis://redis:6379
    volumes:
      - ./collector-service:/app

  product-service:
    build: ./product-service
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://admin:secure_password@postgres:5432/dropshipping
      REDIS_URL: redis://redis:6379

  celery-worker:
    build: ./collector-service
    command: celery -A tasks worker --loglevel=info
    depends_on:
      - redis
      - postgres

  celery-beat:
    build: ./collector-service
    command: celery -A tasks beat --loglevel=info
    depends_on:
      - redis

volumes:
  postgres_data:
```

### 5.2 모니터링 및 알림

```python
# common/monitoring.py
class SystemMonitor:
    def __init__(self):
        self.notification_channels = ['email', 'slack', 'telegram']
        
    async def check_price_changes(self):
        """가격 변동 모니터링"""
        significant_changes = await self._get_significant_price_changes()
        
        for change in significant_changes:
            if change['percentage'] > 10:
                await self.send_alert(
                    f"가격 급등: {change['product_name']} "
                    f"{change['old_price']:,}원 → {change['new_price']:,}원 "
                    f"(+{change['percentage']:.1f}%)"
                )
    
    async def check_order_status(self):
        """주문 상태 모니터링"""
        pending_orders = await self._get_pending_orders()
        
        for order in pending_orders:
            if order['hours_pending'] > 24:
                await self.send_alert(
                    f"주문 지연: {order['order_number']} "
                    f"({order['hours_pending']}시간 대기중)"
                )
```

## 6. 확장 가능성

### 6.1 추가 기능 로드맵
1. **이미지 AI 분석**: 상품 이미지 품질 평가, 자동 편집
2. **리뷰 분석**: 마켓플레이스 리뷰 수집 및 감성 분석
3. **재고 예측**: 판매 추이 기반 재고 소진 예측
4. **자동 가격 조정**: 경쟁사 가격 모니터링 및 자동 조정
5. **챗봇 CS**: 고객 문의 자동 응답 시스템

### 6.2 성능 최적화 전략
1. **캐싱**: Redis를 활용한 상품 정보 캐싱
2. **비동기 처리**: 모든 I/O 작업 비동기화
3. **배치 처리**: 대량 데이터 처리 시 배치 단위 처리
4. **인덱싱**: 검색 성능 향상을 위한 적절한 인덱싱
5. **CDN**: 이미지 서빙을 위한 CDN 활용

이 설계를 기반으로 단계별로 구현하시면 확장 가능한 드랍쉬핑 자동화 시스템을 구축할 수 있습니다.