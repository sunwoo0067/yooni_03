# 드랍쉬핑 상품가공 시스템 종합 설계

## 시스템 아키텍처 개요

```
┌─────────────────┬─────────────────┬─────────────────┐
│   상품명 AI     │  이미지 가공     │ 상세페이지 분석  │
│   생성기        │  엔진           │     모듈        │
└─────────────────┴─────────────────┴─────────────────┘
                           │
    ┌─────────────────────────────────────────────┐
    │           통합 처리 API 레이어               │
    └─────────────────────────────────────────────┘
                           │
    ┌─────────────────────────────────────────────┐
    │      하이브리드 데이터베이스 계층            │
    │    PostgreSQL + Supabase + Redis Cache     │
    └─────────────────────────────────────────────┘
```

## 1. 상품명 AI 생성기 모듈

### 핵심 기능
- 베스트셀러 상품명 패턴 분석
- 마켓별 SEO 최적화 키워드 생성
- 실적 기반 학습 및 피드백 루프
- 카탈로그/가격비교 사이트 회피 전략

### 기술 스택
```python
# 주요 라이브러리
- OpenAI GPT-4o-mini (비용 효율)
- Ollama (야간 오픈소스 모델)
- spaCy/KoNLPy (한국어 자연어 처리)
- scikit-learn (패턴 분석)
- transformers (로컬 모델)
```

### 구현 전략

#### 1.1 베스트셀러 패턴 분석기
```python
class BestsellerPatternAnalyzer:
    def __init__(self):
        self.market_patterns = {
            'coupang': {
                'title_length': (40, 80),
                'keywords': ['특가', '베스트', '인기'],
                'avoid_words': ['카탈로그', '아임템위너']
            },
            'naver': {
                'title_length': (30, 60),
                'keywords': ['추천', '신상', '할인'],
                'avoid_words': ['가격비교']
            },
            '11st': {
                'title_length': (35, 70),
                'keywords': ['할인', '특가', '인기'],
                'avoid_words': ['최저가']
            }
        }
```

#### 1.2 AI 기반 상품명 생성
```python
class ProductNameGenerator:
    def __init__(self, model_type='hybrid'):
        self.day_model = OpenAIGPT4()  # 주간용 고성능
        self.night_model = OllamaLocal()  # 야간용 절약형
        
    def generate_title(self, product_info, market, time_mode='day'):
        model = self.day_model if time_mode == 'day' else self.night_model
        
        prompt = f"""
        마켓: {market}
        원본 상품명: {product_info['original_title']}
        카테고리: {product_info['category']}
        
        요구사항:
        1. 가격비교 사이트 회피
        2. {market} 베스트셀러 패턴 적용
        3. SEO 최적화
        4. 클릭률 향상
        
        새로운 상품명 3개 생성:
        """
        
        return model.generate(prompt)
```

### 마켓별 차이점 대응

| 마켓 | 특징 | 최적화 전략 |
|------|------|-------------|
| 쿠팡 | 간결하고 핵심 키워드 중심 | 브랜드명 + 핵심기능 + 특가 |
| 네이버 | 상세한 설명선호, 리뷰 중요 | 상세 설명 + 품질 강조 |
| 11번가 | 할인 강조, 가격 경쟁력 | 할인율 + 가성비 강조 |

## 2. 이미지 프로세싱 엔진

### 핵심 기능
- 상세페이지 자동 스크래핑
- 최적 영역 AI 탐지
- 마켓별 규격 자동 변환
- 왜곡 없는 이미지 처리
- Supabase 자동 업로드

### 기술 스택
```python
# 이미지 처리
- OpenCV (이미지 처리)
- Pillow (이미지 조작)
- Selenium (웹 스크래핑)
- YOLO/Detectron2 (객체 탐지)
- Supabase Storage API
```

### 구현 설계

#### 2.1 상세페이지 스크래핑
```python
class ProductPageScraper:
    def __init__(self):
        self.driver = self.setup_selenium()
        
    def extract_images(self, url):
        """상세페이지에서 이미지 추출"""
        self.driver.get(url)
        
        # 스크롤하여 모든 이미지 로드
        self.scroll_to_load_all()
        
        # 이미지 영역 탐지
        image_elements = self.find_product_images()
        
        return [self.capture_element(elem) for elem in image_elements]
```

