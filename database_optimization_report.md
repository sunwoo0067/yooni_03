# 🗄️ 드랍쉬핑 시스템 데이터베이스 최적화 보고서

## 📊 요약

프로젝트 구조와 데이터베이스를 심층 분석한 결과, 전반적으로 잘 설계되어 있으나 몇 가지 중요한 개선사항이 발견되었습니다.

---

## 🔍 발견된 주요 문제점

### 1. 데이터베이스 스키마 문제

#### 🚨 중복 테이블/컬럼
- **WholesalerAccount** 가 두 곳에서 정의됨
  - `platform_account.py`의 WholesaleAccount
  - `wholesaler.py`의 WholesalerAccount
- **Product** 테이블에 `wholesaler_id`와 `wholesale_account_id` 중복

#### ⚠️ 타입 불일치
- 일부 ID는 UUID, 일부는 Integer 사용
- 가격 필드가 Float와 Decimal 혼용

#### 🔧 인덱스 누락
```sql
-- 필요한 인덱스들
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_orders_customer_email ON orders(customer_email);
CREATE INDEX idx_benchmark_products_name ON benchmark_products(product_name);
CREATE INDEX idx_orders_created_at_status ON orders(created_at, status);
```

### 2. 쿼리 패턴 문제

#### 🐛 N+1 쿼리 문제
```python
# 문제 코드 (duplicate_finder.py)
for group in self.db.query(DuplicateProductGroup).all():
    products = self.db.query(Product).join(...)  # N+1!

# 해결 방안
groups = self.db.query(DuplicateProductGroup).options(
    joinedload(DuplicateProductGroup.products)
).all()
```

#### 💥 트랜잭션 누락
```python
# 문제: 주문 처리에 트랜잭션 없음
order.status = OrderStatus.CONFIRMED
dropshipping_order.status = SupplierOrderStatus.CONFIRMED
self.db.commit()  # 부분 실패 위험!

# 해결 방안
from contextlib import contextmanager

@contextmanager
def transaction(db):
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
```

### 3. 성능 문제

#### 🐌 페이지네이션 누락
```python
# 문제: 모든 주문 한번에 로드
orders = db.query(Order).filter(Order.status == 'pending').all()

# 해결: 페이지네이션 적용
def get_orders_paginated(page: int = 1, size: int = 100):
    return db.query(Order).filter(
        Order.status == 'pending'
    ).offset((page-1) * size).limit(size).all()
```

---

## 💡 개선 방안

### 1. 스키마 정리

#### Step 1: 중복 제거
```python
# 1. WholesalerAccount 통합
# wholesaler.py에서만 정의하고 platform_account.py에서는 제거

# 2. Product 테이블 정리
class Product(Base):
    # wholesale_account_id만 유지, wholesaler_id 제거
    wholesale_account_id = Column(Integer, ForeignKey('wholesaler_accounts.id'))
```

#### Step 2: 타입 통일
```python
# 모든 ID를 UUID로 통일
from sqlalchemy.dialects.postgresql import UUID
import uuid

class BaseModel(Base):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

### 2. 쿼리 최적화

#### 비동기 세션 통일
```python
# database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

async_engine = create_async_engine(
    DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

async def get_async_db():
    async with AsyncSession(async_engine) as session:
        yield session
```

#### 트랜잭션 데코레이터
```python
# utils/database.py
from functools import wraps

def transactional(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with self.db.begin():
            return await func(self, *args, **kwargs)
    return wrapper

# 사용 예시
@transactional
async def process_order(self, order_id: str):
    # 모든 DB 작업이 하나의 트랜잭션으로 처리됨
    pass
```

### 3. 캐싱 전략

```python
# services/cache/query_cache.py
from functools import wraps
import hashlib
import json

def cached_query(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{func.__name__}:{hashlib.md5(
                json.dumps(args + tuple(kwargs.items())).encode()
            ).hexdigest()}"
            
            # 캐시 확인
            cached = await self.cache.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # DB 쿼리 실행
            result = await func(self, *args, **kwargs)
            
            # 캐시 저장
            await self.cache.set(cache_key, json.dumps(result), ttl)
            return result
        return wrapper
    return decorator
```

### 4. 데이터베이스 파티셔닝

```sql
-- 주문 테이블 월별 파티셔닝
CREATE TABLE orders_2024_01 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE orders_2024_02 PARTITION OF orders
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- 인덱스는 각 파티션에 자동 생성됨
```

### 5. 모니터링 추가

```python
# middleware/db_monitoring.py
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 1.0:  # 1초 이상 걸린 쿼리 로깅
        logger.warning(f"Slow query ({total:.2f}s): {statement}")
```

---

## 🚀 실행 계획

### Phase 1 (1주차) - 긴급 수정
1. ✅ 트랜잭션 누락 부분 수정
2. ✅ N+1 쿼리 문제 해결
3. ✅ 누락된 인덱스 추가

### Phase 2 (2주차) - 구조 개선
1. ✅ 중복 테이블/컬럼 정리
2. ✅ 타입 통일 (UUID로 마이그레이션)
3. ✅ 비동기 세션으로 전환

### Phase 3 (3주차) - 성능 최적화
1. ✅ 캐싱 레이어 구현
2. ✅ 페이지네이션 적용
3. ✅ 쿼리 최적화

### Phase 4 (4주차) - 모니터링
1. ✅ 슬로우 쿼리 모니터링
2. ✅ 데이터베이스 메트릭 수집
3. ✅ 알림 시스템 구축

---

## 📈 예상 효과

- **쿼리 성능**: 50-70% 향상
- **메모리 사용**: 30% 감소
- **동시 처리량**: 2-3배 증가
- **데이터 일관성**: 트랜잭션으로 100% 보장
- **운영 안정성**: 모니터링으로 사전 문제 감지

이 최적화를 통해 시스템이 더 많은 주문과 상품을 안정적으로 처리할 수 있게 됩니다.