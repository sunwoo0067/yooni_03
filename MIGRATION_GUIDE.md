# 🚀 V2 마이그레이션 가이드

이 문서는 기존 코드를 안전하게 V2 패턴으로 마이그레이션하는 방법을 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [준비 사항](#준비-사항)
3. [단계별 마이그레이션](#단계별-마이그레이션)
4. [서비스별 가이드](#서비스별-가이드)
5. [테스트 전략](#테스트-전략)
6. [롤백 계획](#롤백-계획)
7. [체크리스트](#체크리스트)

## 🎯 개요

### V2 패턴의 주요 개선사항

1. **표준화된 에러 처리**
2. **구조화된 로깅**
3. **향상된 캐싱 전략**
4. **비동기 데이터베이스 작업**
5. **통합 모니터링**

### 마이그레이션 원칙

- ✅ **점진적 전환**: 한 번에 하나씩
- ✅ **하위 호환성**: 기존 코드와 공존
- ✅ **테스트 우선**: 변경 전 테스트 작성
- ✅ **모니터링**: 변경 후 메트릭 확인

## 🛠️ 준비 사항

### 1. 환경 설정

```bash
# .env.development에 추가
USE_V2_SERVICES=false  # 처음에는 false로 시작
ENABLE_MONITORING=true
ENABLE_STRUCTURED_LOGGING=true
```

### 2. 의존성 설치

```bash
# 새로운 의존성 설치
pip install aiosqlite  # 비동기 SQLite
pip install psutil     # 시스템 모니터링
pip install fakeredis  # 테스트용 Redis
```

### 3. 테스트 환경 준비

```bash
# 테스트 실행 확인
pytest tests/test_services/test_product_service_v2.py -v
```

## 📝 단계별 마이그레이션

### 1단계: 기본 유틸리티 적용

#### 1.1 상수 사용

```python
# 기존 코드
status = "active"
margin_rate = Decimal("10.0")

# V2 패턴
from app.core.constants import ProductStatus, MarginRates
status = ProductStatus.ACTIVE.value
margin_rate = MarginRates.DEFAULT
```

#### 1.2 로깅 개선

```python
# 기존 코드
logger.info(f"Order created: {order_id}")

# V2 패턴
from app.core.logging_utils import get_logger
logger = get_logger("OrderService")
logger.info("Order created", order_id=order_id, user_id=user_id)
```

#### 1.3 에러 처리

```python
# 기존 코드
if not product:
    raise HTTPException(status_code=404, detail="Product not found")

# V2 패턴
from app.core.exceptions import NotFoundError
if not product:
    raise NotFoundError("Product", product_id)
```

### 2단계: 서비스 마이그레이션

#### 2.1 서비스 클래스 생성

```python
# 새 파일: app/services/order/order_service_v2.py
from app.services.base_service import BaseService

class OrderServiceV2(BaseService):
    def __init__(self, db):
        super().__init__(db, Order)
        # V2 초기화 로직
```

#### 2.2 점진적 전환

```python
# app/services/order/__init__.py
from app.core.config import settings

if settings.USE_V2_SERVICES:
    from .order_service_v2 import OrderServiceV2 as OrderService
else:
    from .order_service import OrderService

__all__ = ["OrderService"]
```

### 3단계: API 엔드포인트 업데이트

#### 3.1 입력 검증 추가

```python
# 기존 코드
@router.post("/orders")
async def create_order(order_data: dict):
    # 검증 없음
    
# V2 패턴
from app.core.validators import OrderCreateValidator

@router.post("/orders")
async def create_order(order_data: OrderCreateValidator):
    # Pydantic이 자동 검증
```

#### 3.2 응답 모델 정의

```python
from pydantic import BaseModel

class OrderResponse(BaseModel):
    id: str
    status: str
    total_amount: float
    
    class Config:
        orm_mode = True

@router.post("/orders", response_model=OrderResponse)
```

### 4단계: 비동기 작업 전환

#### 4.1 Repository 패턴 적용

```python
# 새 파일: app/repositories/product_repository.py
from app.core.async_database_utils import AsyncRepository

class ProductRepository(AsyncRepository[Product]):
    async def find_by_sku(self, sku: str):
        # 커스텀 쿼리 메서드
```

#### 4.2 비동기 서비스 메서드

```python
# 동기 -> 비동기 전환
async def get_product(self, product_id: str):
    return await self.repository.get_or_404(product_id)
```

## 🔧 서비스별 가이드

### OrderProcessor 마이그레이션

```python
# 1. 새 버전 생성
from app.services.order_processing.order_processor_v2 import OrderProcessorV2

# 2. 팩토리 함수 사용
def get_order_processor(db, use_v2=False):
    if use_v2:
        return OrderProcessorV2(db)
    return OrderProcessor(db)

# 3. 점진적 전환
processor = get_order_processor(db, use_v2=settings.USE_V2_SERVICES)
```

### ProductService 마이그레이션

```python
# 1. 캐시 서비스 추가
from app.core.cache_utils import CacheService

cache_service = CacheService(cache_manager, "product")

# 2. V2 서비스 초기화
product_service = ProductServiceV2(db, cache_service)

# 3. 캐싱 활용
product = await product_service.get_product_detail(
    product_id, 
    use_cache=True
)
```

### AI Service 마이그레이션

```python
# 1. 프로바이더 설정
providers = [
    GeminiProvider(api_key),
    OllamaProvider(base_url)
]

# 2. 폴백 지원 서비스
ai_service = AIServiceV2(providers, cache_service)

# 3. 자동 폴백
result = await ai_service.generate_text(prompt)
```

## 🧪 테스트 전략

### 1. 병렬 테스트

```python
# tests/test_services/test_order_comparison.py
@pytest.mark.asyncio
async def test_v1_v2_compatibility():
    # V1 결과
    v1_result = OrderProcessor(db).process_order(order_data)
    
    # V2 결과
    v2_result = await OrderProcessorV2(db).process_order(order_data)
    
    # 동일성 검증
    assert v1_result.total == v2_result.total
```

### 2. 성능 비교

```python
@pytest.mark.benchmark
async def test_performance_improvement():
    # V1 성능
    v1_time = measure_time(lambda: service_v1.process_batch(items))
    
    # V2 성능
    v2_time = measure_time(lambda: await service_v2.process_batch(items))
    
    # V2가 더 빠른지 확인
    assert v2_time < v1_time * 0.8  # 20% 개선 기대
```

### 3. 부하 테스트

```bash
# locust를 사용한 부하 테스트
locust -f tests/load/test_v2_endpoints.py --host=http://localhost:8000
```

## 🔄 롤백 계획

### 1. Feature Flag 사용

```python
# app/core/feature_flags.py
class FeatureFlags:
    USE_V2_ORDER_SERVICE = os.getenv("USE_V2_ORDER_SERVICE", "false") == "true"
    USE_V2_PRODUCT_SERVICE = os.getenv("USE_V2_PRODUCT_SERVICE", "false") == "true"
```

### 2. 빠른 롤백

```bash
# 환경 변수로 즉시 롤백
export USE_V2_SERVICES=false
# 서비스 재시작
```

### 3. 데이터베이스 호환성

```sql
-- V2에서 추가된 컬럼은 nullable로
ALTER TABLE orders ADD COLUMN v2_metadata JSONB NULL;

-- 롤백 시에도 문제 없음
```

## ✅ 체크리스트

### 마이그레이션 전

- [ ] 현재 서비스의 테스트 커버리지 확인
- [ ] 성능 메트릭 기록
- [ ] 백업 수행
- [ ] 롤백 계획 검토

### 마이그레이션 중

- [ ] 개발 환경에서 테스트
- [ ] 스테이징 환경에서 검증
- [ ] 모니터링 대시보드 준비
- [ ] 팀원 교육

### 마이그레이션 후

- [ ] 성능 메트릭 비교
- [ ] 에러율 모니터링
- [ ] 사용자 피드백 수집
- [ ] 문서 업데이트

## 📊 모니터링 지표

### 확인해야 할 메트릭

1. **응답 시간**
   ```
   http.request.duration (p50, p90, p99)
   ```

2. **에러율**
   ```
   http.request.error / http.request.count
   ```

3. **캐시 히트율**
   ```
   cache.hit / (cache.hit + cache.miss)
   ```

4. **데이터베이스 성능**
   ```
   db.query.duration by operation
   ```

### 알림 설정

```python
# 응답 시간 증가 알림
monitoring_service.alert_manager.add_rule(
    name="Slow Response After Migration",
    metric_name="http.request.duration",
    condition="gt",
    threshold=500.0,  # 500ms
    duration=300  # 5분
)
```

## 🎉 마이그레이션 완료

모든 서비스가 V2로 전환되면:

1. **정리 작업**
   ```bash
   # 이전 버전 코드 제거
   rm app/services/*/[!_v2].py
   
   # V2 suffix 제거
   mv order_service_v2.py order_service.py
   ```

2. **설정 단순화**
   ```python
   # USE_V2_SERVICES 제거
   # 모든 서비스가 V2 사용
   ```

3. **문서 업데이트**
   - README.md 업데이트
   - API 문서 재생성
   - 팀 위키 업데이트

## 💡 팁과 트릭

### 1. 단계적 캐싱 적용

```python
# 처음에는 읽기만
if cache_service:
    cached = await cache_service.get(key)
    if cached:
        return cached

# 나중에 쓰기 추가
result = await expensive_operation()
if cache_service:
    await cache_service.set(key, result)
```

### 2. 로깅 마이그레이션

```python
# 임시 래퍼 함수
def log_info(message, **kwargs):
    if hasattr(logger, 'info'):
        # V2 구조화된 로깅
        logger.info(message, **kwargs)
    else:
        # 기존 로깅
        logger.info(f"{message} {kwargs}")
```

### 3. 점진적 비동기 전환

```python
# 동기 래퍼로 시작
def sync_wrapper(async_func):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(async_func(*args, **kwargs))
    return wrapper

# 나중에 완전 비동기로 전환
```

---

이 가이드를 따라 안전하고 체계적으로 V2 패턴으로 마이그레이션할 수 있습니다! 🚀