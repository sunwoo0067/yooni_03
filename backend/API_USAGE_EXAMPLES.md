# 멀티 계정 관리 API 사용 가이드

온라인 셀러를 위한 멀티 플랫폼 계정 관리 API의 사용 방법을 설명합니다.

## 기본 API 정보

- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json`
- **Authentication**: Bearer Token (JWT)

## API 엔드포인트 목록

### 1. 플랫폼 계정 생성
**POST** `/platform-accounts/`

#### 쿠팡 계정 생성 예시
```json
{
  "platform_type": "coupang",
  "account_name": "내 쿠팡 스토어",
  "account_id": "my_coupang_store",
  "store_name": "ABC 전자제품",
  "credentials": {
    "access_key": "your_coupang_access_key",
    "secret_key": "your_coupang_secret_key",
    "vendor_id": "A12345678"
  },
  "sync_enabled": true,
  "auto_pricing_enabled": false,
  "auto_inventory_sync": true,
  "daily_api_quota": 5000,
  "commission_rate": 0.15
}
```

#### 네이버 스마트스토어 계정 생성 예시
```json
{
  "platform_type": "naver",
  "account_name": "네이버 스마트스토어",
  "account_id": "naver_store_001",
  "store_name": "XYZ 패션몰",
  "credentials": {
    "client_id": "your_naver_client_id",
    "client_secret": "your_naver_client_secret",
    "store_id": "12345"
  },
  "sync_enabled": true,
  "auto_inventory_sync": true,
  "commission_rate": 0.12
}
```

#### 11번가 계정 생성 예시
```json
{
  "platform_type": "11st",
  "account_name": "11번가 스토어",
  "account_id": "11st_store_001",
  "store_name": "DEF 생활용품",
  "credentials": {
    "api_key": "your_11st_api_key",
    "secret_key": "your_11st_secret_key",
    "seller_id": "seller123"
  },
  "sync_enabled": true,
  "daily_api_quota": 3000
}
```

### 2. 계정 목록 조회
**GET** `/platform-accounts/`

#### 쿼리 파라미터
- `platform_type`: 플랫폼 타입으로 필터링 (선택사항)
- `status`: 계정 상태로 필터링 (선택사항)
- `skip`: 건너뛸 레코드 수 (기본값: 0)
- `limit`: 최대 반환 레코드 수 (기본값: 100)

#### 예시 요청
```bash
GET /platform-accounts/?platform_type=coupang&status=active&limit=10
```

#### 응답 예시
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "platform_type": "coupang",
    "account_name": "내 쿠팡 스토어",
    "store_name": "ABC 전자제품",
    "status": "active",
    "health_status": "healthy",
    "sync_enabled": true,
    "last_sync_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-01T09:00:00Z"
  }
]
```

### 3. 특정 계정 조회
**GET** `/platform-accounts/{account_id}`

