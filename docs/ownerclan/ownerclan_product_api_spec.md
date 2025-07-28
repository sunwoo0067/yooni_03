# 오너클랜 상품 조회 API 명세서

## 개요
오너클랜 API를 통해 상품 정보를 조회할 수 있는 다양한 엔드포인트를 제공합니다. 모든 API는 GraphQL을 사용하며, JWT 토큰 인증이 필요합니다.

## API 엔드포인트
- **Production**: `https://api.ownerclan.com/v1/graphql`
- **Sandbox**: `https://api-sandbox.ownerclan.com/v1/graphql`

## 공통 인증 방법
모든 API 요청 시 Authorization 헤더에 JWT 토큰을 포함해야 합니다.
```
Authorization: Bearer {your_jwt_token}
```

---

## 1. 단일 상품 정보 조회 API

### 설명
특정 상품 키(key)를 사용하여 단일 상품의 상세 정보를 조회합니다.

### GraphQL 쿼리
```graphql
query GetItem($key: String!, $lang: Language, $currency: Currency) {
    item(key: $key, lang: $lang, currency: $currency) {
        createdAt
        updatedAt
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
    }
}
```

### 파라미터
| 파라미터 | 타입 | 필수 여부 | 기본값 | 설명 |
|----------|------|-----------|--------|------|
| key | String | 필수 | - | 조회할 상품의 오너클랜 코드 |
| lang | Language | 선택 | ko_KR | 텍스트 필드의 언어 설정 |
| currency | Currency | 선택 | KRW | 가격 정보의 화폐 단위 |

### 응답 데이터
| 필드 | 타입 | 설명 |
|------|------|------|
| createdAt | Int | 상품 등록 시각 (Unix timestamp) |
| updatedAt | Int | 최종 업데이트 시각 (Unix timestamp) |
| key | String | 상품의 오너클랜 코드 |
| name | Text | 상품명 |
| model | String | 모델명 |
| production | String | 제조사 |
| origin | String | 제조국가 |
| price | Float | 상품 가격 |
| pricePolicy | PricePolicy | 가격 정책 |
| fixedPrice | Float | 소비자 준수 가격 |
| category | Category | 카테고리 정보 |
| shippingFee | Int | 배송비 |
| shippingType | ShippingType | 배송비 부과 타입 |
| status | String | 상품 상태 |
| options | [ItemOption] | 상품 옵션 정보 배열 |
| taxFree | Boolean | 면세 여부 |
| adultOnly | Boolean | 성인 전용 상품 여부 |
| returnable | Boolean | 반품 가능 여부 |
| images | [URL] | 상품 이미지 URL 목록 |

