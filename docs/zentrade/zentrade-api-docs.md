# 젠트레이드 API 문서

## 개요
젠트레이드에서 제공하는 XML 형태의 API를 통해 상품 데이터 조회 및 주문 정보 조회가 가능합니다.

---

## 1. 상품 API

### 기본 정보
- **URL**: `https://www.zentrade.co.kr/shop/proc/product_api.php`
- **Method**: GET 또는 POST
- **Response Format**: XML

### 요청 파라미터

| 파라미터명 | 필수여부 | 설명 | 예시 |
|-----------|---------|------|------|
| `id` | **필수** | 젠트레이드 계정 ID | `b00679540` |
| `m_skey` | **필수** | 인증키 | `5284c44b0fcf0f877e6791c5884d6ea9` |
| `goodsno` | 선택 | 젠트레이드 상품번호 (특정 상품 1개 조회시) | `123456` |
| `runout` | 선택 | 품절여부 필터<br/>- `1`: 품절상품만<br/>- `0`: 정상상품만 | `0` |
| `opendate_s` | 선택 | 신상품 오픈일자 (시작일) | `2020-09-01` |
| `opendate_e` | 선택 | 신상품 오픈일자 (종료일) | `2020-09-30` |

> **참고**: `opendate_s`와 `opendate_e`는 둘 다 입력해야 검색 가능합니다.

### 응답 XML 구조

```xml
<?xml version="1.0" encoding="euc-kr"?>
<zentrade version="ZENTRADE XML 1.0" datetime="">
    <product code="젠트레이드 상품번호">
        <dome_category dome_catecode="젠트레이드 카테고리 코드">
            <![CDATA[ 젠트레이드 카테고리명 ]]>
        </dome_category>
        <scategory emp_catecode="플레이오토 EMP카테고리코드" 
                   esellers_catecode="이셀러스 카테고리코드" 
                   classcode="상품군코드" />
        <prdtname>
            <![CDATA[ 젠트레이드 상품명 ]]>
        </prdtname>
        <baseinfo madein="원산지" 
                  productcom="제조사" 
                  brand="브랜드" 
                  model="모델명" />
        <price buyprice="젠트레이드 판매가" 
               consumerprice="소비자가" 
               taxmode="과세여부(Y/N)" />
        <listimg url1="목록이미지1URL" 
                 url2="목록이미지2URL" 
                 url3="목록이미지3URL" 
                 url4="목록이미지4URL" 
                 url5="목록이미지5URL" />
        <option opt1nm="옵션명" opt2nm="2차옵션명(사용안함)">
            <![CDATA[ 
                옵션항목1^|^옵션항목1 판매가^|^옵션항목1 소비자가^|^옵션항목1 옵션이미지URL↑=↑
                옵션항목2^|^옵션항목2 판매가^|^옵션항목2 소비자가^|^옵션항목2 옵션이미지URL↑=↑
                ...
            ]]>
        </option>
        <content>
            <![CDATA[ 상세페이지 이미지 소스 ]]>
        </content>
        <keyword>
            <![CDATA[ 키워드(쉼표로 구분) ]]>
        </keyword>
        <status runout="품절여부(1:품절, 0:정상)" opendate="신상품 오픈일자" />
    </product>
</zentrade>
```

### 필드 설명

#### Product 정보
- `code`: 젠트레이드 상품번호
- `dome_category`: 젠트레이드 카테고리 정보
- `scategory`: 외부 쇼핑몰 카테고리 매핑 정보
- `prdtname`: 상품명
- `baseinfo`: 기본 상품 정보 (원산지, 제조사, 브랜드, 모델명)
- `price`: 가격 정보 (판매가, 소비자가, 과세여부)
- `listimg`: 상품 목록 이미지 URL (최대 5개)
- `option`: 상품 옵션 정보
- `content`: 상세페이지 HTML 내용
- `keyword`: 검색 키워드
- `status`: 상품 상태 (품절여부, 오픈일자)

#### 옵션 데이터 형식
옵션 데이터는 다음과 같은 구분자로 분리됩니다:
- `^|^`: 필드 구분자
- `↑=↑`: 옵션 구분자

형식: `옵션명^|^판매가^|^소비자가^|^옵션이미지URL`

---

## 2. 주문 조회 API

### 기본 정보
- **URL**: `https://www.zentrade.co.kr/shop/proc/order_api.php`
- **Method**: GET 또는 POST
- **Response Format**: XML

### 요청 파라미터

