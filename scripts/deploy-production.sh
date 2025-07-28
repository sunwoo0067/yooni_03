#!/bin/bash
# Production deployment script with zero-downtime
# 무중단 프로덕션 배포 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수 정의
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 배포 환경 확인
if [ "$1" != "production" ]; then
    log_error "Usage: $0 production"
    exit 1
fi

log_info "🚀 Starting production deployment..."

# 환경 변수 확인
if [ ! -f .env.production ]; then
    log_error ".env.production file not found!"
    exit 1
fi

# Git 최신 버전 확인
log_info "📦 Checking latest version..."
git fetch --tags
VERSION=$(git describe --tags --abbrev=0)
log_info "Deploying version: $VERSION"

# 배포 전 백업
log_info "💾 Creating backup..."
./scripts/backup-production.sh

# Docker 이미지 빌드
log_info "🔨 Building Docker images..."
docker compose -f docker-compose.prod.yml build \
    --build-arg VERSION=$VERSION \
    --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 이미지 태깅
docker tag dropshipping-backend:latest dropshipping-backend:$VERSION
docker tag dropshipping-frontend:latest dropshipping-frontend:$VERSION

# Blue-Green 배포 시작
log_info "🔄 Starting Blue-Green deployment..."

# 현재 활성 환경 확인
CURRENT_ENV=$(docker compose -f docker-compose.prod.yml ps -q backend_blue 2>/dev/null && echo "blue" || echo "green")
if [ "$CURRENT_ENV" = "blue" ]; then
    NEW_ENV="green"
else
    NEW_ENV="blue"
fi

log_info "Current environment: $CURRENT_ENV"
log_info "Deploying to: $NEW_ENV"

# 새 환경 시작
log_info "🚀 Starting $NEW_ENV environment..."
docker compose -f docker-compose.prod.yml up -d --no-deps \
    backend_$NEW_ENV \
    frontend_$NEW_ENV

# 헬스체크 대기
log_info "🏥 Waiting for health checks..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8001/health >/dev/null 2>&1; then
        log_info "Health check passed!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "Health check failed after $MAX_RETRIES attempts!"
        docker compose -f docker-compose.prod.yml stop backend_$NEW_ENV frontend_$NEW_ENV
        exit 1
    fi
    
    echo -n "."
    sleep 2
done

# 데이터베이스 마이그레이션
log_info "🗄️ Running database migrations..."
docker compose -f docker-compose.prod.yml exec backend_$NEW_ENV \
    alembic upgrade head

# 트래픽 전환
log_info "🔀 Switching traffic to $NEW_ENV..."
cat > nginx/upstream.conf <<EOF
upstream backend {
    server backend_$NEW_ENV:8000;
}

upstream frontend {
    server frontend_$NEW_ENV:3000;
}
EOF

# Nginx 리로드
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 이전 환경 종료 (5분 대기)
log_info "⏱️ Waiting 5 minutes before stopping $CURRENT_ENV environment..."
sleep 300

log_info "🛑 Stopping $CURRENT_ENV environment..."
docker compose -f docker-compose.prod.yml stop \
    backend_$CURRENT_ENV \
    frontend_$CURRENT_ENV

# 정리 작업
log_info "🧹 Cleaning up..."
docker image prune -f

# 배포 완료 알림
log_info "✅ Deployment completed successfully!"
log_info "Version: $VERSION"
log_info "Environment: $NEW_ENV"

# Slack 알림 (선택사항)
if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST $SLACK_WEBHOOK_URL \
        -H 'Content-Type: application/json' \
        -d '{
            "text": "🚀 Production deployment completed",
            "attachments": [{
                "color": "good",
                "fields": [
                    {"title": "Version", "value": "'$VERSION'", "short": true},
                    {"title": "Environment", "value": "'$NEW_ENV'", "short": true}
                ]
            }]
        }'
fi