### 사용 예제
```javascript
// 변수 정의
const variables = {
    key: "W000000",
    lang: "ko_KR",
    currency: "KRW"
};

// 요청 실행
fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({
        query: `
            query GetItem($key: String!, $lang: Language, $currency: Currency) {
                item(key: $key, lang: $lang, currency: $currency) {
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
        `,
        variables: variables
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## 2. 복수 상품 정보 조회 API

### 설명
여러 상품을 검색 조건에 따라 조회합니다. 페이지네이션을 지원하며, 한 번에 최대 1000개까지 조회 가능합니다.

### GraphQL 쿼리
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

### 파라미터
| 파라미터 | 타입 | 필수 여부 | 설명 |
|----------|------|-----------|------|
| after | String | 선택 | 지정된 cursor 값 이후의 상품만 조회 |
| first | Int | 선택 | 조회할 상품 개수 (최대 1000) |
| minPrice | Int | 선택 | 최저 가격 필터 |
| maxPrice | Int | 선택 | 최고 가격 필터 |
| search | String | 선택 | 상품 검색어 |

### 사용 예제
```javascript
const variables = {
    first: 10,
    minPrice: 10000,
    maxPrice: 100000,
    search: "스마트폰"
};

fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({
        query: getAllItemsQuery,
        variables: variables
    })
})
.then(response => response.json())
.then(data => {
    console.log('총 상품 수:', data.data.allItems.edges.length);
    data.data.allItems.edges.forEach(edge => {
        console.log('상품:', edge.node.name, '가격:', edge.node.price);
    });
});
```

---

## 3. 상품 변경 이력 조회 API

### 설명
상품의 품절, 단종, 재입고 등의 변경 이력을 조회합니다.

### GraphQL 쿼리
```graphql
query GetItemHistories($after: String, $first: Int, $dateFrom: Timestamp, $kind: ItemHistoryKind, $itemKey: ID) {
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

### 파라미터
| 파라미터 | 타입 | 필수 여부 | 설명 |
|----------|------|-----------|------|
| after | String | 선택 | 지정된 cursor 값 이후의 이력만 조회 |
| first | Int | 선택 | 조회할 이력 개수 |
| dateFrom | Timestamp | 선택 | 지정된 날짜 이후의 이력만 조회 |
| kind | ItemHistoryKind | 선택 | 조회할 이력 종류 (예: STOCK_OUT, RESTOCK 등) |
| itemKey | ID | 선택 | 특정 상품의 이력만 조회 |

### 사용 예제
```javascript
const variables = {
    first: 20,
    dateFrom: 1640995200, // 2022-01-01 00:00:00 UTC
    kind: "STOCK_OUT",
    itemKey: "W000000"
};

fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({
        query: getItemHistoriesQuery,
        variables: variables
    })
})
.then(response => response.json())
.then(data => {
    data.data.itemHistories.edges.forEach(edge => {
        const history = edge.node;
        console.log(`${new Date(history.timestamp * 1000).toLocaleString()}: ${history.kind} - ${history.description}`);
    });
});
```

---

## 4. 여러 상품 정보 조회 API

### 설명
상품 키(key) 배열을 사용하여 여러 상품의 정보를 한 번에 조회합니다. 최대 5000개까지 가능합니다.

### GraphQL 쿼리
```graphql
query GetItems($keys: [String!]!) {
    items(keys: $keys) {
        createdAt
        updatedAt
        key
        name
        model
        production
        origin
        price
        category {
            id
            name
            level
        }
        content
        shippingFee
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
        returnable
        images
    }
}
```

### 파라미터
| 파라미터 | 타입 | 필수 여부 | 설명 |
|----------|------|-----------|------|
| keys | [String!]! | 필수 | 조회할 상품 키들의 배열 (최대 5000개) |

### 사용 예제
```javascript
const variables = {
    keys: ["W000000", "W000001", "W000002", "W000003"]
};

fetch('https://api-sandbox.ownerclan.com/v1/graphql', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({
        query: `
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
        `,
        variables: variables
    })
})
.then(response => response.json())
.then(data => {
    console.log('조회된 상품 수:', data.data.items.length);
    data.data.items.forEach(item => {
        console.log(`상품 ${item.key}: ${item.name} - ${item.price}원`);
    });
});
```

---

## 공통 데이터 타입

### Category
```javascript
{
    id: "String",           // 카테고리 ID
    name: "String",         // 카테고리 이름
    level: "Int"            // 카테고리 레벨
}
```

### ItemOption
```javascript
{
    id: "String",           // 옵션 ID
    price: "Float",         // 옵션 가격
    quantity: "Int",        // 재고 수량
    optionAttributes: [     // 옵션 속성 배열
        {
            name: "String",   // 속성명 (예: "색상", "사이즈")
            value: "String"   // 속성값 (예: "빨강", "L")
        }
    ]
}
```

### PageInfo
```javascript
{
    hasNextPage: "Boolean",     // 다음 페이지 존재 여부
    hasPreviousPage: "Boolean", // 이전 페이지 존재 여부
    startCursor: "String",      // 시작 커서
    endCursor: "String"         // 끝 커서
}
```

## 오류 처리

### 일반적인 오류 응답
```javascript
{
    "errors": [
        {
            "message": "상품을 찾을 수 없습니다.",
            "locations": [{"line": 2, "column": 3}],
            "path": ["item"],
            "extensions": {
                "code": "ITEM_NOT_FOUND",
                "exception": {
                    "stacktrace": ["..."]
                }
            }
        }
    ],
    "data": {
        "item": null
    }
}
```

### 주요 오류 코드
- `ITEM_NOT_FOUND`: 상품을 찾을 수 없음
- `INVALID_KEY`: 잘못된 상품 키
- `AUTHENTICATION_REQUIRED`: 인증 토큰 필요
- `ACCESS_DENIED`: 접근 권한 없음
- `RATE_LIMIT_EXCEEDED`: 요청 제한 초과

## 모범 사례

### 1. 효율적인 쿼리 작성
```javascript
// 필요한 필드만 요청
query GetItem($key: String!) {
    item(key: $key) {
        key
        name
        price
        status
        // 불필요한 필드는 제외
    }
}
```

### 2. 페이지네이션 처리
```javascript
async function getAllItemsWithPagination() {
    let allItems = [];
    let hasNextPage = true;
    let cursor = null;

    while (hasNextPage) {
        const variables = { first: 100, after: cursor };
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ query, variables })
        });
        
        const data = await response.json();
        const { edges, pageInfo } = data.data.allItems;
        
        allItems.push(...edges.map(edge => edge.node));
        hasNextPage = pageInfo.hasNextPage;
        cursor = pageInfo.endCursor;
    }

    return allItems;
}
```

### 3. 오류 처리
```javascript
async function safeApiCall(query, variables) {
    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ query, variables })
        });

        const data = await response.json();

        if (data.errors) {
            console.error('GraphQL 오류:', data.errors);
            return null;
        }

        return data.data;
    } catch (error) {
        console.error('네트워크 오류:', error);
        return null;
    }
}
```