#### 2.2 최적 영역 자동 탐지
```python
class OptimalImageDetector:
    def __init__(self):
        self.model = YOLO('best_product_detector.pt')
        
    def find_best_crop_area(self, image):
        """베스트 상품 패턴 기반 최적 크롭 영역 탐지"""
        results = self.model(image)
        
        # 상품 중심부 탐지
        product_boxes = self.filter_product_boxes(results)
        
        # 마켓별 최적 비율 적용
        optimal_crop = self.calculate_optimal_crop(product_boxes)
        
        return optimal_crop
```

#### 2.3 마켓별 이미지 최적화
```python
class MarketImageOptimizer:
    def __init__(self):
        self.market_specs = {
            'coupang': {'size': (800, 800), 'format': 'JPEG', 'quality': 85},
            'naver': {'size': (700, 700), 'format': 'JPEG', 'quality': 90},
            '11st': {'size': (750, 750), 'format': 'JPEG', 'quality': 80}
        }
    
    def optimize_for_market(self, image, market):
        """왜곡 없는 마켓별 이미지 최적화"""
        spec = self.market_specs[market]
        
        # 비율 유지하며 리사이징
        resized = self.resize_maintain_ratio(image, spec['size'])
        
        # 배경 패딩 추가 (왜곡 방지)
        padded = self.add_smart_padding(resized, spec['size'])
        
        return padded
```

### 이미지 왜곡 방지 전략

1. **비율 유지 리사이징**
   - 원본 비율 보존
   - 부족한 영역은 스마트 패딩
   - 배경색 자동 감지 및 적용

2. **스마트 크롭핑**
   - AI 기반 중요 영역 탐지
   - 상품 중심부 보존
   - 불필요한 여백 제거

## 3. 상세페이지 분석기

### 핵심 기능
- 제품 대체 용도 발굴
- 베스트 상품 패턴 학습
- 새로운 상세페이지 생성
- 경쟁력 있는 포지셔닝

### 구현 설계

#### 3.1 용도 변경 분석기
```python
class AlternativeUseAnalyzer:
    def __init__(self):
        self.nlp_model = load_korean_nlp_model()
        
    def analyze_alternative_uses(self, product_description):
        """제품의 대체 용도 분석"""
        
        # 제품 특성 추출
        features = self.extract_product_features(product_description)
        
        # 유사 카테고리 제품 분석
        similar_products = self.find_similar_successful_products(features)
        
        # 새로운 용도 제안
        alternative_uses = self.generate_alternative_uses(features, similar_products)
        
        return alternative_uses
```

#### 3.2 베스트 상품 패턴 학습
```python
class BestProductPatternLearner:
    def __init__(self):
        self.pattern_db = PatternDatabase()
        
    def learn_from_bestsellers(self, category):
        """베스트셀러 패턴 학습"""
        
        # 베스트셀러 데이터 수집
        bestsellers = self.collect_bestseller_data(category)
        
        # 공통 패턴 추출
        patterns = {
            'description_structure': self.analyze_structure(bestsellers),
            'keyword_frequency': self.analyze_keywords(bestsellers),
            'image_patterns': self.analyze_image_layouts(bestsellers),
            'pricing_strategy': self.analyze_pricing(bestsellers)
        }
        
        return patterns
```

## 4. 하이브리드 데이터베이스 설계

### 구조
```sql
-- PostgreSQL (주요 비즈니스 로직)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    original_url TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW(),
    market VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE product_names (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    market VARCHAR(50) NOT NULL,
    generated_name TEXT NOT NULL,
    performance_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE processed_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    market VARCHAR(50) NOT NULL,
    supabase_url TEXT NOT NULL,
    optimization_params JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Supabase 활용
```javascript
// Supabase Storage for Images
const supabaseConfig = {
  url: process.env.SUPABASE_URL,
  key: process.env.SUPABASE_ANON_KEY,
  bucket: 'product-images'
}

