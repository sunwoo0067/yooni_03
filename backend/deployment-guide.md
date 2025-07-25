# 드롭시핑 시스템 배포 가이드

## 📋 배포 준비사항

### 시스템 요구사항
- **CPU**: 최소 4코어, 권장 8코어 이상
- **RAM**: 최소 8GB, 권장 16GB 이상
- **디스크**: 최소 100GB SSD, 권장 500GB 이상
- **OS**: Ubuntu 20.04 LTS 이상, CentOS 8 이상

### 필수 소프트웨어
```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🚀 배포 단계

### 1. 환경 설정
```bash
# 프로젝트 클론
git clone <repository_url>
cd dropshipping-system/backend

# 환경 변수 설정
cp .env.production .env
# .env 파일을 실제 값으로 수정
```

### 2. SSL 인증서 설정
```bash
# 자체 서명 인증서 (개발/테스트용)
make ssl-cert

# Let's Encrypt 인증서 (프로덕션용)
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
```

### 3. 배포 실행
```bash
# 프로덕션 배포
make deploy

# 수동 배포
docker-compose up -d --build
```

### 4. 데이터베이스 초기화
```bash
# 마이그레이션 실행
make migrate

# 초기 데이터 생성 (필요한 경우)
docker-compose exec backend python scripts/create_initial_data.py
```

## 🔧 설정 세부사항

### 환경 변수 (.env)
```bash
# 필수 설정 항목
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@db:5432/dbname
SECRET_KEY=your-super-secret-key
OPENAI_API_KEY=your-openai-key

# 외부 API 키들
COUPANG_API_KEY=your-coupang-key
NAVER_API_CLIENT_ID=your-naver-id
```

### Nginx 설정
- `config/nginx.conf`에서 도메인 및 SSL 설정 수정
- Rate limiting 및 보안 헤더 조정

### 모니터링 설정
```bash
# Grafana 접속
http://your-domain:3000
ID: admin, PW: admin123

# Prometheus 접속
http://your-domain:9090
```

## 📊 모니터링 및 로그

### 헬스체크
```bash
# 애플리케이션 상태 확인
make health

# 서비스 상태 확인
make status
```

### 로그 확인
```bash
# 전체 로그
make logs

# 특정 서비스 로그
make logs-backend
make logs-db
make logs-nginx
```

### 메트릭 확인
```bash
# Prometheus 메트릭
make metrics

# 시스템 리소스
docker stats
```

## 🔄 백업 및 복구

### 자동 백업 설정
```bash
# 백업 서비스 활성화
docker-compose --profile backup up -d backup

# 수동 백업
make backup
```

### 복구
```bash
# 백업 파일에서 복구
make restore
# 백업 파일 경로 입력 요청
```

### 백업 파일 위치
- **로컬**: `./backups/`
- **컨테이너**: `/backups/`

## 🔒 보안 설정

### SSL/TLS
- 프로덕션에서는 반드시 유효한 SSL 인증서 사용
- HTTP → HTTPS 리다이렉트 설정됨

### 방화벽 설정
```bash
# UFW 설정 예시
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # PostgreSQL 외부 접근 차단
sudo ufw deny 6379/tcp  # Redis 외부 접근 차단
sudo ufw enable
```

### 보안 업데이트
```bash
# 컨테이너 이미지 업데이트
docker-compose pull
docker-compose up -d

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y
```

## 🚨 트러블슈팅

### 일반적인 문제들

#### 1. 컨테이너 시작 실패
```bash
# 로그 확인
docker-compose logs [service_name]

# 컨테이너 재시작
docker-compose restart [service_name]
```

#### 2. 데이터베이스 연결 실패
```bash
# 데이터베이스 상태 확인
make db-shell

# 연결 설정 확인
docker-compose exec backend env | grep DATABASE_URL
```

#### 3. 높은 메모리 사용량
```bash
# Redis 메모리 설정 확인
docker-compose exec redis redis-cli info memory

# 불필요한 데이터 정리
docker-compose exec redis redis-cli flushdb
```

#### 4. 느린 응답 시간
```bash
# 슬로우 쿼리 확인
docker-compose exec db psql -U dropshipping -d dropshipping_db -c "SELECT * FROM logs.slow_queries LIMIT 10;"

# 커넥션 풀 상태 확인
curl -s http://localhost/metrics | grep db_connection_pool
```

## 📈 성능 최적화

### 데이터베이스 튜닝
```bash
# PostgreSQL 설정 최적화 (메모리에 따라 조정)
# shared_buffers = 256MB
# effective_cache_size = 1GB
# work_mem = 4MB
```

### Redis 설정
```bash
# 메모리 정책 설정
# maxmemory-policy allkeys-lru
```

### 애플리케이션 튜닝
- Uvicorn worker 수 조정 (CPU 코어 수에 맞춰)
- 데이터베이스 연결 풀 크기 조정
- 캐시 TTL 최적화

## 🔄 업데이트 및 배포

### 무중단 배포
```bash
# Rolling update
docker-compose up -d --no-deps backend
```

### 버전 관리
```bash
# 이미지 태깅
docker build -t dropshipping-backend:v1.0.0 .
docker-compose up -d
```

## 📞 지원 및 문의

- **시스템 관리자**: admin@company.com
- **개발팀**: dev@company.com
- **긴급 상황**: +82-10-xxxx-xxxx

## 📚 추가 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Docker Compose 가이드](https://docs.docker.com/compose/)
- [PostgreSQL 튜닝 가이드](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)
- [Nginx 설정 가이드](https://nginx.org/en/docs/)