#### 응답 예시
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-uuid",
  "platform_type": "coupang",
  "account_name": "내 쿠팡 스토어",
  "account_id": "my_coupang_store",
  "store_name": "ABC 전자제품",
  "status": "active",
  "health_status": "healthy",
  "sync_enabled": true,
  "auto_pricing_enabled": false,
  "auto_inventory_sync": true,
  "daily_api_quota": 5000,
  "daily_api_used": 234,
  "commission_rate": 0.15,
  "error_count": 0,
  "consecutive_errors": 0,
  "has_credentials": true,
  "credentials_status": "valid",
  "created_at": "2024-01-01T09:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_sync_at": "2024-01-15T10:30:00Z",
  "last_health_check_at": "2024-01-15T10:25:00Z"
}
```

### 4. 계정 정보 수정
**PUT** `/platform-accounts/{account_id}`

#### 예시 요청
```json
{
  "account_name": "수정된 쿠팡 스토어",
  "sync_enabled": false,
  "auto_pricing_enabled": true,
  "daily_api_quota": 7000,
  "credentials": {
    "access_key": "new_access_key",
    "secret_key": "new_secret_key"
  }
}
```

### 5. 계정 삭제
**DELETE** `/platform-accounts/{account_id}`

응답: `204 No Content`

### 6. 연결 테스트
**POST** `/platform-accounts/{account_id}/test`

#### 응답 예시
```json
{
  "success": true,
  "message": "Coupang connection successful",
  "response_time_ms": 245,
  "api_version": "v1",
  "rate_limit_remaining": 4766,
  "tested_at": "2024-01-15T10:35:00Z"
}
```

### 7. 지원 플랫폼 목록
**GET** `/platform-accounts/platforms/supported`

#### 응답 예시
```json
[
  {
    "platform_type": "coupang",
    "display_name": "쿠팡",
    "description": "대한민국 대표 이커머스 플랫폼",
    "website_url": "https://www.coupang.com",
    "api_documentation_url": "https://developers.coupang.com",
    "required_credentials": ["access_key", "secret_key", "vendor_id"],
    "optional_credentials": ["store_name"],
    "supports_oauth": false,
    "rate_limits": {
      "requests_per_minute": 100,
      "daily_quota": 10000
    },
    "features": ["product_management", "order_management", "inventory_sync"]
  },
  {
    "platform_type": "naver",
    "display_name": "네이버 스마트스토어",
    "description": "네이버 쇼핑 플랫폼",
    "required_credentials": ["client_id", "client_secret", "store_id"],
    "supports_oauth": true,
    "features": ["product_management", "order_management", "review_management"]
  }
]
```

### 8. 계정 통계
**GET** `/platform-accounts/statistics/summary`

#### 응답 예시
```json
{
  "total_accounts": 5,
  "active_accounts": 4,
  "healthy_accounts": 3,
  "accounts_with_errors": 1,
  "platform_breakdown": {
    "coupang": 2,
    "naver": 2,
    "11st": 1
  },
  "last_updated": "2024-01-15T10:40:00Z"
}
```

### 9. 일괄 연결 테스트
**POST** `/platform-accounts/bulk/test-connections`

#### 요청 예시
```json
{
  "operation": "test_connections",
  "account_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "987fcdeb-51a2-43d7-8f65-123456789abc"
  ]
}
```

#### 응답 예시
```json
{
  "operation": "connection_test",
  "total_accounts": 2,
  "successful_accounts": 1,
  "failed_accounts": 1,
  "results": [
    {
      "account_id": "123e4567-e89b-12d3-a456-426614174000",
      "success": true,
      "message": "Coupang connection successful",
      "response_time_ms": 245
    },
    {
      "account_id": "987fcdeb-51a2-43d7-8f65-123456789abc",
      "success": false,
      "message": "Naver API error: 401",
      "error": "Unauthorized"
    }
  ],
  "started_at": "2024-01-15T10:45:00Z",
  "completed_at": "2024-01-15T10:45:30Z"
}
```

### 10. 일괄 동기화 설정 업데이트
**POST** `/platform-accounts/bulk/update-sync-settings`

#### 요청 예시
```json
{
  "operation": "update_sync_settings",
  "account_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "987fcdeb-51a2-43d7-8f65-123456789abc"
  ],
  "parameters": {
    "sync_enabled": true,
    "auto_pricing_enabled": false,
    "auto_inventory_sync": true
  }
}
```

### 11. 동기화 로그 조회
**GET** `/platform-accounts/{account_id}/sync-logs`

#### 응답 예시
```json
[
  {
    "id": "log-uuid",
    "platform_account_id": "123e4567-e89b-12d3-a456-426614174000",
    "sync_type": "products",
    "status": "completed",
    "started_at": "2024-01-15T09:00:00Z",
    "completed_at": "2024-01-15T09:05:30Z",
    "total_items": 100,
    "processed_items": 100,
    "success_count": 95,
    "error_count": 5,
    "success_rate": 95.0,
    "processing_time_seconds": 330,
    "api_calls_made": 25
  }
]
```

### 12. 헬스 체크 실행
**POST** `/platform-accounts/health-check/run`

#### 쿼리 파라미터
- `all_users`: 모든 사용자 계정 체크 여부 (기본값: false, 관리자만)

#### 응답 예시
```json
{
  "message": "Health checks scheduled for your accounts"
}
```

## 에러 응답

API는 표준 HTTP 상태 코드를 사용합니다:

- `200`: 성공
- `201`: 생성 성공
- `204`: 삭제 성공
- `400`: 잘못된 요청
- `401`: 인증 실패
- `403`: 권한 없음
- `404`: 리소스 없음
- `422`: 유효성 검사 실패
- `500`: 서버 오류

#### 에러 응답 예시
```json
{
  "detail": "Platform account not found"
}
```

#### 유효성 검사 에러 예시
```json
{
  "detail": [
    {
      "loc": ["body", "credentials", "access_key"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 보안 고려사항

1. **API 키 암호화**: 모든 민감한 정보는 AES-256으로 암호화되어 저장됩니다.
2. **접근 제어**: 사용자는 자신의 계정만 조회/수정할 수 있습니다.
3. **감사 로그**: 모든 중요한 작업은 로그로 기록됩니다.
4. **속도 제한**: API 호출에 대한 속도 제한이 적용됩니다.

## 환경 설정

`.env` 파일에 다음 설정이 필요합니다:

```env
ENCRYPTION_MASTER_KEY=your-very-secure-encryption-master-key-32-chars-minimum
DATABASE_URL=postgresql://user:password@localhost:5432/multi_seller_db
JWT_SECRET_KEY=your-jwt-secret-key
```

## 프로덕션 배포 시 주의사항

1. **암호화 키 관리**: `ENCRYPTION_MASTER_KEY`는 안전하게 관리하고 정기적으로 교체하세요.
2. **데이터베이스 백업**: 암호화된 데이터의 백업 및 복구 계획을 수립하세요.
3. **모니터링**: 계정 상태와 API 성능을 모니터링하세요.
4. **로그 관리**: 민감한 정보가 로그에 노출되지 않도록 주의하세요.
5. **네트워크 보안**: HTTPS를 사용하고 적절한 방화벽 규칙을 설정하세요.