// Redis Cache for Performance
const cacheConfig = {
  host: 'localhost',
  port: 6379,
  ttl: 3600 // 1시간 캐시
}
```

## 5. 비용 최적화 전략

### AI 모델 하이브리드 운영
```python
class CostOptimizedAI:
    def __init__(self):
        self.cost_tracker = CostTracker()
        self.schedule = {
            'day': {
                'hours': (9, 18),
                'model': 'gpt-4o-mini',
                'priority_accounts': True
            },
            'night': {
                'hours': (19, 8),
                'model': 'ollama_local',
                'batch_processing': True
            }
        }
    
    def get_optimal_model(self, urgency='normal', account_priority='normal'):
        current_hour = datetime.now().hour
        
        if account_priority == 'high' or urgency == 'urgent':
            return self.get_premium_model()
        
        if 9 <= current_hour <= 18:
            return self.get_day_model()
        else:
            return self.get_night_model()
```

### 비용 예산 분석

| 모듈 | 월 예상 비용 | 최적화 방안 |
|------|--------------|-------------|
| 상품명 생성 | $150-300 | 야간 로컬 모델 활용 |
| 이미지 처리 | $50-100 | 배치 처리 최적화 |
| 상세페이지 분석 | $100-200 | 캐싱 및 패턴 재사용 |
| 총합 | $300-600 | 하이브리드 전략으로 50% 절약 |

## 6. 야간 처리 최적화

### 배치 처리 시스템
```python
class NightBatchProcessor:
    def __init__(self):
        self.queue = RedisQueue('night_processing')
        self.local_models = self.load_local_models()
        
    def process_night_batch(self):
        """야간 배치 처리"""
        
        # 낮에 수집된 작업들 가져오기
        pending_jobs = self.queue.get_all_pending()
        
        # 우선순위별 정렬
        sorted_jobs = self.prioritize_jobs(pending_jobs)
        
        # 로컬 모델로 처리
        for job in sorted_jobs:
            result = self.process_with_local_model(job)
            self.store_result(result)
```

## 7. 법적/윤리적 고려사항

### 컴플라이언스 체크리스트
- [ ] 저작권 침해 방지 (이미지 변형 필수)
- [ ] 상표권 존중 (브랜드명 적절 사용)
- [ ] 소비자 기만 방지 (정확한 상품 정보)
- [ ] 개인정보 보호 (스크래핑 데이터 관리)
- [ ] 플랫폼 약관 준수 (각 마켓 정책)

### 리스크 관리
```python
class ComplianceChecker:
    def __init__(self):
        self.prohibited_keywords = self.load_prohibited_words()
        self.brand_whitelist = self.load_allowed_brands()
        
    def check_compliance(self, product_data):
        """컴플라이언스 검증"""
        
        checks = {
            'trademark_safe': self.check_trademark_safety(product_data),
            'description_accurate': self.verify_description_accuracy(product_data),
            'image_legal': self.check_image_legality(product_data),
            'platform_compliant': self.check_platform_rules(product_data)
        }
        
        return all(checks.values()), checks
```

## 8. 구현 우선순위

### Phase 1 (즉시 구현) - 4주
1. 기본 상품명 생성기
2. 단순 이미지 리사이징
3. PostgreSQL 기본 스키마
4. 쿠팡 마켓 우선 지원

### Phase 2 (1-2개월) - 8주
1. AI 기반 이미지 최적화
2. 네이버, 11번가 지원 확장
3. 야간 배치 처리 시스템
4. 성과 분석 대시보드

### Phase 3 (3개월) - 12주
1. 상세페이지 AI 분석
2. 용도 변경 추천 시스템
3. 고급 패턴 학습
4. 완전 자동화

## 9. 예상 ROI 분석

### 효과 지표
- 상품명 최적화: 클릭률 20-40% 증가
- 이미지 최적화: 전환율 15-25% 증가
- 자동화 효과: 처리 시간 80% 단축
- 비용 절약: AI 비용 50% 절감

### 투자 회수 예상
- 개발 비용: $10,000-15,000
- 월 운영 비용: $300-600
- 예상 매출 증가: 월 $5,000-10,000
- ROI: 3-6개월 내 회수

이 설계안은 확장 가능하고 비용 효율적인 드랍쉬핑 상품가공 시스템의 청사진을 제공합니다. 각 단계별로 점진적 구현이 가능하며, 시장 상황에 따른 유연한 조정이 가능합니다.