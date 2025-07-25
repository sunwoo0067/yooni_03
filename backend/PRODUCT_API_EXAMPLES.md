# 통합 상품 관리 API 사용 예시

온라인 셀러를 위한 통합 상품 관리 API의 실제 사용 예시들입니다.

## 목차
1. [기본 상품 관리](#기본-상품-관리)
2. [플랫폼별 상품 등록](#플랫폼별-상품-등록)
3. [일괄 상품 관리](#일괄-상품-관리)
4. [재고 관리](#재고-관리)
5. [가격 관리](#가격-관리)
6. [카테고리 관리](#카테고리-관리)
7. [이미지 관리](#이미지-관리)
8. [CSV 임포트/익스포트](#csv-임포트익스포트)
9. [AI 최적화](#ai-최적화)

## 기본 상품 관리

### 1. 상품 생성
```http
POST /api/v1/products/
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "sku": "SAMSUNG-PHONE-001",
  "name": "삼성 갤럭시 S24 Ultra 256GB",
  "description": "최신 삼성 플래그십 스마트폰. 200MP 카메라, S펜 내장, 6.8인치 Dynamic AMOLED 디스플레이",
  "brand": "Samsung",
  "category_path": "electronics > smartphones",
  "cost_price": 800000.00,
  "wholesale_price": 900000.00,
  "retail_price": 1200000.00,
  "sale_price": 1100000.00,
  "stock_quantity": 50,
  "min_stock_level": 10,
  "weight": 0.234,
  "dimensions": {
    "length": 16.3,
    "width": 7.9,
    "height": 0.89
  },
  "tags": ["스마트폰", "갤럭시", "S24", "플래그십"],
  "keywords": ["갤럭시", "스마트폰", "삼성", "S24", "울트라"],
  "main_image_url": "https://example.com/images/galaxy-s24-ultra-main.jpg",
  "image_urls": [
    "https://example.com/images/galaxy-s24-ultra-1.jpg",
    "https://example.com/images/galaxy-s24-ultra-2.jpg"
  ],
  "attributes": {
    "color": "티타늄 블랙",
    "storage": "256GB",
    "display_size": "6.8인치",
    "camera": "200MP"
  }
}
```

### 2. 상품 조회 (필터링)
```http
GET /api/v1/products/?search=갤럭시&brand=Samsung&min_price=500000&max_price=1500000&page=1&size=20
Authorization: Bearer your_token_here
```

### 3. 특정 상품 조회
```http
GET /api/v1/products/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer your_token_here
```

### 4. 상품 수정
```http
PUT /api/v1/products/123e4567-e89b-12d3-a456-426614174000
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "sale_price": 1050000.00,
  "stock_quantity": 30,
  "description": "최신 삼성 플래그십 스마트폰. 200MP 카메라, S펜 내장, 6.8인치 Dynamic AMOLED 디스플레이. 특가 진행중!"
}
```

## 플랫폼별 상품 등록

### 1. 여러 플랫폼에 동시 등록
```http
POST /api/v1/products/123e4567-e89b-12d3-a456-426614174000/platforms
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "platform_account_ids": [
    "coupang-account-id",
    "naver-account-id",
    "gmarket-account-id"
  ],
  "force_update": false,
  "custom_settings": {
    "coupang-account-id": {
      "custom_title": "삼성 갤럭시 S24 Ultra 256GB 공식판매점",
      "custom_description": "쿠팡 전용 상세 설명...",
      "platform_category_id": "196176",
      "additional_settings": {
        "delivery_type": "rocket_delivery",
        "return_policy": "30일 무료반품"
      }
    }
  }
}
```

### 2. 플랫폼별 등록 상태 조회
```http
GET /api/v1/products/123e4567-e89b-12d3-a456-426614174000/platforms
Authorization: Bearer your_token_here
```

## 일괄 상품 관리

### 1. 일괄 상품 생성
```http
POST /api/v1/products/bulk
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "products": [
    {
      "sku": "APPLE-IPHONE-001",
      "name": "아이폰 15 Pro 128GB",
      "description": "애플의 최신 프로 모델",
      "brand": "Apple",
      "category_path": "electronics > smartphones",
      "cost_price": 900000.00,
      "sale_price": 1200000.00,
      "stock_quantity": 25
    },
    {
      "sku": "APPLE-IPHONE-002", 
      "name": "아이폰 15 Pro Max 256GB",
      "description": "애플의 최대 화면 프로 모델",
      "brand": "Apple",
      "category_path": "electronics > smartphones",
      "cost_price": 1100000.00,
      "sale_price": 1400000.00,
      "stock_quantity": 20
    }
  ],
  "default_platform_account_id": "default-platform-id",
  "default_attributes": {
    "warranty": "1년 무상 A/S",
    "origin_country": "중국"
  }
}
```

### 2. 일괄 상품 수정
```http
PUT /api/v1/products/bulk
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "product_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "987fcdeb-51a2-43d1-9c4f-123456789abc"
  ],
  "update_data": {
    "is_featured": true,
    "tags": ["특가", "인기상품", "추천"]
  }
}
```

## 재고 관리

### 1. 재고 업데이트
```http
PUT /api/v1/products/123e4567-e89b-12d3-a456-426614174000/stock?operation=subtract&quantity_change=5&reason=판매로%20인한%20재고%20차감
Authorization: Bearer your_token_here
```

### 2. 부족 재고 상품 조회
```http
GET /api/v1/products/analytics/low-stock?limit=50
Authorization: Bearer your_token_here
```

## 가격 관리

### 1. 동적 가격 계산
```http
POST /api/v1/products/123e4567-e89b-12d3-a456-426614174000/pricing/calculate
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "competitor_average_price": 1080000,
  "market_average_price": 1120000,
  "demand_score": 8.5
}
```

## 카테고리 관리

### 1. 카테고리 목록 조회
```http
GET /api/v1/products/categories?tree=true
Authorization: Bearer your_token_here
```

### 2. 새 카테고리 생성
```http
POST /api/v1/products/categories
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "name": "게이밍 액세서리",
  "slug": "gaming-accessories",
  "description": "게이밍을 위한 모든 액세서리",
  "parent_id": "electronics-category-id",
  "sort_order": 10
}
```

## 이미지 관리

### 1. 상품 이미지 업로드
```http
POST /api/v1/products/123e4567-e89b-12d3-a456-426614174000/images
Content-Type: multipart/form-data
Authorization: Bearer your_token_here

images=@main_image.jpg
images=@detail_1.jpg  
images=@detail_2.jpg
is_main=true
```

## CSV 임포트/익스포트

### 1. CSV 파일로 상품 임포트
```http
POST /api/v1/products/import
Content-Type: multipart/form-data
Authorization: Bearer your_token_here

file=@products.csv
platform_account_id=your-platform-id
update_existing=true
validate_only=false
```

**CSV 파일 형식 예시:**
```csv
sku,name,description,brand,category_path,cost_price,sale_price,stock_quantity,weight,tags,main_image_url
NIKE-SHOES-001,나이키 에어맥스,편안한 운동화,Nike,fashion > shoes,80000,120000,100,0.5,운동화|나이키|에어맥스,https://example.com/nike1.jpg
ADIDAS-SHOES-001,아디다스 스탠스미스,클래식 스니커즈,Adidas,fashion > shoes,70000,110000,80,0.4,스니커즈|아디다스|클래식,https://example.com/adidas1.jpg
```

### 2. 상품을 CSV로 익스포트
```http
GET /api/v1/products/export/csv?category_path=electronics&status=active
Authorization: Bearer your_token_here
```

## AI 최적화

### 1. 상품 정보 AI 최적화
```http
POST /api/v1/products/optimize
Content-Type: application/json
Authorization: Bearer your_token_here

{
  "product_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "987fcdeb-51a2-43d1-9c4f-123456789abc"
  ],
  "optimization_type": "all",
  "target_platforms": ["coupang", "naver"],
  "custom_instructions": "한국 고객을 대상으로 감성적인 표현 사용"
}
```

## 실제 업무 시나리오

### 시나리오 1: 새 상품 런칭
1. **상품 기본 정보 등록**
```http
POST /api/v1/products/
# 기본 상품 정보 등록
```

2. **이미지 업로드**
```http  
POST /api/v1/products/{product_id}/images
# 상품 이미지들 업로드
```

3. **AI 최적화**
```http
POST /api/v1/products/optimize
# 상품명, 설명, 키워드 최적화
```

4. **플랫폼별 등록**
```http
POST /api/v1/products/{product_id}/platforms
# 쿠팡, 네이버, 11번가 동시 등록
```

### 시나리오 2: 재고 관리
1. **부족 재고 확인**
```http
GET /api/v1/products/analytics/low-stock
```

2. **재고 보충**
```http
PUT /api/v1/products/{product_id}/stock?operation=add
```

3. **가격 재계산**
```http
POST /api/v1/products/{product_id}/pricing/calculate
```

### 시나리오 3: 대량 상품 관리
1. **CSV로 상품 일괄 등록**
```http
POST /api/v1/products/import
```

2. **카테고리별 일괄 수정**
```http
PUT /api/v1/products/bulk
```

3. **성과 분석**
```http
GET /api/v1/products/analytics/performance
```

## 에러 처리 예시

### 400 Bad Request
```json
{
  "detail": "Validation errors: ['SKU already exists', 'Sale price cannot be less than cost price']"
}
```

### 404 Not Found
```json
{
  "detail": "Product not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error: Database connection failed"
}
```

## 응답 예시

### 성공적인 상품 생성 응답
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "sku": "SAMSUNG-PHONE-001",
  "name": "삼성 갤럭시 S24 Ultra 256GB", 
  "description": "최신 삼성 플래그십 스마트폰...",
  "brand": "Samsung",
  "category_path": "electronics > smartphones",
  "cost_price": 800000.00,
  "sale_price": 1100000.00,
  "stock_quantity": 50,
  "available_quantity": 50,
  "is_low_stock": false,
  "gross_margin": 27.27,
  "status": "active",
  "created_at": "2024-07-24T10:30:00Z",
  "updated_at": "2024-07-24T10:30:00Z"
}
```

### 상품 목록 조회 응답
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "sku": "SAMSUNG-PHONE-001",
      "name": "삼성 갤럭시 S24 Ultra 256GB",
      "sale_price": 1100000.00,
      "stock_quantity": 50,
      "status": "active"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

이 API를 사용하여 온라인 셀러는 효율적으로 다중 플랫폼 상품을 관리할 수 있습니다.