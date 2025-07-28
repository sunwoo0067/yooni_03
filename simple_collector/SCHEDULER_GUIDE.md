# 배치 스케줄러 시스템 가이드

## 시스템 개요

배치 스케줄러는 정기적인 자동화 작업을 관리하는 시스템입니다. 도매처 수집, 이미지 처리, 데이터 정리 등의 작업을 자동으로 실행합니다.

### 주요 기능
- ✅ 크론 표현식 기반 스케줄링
- ✅ 작업 실행 관리 및 모니터링
- ✅ 오류 처리 및 재시도
- ✅ 실행 히스토리 추적
- ✅ 웹 UI 관리 인터페이스
- ✅ 동적 작업 추가/삭제
- ✅ 타임아웃 및 리소스 관리

## 웹 UI 사용법

### 스케줄러 관리 페이지
http://localhost:4173/scheduler

#### 기본 기능

1. **스케줄러 시작/중지**
   - 시작/중지 버튼으로 전체 스케줄러 제어
   - 실행 상태 실시간 모니터링

2. **기본 작업 생성**
   - "기본 작업 생성" 버튼으로 권장 작업들 자동 생성
   - 도매처 수집, 베스트셀러 수집, 이미지 처리 등

3. **작업 관리**
   - 작업별 활성화/비활성화 스위치
   - 실행 히스토리 확인
   - 작업 삭제

4. **커스텀 작업 생성**
   - "작업 추가" 버튼으로 새 작업 생성
   - 크론 표현식으로 실행 시간 설정
   - JSON 형식으로 매개변수 설정

## 기본 제공 작업들

### 1. 도매처 상품 수집
- **함수**: `collect_wholesale_products`
- **실행 시간**: 매일 새벽 2시
- **설명**: 모든 도매처에서 상품 정보 수집
- **매개변수**:
  ```json
  {
    "suppliers": ["zentrade", "ownerclan", "domeggook", "domomae"],
    "test_mode": false
  }
  ```

### 2. 베스트셀러 수집
- **함수**: `collect_bestsellers`
- **실행 시간**: 매일 오후 2시
- **설명**: 쿠팡, 네이버 등 마켓플레이스 베스트셀러 수집
- **매개변수**:
  ```json
  {
    "marketplaces": ["coupang", "naver"]
  }
  ```

### 3. 이미지 처리
- **함수**: `process_images`
- **실행 시간**: 매일 새벽 3시
- **설명**: 도매처 상품 이미지 최적화 및 호스팅
- **매개변수**:
  ```json
  {
    "limit": 100,
    "suppliers": null
  }
  ```

### 4. 데이터 정리
- **함수**: `cleanup_old_data`
- **실행 시간**: 주 1회 일요일 새벽 1시
- **설명**: 30일 이상 된 로그 및 이미지 정리
- **매개변수**:
  ```json
  {
    "days": 30
  }
  ```

### 5. 일일 리포트 생성
- **함수**: `generate_daily_report`
- **실행 시간**: 매일 오후 11시
- **설명**: 상품 통계 및 수집 현황 리포트 생성
- **매개변수**: `{}`

### 6. 트렌드 분석
- **함수**: `analyze_trends`
- **실행 시간**: 매일 오후 6시
- **설명**: AI 기반 시장 트렌드 분석
- **매개변수**: `{}`

## API 사용법

### 스케줄러 제어

#### 스케줄러 시작
```bash
curl -X POST "http://localhost:8000/scheduler/start"
```

#### 스케줄러 중지
```bash
curl -X POST "http://localhost:8000/scheduler/stop"
```

#### 상태 확인
```bash
curl "http://localhost:8000/scheduler/status"
```

### 작업 관리

#### 작업 목록 조회
```bash
curl "http://localhost:8000/scheduler/jobs"
```

#### 새 작업 생성
```bash
curl -X POST "http://localhost:8000/scheduler/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "커스텀 수집 작업",
    "job_type": "COLLECTION",
    "function_name": "collect_wholesale_products",
    "cron_expression": "0 3 * * *",
    "parameters": {"test_mode": false},
    "max_retries": 3,
    "timeout_seconds": 3600
  }'
```

#### 기본 작업 생성
```bash
curl -X POST "http://localhost:8000/scheduler/jobs/presets"
```