| 파라미터명 | 필수여부 | 설명 | 예시 |
|-----------|---------|------|------|
| `id` | **필수** | 젠트레이드 계정 ID | `b00679540` |
| `m_skey` | **필수** | 인증키 | `5284c44b0fcf0f877e6791c5884d6ea9` |
| `ordno` | **선택적필수** | 13자리 젠트레이드 주문번호 | `2024123456789` |
| `pordno` | **선택적필수** | 개인고유주문번호 | `MY_ORDER_001` |

> **중요**: `ordno` 또는 `pordno` 중 하나는 반드시 입력해야 합니다.

### 응답 XML 구조

```xml
<?xml version="1.0" encoding="euc-kr"?>
<zentrade version="ZENTRADE ORDER XML 1.0" datetime="">
    <ord_info ordno="젠트레이드 주문번호" pordno="개인고유주문번호">
        <ord_date>주문일시</ord_date>
        <nameReceiver>
            <![CDATA[ 받는사람 이름 ]]>
        </nameReceiver>
        <phoneReceiver>
            <![CDATA[ 받는사람 전화번호 ]]>
        </phoneReceiver>
        <mobileReceiver>
            <![CDATA[ 받는사람 핸드폰번호 ]]>
        </mobileReceiver>
        <address>
            <![CDATA[ 받는사람 주소 ]]>
        </address>
        <ord_item1>
            <![CDATA[ 젠트레이드 상품번호 - 상품명 / 옵션 ]]>
        </ord_item1>
        <ord_item2>
            <![CDATA[ 젠트레이드 상품번호 - 상품명 / 옵션 ]]>
        </ord_item2>
        <!-- 추가 주문상품들... -->
        <deli_info delicom="택배회사" delinum="송장번호" />
        <zentrade_msg>
            <![CDATA[ 젠트레이드 관리자 전달 메모 ]]>
        </zentrade_msg>
    </ord_info>        
</zentrade>
```

### 필드 설명

#### 주문 정보
- `ordno`: 젠트레이드 주문번호
- `pordno`: 개인고유주문번호
- `ord_date`: 주문일시
- `nameReceiver`: 받는사람 이름
- `phoneReceiver`: 받는사람 전화번호
- `mobileReceiver`: 받는사람 핸드폰번호
- `address`: 받는사람 주소
- `ord_item[N]`: 주문상품 목록 (N번째 상품)
- `deli_info`: 배송 정보 (택배회사, 송장번호)
- `zentrade_msg`: 젠트레이드 관리자 메모

---

## 사용 예시

### 상품 API 호출 예시

```bash
# 전체 상품 조회
GET https://www.zentrade.co.kr/shop/proc/product_api.php?id=b00679540&m_skey=5284c44b0fcf0f877e6791c5884d6ea9

# 특정 상품 조회
GET https://www.zentrade.co.kr/shop/proc/product_api.php?id=b00679540&m_skey=5284c44b0fcf0f877e6791c5884d6ea9&goodsno=123456

# 정상 상품만 조회
GET https://www.zentrade.co.kr/shop/proc/product_api.php?id=b00679540&m_skey=5284c44b0fcf0f877e6791c5884d6ea9&runout=0

# 특정 기간 신상품 조회
GET https://www.zentrade.co.kr/shop/proc/product_api.php?id=b00679540&m_skey=5284c44b0fcf0f877e6791c5884d6ea9&opendate_s=2024-01-01&opendate_e=2024-01-31
```

### 주문 API 호출 예시

```bash
# 젠트레이드 주문번호로 조회
GET https://www.zentrade.co.kr/shop/proc/order_api.php?id=b00679540&m_skey=5284c44b0fcf0f877e6791c5884d6ea9&ordno=2024123456789

# 개인고유주문번호로 조회
GET https://www.zentrade.co.kr/shop/proc/order_api.php?id=b00679540&m_skey=5284c44b0fcf0f877e6791c5884d6ea9&pordno=MY_ORDER_001
```

---

## 주의사항

1. **인코딩**: 모든 XML 응답은 `euc-kr` 인코딩을 사용합니다.
2. **CDATA**: 한글 텍스트는 `<![CDATA[...]]>` 형태로 감싸져 있습니다.
3. **옵션 품절**: 옵션별 품절 상태는 지원하지 않습니다.
4. **데이터 가공**: API에서 받은 데이터의 가공 및 처리는 개발자가 직접 구현해야 합니다.
5. **인증**: API 호출시 올바른 `id`와 `m_skey` 값이 필요합니다.