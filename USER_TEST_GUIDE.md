# 🧪 드롭쉬핑 시스템 사용자 테스트 가이드

## 🚀 시작하기

### 1. 서버 시작
```bash
cd backend
python main.py
```

서버가 성공적으로 시작되면 다음 메시지가 표시됩니다:
```
INFO: Application startup completed successfully
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 2. 시스템 상태 확인
브라우저에서 http://localhost:8000/health 접속하여 시스템 상태를 확인하세요.

예상 응답:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-26T17:12:32.384111"
}
```

## 📚 API 문서 접속

### Swagger UI (추천)
- URL: http://localhost:8000/docs
- 모든 API를 대화형으로 테스트할 수 있습니다
- "Try it out" 버튼으로 실제 API 호출 가능

### ReDoc
- URL: http://localhost:8000/redoc  
- 깔끔한 문서 형태로 API 확인 가능

## 🔍 핵심 기능 테스트

### 1. 플랫폼 계정 관리

#### 계정 목록 조회
```bash
curl -X GET "http://localhost:8000/api/v1/platform-accounts/" \
  -H "accept: application/json"
```

#### 새 플랫폼 계정 생성
```bash
curl -X POST "http://localhost:8000/api/v1/platform-accounts/" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "platform_type": "coupang",
    "account_name": "테스트 쿠팡 계정",
    "api_credentials": {
      "access_key": "your_access_key",
      "secret_key": "your_secret_key"
    },
    "is_active": true
  }'
```

### 2. 상품 관리

#### 상품 목록 조회
```bash
curl -X GET "http://localhost:8000/api/v1/products/" \
  -H "accept: application/json"
```

#### 새 상품 등록
```bash
curl -X POST "http://localhost:8000/api/v1/products/" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "테스트 상품",
    "description": "테스트용 상품입니다",
    "category": "electronics",
    "price": 29900,
    "stock_quantity": 100,
    "sku": "TEST-001"
  }'
```

### 3. 주문 관리

#### 주문 목록 조회
```bash
curl -X GET "http://localhost:8000/api/v1/orders/" \
  -H "accept: application/json"
```

## 🧪 테스트 시나리오

### 시나리오 1: 기본 워크플로우
1. 플랫폼 계정 생성
2. 상품 등록
3. 상품 목록 확인
4. 플랫폼별 상품 등록 상태 확인

### 시나리오 2: 대량 작업
1. 여러 플랫폼 계정 생성
2. 대량 상품 등록 (bulk API 사용)
3. 성능 모니터링

### 시나리오 3: 에러 처리
1. 잘못된 데이터로 API 호출
2. 인증 없이 보호된 엔드포인트 접근
3. 시스템 응답 확인

## 📊 성능 테스트

### 응답 시간 측정
```bash
# 헬스체크 응답 시간
time curl -s http://localhost:8000/health

# API 응답 시간  
time curl -s http://localhost:8000/api/v1/products/
```

### 동시 요청 테스트
```bash
# 10개 동시 요청
for i in {1..10}; do
  curl -s http://localhost:8000/health &
done
wait
```

## 🐛 문제 해결

### 자주 발생하는 문제

#### 1. 서버 시작 실패
- 포트 8000이 이미 사용 중인지 확인
- 데이터베이스 연결 상태 확인
- 로그 파일에서 에러 메시지 확인

#### 2. API 응답 없음
- 서버가 실행 중인지 확인
- 올바른 URL 사용 여부 확인
- 네트워크 연결 상태 확인

#### 3. 데이터베이스 오류
- PostgreSQL 서버 상태 확인
- 데이터베이스 연결 정보 확인
- 필요한 테이블이 생성되었는지 확인

## 📈 피드백 수집

테스트 중 발견한 이슈나 개선사항을 다음과 같이 기록해주세요:

### 성능 관련
- API 응답 시간
- 메모리 사용량
- CPU 사용률

### 기능 관련  
- 예상대로 동작하지 않는 기능
- 누락된 기능
- 사용성 개선 사항

### 안정성 관련
- 에러 발생 빈도
- 시스템 크래시
- 데이터 정합성 문제

## 🔄 다음 단계

사용자 테스트 완료 후 다음 기능들을 단계적으로 활성화할 예정입니다:

1. **AI 기능 재활성화**
2. **고급 동기화 기능**
3. **실시간 모니터링**
4. **추가 마켓플레이스 연동**

---

## 📞 지원

테스트 중 문제가 발생하면 다음을 확인해주세요:

1. **로그 파일**: `backend/server.log`
2. **API 문서**: http://localhost:8000/docs
3. **시스템 상태**: http://localhost:8000/health

**좋은 테스트 되세요!** 🚀