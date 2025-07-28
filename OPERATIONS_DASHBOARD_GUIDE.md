# 운영 대시보드 가이드 (Operations Dashboard Guide)

## 개요

드롭쉬핑 시스템의 운영 대시보드는 실시간 모니터링, 비즈니스 분석, 시스템 관리를 위한 통합 인터페이스입니다.

## 주요 기능

### 1. 실시간 모니터링
- **WebSocket 기반 실시간 업데이트**: 모든 메트릭이 실시간으로 갱신
- **시스템 상태 모니터링**: API, 데이터베이스, Redis, 외부 서비스 상태
- **리소스 사용량**: CPU, 메모리, 디스크, 네트워크 모니터링

### 2. 비즈니스 메트릭
- **매출 분석**: 일별/월별 매출 추이, 성장률
- **주문 현황**: 플랫폼별 주문 분포, 상태별 현황
- **고객 분석**: 재구매율, 전환율, 고객 생애가치(LTV)
- **상품 순위**: 베스트셀러, 카테고리별 판매 현황

### 3. 성능 메트릭
- **응답 시간**: API 엔드포인트별 응답 시간
- **처리량**: 초당 요청 수, 일별 처리량
- **에러율**: 시간대별 에러 발생률
- **캐시 성능**: 캐시 히트율, 미스율

### 4. 알림 관리
- **자동 알림**: 임계값 기반 자동 알림 생성
- **알림 우선순위**: Critical, Warning, Info
- **알림 처리**: 확인, 해결, 무시 워크플로우
- **알림 이력**: 과거 알림 조회 및 분석

### 5. 로그 뷰어
- **실시간 로그 스트리밍**: 애플리케이션 로그 실시간 확인
- **로그 필터링**: 레벨, 서비스, 시간대별 필터
- **로그 검색**: 키워드 검색 기능
- **로그 다운로드**: 필터된 로그 내보내기

## 설치 및 설정

### 1. 백엔드 설정

```python
# backend/app/api/v1/__init__.py에 라우터 추가
from app.api.v1.endpoints import operations_dashboard

api_router.include_router(
    operations_dashboard.router,
    prefix="/operations-dashboard",
    tags=["operations-dashboard"]
)
```

### 2. 프론트엔드 설정

```typescript
// frontend/src/router/index.tsx에 라우트 추가
import OperationsDashboard from '@pages/Dashboard/OperationsDashboard';

{
  path: '/operations',
  element: <ProtectedRoute><OperationsDashboard /></ProtectedRoute>
}
```

### 3. 환경 변수 설정

```bash
# .env.production
REDIS_URL=redis://localhost:6379/0
WEBSOCKET_URL=wss://api.yourdomain.com/ws
DASHBOARD_REFRESH_INTERVAL=5000  # 5초
ALERT_CHECK_INTERVAL=60000       # 1분
```

## 사용 방법

### 1. 대시보드 접속

```
https://app.yourdomain.com/operations
```

### 2. 실시간 모니터링

대시보드에 접속하면 자동으로 WebSocket 연결이 수립되고 실시간 데이터가 표시됩니다.

### 3. 데이터 내보내기

우측 상단의 내보내기 버튼을 클릭하여 데이터를 다운로드할 수 있습니다:
- CSV: 엑셀에서 바로 열 수 있는 형식
- Excel: 서식이 적용된 엑셀 파일
- JSON: 프로그래밍 용도의 JSON 형식

### 4. 알림 관리

알림 탭에서:
1. 새로운 알림 확인
2. 알림 우선순위별 필터링
3. 알림 확인 및 해결 처리
4. 알림 규칙 설정

## API 엔드포인트

### 메트릭 조회
```
GET /api/v1/operations-dashboard/metrics?period=24h
```

### 건강 상태 확인
```
GET /api/v1/operations-dashboard/health
```

### 알림 관리
```
GET /api/v1/operations-dashboard/alerts
POST /api/v1/operations-dashboard/alerts
PUT /api/v1/operations-dashboard/alerts/{alert_id}
```

