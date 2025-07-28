# 모니터링 및 로깅 시스템 가이드

## 개요

이 문서는 애플리케이션의 모니터링 및 로깅 시스템 사용 방법을 설명합니다.

## 주요 구성 요소

### 1. 메트릭 수집기 (Metrics Collector)
- **위치**: `app/services/monitoring/metrics_collector.py`
- **기능**: 
  - API 응답 시간 추적
  - 데이터베이스 쿼리 성능 모니터링
  - 캐시 히트율 측정
  - 비즈니스 메트릭 수집 (주문, 매출 등)

### 2. 헬스 체커 (Health Checker)
- **위치**: `app/services/monitoring/health_checker.py`
- **기능**:
  - 데이터베이스 연결 상태 확인
  - Redis 연결 상태 확인
  - 디스크 공간 모니터링
  - 메모리 사용량 체크
  - 외부 API 상태 확인

### 3. 알림 관리자 (Alert Manager)
- **위치**: `app/services/monitoring/alert_manager.py`
- **기능**:
  - 임계값 기반 알림
  - 이메일/슬랙 알림 전송
  - 알림 규칙 관리
  - 알림 이력 저장

### 4. 로깅 미들웨어
- **위치**: `app/middleware/logging_middleware.py`
- **기능**:
  - 모든 HTTP 요청/응답 로깅
  - 성능 메트릭 자동 수집
  - 느린 요청 감지

## API 엔드포인트

### 헬스 체크
```bash
# 시스템 전체 헬스 체크
GET /api/v1/monitoring/health

# Kubernetes readiness probe
GET /api/v1/monitoring/health/ready

# Kubernetes liveness probe
GET /api/v1/monitoring/health/live
```

### 메트릭 조회
```bash
# 전체 메트릭 요약
GET /api/v1/monitoring/metrics

# API 메트릭
GET /api/v1/monitoring/metrics/api

# 비즈니스 메트릭
GET /api/v1/monitoring/metrics/business
```

### 알림 관리
```bash
# 알림 규칙 목록
GET /api/v1/monitoring/alerts/rules

# 알림 규칙 생성
POST /api/v1/monitoring/alerts/rules

# 알림 규칙 삭제
DELETE /api/v1/monitoring/alerts/rules/{rule_name}

# 알림 이력 조회
GET /api/v1/monitoring/alerts/history?hours=24

# 알림 규칙 테스트
POST /api/v1/monitoring/alerts/test/{rule_name}?test_value=10.5
```

### 대시보드 데이터
```bash
# 모니터링 대시보드용 종합 데이터
GET /api/v1/monitoring/dashboard
```

## 사용 예제

### 1. 메트릭 수집

```python
from app.services.monitoring import metrics_collector, track_time

# 카운터 증가
metrics_collector.increment_counter("custom.event.count")

# 게이지 값 기록
metrics_collector.record_gauge("queue.size", 42)

# 타이밍 기록
metrics_collector.record_timing("operation.duration", 0.123)

# 함수 실행 시간 자동 추적
@track_time("function.execution.time")
async def my_function():
    # 함수 로직
    pass
```

### 2. 캐시 메트릭

```python
from app.services.monitoring import CacheMetrics

# 캐시 히트/미스 기록
await CacheMetrics.record_hit()
await CacheMetrics.record_miss()

# 캐시 히트율 확인
hit_rate = CacheMetrics.get_hit_rate()
```

### 3. 커스텀 알림 규칙

```python
from app.services.monitoring import alert_manager, AlertRule, AlertSeverity, AlertChannel

# 새 알림 규칙 추가
alert_manager.add_rule(
    AlertRule(
        name="high_order_value",
        metric_name="business.order.value",
        condition=lambda x: x > 10000,  # 10,000 이상
        severity=AlertSeverity.INFO,
        channels=[AlertChannel.SLACK],
        message_template="고액 주문 발생: ${value}",
        cooldown_minutes=5
    )
)
```

## 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```env
# 관리자 이메일 (알림 수신용)
ADMIN_EMAIL=admin@example.com

# 슬랙 웹훅 URL
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# 커스텀 웹훅 URL
ALERT_WEBHOOK_URL=https://your-monitoring-system.com/webhook

# 외부 API 엔드포인트 (헬스 체크용)
PAYMENT_API_URL=https://payment-gateway.com/health
EMAIL_SERVICE_URL=https://email-service.com/health
```

## 기본 알림 규칙

시스템은 다음과 같은 기본 알림 규칙을 포함합니다:

1. **API 에러율**: 10% 이상일 때 (ERROR)
2. **API 응답 시간**: P95가 1초 이상일 때 (WARNING)
3. **디스크 공간**: 85% 이상 사용 시 (WARNING)
4. **메모리 사용량**: 90% 이상일 때 (CRITICAL)
5. **DB 연결 풀**: 가용률 10% 미만일 때 (CRITICAL)
6. **캐시 히트율**: 70% 미만일 때 (INFO)

## 모니터링 대시보드

대시보드 API는 다음 정보를 제공합니다:

- 시스템 헬스 상태
- API 에러율 및 요청 수
- 캐시 히트율
- 최근 알림 목록
- 시스템 가동 시간

## 로그 형식

모든 로그는 다음 정보를 포함합니다:

- Request ID: 요청 추적용 고유 ID
- Method & Path: HTTP 메서드와 경로
- Status Code: 응답 상태 코드
- Duration: 요청 처리 시간 (밀리초)
- Client IP: 클라이언트 IP 주소
- User Agent: 브라우저/클라이언트 정보

## 성능 최적화

- 메트릭은 메모리에 저장되며 최근 1000개만 유지
- 타이밍 데이터는 24시간 동안만 보관
- 느린 요청은 Redis에 7일간 저장
- 알림은 쿨다운 기간을 통해 중복 방지

## 문제 해결

### 알림이 발송되지 않을 때
1. 환경 변수 설정 확인
2. 알림 채널 설정 확인
3. 알림 규칙의 조건 확인
4. 쿨다운 시간 확인

### 메트릭이 수집되지 않을 때
1. 메트릭 수집 서비스 시작 확인
2. 로깅 미들웨어 등록 확인
3. 스킵 경로 설정 확인

### 헬스 체크 실패 시
1. 각 컴포넌트별 상태 확인
2. 데이터베이스 연결 확인
3. Redis 연결 확인
4. 디스크 공간 확인