#### 작업 활성화/비활성화
```bash
curl -X PATCH "http://localhost:8000/scheduler/jobs/1" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

#### 실행 히스토리 조회
```bash
curl "http://localhost:8000/scheduler/jobs/1?limit=10"
```

## 크론 표현식 가이드

크론 표현식 형식: `분 시 일 월 요일`

### 예시
- `0 2 * * *` - 매일 새벽 2시
- `30 14 * * *` - 매일 오후 2시 30분
- `0 */2 * * *` - 2시간마다
- `0 9 * * 1-5` - 평일 오전 9시
- `0 0 1 * *` - 매월 1일 자정
- `0 6 * * 0` - 매주 일요일 오전 6시

### 특수 문자
- `*` - 모든 값
- `*/n` - n간격으로
- `1,3,5` - 특정 값들
- `1-5` - 범위

## 프로그래밍 사용법

### 스케줄러 직접 사용
```python
from services.scheduler.scheduler_core import BatchScheduler, JobType, CronSchedule

# 스케줄러 생성
scheduler = BatchScheduler()

# 작업 생성
job_id = scheduler.create_job(
    name="테스트 작업",
    job_type=JobType.COLLECTION,
    function_name="collect_wholesale_products",
    schedule=CronSchedule.daily(hour=2, minute=0),
    parameters={"test_mode": True}
)

# 스케줄러 시작 (비동기)
await scheduler.start()
```

### 커스텀 작업 함수 추가
```python
# 새로운 작업 함수 정의
async def my_custom_job(param1: str, param2: int = 10) -> dict:
    # 작업 로직
    return {
        'status': 'completed',
        'result': f'처리완료: {param1}',
        'count': param2
    }

# 함수 등록
scheduler.register_job_function('my_custom_job', my_custom_job)

# 작업 생성
job_id = scheduler.create_job(
    name="커스텀 작업",
    job_type=JobType.ANALYSIS,
    function_name="my_custom_job",
    schedule=CronSchedule.hourly(minute=15),
    parameters={"param1": "테스트", "param2": 20}
)
```

## 모니터링

### 로그 확인
```bash
# 스케줄러 관련 로그
tail -f logs/app.log | grep -i "scheduler\|job"

# 특정 작업 로그
tail -f logs/app.log | grep "작업이름"
```

### 상태 확인
- 웹 UI에서 실시간 모니터링
- API로 자동 모니터링 가능
- 실행 히스토리 추적

### 알림 설정 (선택사항)
```python
# 작업 실패 시 알림 (예시)
def send_notification(job_name: str, error: str):
    # 이메일, 슬랙 등으로 알림 발송
    pass

# 스케줄러에 알림 핸들러 추가
# (실제 구현 시 확장 가능)
```

## 문제 해결

### 작업이 실행되지 않을 때
1. 스케줄러가 실행 중인지 확인
2. 작업이 활성화되어 있는지 확인
3. 크론 표현식이 올바른지 확인
4. 다음 실행 시간이 미래인지 확인

### 작업이 실패할 때
1. 실행 히스토리에서 오류 메시지 확인
2. 함수 매개변수 확인
3. 의존성 서비스 상태 확인 (API 서버 등)
4. 타임아웃 설정 확인

### 성능 문제
1. 동시 실행 작업 수 제한
2. 타임아웃 시간 조정
3. 대용량 작업은 배치 크기 조정

## 테스트

### 종합 테스트 실행
```bash
python test_scheduler.py
```

테스트 항목:
1. ✅ 크론 스케줄 파싱
2. ✅ 작업 생성/삭제
3. ✅ API 엔드포인트
4. ✅ 작업 실행
5. ✅ 오류 처리

## 보안 고려사항

1. **권한 관리**: 중요한 작업은 적절한 권한으로 실행
2. **매개변수 검증**: 사용자 입력 매개변수 검증
3. **리소스 제한**: 메모리 및 CPU 사용량 모니터링
4. **로그 보안**: 민감 정보 로그 출력 방지

## 자동 시작 설정

### Windows 서비스 등록 (선택사항)
```batch
# 스케줄러 자동 시작 스크립트
@echo off
cd /d D:\new\win_with_claude\yooni_03\simple_collector
python -c "
import asyncio
import requests
requests.post('http://localhost:8000/scheduler/start')
print('스케줄러가 시작되었습니다.')
"
```

### 시작 시 자동 실행
main.py의 startup 이벤트에서 스케줄러 자동 시작 (선택사항)