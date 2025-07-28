# 🚀 배포 가이드

이 문서는 Dropshipping Automation System의 배포 과정을 안내합니다.

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [환경 설정](#환경-설정)
3. [배포 방법](#배포-방법)
4. [CI/CD 파이프라인](#cicd-파이프라인)
5. [모니터링 설정](#모니터링-설정)
6. [문제 해결](#문제-해결)

## 사전 요구사항

### 시스템 요구사항

- **OS:** Ubuntu 20.04 LTS 이상 또는 CentOS 8 이상
- **CPU:** 최소 4 코어 (권장: 8 코어)
- **메모리:** 최소 8GB RAM (권장: 16GB)
- **스토리지:** 최소 100GB SSD (권장: 200GB)
- **네트워크:** 고정 IP 주소, 도메인 설정

### 필수 소프트웨어

```bash
# Docker 및 Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Git
sudo apt update
sudo apt install git -y

# 기타 유틸리티
sudo apt install curl wget htop vim -y
```

### 포트 설정

다음 포트들이 열려있어야 합니다:

- **80, 443:** HTTP/HTTPS (Nginx)
- **22:** SSH
- **8000:** 백엔드 API (내부)
- **3000:** 프론트엔드 (내부)
- **5432:** PostgreSQL (내부)
- **6379:** Redis (내부)
- **9090:** Prometheus (내부)
- **3000:** Grafana (내부)

## 환경 설정

### 1. 프로젝트 클론

```bash
# 운영 서버에서
cd /opt
sudo git clone https://github.com/your-username/dropshipping-system.git
sudo chown -R $USER:$USER dropshipping-system
cd dropshipping-system
```

### 2. 환경 변수 설정

```bash
# 운영환경 설정 복사
cp .env.production .env

# 환경 변수 편집
vim .env
```

**필수 수정 항목:**

```bash
# 보안 키 (32자 이상의 랜덤 문자열)
SECRET_KEY="your-super-secret-production-key-here"

# 데이터베이스 비밀번호
DB_PASSWORD="your-strong-database-password"

# 도메인 설정
DOMAIN_NAME="yourdomain.com" 
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]

# API 키들
OPENAI_API_KEY="your-openai-api-key"
COUPANG_ACCESS_KEY="your-coupang-access-key"
COUPANG_SECRET_KEY="your-coupang-secret-key"
# ... 기타 API 키들

# 이메일 설정
SMTP_HOST="smtp.gmail.com"
SMTP_USER="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"

# 모니터링
GRAFANA_ADMIN_PASSWORD="your-grafana-admin-password"
SENTRY_DSN="your-sentry-dsn"

# 백업 설정 (S3)
AWS_ACCESS_KEY_ID="your-aws-access-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
BACKUP_S3_BUCKET="your-backup-bucket"
```

### 3. SSL 인증서 설정

#### Let's Encrypt 사용 (권장)

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx -y

# 인증서 발급 (Docker 컨테이너 실행 전)
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  -d api.yourdomain.com \
  --agree-tos \
  --email admin@yourdomain.com

# 인증서를 프로젝트 디렉토리로 복사
sudo cp -L /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./nginx/ssl/
sudo cp -L /etc/letsencrypt/live/yourdomain.com/privkey.pem ./nginx/ssl/
sudo cp -L /etc/letsencrypt/live/yourdomain.com/chain.pem ./nginx/ssl/
sudo chown $USER:$USER ./nginx/ssl/*

# 자동 갱신 설정
sudo crontab -e
# 다음 라인 추가:
# 0 12 * * * /usr/bin/certbot renew --quiet && docker compose -f /opt/dropshipping-system/docker-compose.prod.yml restart nginx
```

#### 자체 서명 인증서 (개발/테스트용)

```bash
cd nginx/ssl
openssl genrsa -out privkey.pem 2048
openssl req -new -key privkey.pem -out cert.csr -subj "/C=KR/ST=Seoul/L=Seoul/O=Development/CN=localhost"
openssl x509 -req -days 365 -in cert.csr -signkey privkey.pem -out fullchain.pem
cp fullchain.pem chain.pem
```

## 배포 방법

### 방법 1: 자동 배포 스크립트 사용 (권장)

```bash
# 배포 스크립트 실행 권한 부여
chmod +x scripts/deploy.py

# 운영환경 배포
python3 scripts/deploy.py production

# 또는 특정 태그/커밋으로 배포
python3 scripts/deploy.py production --tag v1.2.3
```

### 방법 2: 수동 배포

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 환경 변수 확인
source .env

# 3. 데이터베이스 백업 (선택사항)
python3 scripts/backup.py backup

# 4. 컨테이너 빌드 및 실행
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 5. 헬스 체크
sleep 30
curl -f https://yourdomain.com/health

# 6. 로그 확인
docker compose -f docker-compose.prod.yml logs -f
```

### 방법 3: Docker 이미지 사용

```bash
# 사전 빌드된 이미지 사용
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## CI/CD 파이프라인

### GitHub Actions 설정

1. **Repository Secrets 설정:**

GitHub Repository → Settings → Secrets and variables → Actions에서 다음 secrets를 추가:

```
DEPLOY_HOST=your-server-ip
DEPLOY_USER=your-ssh-user
DEPLOY_SSH_KEY=your-private-ssh-key
GITHUB_TOKEN=automatically-provided
SLACK_WEBHOOK=your-slack-webhook-url
SENTRY_DSN=your-sentry-dsn
```

2. **SSH 키 설정:**

```bash
# 로컬에서 SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "github-actions@yourdomain.com"

# 공개키를 서버에 추가
ssh-copy-id -i ~/.ssh/id_rsa.pub user@your-server

# 개인키를 GitHub Secrets에 추가 (DEPLOY_SSH_KEY)
cat ~/.ssh/id_rsa
```

3. **자동 배포 트리거:**

- `main` 브랜치에 push 시 → 운영환경 배포
- `develop` 브랜치에 push 시 → 스테이징 배포
- Pull Request 생성 시 → 테스트 및 검증

### 수동 워크플로우 실행

```bash
# GitHub CLI 사용
gh workflow run "CI/CD Pipeline" --ref main

# 또는 GitHub 웹 인터페이스에서 Actions → Workflow → Run workflow
```

## 모니터링 설정

### 1. Grafana 대시보드 접근

```
URL: https://yourdomain.com/grafana/
Username: admin
Password: (GRAFANA_ADMIN_PASSWORD에서 설정한 값)
```

### 2. Prometheus 메트릭

```
URL: https://yourdomain.com/monitoring/
```

### 3. 로그 모니터링

```bash
# 실시간 로그 확인
docker compose -f docker-compose.prod.yml logs -f

# 특정 서비스 로그
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx

# 로그 파일 위치
./backend/logs/app.log
./nginx/logs/access.log
./nginx/logs/error.log
```

### 4. 알림 설정

Slack 웹훅 설정:
1. Slack 워크스페이스에서 앱 생성
2. Incoming Webhooks 활성화
3. 웹훅 URL을 환경 변수에 설정

## 문제 해결

### 일반적인 문제들

#### 1. 컨테이너 시작 실패

```bash
# 컨테이너 상태 확인
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs [service-name]

# 컨테이너 재시작
docker compose -f docker-compose.prod.yml restart [service-name]
```

#### 2. 데이터베이스 연결 오류

```bash
# 데이터베이스 컨테이너 확인
docker compose -f docker-compose.prod.yml logs db

# 데이터베이스 연결 테스트
docker compose -f docker-compose.prod.yml exec db psql -U dropshipping -d dropshipping_db -c "SELECT 1;"
```

#### 3. SSL 인증서 문제

```bash
# 인증서 파일 확인
ls -la nginx/ssl/

# 인증서 유효성 검사
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# Let's Encrypt 인증서 갱신
sudo certbot renew --dry-run
```

#### 4. 메모리 부족

```bash
# 시스템 리소스 확인
free -h
df -h
htop

# 컨테이너 리소스 사용량 확인
docker stats

# 불필요한 이미지/컨테이너 정리
docker system prune -a
```

### 헬스 체크 스크립트

```bash
# 시스템 전체 헬스 체크
python3 scripts/health_check.py

# 특정 컴포넌트만 체크
curl -f https://yourdomain.com/health
curl -f https://yourdomain.com/api/v1/health
```

### 롤백 절차

#### 자동 롤백 (배포 스크립트 사용)

```bash
# 이전 버전으로 롤백
python3 scripts/deploy.py production --tag previous-version
```

#### 수동 롤백

```bash
# 1. 이전 커밋으로 되돌리기
git log --oneline -10  # 최근 10개 커밋 확인
git reset --hard [previous-commit-hash]

# 2. 컨테이너 재배포
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# 3. 헬스 체크
sleep 30
curl -f https://yourdomain.com/health
```

### 백업 및 복원

#### 백업

```bash
# 자동 백업 (스케줄러에 의해 실행)
python3 scripts/backup.py backup

# 수동 백업
docker compose -f docker-compose.prod.yml exec db pg_dump -U dropshipping dropshipping_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 복원

```bash
# 백업 목록 확인
python3 scripts/backup.py list

# 특정 백업 복원
python3 scripts/backup.py restore /path/to/backup.sql

# 또는 직접 복원
docker compose -f docker-compose.prod.yml exec -T db psql -U dropshipping dropshipping_db < backup.sql
```

## 성능 최적화

### 1. 데이터베이스 최적화

```sql
-- 인덱스 확인 및 생성
EXPLAIN ANALYZE SELECT * FROM products WHERE status = 'active';

-- 성능 통계
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

### 2. Redis 메모리 최적화

```bash
# Redis 메모리 사용량 확인
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory

# 캐시 정책 확인
docker compose -f docker-compose.prod.yml exec redis redis-cli config get maxmemory-policy
```

### 3. Nginx 캐싱 최적화

```bash
# 캐시 상태 확인
curl -I https://yourdomain.com/api/v1/products

# 캐시 디렉토리 정리
docker compose -f docker-compose.prod.yml exec nginx find /var/cache/nginx -type f -delete
```

## 보안 고려사항

### 1. 정기 보안 업데이트

```bash
# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Docker 이미지 업데이트
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### 2. 방화벽 설정

```bash
# UFW 설정
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 3. SSL 등급 확인

```bash
# SSL Labs 테스트
curl -s "https://api.ssllabs.com/api/v3/analyze?host=yourdomain.com"
```

## 지원 및 연락처

- **기술 지원:** tech-support@yourdomain.com
- **긴급 상황:** emergency@yourdomain.com  
- **문서:** https://docs.yourdomain.com
- **모니터링:** https://yourdomain.com/grafana/

---

**참고:** 이 가이드는 운영 환경 배포를 위한 것입니다. 개발 환경 설정은 `README.md`를 참조하세요.