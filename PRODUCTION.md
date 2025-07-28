# 🏭 운영 환경 가이드

이 문서는 Dropshipping Automation System의 운영 환경 관리 및 운영 절차를 다룹니다.

## 목차

1. [시스템 아키텍처](#시스템-아키텍처)
2. [운영 절차](#운영-절차)
3. [모니터링 및 알림](#모니터링-및-알림)
4. [성능 관리](#성능-관리)
5. [보안 운영](#보안-운영)
6. [장애 대응](#장애-대응)
7. [유지보수](#유지보수)
8. [백업 및 재해복구](#백업-및-재해복구)

## 시스템 아키텍처

### 인프라 구성

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer (Nginx)                   │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React)  │  Backend API (FastAPI)  │  WebSocket   │
├─────────────────────────────────────────────────────────────┤
│     PostgreSQL     │      Redis Cache        │   Task Queue │
├─────────────────────────────────────────────────────────────┤
│    Prometheus      │      Grafana           │   Log Aggreg  │
├─────────────────────────────────────────────────────────────┤
│              Docker Containers (Ubuntu Server)              │
└─────────────────────────────────────────────────────────────┘
```

### 서비스 구성

| 서비스 | 컨테이너명 | 포트 | 역할 |
|--------|------------|------|------|
| Nginx | dropshipping_nginx | 80, 443 | 리버스 프록시, SSL 종단 |
| Frontend | dropshipping_frontend | 3000 | React SPA |
| Backend | dropshipping_backend | 8000 | FastAPI 애플리케이션 |
| PostgreSQL | dropshipping_db | 5432 | 주 데이터베이스 |
| Redis | dropshipping_redis | 6379 | 캐시, 세션 저장소 |
| Prometheus | dropshipping_prometheus | 9090 | 메트릭 수집 |
| Grafana | dropshipping_grafana | 3000 | 대시보드 |

## 운영 절차

### 일일 운영 체크리스트

#### 오전 체크 (09:00)

```bash
# 1. 시스템 상태 확인
python3 scripts/health_check.py --format table

# 2. 리소스 사용량 확인
docker stats --no-stream

# 3. 로그 에러 확인
docker compose -f docker-compose.prod.yml logs --since 24h | grep -i error

# 4. 백업 상태 확인
ls -la backups/ | tail -5

# 5. SSL 인증서 만료일 확인
openssl x509 -in nginx/ssl/fullchain.pem -noout -dates
```

#### 저녁 체크 (18:00)

```bash
# 1. 비즈니스 메트릭 확인
curl -s https://yourdomain.com/api/v1/business-metrics | jq '.daily_summary'

# 2. 성능 지표 확인
curl -s https://yourdomain.com/api/v1/system/performance

# 3. 보안 이벤트 확인
grep -i "failed\|blocked\|denied" /var/log/nginx/access.log | tail -10
```

### 주간 운영 체크리스트

#### 매주 월요일

- [ ] 백업 무결성 검증
- [ ] 보안 패치 확인 및 적용
- [ ] 성능 트렌드 분석
- [ ] 용량 계획 검토
- [ ] 장애 로그 분석

```bash
# 주간 리포트 생성
python3 scripts/generate_weekly_report.py --week $(date +%Y-W%V)
```

### 월간 운영 체크리스트

#### 매월 첫째 주

- [ ] 전체 시스템 백업
- [ ] DR(재해복구) 테스트
- [ ] 보안 감사
- [ ] 성능 최적화 검토
- [ ] 라이선스 갱신 확인

## 모니터링 및 알림

### 핵심 메트릭 (SLI/SLO)

#### 가용성 (Availability)
- **SLO:** 99.9% 이상
- **측정:** `(1 - error_rate) * 100`
- **알림:** 99.5% 미만 시 critical

#### 응답 시간 (Latency)
- **SLO:** 95%ile < 1초, 99%ile < 2초
- **측정:** `histogram_quantile(0.95, http_request_duration_seconds)`
- **알림:** 95%ile > 1.5초 시 warning

#### 처리량 (Throughput)
- **SLO:** 1000 RPS 처리 가능
- **측정:** `rate(http_requests_total[5m])`
- **알림:** 평소 대비 50% 감소 시 warning

#### 에러율 (Error Rate)
- **SLO:** < 0.1%
- **측정:** `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100`
- **알림:** > 1% 시 critical

### 알림 채널 설정

#### Slack 알림

**Critical 알림:**
- 서비스 다운
- 데이터베이스 연결 실패
- 높은 에러율 (>5%)
- 디스크 사용량 >90%

**Warning 알림:**
- 높은 응답 시간
- 메모리 사용량 >85%
- SSL 인증서 만료 30일 전

#### 이메일 알림

**Critical 및 Warning 알림 모두 이메일로 전송**

```json
{
  "alertmanager_config": {
    "route": {
      "group_by": ["alertname"],
      "group_wait": "10s",
      "group_interval": "10s",
      "repeat_interval": "1h",
      "receiver": "web.hook"
    },
    "receivers": [
      {
        "name": "web.hook",
        "slack_configs": [
          {
            "api_url": "${SLACK_WEBHOOK}",
            "channel": "#alerts",
            "title": "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}",
            "text": "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
          }
        ]
      }
    ]
  }
}
```

### 대시보드 구성

#### 운영 대시보드 (24/7 모니터링)

1. **System Overview**
   - 전체 서비스 상태
   - 리소스 사용량 (CPU, Memory, Disk)
   - 네트워크 트래픽

2. **Application Metrics**
   - Request Rate & Response Time
   - Error Rate by Endpoint
   - Database Connections
   - Cache Hit Rate

3. **Business Metrics**
   - 주문 처리량
   - 매출 현황
   - 사용자 활동
   - API 사용량

#### 성능 대시보드

1. **Infrastructure Performance**
   - CPU, Memory, Disk I/O
   - Network Performance
   - Container Resource Usage

2. **Application Performance**
   - Slow Queries
   - Cache Performance  
   - API Response Times by Endpoint

3. **Database Performance**
   - Connection Pool Usage
   - Query Performance
   - Lock Statistics
   - Replication Lag (if applicable)

## 성능 관리

### 성능 최적화 기준

#### Database Performance

```sql
-- 주간 성능 분석
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time
FROM pg_stat_statements 
WHERE calls > 100 
ORDER BY total_time DESC 
LIMIT 20;

-- 인덱스 사용률 확인
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'public' 
ORDER BY n_distinct DESC;
```

#### Redis Performance

```bash
# Redis 성능 메트릭
redis-cli --latency-history -i 1

# 메모리 사용률 분석
redis-cli info memory | grep used_memory_human

# Slow log 확인
redis-cli slowlog get 10
```

#### Application Performance

```bash
# API 엔드포인트별 성능 분석
curl -s "https://yourdomain.com/api/v1/metrics" | grep http_request_duration

# 메모리 프로파일링 (개발 환경)
python -m memory_profiler scripts/profile_memory.py
```

### 용량 계획

#### 트래픽 예측

```python
# 월간 성장률 계산
def calculate_growth_rate():
    current_month_requests = get_monthly_requests()
    previous_month_requests = get_previous_monthly_requests()
    growth_rate = (current_month_requests - previous_month_requests) / previous_month_requests
    return growth_rate

# 리소스 필요량 예측
def predict_resource_needs(growth_rate, months=3):
    current_cpu = get_current_cpu_usage()
    current_memory = get_current_memory_usage() 
    predicted_cpu = current_cpu * (1 + growth_rate) ** months
    predicted_memory = current_memory * (1 + growth_rate) ** months
    return predicted_cpu, predicted_memory
```

#### 스케일링 기준

**수평 확장 (Scale Out) 기준:**
- CPU 사용률 > 70% (지속 10분)
- Memory 사용률 > 80% (지속 5분)
- 응답 시간 > 2초 (95%ile, 지속 5분)

**수직 확장 (Scale Up) 기준:**
- 컨테이너 리소스 제한 도달
- I/O 대기 시간 증가
- 캐시 미스율 증가

## 보안 운영

### 보안 모니터링

#### 실시간 보안 모니터링

```bash
# 의심스러운 IP 활동 모니터링
tail -f /var/log/nginx/access.log | grep -E "40[0-9]|50[0-9]" | awk '{print $1}' | sort | uniq -c | sort -nr

# SQL Injection 시도 탐지
grep -i "union\|select\|drop\|insert\|update\|delete" /var/log/nginx/access.log

# 무차별 대입 공격 탐지
grep "POST /api/v1/auth/login" /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | awk '$1 > 10 {print $2}'
```

#### 정기 보안 점검

**매일 수행:**

```bash
# 보안 스캔 실행
python3 scripts/security_scan.py --daily

# 취약점 스캔
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image dropshipping-backend:latest
```

**매주 수행:**

```bash
# 의존성 취약점 점검
safety check
npm audit

# 설정 파일 보안 점검
docker run --rm -v "$PWD:/project" hadolint/hadolint:latest hadolint /project/Dockerfile
```

### 침입 탐지 및 대응

#### Fail2ban 설정

```bash
# Fail2ban 설치 및 설정
sudo apt install fail2ban -y

# Nginx 관련 jail 설정
sudo tee /etc/fail2ban/jail.local << EOF
[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 6

[nginx-badbots]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2
EOF

sudo systemctl restart fail2ban
```

#### 보안 사건 대응 절차

1. **즉시 대응 (0-15분)**
   - 의심스러운 활동 확인
   - 필요시 서비스 일시 중단
   - 로그 수집 및 보존

2. **초기 분석 (15분-1시간)**
   - 공격 유형 식별
   - 영향 범위 평가
   - 임시 차단 조치

3. **상세 분석 (1-4시간)**
   - 취약점 분석
   - 데이터 유출 여부 확인
   - 복구 계획 수립

4. **복구 및 사후 조치 (4시간-)**
   - 시스템 복구
   - 보안 패치 적용
   - 사후 분석 보고서 작성

## 장애 대응

### 장애 등급 분류

#### P0 (Critical) - 즉시 대응
- 전체 서비스 다운
- 데이터 손실 위험
- 보안 침해

**대응 시간:** 15분 이내 대응 시작, 1시간 이내 복구

#### P1 (High) - 긴급 대응
- 주요 기능 장애
- 성능 심각한 저하
- 일부 서비스 불가

**대응 시간:** 30분 이내 대응 시작, 4시간 이내 복구

#### P2 (Medium) - 일반 대응
- 부분 기능 장애
- 성능 저하
- 우회 방법 존재

**대응 시간:** 2시간 이내 대응 시작, 24시간 이내 복구

### 장애 대응 프로세스

#### 1. 장애 감지 및 알림

```bash
# 자동 장애 감지 스크립트
#!/bin/bash
# incident_detection.sh

check_service_health() {
    local service=$1
    local endpoint=$2
    
    if ! curl -f -s --max-time 10 "$endpoint" > /dev/null; then
        echo "ALERT: $service is down - $endpoint"
        send_alert "P0" "$service service is down"
        return 1
    fi
    return 0
}

# 주요 서비스 체크
check_service_health "Frontend" "https://yourdomain.com/health"
check_service_health "Backend API" "https://yourdomain.com/api/v1/health"
check_service_health "Database" "http://localhost:5432"
```

#### 2. 초기 대응

```bash
# 빠른 진단 스크립트
#!/bin/bash
# quick_diagnosis.sh

echo "=== System Status ==="
docker compose -f docker-compose.prod.yml ps

echo "=== Resource Usage ==="
free -h
df -h

echo "=== Recent Errors ==="
docker compose -f docker-compose.prod.yml logs --since 10m | grep -i error | tail -20

echo "=== Network Connectivity ==="
curl -I https://yourdomain.com/health
```

#### 3. 상세 분석

```bash
# 상세 로그 분석
python3 scripts/analyze_incident.py --start "2024-01-01 10:00" --end "2024-01-01 11:00"

# 성능 메트릭 분석
curl -s "http://prometheus:9090/api/v1/query_range?query=up&start=2024-01-01T10:00:00Z&end=2024-01-01T11:00:00Z&step=60s"
```

### 일반적인 장애 해결

#### 서비스 무응답

```bash
# 1. 컨테이너 상태 확인
docker compose -f docker-compose.prod.yml ps

# 2. 리소스 확인
docker stats --no-stream

# 3. 서비스 재시작
docker compose -f docker-compose.prod.yml restart [service-name]

# 4. 전체 재시작 (마지막 수단)
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

#### 데이터베이스 연결 실패

```bash
# 1. PostgreSQL 컨테이너 확인
docker compose -f docker-compose.prod.yml logs db

# 2. 연결 테스트
docker compose -f docker-compose.prod.yml exec db psql -U dropshipping -d dropshipping_db -c "SELECT 1;"

# 3. 연결 수 확인
docker compose -f docker-compose.prod.yml exec db psql -U dropshipping -d dropshipping_db -c "SELECT count(*) FROM pg_stat_activity;"

# 4. 데이터베이스 재시작
docker compose -f docker-compose.prod.yml restart db
```

#### 높은 메모리 사용량

```bash
# 1. 메모리 사용량 분석
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# 2. 캐시 정리
docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB

# 3. 애플리케이션 재시작
docker compose -f docker-compose.prod.yml restart backend
```

## 유지보수

### 정기 유지보수 일정

#### 매일
- [ ] 자동 백업 실행 (02:00)
- [ ] 로그 로테이션
- [ ] 헬스 체크 실행

#### 매주 (일요일 02:00-04:00)
- [ ] 시스템 업데이트 확인
- [ ] Docker 이미지 업데이트
- [ ] 불필요한 파일 정리
- [ ] 성능 최적화 스크립트 실행

```bash
#!/bin/bash
# weekly_maintenance.sh

# Docker 정리
docker system prune -f
docker image prune -a -f

# 로그 파일 정리 (30일 이상)
find ./logs -name "*.log" -mtime +30 -delete

# 백업 파일 정리 (90일 이상)
find ./backups -name "*.sql*" -mtime +90 -delete

# 시스템 업데이트 확인
apt list --upgradable
```

#### 매월 (첫째 주 일요일)
- [ ] 전체 시스템 백업
- [ ] 보안 패치 적용
- [ ] SSL 인증서 갱신 확인
- [ ] 용량 계획 검토

### 업데이트 프로세스

#### 1. 사전 검증
```bash
# 스테이징 환경에서 테스트
git checkout develop
docker compose -f docker-compose.staging.yml up -d
python3 scripts/health_check.py --env staging
```

#### 2. 운영 환경 적용
```bash
# 백업 생성
python3 scripts/backup.py backup

# 블루-그린 배포 (가능한 경우)
python3 scripts/deploy.py production --strategy blue-green

# 또는 일반 배포
python3 scripts/deploy.py production
```

#### 3. 배포 후 검증
```bash
# 헬스 체크
python3 scripts/health_check.py --comprehensive

# 연기 테스트
python3 scripts/smoke_test.py

# 메트릭 확인
curl -s https://yourdomain.com/api/v1/metrics | jq .
```

## 백업 및 재해복구

### 백업 전략

#### 데이터베이스 백업

**일일 백업 (자동):**
```bash
# crontab 설정
0 2 * * * /opt/dropshipping-system/scripts/backup.py backup --type daily
0 3 * * 0 /opt/dropshipping-system/scripts/backup.py backup --type weekly
0 4 1 * * /opt/dropshipping-system/scripts/backup.py backup --type monthly
```

**실시간 백업 (WAL-E 사용 시):**
```sql
-- PostgreSQL 설정
wal_level = replica
archive_mode = on
archive_command = 'wal-e wal-push %p'
```

#### 파일 시스템 백업

```bash
# 중요 파일들 백업
tar -czf system_backup_$(date +%Y%m%d).tar.gz \
  .env \
  nginx/ssl/ \
  scripts/ \
  docker-compose.prod.yml
```

#### S3 백업

```python
# 자동 S3 업로드
import boto3
from datetime import datetime

def upload_to_s3(file_path, bucket, key):
    s3 = boto3.client('s3')
    s3.upload_file(file_path, bucket, key)
    
    # 라이프사이클 정책으로 90일 후 자동 삭제
    s3.put_object_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={
            'Rules': [{
                'Status': 'Enabled',
                'Filter': {'Prefix': 'backups/'},
                'Expiration': {'Days': 90}
            }]
        }
    )
```

### 재해복구 계획

#### RTO/RPO 목표
- **RTO (Recovery Time Objective):** 4시간
- **RPO (Recovery Point Objective):** 1시간

#### 복구 절차

**1단계: 인프라 복구 (0-1시간)**
```bash
# 새 서버에서 환경 구성
git clone https://github.com/your-repo/dropshipping-system.git
cd dropshipping-system
cp .env.backup .env
```

**2단계: 데이터 복구 (1-2시간)**
```bash
# 최신 백업에서 데이터베이스 복원
python3 scripts/backup.py restore s3://your-bucket/latest-backup.sql

# 데이터 무결성 확인
python3 scripts/verify_data_integrity.py
```

**3단계: 서비스 복구 (2-3시간)**
```bash
# 서비스 시작
docker compose -f docker-compose.prod.yml up -d

# 헬스 체크
python3 scripts/health_check.py --comprehensive
```

**4단계: 검증 및 완료 (3-4시간)**
```bash
# 연기 테스트
python3 scripts/smoke_test.py

# DNS 변경 (필요시)
# 모니터링 재시작
```

### 백업 검증

```bash
# 월간 백업 복원 테스트
#!/bin/bash
# backup_verification.sh

BACKUP_FILE="latest_backup.sql"
TEST_DB="test_restore_db"

# 테스트 데이터베이스 생성
createdb $TEST_DB

# 백업 복원
psql $TEST_DB < $BACKUP_FILE

# 데이터 무결성 검사
python3 scripts/verify_backup.py --database $TEST_DB

# 테스트 DB 삭제
dropdb $TEST_DB
```

## 연락처 및 에스컬레이션

### 운영팀 연락처

**1차 대응 (24/7)**
- 운영팀: ops@yourdomain.com
- 긴급 전화: +82-10-1234-5678

**2차 대응 (업무시간)**
- 개발팀: dev@yourdomain.com
- 보안팀: security@yourdomain.com

**3차 대응 (Critical 장애)**
- CTO: cto@yourdomain.com
- CEO: ceo@yourdomain.com

### 에스컬레이션 기준

- **15분 내 미해결:** 2차 대응팀 호출
- **1시간 내 미해결:** 3차 대응팀 호출
- **데이터 유출 의심:** 즉시 보안팀 및 경영진 보고

---

**마지막 업데이트:** 2024년 1월
**문서 버전:** 1.0
**검토 주기:** 분기별