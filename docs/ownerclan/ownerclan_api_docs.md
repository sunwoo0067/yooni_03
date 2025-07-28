# 오너클랜 API 통합 문서

## 목차
1. [개요](#개요)
2. [시작하기](#시작하기)
3. [인증 API](#인증-api)
4. [상품 조회 API](#상품-조회-api)
5. [Python 상품 수집 시스템](#python-상품-수집-시스템)
6. [실습 예제](#실습-예제)
7. [문제 해결](#문제-해결)

---

## 개요

오너클랜 API는 상품 정보를 조회할 수 있는 GraphQL 기반의 RESTful API입니다. JWT 토큰 인증을 사용하며, 단일 상품 조회부터 대용량 상품 수집까지 다양한 기능을 제공합니다.

### 주요 기능
- 단일/복수 상품 정보 조회
- 상품 변경 이력 조회
- 검색 조건별 상품 필터링
- 페이지네이션 지원
- 자동화된 대용량 데이터 수집

### API 환경
| 환경 | 인증 URL | API URL |
|------|----------|---------|
| **Sandbox** | `https://auth-sandbox.ownerclan.com/auth` | `https://api-sandbox.ownerclan.com/v1/graphql` |
| **Production** | `https://auth.ownerclan.com/auth` | `https://api.ownerclan.com/v1/graphql` |

> 💡 **초보자 팁**: 개발 시에는 항상 Sandbox 환경에서 테스트한 후 Production으로 이동하세요.

---

## 시작하기

### 필요한 준비물
1. **오너클랜 판매사 계정** (아이디/비밀번호)
2. **개발 환경** (JavaScript, Python, 또는 기타 언어)
3. **HTTP 클라이언트** (Postman, curl, 또는 코드)

### 기본 API 흐름
```
1. 인증 토큰 발급 → 2. GraphQL API 호출 → 3. 데이터 처리
```

---

## 인증 API

### 토큰 발급하기

#### 요청 방법
```http
POST https://auth-sandbox.ownerclan.com/auth
Content-Type: application/json
```

#### 요청 데이터
```json
{
    "service": "ownerclan",
    "userType": "seller",
    "username": "여기에_판매사ID",
    "password": "여기에_판매사PW"
}
```

#### 성공 응답
```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresIn": 3600,
    "tokenType": "Bearer"
}
```

### JavaScript 구현 예제

#### 기본 인증 함수
```javascript
async function getOwnerClanToken(username, password) {
    try {
        const response = await fetch('https://auth-sandbox.ownerclan.com/auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                service: "ownerclan",
                userType: "seller",
                username: username,
                password: password
            })
        });

        if (!response.ok) {
            throw new Error(`인증 실패: ${response.status}`);
        }

        const data = await response.json();
        return data.token;
    } catch (error) {
        console.error('인증 오류:', error);
        throw error;
    }
}

// 사용 예시
const token = await getOwnerClanToken('your_id', 'your_password');
console.log('토큰 발급 완료:', token);
```

#### 토큰 자동 갱신 클래스
```javascript
class OwnerClanAuth {
    constructor(username, password) {
        this.username = username;
        this.password = password;
        this.token = null;
        this.expiresAt = null;
    }

    async getValidToken() {
        // 토큰이 없거나 만료된 경우 새로 발급
        if (!this.token || Date.now() >= this.expiresAt) {
            await this.authenticate();
        }
        return this.token;
    }

    async authenticate() {
        const response = await fetch('https://auth-sandbox.ownerclan.com/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                service: "ownerclan",
                userType: "seller",
                username: this.username,
                password: this.password
            })
        });

        const data = await response.json();
        this.token = data.token;
        // 만료 5분 전에 갱신하도록 설정
        this.expiresAt = Date.now() + (data.expiresIn - 300) * 1000;
    }
}
```

---

## 상품 조회 API

모든 GraphQL API 요청에는 인증 토큰이 필요합니다:
```http
Authorization: Bearer {발급받은_토큰}
```

### 1. 단일 상품 조회

#### GraphQL 쿼리
```graphql
query GetItem($key: String!, $lang: Language, $currency: Currency) {
    item(key: $key, lang: $lang, currency: $currency) {
        key
        name
        model
        production
        origin
        price
        pricePolicy
        fixedPrice
        category {
            id
            name
            level
        }
        shippingFee
        shippingType
        status
        options {
            id
            price
            quantity
            optionAttributes {
                name
                value
            }
        }
        taxFree
        adultOnly
        returnable
        images
        createdAt
        updatedAt
    }
}
```

#### JavaScript 구현
```javascript
async function getProduct(token, productKey) {
    const query = `
        query GetItem($key: String!) {
            item(key: $key) {
                key
                name
                price
                status
                options {
                    price
                    quantity
                }
            }
        }
    `;

    const response = await fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            query: query,
            variables: { key: productKey }
        })
    });

    const data = await response.json();
    return data.data.item;
}

// 사용 예시
const product = await getProduct(token, "W000000");
console.log('상품 정보:', product);
```

### 2. 복수 상품 조회 (페이지네이션)

#### GraphQL 쿼리
```graphql
query GetAllItems($after: String, $first: Int, $minPrice: Int, $maxPrice: Int, $search: String) {
    allItems(after: $after, first: $first, minPrice: $minPrice, maxPrice: $maxPrice, search: $search) {
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        edges {
            cursor
            node {
                key
                name
                price
                status
                category {
                    name
                }
                options {
                    price
                    quantity
                }
                images
            }
        }
    }
}
```

#### 페이지네이션 구현
```javascript
async function getAllProducts(token, searchOptions = {}) {
    let allProducts = [];
    let hasNextPage = true;
    let cursor = null;

    while (hasNextPage) {
        const variables = {
            first: 100,
            after: cursor,
            ...searchOptions
        };

        const response = await fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                query: getAllItemsQuery,
                variables: variables
            })
        });

        const data = await response.json();
        const result = data.data.allItems;

        // 현재 페이지의 상품들을 배열에 추가
        allProducts.push(...result.edges.map(edge => edge.node));

        // 다음 페이지 정보 업데이트
        hasNextPage = result.pageInfo.hasNextPage;
        cursor = result.pageInfo.endCursor;

        console.log(`현재까지 수집된 상품 수: ${allProducts.length}`);
    }

    return allProducts;
}

// 사용 예시 - 가격 범위로 검색
const products = await getAllProducts(token, {
    minPrice: 10000,
    maxPrice: 100000,
    search: "스마트폰"
});
```

### 3. 특정 상품들 일괄 조회

#### GraphQL 쿼리
```graphql
query GetItems($keys: [String!]!) {
    items(keys: $keys) {
        key
        name
        price
        status
        options {
            price
            quantity
        }
    }
}
```

#### JavaScript 구현
```javascript
async function getMultipleProducts(token, productKeys) {
    // 최대 5000개까지 한 번에 조회 가능
    if (productKeys.length > 5000) {
        throw new Error('한 번에 최대 5000개까지만 조회 가능합니다.');
    }

    const query = `
        query GetItems($keys: [String!]!) {
            items(keys: $keys) {
                key
                name
                price
                status
            }
        }
    `;

    const response = await fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            query: query,
            variables: { keys: productKeys }
        })
    });

    const data = await response.json();
    return data.data.items;
}

// 사용 예시
const productKeys = ["W000000", "W000001", "W000002"];
const products = await getMultipleProducts(token, productKeys);
```

### 4. 상품 변경 이력 조회

#### GraphQL 쿼리
```graphql
query GetItemHistories($after: String, $first: Int, $dateFrom: Int, $kind: ItemHistoryKind, $itemKey: ID) {
    itemHistories(after: $after, first: $first, dateFrom: $dateFrom, kind: $kind, itemKey: $itemKey) {
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        edges {
            cursor
            node {
                id
                timestamp
                kind
                itemKey
                description
                changes {
                    field
                    oldValue
                    newValue
                }
            }
        }
    }
}
```

#### JavaScript 구현
```javascript
async function getProductHistories(token, options = {}) {
    const query = `
        query GetItemHistories($after: String, $first: Int, $dateFrom: Int, $kind: ItemHistoryKind, $itemKey: ID) {
            itemHistories(after: $after, first: $first, dateFrom: $dateFrom, kind: $kind, itemKey: $itemKey) {
                edges {
                    node {
                        timestamp
                        kind
                        itemKey
                        description
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    `;

    const response = await fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            query: query,
            variables: options
        })
    });

    const data = await response.json();
    return data.data.itemHistories;
}

// 사용 예시 - 최근 30일간 품절된 상품들
const thirtyDaysAgo = Math.floor(Date.now() / 1000) - (30 * 24 * 60 * 60);
const histories = await getProductHistories(token, {
    first: 100,
    dateFrom: thirtyDaysAgo,
    kind: "STOCK_OUT"
});
```

---

## Python 상품 수집 시스템

대용량 상품 데이터를 효율적으로 수집하기 위한 Python 시스템입니다.

### 시스템 구조

```
ownerclan_collector/
├── main.py                 # 메인 실행 파일
├── config/
│   ├── settings.py         # 설정 관리
│   └── database.py         # DB 연결 설정
├── collector/
│   ├── auth.py            # 인증 관리
│   ├── api_client.py      # API 클라이언트
│   ├── product_collector.py  # 상품 수집 로직
│   └── cache_manager.py   # 캐시 관리
├── models/
│   ├── product.py         # 상품 모델
│   └── database_models.py # DB 모델
└── requirements.txt
```

### 설치 및 설정

```bash
# 필수 라이브러리 설치
pip install requests aiohttp asyncio python-dotenv sqlalchemy psycopg2-binary

# 환경 변수 설정 (.env 파일)
OWNERCLAN_API_URL=https://api-sandbox.ownerclan.com/v1/graphql
OWNERCLAN_AUTH_URL=https://auth-sandbox.ownerclan.com/auth
OWNERCLAN_USERNAME=your_username
OWNERCLAN_PASSWORD=your_password
DATABASE_URL=postgresql://user:password@localhost:5432/ownerclan_db
```

### 기본 사용법

#### 1. 설정 파일 (config/settings.py)
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API 설정
    API_URL = os.getenv('OWNERCLAN_API_URL')
    AUTH_URL = os.getenv('OWNERCLAN_AUTH_URL')
    USERNAME = os.getenv('OWNERCLAN_USERNAME')
    PASSWORD = os.getenv('OWNERCLAN_PASSWORD')
    
    # 수집 설정
    BATCH_SIZE = 1000           # 1단계 배치 크기
    DETAIL_BATCH_SIZE = 100     # 2단계 배치 크기
    REQUEST_DELAY = 0.1         # API 호출 간격 (초)
    RETRY_COUNT = 3             # 재시도 횟수
    TIMEOUT = 30                # 요청 타임아웃 (초)
    
    # 데이터베이스 설정
    DATABASE_URL = os.getenv('DATABASE_URL')
```

#### 2. 인증 관리자 (collector/auth.py)
```python
import requests
import time
from config.settings import Settings

class AuthManager:
    def __init__(self):
        self.token = None
        self.token_expires_at = None
        self.settings = Settings()
    
    async def get_token(self):
        """JWT 토큰 획득 또는 갱신"""
        if self.token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.token
        
        return await self._authenticate()
    
    async def _authenticate(self):
        """인증 수행"""
        auth_data = {
            "service": "ownerclan",
            "userType": "seller",
            "username": self.settings.USERNAME,
            "password": self.settings.PASSWORD
        }
        
        response = requests.post(self.settings.AUTH_URL, json=auth_data)
        response.raise_for_status()
        
        data = response.json()
        self.token = data['token']
        expires_in = data.get('expiresIn', 3600)
        self.token_expires_at = time.time() + expires_in - 300  # 5분 여유
        
        return self.token
```

#### 3. 메인 수집 스크립트 (main.py)
```python
import asyncio
import time
from collector.product_collector import ProductCollector

async def main():
    """메인 실행 함수"""
    
    # 검색 조건 설정
    search_conditions = {
        'include_all': True,                    # 전체 상품 포함
        'keywords': ['스마트폰', '노트북'],      # 키워드 검색
        'price_ranges': [                       # 가격 범위 검색
            {'min': 0, 'max': 50000},
            {'min': 50000, 'max': 200000}
        ],
        'combined_search': True,                # 조합 검색 활성화
        'date_ranges': [{                       # 날짜 범위 검색
            'from': int(time.time()) - (30 * 24 * 60 * 60),  # 30일 전
            'to': int(time.time())  # 현재
        }]
    }
    
    # 수집기 실행
    collector = ProductCollector()
    
    # 1단계: 상품 코드 수집
    print("1단계: 상품 코드 수집 시작...")
    product_keys = await collector.collect_product_keys(search_conditions)
    print(f"수집된 상품 코드 수: {len(product_keys)}")
    
    # 2단계: 상품 상세 정보 수집
    print("2단계: 상품 상세 정보 수집 시작...")
    
    async def save_callback(products):
        """상품 데이터 저장 콜백"""
        print(f"배치 저장: {len(products)}개 상품")
        # 여기에 데이터베이스 저장 로직 추가
    
    detailed_products = await collector.collect_detailed_products(
        product_keys, 
        save_callback
    )
    
    print(f"수집 완료: 총 {len(detailed_products)}개 상품")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2단계 수집 프로세스

#### 1단계: 상품 코드 수집
- 다양한 검색 조건으로 상품 키 수집
- 메모리 캐시에 중복 제거하여 저장
- 페이지네이션을 통한 전체 데이터 수집

#### 2단계: 상품 상세 정보 수집
- 수집된 상품 키로 상세 정보 조회
- 배치 단위로 처리 (기본 100개씩)
- 데이터베이스에 실시간 저장

---

## 실습 예제

### 예제 1: 기본 상품 조회 시스템

```javascript
class OwnerClanAPI {
    constructor(username, password) {
        this.auth = new OwnerClanAuth(username, password);
        this.apiUrl = 'https://api-sandbox.ownerclan.com/v1/graphql';
    }

    async request(query, variables = {}) {
        const token = await this.auth.getValidToken();
        
        const response = await fetch(this.apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ query, variables })
        });

        const data = await response.json();
        
        if (data.errors) {
            throw new Error(`GraphQL Error: ${data.errors[0].message}`);
        }
        
        return data.data;
    }

    async getProduct(key) {
        const query = `
            query GetItem($key: String!) {
                item(key: $key) {
                    key
                    name
                    price
                    status
                    category { name }
                }
            }
        `;
        
        const result = await this.request(query, { key });
        return result.item;
    }

    async searchProducts(searchTerm, maxPrice = null) {
        const query = `
            query SearchProducts($search: String, $maxPrice: Int, $first: Int) {
                allItems(search: $search, maxPrice: $maxPrice, first: $first) {
                    edges {
                        node {
                            key
                            name
                            price
                            status
                        }
                    }
                }
            }
        `;
        
        const variables = { search: searchTerm, first: 50 };
        if (maxPrice) variables.maxPrice = maxPrice;
        
        const result = await this.request(query, variables);
        return result.allItems.edges.map(edge => edge.node);
    }
}

// 사용 예시
const api = new OwnerClanAPI('your_username', 'your_password');

// 단일 상품 조회
const product = await api.getProduct('W000000');
console.log('상품:', product);

// 상품 검색
const products = await api.searchProducts('아이폰', 1000000);
console.log('검색 결과:', products);
```

### 예제 2: 상품 모니터링 시스템

```javascript
class ProductMonitor {
    constructor(api) {
        this.api = api;
        this.watchList = new Set();
    }

    addToWatchList(productKey) {
        this.watchList.add(productKey);
    }

    async checkPriceChanges() {
        const results = [];
        
        for (const key of this.watchList) {
            try {
                const product = await this.api.getProduct(key);
                
                // 이전 가격과 비교 (실제로는 데이터베이스나 파일에서 읽어옴)
                const previousPrice = this.getPreviousPrice(key);
                
                if (previousPrice && product.price !== previousPrice) {
                    results.push({
                        key: key,
                        name: product.name,
                        previousPrice: previousPrice,
                        currentPrice: product.price,
                        change: product.price - previousPrice
                    });
                }
                
                // 현재 가격 저장
                this.savePreviousPrice(key, product.price);
                
            } catch (error) {
                console.error(`상품 ${key} 조회 실패:`, error);
            }
        }
        
        return results;
    }

    // 데이터 저장/로드 메소드들 (실제 구현 필요)
    getPreviousPrice(key) {
        // localStorage, 데이터베이스, 또는 파일에서 이전 가격 로드
        return parseInt(localStorage.getItem(`price_${key}`)) || null;
    }

    savePreviousPrice(key, price) {
        // 현재 가격을 저장
        localStorage.setItem(`price_${key}`, price.toString());
    }
}

// 사용 예시
const monitor = new ProductMonitor(api);
monitor.addToWatchList('W000000');
monitor.addToWatchList('W000001');

// 주기적으로 가격 변화 확인
setInterval(async () => {
    const changes = await monitor.checkPriceChanges();
    
    if (changes.length > 0) {
        console.log('가격 변화 감지:', changes);
    }
}, 60000); // 1분마다 확인
```

### 예제 3: 재고 알림 시스템

```javascript
class StockAlert {
    constructor(api) {
        this.api = api;
        this.subscribers = new Map(); // productKey -> callback functions
    }

    subscribe(productKey, callback) {
        if (!this.subscribers.has(productKey)) {
            this.subscribers.set(productKey, []);
        }
        this.subscribers.get(productKey).push(callback);
    }

    async checkStock() {
        for (const [productKey, callbacks] of this.subscribers) {
            try {
                const product = await this.api.getProduct(productKey);
                
                // 재고 상태 확인
                const totalStock = product.options?.reduce((sum, option) => {
                    return sum + (option.quantity || 0);
                }, 0) || 0;

                const stockInfo = {
                    key: productKey,
                    name: product.name,
                    status: product.status,
                    totalStock: totalStock,
                    isInStock: totalStock > 0 && product.status === 'ACTIVE'
                };

                // 구독자들에게 알림
                callbacks.forEach(callback => {
                    try {
                        callback(stockInfo);
                    } catch (error) {
                        console.error('콜백 실행 오류:', error);
                    }
                });

            } catch (error) {
                console.error(`재고 확인 실패 ${productKey}:`, error);
            }
        }
    }

    startMonitoring(intervalMinutes = 5) {
        setInterval(() => {
            this.checkStock();
        }, intervalMinutes * 60 * 1000);
        
        console.log(`재고 모니터링 시작 (${intervalMinutes}분 간격)`);
    }
}

// 사용 예시
const stockAlert = new StockAlert(api);

// 재고 부족 알림 구독
stockAlert.subscribe('W000000', (stockInfo) => {
    if (stockInfo.totalStock < 10) {
        console.log(`⚠️ 재고 부족 경고: ${stockInfo.name} (남은 재고: ${stockInfo.totalStock})`);
    }
});

// 품절 알림 구독
stockAlert.subscribe('W000001', (stockInfo) => {
    if (!stockInfo.isInStock) {
        console.log(`❌ 품절 알림: ${stockInfo.name}`);
    }
});

// 모니터링 시작
stockAlert.startMonitoring(10); // 10분마다 확인
```

---

## 문제 해결

### 자주 발생하는 오류들

#### 1. 인증 오류 (401 Unauthorized)
```javascript
// 해결 방법: 토큰 갱신 후 재시도
async function handleAuthError(apiCall) {
    try {
        return await apiCall();
    } catch (error) {
        if (error.message.includes('401')) {
            console.log('토큰 만료, 재인증 시도...');
            await auth.authenticate();
            return await apiCall();
        }
        throw error;
    }
}
```

#### 2. 요청 제한 초과 (429 Too Many Requests)
```javascript
// 해결 방법: 지수 백오프 재시도
async function withRetry(apiCall, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await apiCall();
        } catch (error) {
            if (error.message.includes('429') && i < maxRetries - 1) {
                const delay = Math.pow(2, i) * 1000; // 1초, 2초, 4초...
                console.log(`요청 제한 초과, ${delay}ms 후 재시도...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                continue;
            }
            throw error;
        }
    }
}
```

#### 3. GraphQL 오류 처리
```javascript
function handleGraphQLErrors(response) {
    if (response.errors) {
        const errorMessages = response.errors.map(err => err.message).join(', ');
        
        // 특정 오류 타입별 처리
        if (errorMessages.includes('ITEM_NOT_FOUND')) {
            console.warn('상품을 찾을 수 없습니다');
            return null;
        }
        
        if (errorMessages.includes('INVALID_KEY')) {
            throw new Error('잘못된 상품 키입니다');
        }
        
        throw new Error(`GraphQL 오류: ${errorMessages}`);
    }
    
    return response.data;
}
```

### 성능 최적화 팁

#### 1. 배치 처리
```javascript
// 상품을 100개씩 묶어서 처리
function chunkArray(array, chunkSize) {
    const chunks = [];
    for (let i = 0; i < array.length; i += chunkSize) {
        chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
}

async function processProductsInBatches(productKeys, batchSize = 100) {
    const batches = chunkArray(productKeys, batchSize);
    const results = [];
    
    for (let i = 0; i < batches.length; i++) {
        console.log(`배치 ${i + 1}/${batches.length} 처리 중...`);
        
        const batchResult = await api.getMultipleProducts(batches[i]);
        results.push(...batchResult);
        
        // API 호출 간격 조정
        if (i < batches.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }
    
    return results;
}
```

#### 2. 캐싱 구현
```javascript
class APICache {
    constructor(ttl = 5 * 60 * 1000) { // 5분 TTL
        this.cache = new Map();
        this.ttl = ttl;
    }

    get(key) {
        const item = this.cache.get(key);
        
        if (!item) return null;
        
        if (Date.now() > item.expires) {
            this.cache.delete(key);
            return null;
        }
        
        return item.data;
    }

    set(key, data) {
        this.cache.set(key, {
            data: data,
            expires: Date.now() + this.ttl
        });
    }
}

// 캐시가 적용된 API 래퍼
class CachedOwnerClanAPI extends OwnerClanAPI {
    constructor(username, password) {
        super(username, password);
        this.cache = new APICache();
    }

    async getProduct(key) {
        const cached = this.cache.get(key);
        if (cached) {
            console.log(`캐시에서 상품 ${key} 로드`);
            return cached;
        }

        const product = await super.getProduct(key);
        this.cache.set(key, product);
        return product;
    }
}
```

### 디버깅 도구

#### 로깅 시스템
```javascript
class Logger {
    constructor(level = 'INFO') {
        this.level = level;
        this.levels = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
    }

    log(level, message, data = null) {
        if (this.levels[level] >= this.levels[this.level]) {
            const timestamp = new Date().toISOString();
            console.log(`[${timestamp}] ${level}: ${message}`);
            
            if (data) {
                console.log('Data:', data);
            }
        }
    }

    debug(message, data) { this.log('DEBUG', message, data); }
    info(message, data) { this.log('INFO', message, data); }
    warn(message, data) { this.log('WARN', message, data); }
    error(message, data) { this.log('ERROR', message, data); }
}

const logger = new Logger('DEBUG');

// API 호출 로깅
async function loggedRequest(apiCall, operation) {
    logger.info(`${operation} 시작`);
    const startTime = Date.now();
    
    try {
        const result = await apiCall();
        const duration = Date.now() - startTime;
        logger.info(`${operation} 완료 (${duration}ms)`);
        return result;
    } catch (error) {
        const duration = Date.now() - startTime;
        logger.error(`${operation} 실패 (${duration}ms)`, error);
        throw error;
    }
}
```

이 통합 문서를 통해 오너클랜 API를 체계적으로 이해하고 활용할 수 있습니다. 초보 개발자도 단계별로 따라하면서 자신만의 상품 관리 시스템을 구축할 수 있습니다.