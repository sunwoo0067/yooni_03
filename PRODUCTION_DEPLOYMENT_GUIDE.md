# 🚀 프로덕션 배포 가이드

## 📋 목차

1. [사전 준비](#사전-준비)
2. [인프라 구성](#인프라-구성)
3. [보안 설정](#보안-설정)
4. [배포 프로세스](#배포-프로세스)
5. [모니터링 설정](#모니터링-설정)
6. [백업 및 복구](#백업-및-복구)
7. [트러블슈팅](#트러블슈팅)
8. [체크리스트](#체크리스트)

## 🔧 사전 준비

### 1. 시스템 요구사항

#### 최소 사양
- **CPU**: 4 vCPU
- **Memory**: 8GB RAM
- **Storage**: 100GB SSD
- **Network**: 1Gbps

#### 권장 사양
- **CPU**: 8 vCPU
- **Memory**: 16GB RAM
- **Storage**: 500GB SSD (RAID 1)
- **Network**: 10Gbps

### 2. 소프트웨어 요구사항

```bash
# 운영체제
Ubuntu 22.04 LTS 또는 Amazon Linux 2023

# Docker & Docker Compose
Docker Engine 24.0+
Docker Compose 2.20+

# 데이터베이스
PostgreSQL 15+
Redis 7+

# 모니터링
Prometheus 2.45+
Grafana 10+
```

### 3. 도메인 및 SSL 인증서

```bash
# 도메인 설정
api.yourdomain.com      # API 서버
app.yourdomain.com      # 프론트엔드
monitor.yourdomain.com  # 모니터링

# SSL 인증서 (Let's Encrypt)
sudo certbot certonly --standalone -d api.yourdomain.com
```

## 🏗️ 인프라 구성

### 1. AWS 인프라 (권장)

```yaml
# terraform/main.tf
provider "aws" {
  region = "ap-northeast-2"
}

# VPC 구성
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "dropshipping-vpc"
  }
}

# 서브넷 구성 (Multi-AZ)
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-northeast-2a"
  map_public_ip_on_launch = true
}

resource "aws_subnet" "public_c" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "ap-northeast-2c"
  map_public_ip_on_launch = true
}

# RDS (PostgreSQL)
resource "aws_db_instance" "postgres" {
  identifier             = "dropshipping-db"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.medium"
  allocated_storage      = 100
  storage_encrypted      = true
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
}

# ElastiCache (Redis)
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "dropshipping-cache"
  engine               = "redis"
  node_type            = "cache.t3.medium"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
}

# ECS 클러스터
resource "aws_ecs_cluster" "main" {
  name = "dropshipping-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "dropshipping-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_c.id]

  enable_deletion_protection = true
  enable_http2              = true
}
```

### 2. Docker Compose 프로덕션 구성

```yaml
# docker-compose.prod.yml
version: '3.9'

services:
  nginx:
    image: nginx:alpine
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_volume:/app/static
    depends_on:
      - backend
      - frontend
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend
    env_file:
      - .env.production
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    depends_on:
      - postgres
      - redis
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_URL=https://api.yourdomain.com
    container_name: frontend
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    container_name: postgres
    env_file:
      - .env.production
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/postgres-init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: always
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c work_mem=4MB
      -c min_wal_size=1GB
      -c max_wal_size=4GB

  redis:
    image: redis:7-alpine
    container_name: redis
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
    volumes:
      - redis_data:/data
    restart: always

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--storage.tsdb.retention.time=30d'
    restart: always

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    restart: always

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  prometheus_data:
  grafana_data:

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 3. Nginx 프로덕션 설정

```nginx
# nginx/nginx.prod.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 로깅 설정
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;

    # 성능 최적화
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 50M;

    # Gzip 압축
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline' https:;" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Backend upstream
    upstream backend {
        least_conn;
        server backend:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # Frontend upstream
    upstream frontend {
        server frontend:3000;
        keepalive 32;
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name api.yourdomain.com app.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # API Server
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/api.crt;
        ssl_certificate_key /etc/nginx/ssl/api.key;

        location / {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            
            # Rate limiting
            limit_req zone=api burst=20 nodelay;
        }

        location /static/ {
            alias /app/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        location /media/ {
            alias /app/media/;
            expires 7d;
            add_header Cache-Control "public";
        }

        # Health check endpoint (no rate limiting)
        location /health {
            proxy_pass http://backend/health;
            access_log off;
        }
    }

    # Frontend Application
    server {
        listen 443 ssl http2;
        server_name app.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/app.crt;
        ssl_certificate_key /etc/nginx/ssl/app.key;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            proxy_pass http://frontend;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## 🔒 보안 설정

### 1. 환경 변수 관리

```bash
# .env.production (절대 Git에 커밋하지 말 것!)
# 데이터베이스
DATABASE_URL=postgresql://dropship_user:strong_password@postgres:5432/dropship_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://:redis_password@redis:6379/0
REDIS_PASSWORD=strong_redis_password

# 보안
SECRET_KEY=your-very-long-random-secret-key-here
JWT_SECRET_KEY=another-very-long-random-jwt-secret
ENCRYPTION_KEY=base64-encoded-32-byte-key

# API Keys (프로덕션용)
GEMINI_API_KEY=your-production-gemini-key
OPENAI_API_KEY=your-production-openai-key

# 마켓플레이스 API
COUPANG_ACCESS_KEY=your-coupang-key
COUPANG_SECRET_KEY=your-coupang-secret
NAVER_CLIENT_ID=your-naver-id
NAVER_CLIENT_SECRET=your-naver-secret

# 모니터링
SENTRY_DSN=https://xxx@sentry.io/xxx
DATADOG_API_KEY=your-datadog-key

# 환경
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### 2. 방화벽 설정

```bash
# UFW 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH (IP 제한)
sudo ufw allow from YOUR_IP to any port 22

# HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 모니터링 (내부망만)
sudo ufw allow from 10.0.0.0/16 to any port 9090  # Prometheus
sudo ufw allow from 10.0.0.0/16 to any port 3000  # Grafana

# 활성화
sudo ufw enable
```

### 3. SELinux/AppArmor 설정

```bash
# SELinux (CentOS/RHEL)
sudo setsebool -P httpd_can_network_connect 1
sudo setsebool -P httpd_can_network_connect_db 1

# AppArmor (Ubuntu)
sudo aa-enforce /etc/apparmor.d/docker
```

## 📦 배포 프로세스

### 1. 자동 배포 스크립트

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Starting production deployment..."

# 환경 변수 확인
if [ ! -f .env.production ]; then
    echo "❌ .env.production file not found!"
    exit 1
fi

# 백업
echo "📦 Creating backup..."
./scripts/backup-production.sh

# 이미지 빌드
echo "🔨 Building Docker images..."
docker compose -f docker-compose.prod.yml build

# 데이터베이스 마이그레이션
echo "🗄️ Running database migrations..."
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Blue-Green 배포
echo "🔄 Starting Blue-Green deployment..."

# 새 컨테이너 시작 (Green)
docker compose -f docker-compose.prod.yml up -d --scale backend=2 --no-deps backend_green

# 헬스체크
echo "🏥 Health checking new containers..."
./scripts/health-check.sh backend_green

# 트래픽 전환
echo "🔀 Switching traffic..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 이전 컨테이너 제거
echo "🧹 Removing old containers..."
docker compose -f docker-compose.prod.yml stop backend_blue
docker compose -f docker-compose.prod.yml rm -f backend_blue

echo "✅ Deployment completed successfully!"
```

### 2. 롤백 절차

```bash
#!/bin/bash
# scripts/rollback.sh

set -e

echo "🔙 Starting rollback..."

# 이전 버전 태그 확인
PREVIOUS_VERSION=$(docker images --format "{{.Tag}}" | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -2 | head -1)

if [ -z "$PREVIOUS_VERSION" ]; then
    echo "❌ No previous version found!"
    exit 1
fi

echo "📌 Rolling back to version: $PREVIOUS_VERSION"

# 이전 버전으로 재배포
docker compose -f docker-compose.prod.yml up -d --no-deps \
    backend:$PREVIOUS_VERSION \
    frontend:$PREVIOUS_VERSION

# 헬스체크
./scripts/health-check.sh

echo "✅ Rollback completed!"
```

### 3. 데이터베이스 백업 및 복구

```bash
#!/bin/bash
# scripts/backup-production.sh

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/dropship_prod_$TIMESTAMP.sql"

echo "🗄️ Creating database backup..."

# PostgreSQL 백업
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U $POSTGRES_USER -d $POSTGRES_DB > $BACKUP_FILE

# 압축
gzip $BACKUP_FILE

# S3 업로드 (선택사항)
aws s3 cp $BACKUP_FILE.gz s3://your-backup-bucket/database/

# 오래된 백업 삭제 (30일 이상)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "✅ Backup completed: $BACKUP_FILE.gz"
```

## 📊 모니터링 설정

### 1. Prometheus 설정

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - "alerts/*.yml"

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 2. 알림 규칙

```yaml
# monitoring/alerts/application.yml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: rate(http_request_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5% for 5 minutes"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time"
          description: "95th percentile response time is above 1 second"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is above 90%"
```

### 3. Grafana 대시보드

```json
{
  "dashboard": {
    "title": "Dropshipping Production Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_request_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_request_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      }
    ]
  }
}
```

## 💾 백업 및 복구

### 1. 자동 백업 스케줄

```bash
# crontab -e
# 데이터베이스 백업 (매일 새벽 3시)
0 3 * * * /opt/dropshipping/scripts/backup-production.sh

# 애플리케이션 로그 백업 (매주 일요일)
0 4 * * 0 /opt/dropshipping/scripts/backup-logs.sh

# Redis 스냅샷 (6시간마다)
0 */6 * * * docker exec redis redis-cli BGSAVE
```

### 2. 재해 복구 계획

```bash
#!/bin/bash
# scripts/disaster-recovery.sh

# 1. 최신 백업 확인
LATEST_BACKUP=$(aws s3 ls s3://your-backup-bucket/database/ | sort | tail -1 | awk '{print $4}')

# 2. 백업 다운로드
aws s3 cp s3://your-backup-bucket/database/$LATEST_BACKUP /tmp/

# 3. 데이터베이스 복원
gunzip /tmp/$LATEST_BACKUP
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U $POSTGRES_USER -d $POSTGRES_DB < /tmp/${LATEST_BACKUP%.gz}

# 4. 캐시 재구축
docker compose -f docker-compose.prod.yml exec backend \
    python -m app.scripts.rebuild_cache

# 5. 헬스체크
./scripts/health-check.sh
```

## 🔧 트러블슈팅

### 1. 일반적인 문제 해결

#### 메모리 부족
```bash
# 메모리 사용량 확인
docker stats

# 컨테이너 메모리 제한 조정
docker update --memory="4g" --memory-swap="4g" backend
```

#### 디스크 공간 부족
```bash
# Docker 정리
docker system prune -a --volumes

# 오래된 로그 삭제
find /var/log -name "*.log" -mtime +30 -delete
```

#### 느린 데이터베이스 쿼리
```sql
-- 느린 쿼리 확인
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- 인덱스 추가
CREATE INDEX CONCURRENTLY idx_orders_user_created 
ON orders(user_id, created_at);
```

### 2. 긴급 대응 절차

```bash
#!/bin/bash
# scripts/emergency-response.sh

case "$1" in
  "high-load")
    # 자동 스케일링
    docker compose -f docker-compose.prod.yml up -d --scale backend=4
    ;;
    
  "database-down")
    # 읽기 전용 모드 전환
    docker compose -f docker-compose.prod.yml exec backend \
      python -m app.scripts.enable_readonly_mode
    ;;
    
  "security-breach")
    # 모든 API 키 순환
    ./scripts/rotate-api-keys.sh
    # 의심스러운 IP 차단
    ./scripts/block-suspicious-ips.sh
    ;;
esac
```

## ✅ 체크리스트

### 배포 전
- [ ] 모든 환경 변수가 설정되었는가?
- [ ] SSL 인증서가 유효한가?
- [ ] 데이터베이스 백업이 완료되었는가?
- [ ] 로드 테스트를 수행했는가?
- [ ] 보안 스캔을 완료했는가?

### 배포 중
- [ ] 헬스체크가 통과하는가?
- [ ] 로그에 에러가 없는가?
- [ ] 메트릭이 정상 범위인가?
- [ ] 트래픽이 정상적으로 라우팅되는가?

### 배포 후
- [ ] 모든 기능이 정상 작동하는가?
- [ ] 성능이 기대 수준인가?
- [ ] 알림이 정상 작동하는가?
- [ ] 백업이 예약되어 있는가?
- [ ] 문서가 업데이트되었는가?

## 📞 비상 연락처

```yaml
on-call:
  primary:
    name: "DevOps Lead"
    phone: "+82-10-XXXX-XXXX"
    email: "devops@company.com"
  
  secondary:
    name: "Backend Lead"
    phone: "+82-10-YYYY-YYYY"
    email: "backend@company.com"

external:
  aws_support: "https://console.aws.amazon.com/support"
  datadog_support: "support@datadog.com"
```

---

이 가이드를 따라 안전하고 안정적인 프로덕션 배포를 수행할 수 있습니다. 정기적인 업데이트와 모니터링을 통해 시스템의 건강성을 유지하세요. 🚀