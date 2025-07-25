# 도매처 연동 모듈 API 가이드

이 문서는 도매처 연동 모듈의 완전한 API 사용법과 구현 예제를 제공합니다.

## 📋 목차

1. [개요](#개요)
2. [주요 기능](#주요-기능)
3. [API 엔드포인트](#api-엔드포인트)
4. [사용 예제](#사용-예제)
5. [엑셀 파일 처리](#엑셀-파일-처리)
6. [자동 수집 스케줄러](#자동-수집-스케줄러)
7. [분석 및 통계](#분석-및-통계)
8. [에러 처리](#에러-처리)

## 🎯 개요

도매처 연동 모듈은 온라인 셀러들이 여러 도매처의 상품을 효율적으로 관리할 수 있도록 하는 완전 자동화 시스템입니다.

### 지원 도매처
- **도매매(도매꾹)**: 한국 대표 도매 플랫폼
- **오너클랜**: B2B 전문 도매 사이트  
- **젠트레이드**: 해외 도매 플랫폼

## 🚀 주요 기능

### 1. 엑셀 파일 처리
- 📊 자동 컬럼 매핑
- ✅ 데이터 검증 및 오류 체크
- 📈 일괄 상품 등록
- 📋 업로드 이력 관리

### 2. 자동 수집 스케줄러
- ⏰ 주기적 상품 수집 (일/주/월)
- 🔍 변경사항 자동 감지
- 🆕 신상품 알림
- 🔄 백그라운드 작업 큐

### 3. 최근 자료 조회 및 분석
- 📅 최근 7일/30일 신상품 조회
- 💰 가격 변동 추적
- 📦 재고 변화 모니터링
- 📊 트렌드 분석

## 🔧 API 엔드포인트

### 도매처 계정 관리

```
POST   /api/v1/wholesaler/accounts              # 도매처 계정 생성
GET    /api/v1/wholesaler/accounts              # 계정 목록 조회
GET    /api/v1/wholesaler/accounts/{id}         # 특정 계정 조회
PUT    /api/v1/wholesaler/accounts/{id}         # 계정 정보 수정
DELETE /api/v1/wholesaler/accounts/{id}         # 계정 삭제
POST   /api/v1/wholesaler/accounts/{id}/test-connection  # 연결 테스트
```

### 상품 관리

```
GET    /api/v1/wholesaler/accounts/{id}/products     # 계정별 상품 목록
GET    /api/v1/wholesaler/products/recent            # 최근 수집 상품
GET    /api/v1/wholesaler/products/low-stock         # 재고 부족 상품
```

### 엑셀 파일 처리

```
POST   /api/v1/wholesaler/accounts/{id}/excel/upload      # 엑셀 파일 업로드
POST   /api/v1/wholesaler/excel/{upload_id}/process       # 엑셀 파일 처리
GET    /api/v1/wholesaler/accounts/{id}/excel/history     # 업로드 이력
```

### 스케줄 관리

```
POST   /api/v1/wholesaler/accounts/{id}/schedules         # 스케줄 생성
GET    /api/v1/wholesaler/accounts/{id}/schedules         # 스케줄 목록
PUT    /api/v1/wholesaler/schedules/{id}                  # 스케줄 수정
POST   /api/v1/wholesaler/schedules/{id}/activate         # 스케줄 활성화
POST   /api/v1/wholesaler/schedules/{id}/deactivate       # 스케줄 비활성화
```

### 수집 관리

```
POST   /api/v1/wholesaler/accounts/{id}/collect           # 수동 수집 실행
GET    /api/v1/wholesaler/accounts/{id}/collections       # 수집 로그 조회
```

### 분석 및 통계

```
GET    /api/v1/wholesaler/accounts/{id}/analysis/dashboard  # 대시보드 데이터
GET    /api/v1/wholesaler/analysis/recent-products          # 최근 상품 분석
GET    /api/v1/wholesaler/analysis/trends                   # 트렌드 분석
GET    /api/v1/wholesaler/analysis/report                   # 분석 보고서
```

## 💡 사용 예제

### 1. 도매처 계정 등록

```python
import httpx
import asyncio

async def create_wholesaler_account():
    async with httpx.AsyncClient() as client:
        # 도매매 계정 등록
        domeggook_data = {
            "wholesaler_type": "domeggook",
            "account_name": "메인 도매매 계정",
            "api_credentials": {
                "api_key": "your_domeggook_api_key",
                "user_id": "your_user_id"  # 선택사항
            },
            "auto_collect_enabled": True,
            "collect_interval_hours": 24,
            "collect_recent_days": 7,
            "max_products_per_collection": 1000
        }
        
        response = await client.post(
            "http://localhost:8000/api/v1/wholesaler/accounts",
            json=domeggook_data,
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        if response.status_code == 200:
            account = response.json()
            print(f"계정 생성 성공: {account['id']}")
            return account
        else:
            print(f"계정 생성 실패: {response.text}")

# 실행
asyncio.run(create_wholesaler_account())
```

### 2. 연결 테스트

```python
async def test_connection(account_id):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/api/v1/wholesaler/accounts/{account_id}/test-connection",
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        result = response.json()
        print(f"연결 테스트 결과: {result['status']}")
        return result['status'] == 'connected'
```

### 3. 수동 상품 수집

```python
async def collect_products(account_id):
    async with httpx.AsyncClient() as client:
        collect_data = {
            "collection_type": "recent",
            "filters": {
                "categories": ["전자제품", "생활용품"],
                "min_price": 1000,
                "max_price": 100000
            },
            "max_products": 500
        }
        
        response = await client.post(
            f"http://localhost:8000/api/v1/wholesaler/accounts/{account_id}/collect",
            json=collect_data,
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        result = response.json()
        if result['success']:
            print(f"수집 시작됨. 로그 ID: {result['collection_log_id']}")
            print(f"수집된 상품: {result['stats']['collected']}개")
        else:
            print(f"수집 실패: {result['message']}")
```

## 📊 엑셀 파일 처리

### 1. 엑셀 파일 업로드

```python
async def upload_excel_file(account_id, file_path):
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            
            response = await client.post(
                f"http://localhost:8000/api/v1/wholesaler/accounts/{account_id}/excel/upload",
                files=files,
                headers={"Authorization": "Bearer your_access_token"}
            )
            
            result = response.json()
            if result['success']:
                print("파일 업로드 성공!")
                print(f"업로드 ID: {result['upload_log_id']}")
                print(f"자동 매핑된 컬럼: {result['column_mapping']}")
                return result
            else:
                print(f"업로드 실패: {result['message']}")
```

### 2. 컬럼 매핑 및 처리

```python
async def process_excel_file(upload_log_id, column_mapping, file_path):
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            data = {'column_mapping': json.dumps(column_mapping)}
            
            response = await client.post(
                f"http://localhost:8000/api/v1/wholesaler/excel/{upload_log_id}/process",
                files=files,
                data=data,
                headers={"Authorization": "Bearer your_access_token"}
            )
            
            result = response.json()
            if result['success']:
                print("파일 처리 완료!")
                print(f"성공: {result['stats']['success_count']}개")
                print(f"실패: {result['stats']['failed_count']}개")
            else:
                print(f"처리 실패: {result['message']}")
```

### 3. 엑셀 컬럼 매핑 예제

```python
# 자동 매핑 결과 예시
auto_mapping = {
    "상품명": "name",
    "도매가": "wholesale_price", 
    "소매가": "price",
    "재고수량": "stock",
    "카테고리": "category",
    "상품코드": "sku",
    "상품설명": "description",
    "이미지URL": "image_url"
}

# 수동 매핑 수정
custom_mapping = auto_mapping.copy()
custom_mapping["특별가격"] = "wholesale_price"  # 커스텀 컬럼 매핑
custom_mapping["브랜드명"] = "brand"           # 추가 필드 매핑
```

## ⏰ 자동 수집 스케줄러

### 1. 스케줄 생성

```python
async def create_collection_schedule(account_id):
    async with httpx.AsyncClient() as client:
        schedule_data = {
            "schedule_name": "일일 신상품 수집",
            "collection_type": "recent",
            "cron_expression": "0 2 * * *",  # 매일 오전 2시
            "timezone": "Asia/Seoul",
            "filters": {
                "days": 1,  # 최근 1일 상품만
                "categories": ["전자제품", "패션", "생활용품"]
            },
            "max_products": 1000,
            "is_active": True
        }
        
        response = await client.post(
            f"http://localhost:8000/api/v1/wholesaler/accounts/{account_id}/schedules",
            json=schedule_data,
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        if response.status_code == 200:
            schedule = response.json()
            print(f"스케줄 생성 성공: {schedule['id']}")
            print(f"다음 실행: {schedule['next_run_at']}")
        else:
            print(f"스케줄 생성 실패: {response.text}")
```

### 2. 크론 표현식 예제

```python
# 자주 사용되는 크론 표현식
CRON_EXPRESSIONS = {
    "매시간": "0 * * * *",
    "매일 오전 2시": "0 2 * * *", 
    "매주 월요일 오전 9시": "0 9 * * 1",
    "매월 1일 오전 10시": "0 10 1 * *",
    "평일 오후 6시": "0 18 * * 1-5",
    "주말 오전 11시": "0 11 * * 6,0"
}
```

### 3. 스케줄 관리

```python
async def manage_schedules(account_id):
    async with httpx.AsyncClient() as client:
        # 스케줄 목록 조회
        response = await client.get(
            f"http://localhost:8000/api/v1/wholesaler/accounts/{account_id}/schedules",
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        schedules = response.json()
        print(f"총 {len(schedules)}개의 스케줄이 있습니다.")
        
        for schedule in schedules:
            print(f"- {schedule['schedule_name']}: {schedule['cron_expression']}")
            print(f"  상태: {'활성' if schedule['is_active'] else '비활성'}")
            print(f"  성공률: {schedule['successful_runs']}/{schedule['total_runs']}")
```

## 📈 분석 및 통계

### 1. 대시보드 데이터 조회

```python
async def get_dashboard_data(account_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/wholesaler/accounts/{account_id}/analysis/dashboard",
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        data = response.json()
        
        # 최근 상품 현황
        recent_products = data['recent_products']
        print(f"최근 7일 신상품: {recent_products['stats']['total_count']}개")
        
        # 재고 현황
        stock_status = data['stock_status']
        print(f"재고율: {stock_status['summary']['stock_rate']:.1f}%")
        
        # 수집 성과
        collection_perf = data['collection_performance']
        print(f"수집 성공률: {collection_perf['summary']['success_rate']:.1f}%")
        
        return data
```

### 2. 트렌드 분석

```python
async def analyze_trends():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/wholesaler/analysis/trends?days=30&top_n=20",
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        trends = response.json()
        
        # 인기 카테고리
        print("🔥 인기 카테고리 TOP 10:")
        for i, category in enumerate(trends['category_trends'][:10], 1):
            print(f"{i}. {category['category']}: {category['product_count']}개")
        
        # 트렌드 키워드
        print("\n📊 트렌드 키워드 TOP 10:")
        for i, keyword in enumerate(trends['keyword_trends'][:10], 1):
            print(f"{i}. {keyword['keyword']}: {keyword['frequency']}회")
```

### 3. 분석 보고서 생성

```python
async def generate_report(account_id=None, report_type="weekly"):
    async with httpx.AsyncClient() as client:
        params = {"report_type": report_type}
        if account_id:
            params["account_id"] = account_id
            
        response = await client.get(
            "http://localhost:8000/api/v1/wholesaler/analysis/report",
            params=params,
            headers={"Authorization": "Bearer your_access_token"}
        )
        
        report = response.json()
        
        print(f"📋 {report_type.upper()} 보고서")
        print(f"생성일시: {report['generated_at']}")
        print(f"분석 기간: {report['period']}일")
        
        # 각 섹션별 요약
        sections = report['sections']
        if sections['recent_products']:
            recent = sections['recent_products']['stats']
            print(f"\n🆕 신상품: {recent['total_count']}개")
            
        if sections['price_analysis']:
            price = sections['price_analysis']['price_statistics']
            if 'wholesale_price' in price:
                avg_price = price['wholesale_price']['avg']
                print(f"💰 평균 도매가: {avg_price:,.0f}원")
        
        return report
```

## 🛠 에러 처리

### 1. 일반적인 에러 처리

```python
async def handle_api_errors():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8000/api/v1/wholesaler/accounts",
                headers={"Authorization": "Bearer invalid_token"}
            )
            response.raise_for_status()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("인증 오류: 토큰이 유효하지 않습니다.")
            elif e.response.status_code == 403:
                print("권한 오류: 접근 권한이 없습니다.")
            elif e.response.status_code == 404:
                print("리소스를 찾을 수 없습니다.")
            elif e.response.status_code == 422:
                error_detail = e.response.json()
                print(f"검증 오류: {error_detail}")
            else:
                print(f"API 오류: {e.response.status_code} - {e.response.text}")
                
        except httpx.RequestError as e:
            print(f"네트워크 오류: {e}")
```

### 2. 재시도 로직

```python
import asyncio
from typing import Optional

async def api_call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs
) -> Optional[httpx.Response]:
    """재시도 로직이 포함된 API 호출"""
    
    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500:  # 클라이언트 오류는 재시도하지 않음
                raise
                
            if attempt == max_retries:
                print(f"최대 재시도 횟수 초과: {e}")
                raise
                
            wait_time = retry_delay * (2 ** attempt)  # 지수 백오프
            print(f"재시도 {attempt + 1}/{max_retries}, {wait_time}초 후 재시도...")
            await asyncio.sleep(wait_time)
            
        except httpx.RequestError as e:
            if attempt == max_retries:
                print(f"네트워크 오류 최대 재시도 초과: {e}")
                raise
                
            wait_time = retry_delay * (2 ** attempt)
            print(f"네트워크 오류 재시도 {attempt + 1}/{max_retries}, {wait_time}초 후 재시도...")
            await asyncio.sleep(wait_time)
```

## 🎯 실제 활용 시나리오

### 1. 완전 자동화 셀러 시스템

```python
class AutomatedSellerSystem:
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.token = "your_access_token"
        
    async def setup_automated_system(self):
        """완전 자동화 시스템 설정"""
        
        # 1. 도매처 계정 등록
        accounts = await self.register_all_wholesalers()
        
        # 2. 각 계정별 자동 수집 스케줄 설정
        for account in accounts:
            await self.setup_collection_schedule(account['id'])
            
        # 3. 알림 및 모니터링 설정
        await self.setup_monitoring()
        
        print("✅ 완전 자동화 시스템 설정 완료!")
        
    async def register_all_wholesalers(self):
        """모든 도매처 계정 등록"""
        accounts = []
        
        # 도매매 계정
        domeggook = await self.create_account("domeggook", {
            "api_key": "your_domeggook_key"
        })
        accounts.append(domeggook)
        
        # 오너클랜 계정
        ownerclan = await self.create_account("ownerclan", {
            "username": "your_username",
            "password": "your_password"
        })
        accounts.append(ownerclan)
        
        return accounts
        
    async def setup_collection_schedule(self, account_id):
        """자동 수집 스케줄 설정"""
        
        # 신상품 수집 (매일 새벽 2시)
        await self.create_schedule(account_id, {
            "schedule_name": "신상품 자동수집",
            "collection_type": "recent",
            "cron_expression": "0 2 * * *",
            "filters": {"days": 1},
            "max_products": 500
        })
        
        # 가격 업데이트 (매일 오후 2시)
        await self.create_schedule(account_id, {
            "schedule_name": "가격 업데이트",
            "collection_type": "price_update", 
            "cron_expression": "0 14 * * *",
            "filters": {"update_existing": True}
        })
        
    async def daily_report(self):
        """일일 자동 보고서"""
        report = await self.generate_report("daily")
        
        # 슬랙, 이메일 등으로 보고서 전송
        await self.send_notification(f"""
        📊 일일 보고서
        
        🆕 신상품: {report['new_products']}개
        💰 평균 도매가: {report['avg_price']:,}원
        📦 재고 부족: {report['low_stock']}개
        ⚠️ 수집 실패: {report['failed_collections']}건
        """)
```

### 2. 스마트 재고 관리

```python
class SmartInventoryManager:
    async def monitor_inventory(self):
        """스마트 재고 모니터링"""
        
        # 재고 부족 상품 확인
        low_stock = await self.get_low_stock_products(threshold=5)
        
        # 자동 재주문 추천
        reorder_suggestions = []
        for product in low_stock:
            if await self.should_reorder(product):
                suggestion = await self.calculate_reorder_quantity(product)
                reorder_suggestions.append(suggestion)
        
        # 알림 발송
        if reorder_suggestions:
            await self.send_reorder_alert(reorder_suggestions)
            
    async def should_reorder(self, product):
        """재주문 여부 판단"""
        # 판매 속도, 시즌성, 트렌드 등을 고려한 AI 판단
        sales_velocity = await self.get_sales_velocity(product['id'])
        trend_score = await self.get_trend_score(product['category'])
        
        return sales_velocity > 0.5 and trend_score > 0.3
```

이 가이드를 통해 도매처 연동 모듈의 모든 기능을 완전히 활용할 수 있습니다. 추가 질문이나 커스터마이징이 필요한 경우 언제든 문의해 주세요!