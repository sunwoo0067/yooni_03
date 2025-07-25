# 멀티 플랫폼 API 연동 가이드

이 문서는 온라인 셀러를 위한 멀티 플랫폼 API 연동 모듈의 사용 방법을 설명합니다.

## 목차
1. [개요](#개요)
2. [플랫폼 계정 설정](#플랫폼-계정-설정)
3. [상품 동기화](#상품-동기화)
4. [주문 처리](#주문-처리)
5. [재고 관리](#재고-관리)
6. [자동 동기화 설정](#자동-동기화-설정)
7. [웹훅 처리](#웹훅-처리)
8. [에러 처리](#에러-처리)

## 개요

이 시스템은 쿠팡, 네이버 스마트스토어, 11번가의 API를 통합하여 다음 기능을 제공합니다:

- **통합 상품 관리**: 한 번의 등록으로 모든 플랫폼에 상품 등록
- **실시간 주문 처리**: 모든 플랫폼의 주문을 통합 관리
- **자동 재고 동기화**: 재고 수준을 모든 플랫폼에서 동일하게 유지
- **자동화된 워크플로우**: 주문 확인, 배송 처리, 재고 업데이트 자동화

## 플랫폼 계정 설정

### 1. 쿠팡 파트너스 계정 추가

```bash
POST /api/v1/platform-accounts
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "platform": "coupang",
  "name": "내 쿠팡 스토어",
  "credentials": {
    "access_key": "your_coupang_access_key",
    "secret_key": "your_coupang_secret_key",
    "vendor_id": "A00000000"
  }
}
```

### 2. 네이버 스마트스토어 계정 추가

```bash
POST /api/v1/platform-accounts
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "platform": "naver",
  "name": "내 스마트스토어",
  "credentials": {
    "client_id": "your_naver_client_id",
    "client_secret": "your_naver_client_secret",
    "refresh_token": "your_refresh_token"
  }
}
```

### 3. 11번가 계정 추가

```bash
POST /api/v1/platform-accounts
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "platform": "eleventh_street",
  "name": "내 11번가 스토어",
  "credentials": {
    "api_key": "your_11st_api_key",
    "seller_id": "your_seller_id"
  }
}
```

### 4. 연결 테스트

```bash
POST /api/v1/sync/platforms/{platform}/test
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "platform": "coupang",
  "account_id": 1
}
```

## 상품 동기화

### 1. 통합 상품 등록 후 플랫폼 동기화

```bash
# 1단계: 통합 상품 등록
POST /api/v1/products
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "name": "프리미엄 무선 이어폰",
  "description": "최신 노이즈 캔슬링 기능이 탑재된 프리미엄 무선 이어폰",
  "price": 149000,
  "stock_quantity": 100,
  "category_id": "electronics_audio",
  "brand": "TechBrand",
  "weight": 250,
  "main_image": "https://example.com/images/earphone-main.jpg",
  "additional_images": [
    "https://example.com/images/earphone-1.jpg",
    "https://example.com/images/earphone-2.jpg"
  ],
  "delivery_type": "DELIVERY",
  "delivery_fee": 3000
}

# 2단계: 모든 플랫폼에 동기화
POST /api/v1/sync/products
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "product_ids": [1]  // 방금 생성한 상품 ID
}
```

### 2. 플랫폼 상품을 로컬로 가져오기

```bash
POST /api/v1/sync/products
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "platform_account_ids": [1, 2, 3]  // 동기화할 플랫폼 계정 ID들
}
```

### 3. 대량 상품 동기화

```bash
# 모든 상품을 모든 플랫폼에 동기화
POST /api/v1/sync/products
Authorization: Bearer {your_token}
```

## 주문 처리

### 1. 주문 동기화

```bash
# 최근 7일간의 주문 가져오기
POST /api/v1/sync/orders
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-07T23:59:59"
}
```

### 2. 주문 상태 업데이트

```python
# Python 예제: 주문 배송 처리
import httpx
from datetime import datetime

async def ship_order(order_id: int, tracking_info: dict):
    async with httpx.AsyncClient() as client:
        # 1. 로컬 주문 상태 업데이트
        response = await client.put(
            f"https://api.example.com/api/v1/orders/{order_id}/status",
            json={
                "status": "shipped",
                "shipping_info": tracking_info
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 2. 플랫폼에도 자동으로 업데이트됨
        return response.json()

# 사용 예
tracking_info = {
    "deliveryCompanyCode": "KOREX",  # 택배사 코드
    "trackingNumber": "1234567890",   # 운송장 번호
    "sendDate": datetime.now().isoformat()
}

await ship_order(123, tracking_info)
```

### 3. 주문 일괄 처리

```bash
# 여러 주문 한번에 확인
POST /api/v1/orders/batch-confirm
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "order_ids": [123, 124, 125],
  "ship_date": "2024-01-08"
}
```

## 재고 관리

### 1. 실시간 재고 동기화

```bash
# 모든 상품의 재고를 플랫폼 간 동기화
POST /api/v1/sync/inventory
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "auto_disable_out_of_stock": true  // 품절 상품 자동 비활성화
}
```

### 2. 특정 상품 재고 업데이트

```python
# Python 예제: 재고 수동 조정
async def adjust_inventory(product_id: int, new_quantity: int):
    async with httpx.AsyncClient() as client:
        # 1. 로컬 재고 업데이트
        response = await client.put(
            f"https://api.example.com/api/v1/products/{product_id}",
            json={"stock_quantity": new_quantity},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 2. 모든 플랫폼에 동기화
        sync_response = await client.post(
            "https://api.example.com/api/v1/sync/inventory",
            json={"product_ids": [product_id]},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        return sync_response.json()
```

### 3. 재고 부족 알림 확인

```bash
GET /api/v1/inventory/low-stock
Authorization: Bearer {your_token}

# 응답 예시
{
  "low_stock_products": [
    {
      "product_id": 1,
      "product_name": "프리미엄 무선 이어폰",
      "current_stock": 3,
      "safety_stock": 5,
      "stock_status": "low_stock"
    }
  ]
}
```

## 자동 동기화 설정

### 1. 주기적 동기화 스케줄 설정

```bash
POST /api/v1/sync/schedule
Content-Type: application/json
Authorization: Bearer {your_token}

{
  "interval_minutes": 30,  // 30분마다 동기화
  "sync_types": ["orders", "inventory"],  // 주문과 재고만 동기화
  "active_hours": {
    "start": 9,   // 오전 9시부터
    "end": 18     // 오후 6시까지만 동기화
  }
}
```

### 2. 전체 동기화 실행

```bash
# 모든 데이터 동기화 (상품, 주문, 재고)
POST /api/v1/sync/all
Authorization: Bearer {your_token}
```

## 웹훅 처리

### 1. 웹훅 엔드포인트 설정

각 플랫폼에서 다음 URL로 웹훅을 설정하세요:

```
POST https://your-domain.com/api/v1/sync/webhook
```

### 2. 웹훅 예제 (쿠팡 주문)

```json
{
  "platform": "coupang",
  "event_type": "order.created",
  "data": {
    "orderId": "5000000123",
    "orderedAt": "2024-01-08T10:30:00Z",
    "orderItems": [
      {
        "vendorItemId": "70000123",
        "vendorItemName": "프리미엄 무선 이어폰",
        "shippingCount": 1,
        "orderPrice": 149000
      }
    ]
  }
}
```

## 에러 처리

### 1. 동기화 로그 확인

```bash
GET /api/v1/sync/logs?start_date=2024-01-01&platform=coupang
Authorization: Bearer {your_token}
```

### 2. 실패한 동기화 재시도

```python
# Python 예제: 실패한 동기화 자동 재시도
async def retry_failed_syncs():
    async with httpx.AsyncClient() as client:
        # 1. 실패한 동기화 목록 가져오기
        logs = await client.get(
            "https://api.example.com/api/v1/sync/logs",
            params={"status": "failed", "limit": 50},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        failed_syncs = logs.json()["logs"]
        
        # 2. 각 실패한 동기화 재시도
        for sync in failed_syncs:
            if sync["sync_type"] == "products":
                await client.post(
                    "https://api.example.com/api/v1/sync/products",
                    json={"product_ids": sync["product_ids"]},
                    headers={"Authorization": f"Bearer {token}"}
                )
```

## 실제 업무 시나리오

### 시나리오 1: 신규 상품 출시

```python
async def launch_new_product(product_data: dict):
    """신규 상품을 모든 플랫폼에 출시"""
    
    # 1. 통합 상품 등록
    product = await create_product(product_data)
    
    # 2. 모든 플랫폼에 동기화
    sync_result = await sync_to_platforms(product.id)
    
    # 3. 초기 재고 설정
    await set_initial_inventory(product.id, product_data["initial_stock"])
    
    # 4. 가격 정책 적용 (플랫폼별 수수료 고려)
    await apply_pricing_strategy(product.id)
    
    return {
        "product_id": product.id,
        "platform_results": sync_result
    }
```

### 시나리오 2: 대량 주문 처리

```python
async def process_bulk_orders():
    """오전에 들어온 모든 주문 일괄 처리"""
    
    # 1. 새 주문 동기화
    orders = await sync_morning_orders()
    
    # 2. 재고 확인 및 할당
    for order in orders:
        await allocate_inventory(order)
    
    # 3. 송장 일괄 생성
    shipping_labels = await generate_shipping_labels(orders)
    
    # 4. 플랫폼에 배송 정보 업데이트
    await update_shipping_info(orders, shipping_labels)
    
    return {
        "processed_orders": len(orders),
        "total_value": sum(o.total for o in orders)
    }
```

### 시나리오 3: 품절 임박 상품 관리

```python
async def manage_low_stock():
    """품절 임박 상품 자동 관리"""
    
    # 1. 재고 부족 상품 확인
    low_stock = await check_low_stock_products()
    
    for product in low_stock:
        if product.stock <= 0:
            # 2. 품절 상품은 모든 플랫폼에서 판매 중지
            await disable_on_all_platforms(product.id)
        elif product.stock <= product.safety_stock:
            # 3. 재고 부족 상품은 알림 전송
            await send_restock_alert(product)
            
            # 4. 선택적: 가격 인상으로 판매 속도 조절
            if product.high_demand:
                await increase_price(product.id, percent=10)
```

## 모니터링 및 분석

### 1. 동기화 상태 대시보드

```bash
GET /api/v1/sync/status
Authorization: Bearer {your_token}

# 응답: 현재 진행중인 동기화와 최근 기록
```

### 2. 플랫폼별 성과 분석

```python
async def analyze_platform_performance():
    """플랫폼별 판매 성과 분석"""
    
    analytics = await get_platform_analytics()
    
    return {
        "coupang": {
            "orders": analytics.coupang_orders,
            "revenue": analytics.coupang_revenue,
            "best_sellers": analytics.coupang_top_products
        },
        "naver": {
            "orders": analytics.naver_orders,
            "revenue": analytics.naver_revenue,
            "best_sellers": analytics.naver_top_products
        },
        "11st": {
            "orders": analytics.eleventh_orders,
            "revenue": analytics.eleventh_revenue,
            "best_sellers": analytics.eleventh_top_products
        }
    }
```

## 보안 고려사항

1. **API 키 관리**: 모든 API 키는 암호화되어 저장됩니다
2. **접근 제어**: 각 사용자는 자신의 플랫폼 계정만 관리할 수 있습니다
3. **속도 제한**: 각 플랫폼의 API 제한을 준수합니다
4. **감사 로그**: 모든 동기화 작업은 로그로 기록됩니다

## 문제 해결

### 자주 발생하는 문제

1. **동기화 실패**
   - 플랫폼 API 키 확인
   - 네트워크 연결 확인
   - API 속도 제한 확인

2. **재고 불일치**
   - 수동 재고 동기화 실행
   - 플랫폼별 재고 확인
   - 동기화 로그 검토

3. **주문 누락**
   - 웹훅 설정 확인
   - 주문 기간 재동기화
   - 플랫폼 API 상태 확인