### 로그 조회
```
GET /api/v1/operations-dashboard/logs?level=error&limit=100
```

### WebSocket 연결
```
WS /api/v1/operations-dashboard/ws
```

## WebSocket 채널

### 구독 가능한 채널

```javascript
// 시스템 메트릭
{
  "action": "subscribe",
  "channel": "system_metrics"
}

// 비즈니스 메트릭
{
  "action": "subscribe",
  "channel": "business_metrics"
}

// 알림
{
  "action": "subscribe",
  "channel": "alerts"
}

// 로그
{
  "action": "subscribe",
  "channel": "logs"
}
```

## 커스터마이징

### 1. 새로운 메트릭 추가

```python
# backend/app/services/monitoring/operations_dashboard_service.py

async def get_custom_metric(self) -> Dict[str, Any]:
    """커스텀 메트릭 추가"""
    return {
        "metric_name": "custom_value",
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 2. 새로운 차트 추가

```typescript
// frontend/src/components/Dashboard/CustomChart.tsx

import { RealtimeChart } from './RealtimeChart';

export const CustomChart: React.FC = () => {
  const data = useDashboardData('/custom-metric');
  
  return (
    <RealtimeChart
      data={data}
      title="Custom Metric"
      yAxisLabel="Value"
    />
  );
};
```

### 3. 알림 규칙 추가

```python
# backend/app/services/monitoring/alert_manager.py

ALERT_RULES = [
    {
        "name": "custom_alert",
        "condition": lambda metrics: metrics["custom_value"] > 100,
        "severity": "warning",
        "message": "Custom value exceeded threshold"
    }
]
```

## 성능 최적화

### 1. 캐싱 전략

- Redis를 사용한 메트릭 캐싱
- 5초 TTL로 실시간성과 성능 균형
- 자주 변경되지 않는 데이터는 더 긴 TTL 설정

### 2. 데이터 집계

- 실시간 데이터는 1분 단위로 집계
- 과거 데이터는 시간/일 단위로 집계
- 인덱스 최적화로 쿼리 성능 향상

### 3. WebSocket 최적화

- 채널별 구독으로 불필요한 데이터 전송 방지
- 메시지 배치 처리로 네트워크 부하 감소
- 자동 재연결로 안정성 확보

## 트러블슈팅

### WebSocket 연결 실패

1. 네트워크 연결 확인
2. WebSocket URL 설정 확인
3. 프록시/방화벽 설정 확인
4. 브라우저 콘솔에서 에러 메시지 확인

### 데이터 업데이트 지연

1. Redis 연결 상태 확인
2. 백엔드 로그에서 에러 확인
3. 네트워크 지연 확인
4. 캐시 TTL 설정 검토

### 높은 리소스 사용량

1. 불필요한 채널 구독 해제
2. 데이터 새로고침 간격 조정
3. 차트 렌더링 최적화
4. 메모리 누수 확인

## 보안 고려사항

1. **인증**: 대시보드 접근에는 반드시 인증 필요
2. **권한**: 관리자 권한이 있는 사용자만 접근 가능
3. **암호화**: WebSocket 연결은 WSS(TLS) 사용
4. **감사**: 모든 대시보드 액션은 로그에 기록

## 모니터링 모범 사례

1. **정기 점검**: 매일 아침 대시보드 확인
2. **알림 설정**: 중요 메트릭에 대한 알림 설정
3. **트렌드 분석**: 주간/월간 트렌드 분석
4. **리포트 생성**: 정기적인 성과 리포트 생성
5. **이상 징후 감지**: 비정상적인 패턴 조기 발견

## 다음 단계

1. **모바일 앱**: 모바일 전용 대시보드 앱 개발
2. **AI 분석**: 머신러닝 기반 이상 감지
3. **예측 분석**: 미래 트렌드 예측 기능
4. **통합 알림**: Slack, Email 등 외부 알림 통합
5. **대시보드 템플릿**: 사용자 정의 대시보드 템플릿