# 오너클랜 API 셀러러

**Version:** v0.11.0  
**Document version:** v0.11.0.0  
**Date:** 10/21/2020

## 목차

- [변경사항](#변경사항)
- [엔드포인트](#엔드포인트)
- [사용법](#사용법)
- [메소드](#메소드)
- [데이터 타입](#데이터-타입)
- [상품 운영시 참조사항](#상품-운영시-참조사항)

## 변경사항

### v0.10.17 → v0.11.0
- 반품/교환 신청 기능 추가
- 자세한 사항은 Methods 섹션의 `requestRefundOrExchange` 쿼리 설명 참고

### v0.10.13 → v0.10.17
- 주문 생성시 여러 상품을 주문하는 경우, 다음 기준에 의해 필요한 경우 자동으로 여러 주문으로 나뉘어 생성되도록 변경:
  - 상품 공급사가 다른 경우(`Item.metadata.vendorKey`)
  - 상품 배송비 부과 타입이 다른 경우(`Item.shippingType`)
- JWT 인증 토큰 발급 서버 URL 변경
  - **기존:**
    - sandbox: API Authentication endpoint(Sandbox)(Deprecated)
    - production: API Authentication endpoint(Production)(Deprecated)
  - **변경:**
    - sandbox: API Authentication endpoint(Sandbox)
    - production: API Authentication endpoint(Production)

### v0.10.11 → v0.10.13
- 해외배송 상품 주문 시 개인통관 고유번호/생년월일 입력 추가 및 형식 변경
  - 기존 string 타입에서 `CustomsClearanceCodeInput` 타입으로 변경
- 송장번호 입력일 기준으로 주문 검색하는 기능 추가
  - `allOrders` 파라미터에 `shippedAfter`, `shippedBefore` 추가

### v0.10.10 → v0.10.11
- key의 배열로 상품 리스트를 조회하는 기능 추가 (`itemsByKeys`)
- 상품 등록(`createItem`) 및 수정(`updateItem`)시 옵션명 및 옵션값 글자 수 제한 적용:
  - 옵션명: euc-kr 인코딩 기준 40bytes 이하
  - 옵션값: euc-kr 인코딩 기준 20bytes 이하

## 엔드포인트

### API Endpoint
- **Production:** `https://api.ownerclan.com/v1/graphql`
- **Sandbox:** `https://api-sandbox.ownerclan.com/v1/graphql`

### GUI Test Endpoint (GraphQL Playground)
- **Production:** `https://api.ownerclan.com/v1/graphql`
- **Sandbox:** `https://api-sandbox.ownerclan.com/v1/graphql`

### Authentication Endpoint
- **Production:** `https://auth.ownerclan.com/auth`
- **Sandbox:** `https://auth-sandbox.ownerclan.com/auth`
- **인증 방식:** JWT

## 사용법

### GraphQL
오너클랜 API는 GraphQL로 구현되어 있습니다. GraphQL은 URL과 Method에 따라 query가 구분되었던 REST API와 다르게 GraphQL 언어를 통해 쿼리를 작성하고 단 하나의 엔드포인트로 모든 요청을 보내도록 되어있습니다.

#### 예시 쿼리
```graphql
query {
  item(key: "W000000") {
    name
    model
    options {
      price
      quantity
      optionAttributes {
        name
        value
      }
    }
  }
}
```

#### 예시 응답
```json
{
  "data": {
    "name": "예시 상품",
    "model": "예시 모델",
    "options": [
      {
        "price": 35000,
        "quantity": 23,
        "optionAttributes": [
          {
            "name": "색상",
            "value": "RED"
          },
          {
            "name": "사이즈",
            "value": "95"
          }
        ]
      }
    ]
  }
}
```

### GraphQL 쿼리 보내기

#### READ (query): GET method
- 쿼리 내용은 URL의 query parameter로 전달
- 예시: `https://api-sandbox.ownerclan.com/v1/graphql?query=EXAMPLE_QUERY`

#### CREATE, UPDATE, DELETE (mutation): POST method

### JWT 인증
오너클랜 API는 JWT를 기반으로 한 토큰 인증 방식을 사용합니다.

```javascript
var authData = {
  service: "ownerclan",
  userType: "seller",
  username: "판매사ID",
  password: "판매사PW"
};

$.ajax({
  url: "https://auth-sandbox.ownerclan.com/auth",
  type: "POST",
  contentType: "application/json",
  processData: false,
  data: JSON.stringify(authData),
  success: function(data) {
    console.log(data);
  },
  error: function(data) {
    console.error(data.responseText, data.status);
  }
});
```

## 메소드

### item
단일 상품 정보를 조회합니다.

#### 파라미터
- `key` (String): 정보를 조회할 상품의 key (오너클랜 상품 코드)
- `lang` (Language): Text 타입 필드들의 기본 언어 설정 (기본값: ko_KR)
- `currency` (Currency): 가격 정보 필드들의 기본 화폐 단위 설정 (기본값: KRW)

#### 반환 데이터
- `createdAt` (Int): 상품 DB 등록 시각 (Unix timestamp)
- `updatedAt` (Int): 상품 최종 업데이트 시각 (Unix timestamp)
- `key` (String): 상품의 오너클랜 코드
- `name` (Text): 상품 이름
- `model` (String): 상품 모델명
- `production` (String): 제조사
- `origin` (String): 제조 국가
- `price` (Float): 상품 가격
- `pricePolicy` (PricePolicy): 상품 가격 정책
- `fixedPrice` (Float): 소비자 준수가격 (pricePolicy가 fixed인 경우)
- `category` (Category): 상품 카테고리 정보
- `content` (String): 상품 상세정보
- `shippingFee` (Int): 상품 배송비
- `shippingType` (ShippingType): 상품 배송비 부과 타입
- `images` ([URL]): 상품 이미지 (size 파라미터 필수)
- `status` (String): 상품 현재 상태
  - `soldout`: 품절
  - `available`: 판매중
  - `unavailable`: 판매하지 않는 상태
  - `discontinued`: 단종
- `options` ([ItemOption]): 상품 옵션 정보
- `taxFree` (Boolean): 면세 상품 여부
- `adultOnly` (Boolean): 미성년자 판매 불가 여부
- `returnable` (Boolean): 반품 가능 여부
- `openmarketSellable` (Boolean): 오픈마켓 판매 가능 여부
- `metadata` (JSON): 상품 추가 정보

#### 예시 쿼리
```graphql
query testQuery {
  item(key: "W000000") {
    key
    name
    model
    price
    category {
      key
      name
      fullName
    }
    images(size: large)
    status
    options {
      optionAttributes {
        name
        value
      }
      price
      quantity
    }
  }
}
```

### allItems
복수의 상품을 조회합니다. 한 번에 최대 1000개의 상품 정보를 조회할 수 있으며, pagination을 위한 cursor를 제공합니다.

#### 파라미터

##### Pagination 관련
- `after` (String): cursor 값 이후의 상품만 조회
- `before` (String): cursor 값 이전의 상품만 조회
- `first` (Int): 처음 몇 개의 상품을 조회할지 설정
- `last` (Int): 마지막 몇 개의 상품을 조회할지 설정

##### Search 관련
- `dateFrom` (Timestamp): 상품 수정 시각 시작 범위
- `dateTo` (Timestamp): 상품 수정 시각 종료 범위
- `minPrice` (Int): 최저가 검색 조건
- `maxPrice` (Int): 최고가 검색 조건
- `search` (String): 검색어
- `vendor` (ID): 공급사 코드
- `status` (ItemStatus): 상품 상태
- `category` (ID): 카테고리 코드
- `attributes` ([String]): 상품 속성
- `sortBy` (ItemSortCriteria): 정렬 조건
- `openmarketSellable` (Boolean): 오픈마켓 판매 가능 여부

#### 반환 값
```graphql
{
  pageInfo {
    hasNextPage
    hasPreviousPage
    startCursor
    endCursor
  }
  edges {
    cursor
    node {
      # item 쿼리와 동일한 필드들
    }
  }
}
```

### order
단일 주문 정보를 조회합니다.

#### 파라미터
- `key` (String): 조회할 주문의 key (오너클랜 주문 코드)

#### 반환 데이터
- `key` (String): 주문 코드
- `products` ([OrderProduct]): 주문 제품 정보
- `status` (OrderStatus): 주문 상태
- `shippingInfo` (ShippingInfo): 배송 정보
- `createdAt` (Int): 주문 생성 시각
- `note` (String): 원장주문코드
- `ordererNote` (String): 고객 메모
- `sellerNote` (String): 판매자 메모

### allOrders
복수의 주문내역을 조회합니다.

#### 파라미터
- Pagination: `after`, `before`, `first`, `last`
- Search: `dateFrom`, `dateTo`, `note`, `sellerNote`, `status`, `shippedAfter`, `shippedBefore`

### createOrder
새 주문을 등록합니다.

#### 파라미터
- `input` (OrderInput): 입력 데이터
- `simulationResult` ([object]): 시뮬레이션 결과 (선택사항)

#### 입력 데이터
- `sender` (SenderInput): 보내는 사람 정보
- `recipient` (RecipientInput): 받는 사람 정보 (필수)
- `products` ([OrderProductInput]): 주문 상품 리스트 (필수)
- `note` (String): 원장주문코드
- `sellerNote` (String): 판매자 메모
- `ordererNote` (String): 배송 요청사항
- `customsClearanceCode` (CustomsClearanceCodeInput): 해외배송 통관정보

## 데이터 타입

### ShippingType
배송비 유형:
- `inAdvance`: 선불 전용
- `uponArrival`: 착불 전용
- `free`: 무료 배송

### ItemStatus
상품 상태:
- `soldout`: 일시 품절
- `available`: 판매 가능
- `unavailable`: 판매 불가 (재입고 가능)
- `discontinued`: 단종 (재입고 불가)

### ItemSortCriteria
상품 정렬 기준:
- `dateDesc`: 수정일 내림차순
- `dateAsc`: 수정일 오름차순
- `nameAsc`: 상품명 오름차순
- `nameDesc`: 상품명 내림차순
- `priceAsc`: 가격 오름차순
- `priceDesc`: 가격 내림차순

### OrderStatus
주문 상태:
- `placed`: 미처리
- `paid`: 입금완료
- `preparing`: 발송 준비
- `cancelled`: 주문 취소
- `shipped`: 발송 완료
- `refunded`: 반품 완료

### Currency
화폐 단위:
- `KRW`: 한국 원화
- `USD`: 미국 달러
- `CNY`: 중국 위안

### Language
언어 코드:
- `ko_KR`: 한국어
- `en_US`: 영어
- `zh_CN`: 중국어

## 상품 운영시 참조사항

### 상품 판매상태 업데이트 가이드라인

API를 통해 조회한 상품 정보를 사용할 때는 상품 판매상태를 지속적으로 업데이트해야 합니다.

#### 업데이트 방법

1. **개별 상품 정보 조회**
   - `item` 쿼리를 사용하여 각 상품의 상태를 직접 조회
   - 1초에 최대 1000건 요청 가능

2. **allItems 쿼리 사용**
   - 주기적 업데이트에 적합
   - `dateFrom`, `dateTo` 파라미터로 시간 범위 설정
   - 업데이트 주기의 2배 이상 시간 범위 권장

3. **itemHistories 쿼리 사용**
   - 상품 변경 이력을 통한 업데이트
   - 특정 상품 또는 특정 기간의 변경 이력 조회 가능

### 오픈마켓 판매 가능 여부

`Item.openmarketSellable` 필드가 `false`인 상품을 오픈마켓에 등록하면 제재를 받을 수 있습니다. 반드시 `true`인 상품만 등록하세요.

### 배송비 계산

#### 묶음배송 가능 수량
`Item.boxQuantity` 필드를 참고하여 배송비를 계산합니다:
- 묶음배송 가능 수량이 없으면: 상품 개수와 관계없이 `Item.shippingFee` 적용
- 묶음배송 가능 수량이 있으면: `(구매수량-1) ÷ 묶음배송수량 × 배송비`

#### 여러 상품 주문시
각 상품의 배송비를 계산한 후 최댓값이 최종 배송비가 됩니다.

### 특수 상품군

#### 건강식품 및 의료기기
별도 허가가 필요한 상품군입니다:
- 건강식품: `"ATTR_H_FOOD"` 속성
- 의료기기: `"ATTR_MEDICAL"` 속성

#### 해외배송 상품
- 해외배송: `"ATTR_OVERSEA"` 속성
- 해외직배송: `"ATTR_OVERSEA_DIRECT"` 속성

#### 유통금지 상품
`"PROHIBIT"` 속성이 있는 상품은 즉시 판매를 중단해야 합니다.

### 반품 관련

#### 반품 가능 여부
- `Item.returnable`: 반품 가능 여부
- `Item.noReturnReason`: 반품 불가 사유 (반품 불가시)

#### 반품 접수 유형
- `vendor`: 공급사 반품접수
- `seller`: 원운송장 반품접수

---

**참고:** 이 문서는 v0.11.0 기준으로 작성되었으며, 최신 정보는 오너클랜 API 문서를 확인하시기 바랍니다.