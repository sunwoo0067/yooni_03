#!/bin/bash
# Production rollback script
# 프로덕션 롤백 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# 사용법 확인
if [ "$#" -eq 0 ]; then
    echo "Usage: $0 [version|latest|quick]"
    echo "  version - Rollback to specific version (e.g., v1.2.3)"
    echo "  latest  - Rollback to latest stable version"
    echo "  quick   - Quick rollback by swapping environments"
    exit 1
fi

ROLLBACK_TYPE=$1
ROLLBACK_VERSION=$2

log_warn "🔙 Starting production rollback..."
log_warn "Type: $ROLLBACK_TYPE"

# 현재 상태 저장
CURRENT_TIME=$(date +%Y%m%d_%H%M%S)
ROLLBACK_LOG="/var/log/dropshipping/rollback_$CURRENT_TIME.log"
mkdir -p $(dirname $ROLLBACK_LOG)

# 로깅 시작
exec 1> >(tee -a $ROLLBACK_LOG)
exec 2>&1

case $ROLLBACK_TYPE in
    "quick")
        # 빠른 롤백 - Blue/Green 환경 전환
        log_info "🔄 Performing quick rollback..."
        
        # 현재 활성 환경 확인
        CURRENT_ENV=$(cat nginx/upstream.conf | grep backend | grep -oE '(blue|green)' | head -1)
        if [ "$CURRENT_ENV" = "blue" ]; then
            PREVIOUS_ENV="green"
        else
            PREVIOUS_ENV="blue"
        fi
        
        log_info "Switching from $CURRENT_ENV to $PREVIOUS_ENV"
        
        # 이전 환경이 실행 중인지 확인
        if ! docker compose -f docker-compose.prod.yml ps backend_$PREVIOUS_ENV | grep -q "Up"; then
            log_error "Previous environment ($PREVIOUS_ENV) is not running!"
            log_info "Starting previous environment..."
            docker compose -f docker-compose.prod.yml up -d --no-deps \
                backend_$PREVIOUS_ENV \
                frontend_$PREVIOUS_ENV
            
            # 헬스체크 대기
            sleep 30
        fi
        
        # 트래픽 전환
        cat > nginx/upstream.conf <<EOF
upstream backend {
    server backend_$PREVIOUS_ENV:8000;
}

upstream frontend {
    server frontend_$PREVIOUS_ENV:3000;
}
EOF
        
        # Nginx 리로드
        docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
        
        log_info "✅ Quick rollback completed!"
        ;;
        
    "version")
        # 특정 버전으로 롤백
        if [ -z "$ROLLBACK_VERSION" ]; then
            log_error "Version not specified!"
            exit 1
        fi
        
        log_info "📌 Rolling back to version: $ROLLBACK_VERSION"
        
        # 버전 태그 확인
        if ! docker images | grep -q "dropshipping-backend.*$ROLLBACK_VERSION"; then
            log_error "Version $ROLLBACK_VERSION not found in local images!"
            log_info "Pulling from registry..."
            
            docker pull ghcr.io/yourusername/dropshipping-backend:$ROLLBACK_VERSION
            docker pull ghcr.io/yourusername/dropshipping-frontend:$ROLLBACK_VERSION
        fi
        
        # 현재 환경 확인
        CURRENT_ENV=$(cat nginx/upstream.conf | grep backend | grep -oE '(blue|green)' | head -1)
        if [ "$CURRENT_ENV" = "blue" ]; then
            DEPLOY_ENV="green"
        else
            DEPLOY_ENV="blue"
        fi
        
        # 이전 버전으로 배포
        log_info "Deploying version $ROLLBACK_VERSION to $DEPLOY_ENV..."
        
        # Docker Compose 오버라이드 생성
        cat > docker-compose.rollback.yml <<EOF
version: '3.9'
services:
  backend_$DEPLOY_ENV:
    image: ghcr.io/yourusername/dropshipping-backend:$ROLLBACK_VERSION
  frontend_$DEPLOY_ENV:
    image: ghcr.io/yourusername/dropshipping-frontend:$ROLLBACK_VERSION
EOF
        
        # 배포
        docker compose -f docker-compose.prod.yml -f docker-compose.rollback.yml \
            up -d --no-deps backend_$DEPLOY_ENV frontend_$DEPLOY_ENV
        
        # 헬스체크
        log_info "🏥 Waiting for health checks..."
        sleep 30
        
        if ! ./scripts/health-check-production.sh; then
            log_error "Health check failed!"
            exit 1
        fi
        
        # 트래픽 전환
        cat > nginx/upstream.conf <<EOF
upstream backend {
    server backend_$DEPLOY_ENV:8000;
}

upstream frontend {
    server frontend_$DEPLOY_ENV:3000;
}
EOF
        
        docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
        
        log_info "✅ Version rollback completed!"
        ;;
        
    "latest")
        # 최신 안정 버전으로 롤백
        log_info "🔍 Finding latest stable version..."
        
        # 최근 성공한 배포 버전 찾기
        LATEST_STABLE=$(docker images --format "{{.Tag}}" | \
            grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | \
            sort -V | tail -1)
        
        if [ -z "$LATEST_STABLE" ]; then
            log_error "No stable version found!"
            exit 1
        fi
        
        log_info "Latest stable version: $LATEST_STABLE"
        
        # 버전 롤백 실행
        $0 version $LATEST_STABLE
        ;;
        
    *)
        log_error "Unknown rollback type: $ROLLBACK_TYPE"
        exit 1
        ;;
esac

# 롤백 후 검증
log_info "🔍 Verifying rollback..."

# 헬스체크
if ./scripts/health-check-production.sh; then
    log_info "✅ Health check passed!"
else
    log_error "❌ Health check failed after rollback!"
fi

# 메트릭 확인
log_info "📊 Checking metrics..."
CURRENT_ERROR_RATE=$(curl -s "$API_URL/metrics" | grep http_request_error | tail -1 | awk '{print $2}')
log_info "Current error rate: $CURRENT_ERROR_RATE"

# 롤백 완료 알림
ROLLBACK_DETAILS="Type: $ROLLBACK_TYPE"
if [ ! -z "$ROLLBACK_VERSION" ]; then
    ROLLBACK_DETAILS="$ROLLBACK_DETAILS, Version: $ROLLBACK_VERSION"
fi

# Slack 알림
if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST $SLACK_WEBHOOK_URL \
        -H 'Content-Type: application/json' \
        -d '{
            "text": "🔙 Production rollback completed",
            "attachments": [{
                "color": "warning",
                "fields": [
                    {"title": "Details", "value": "'$ROLLBACK_DETAILS'", "short": false},
                    {"title": "Timestamp", "value": "'$(date)'", "short": true}
                ]
            }]
        }'
fi

# 인시던트 리포트 생성
cat > /var/log/dropshipping/incident_$CURRENT_TIME.md <<EOF
# Production Rollback Incident Report

**Date**: $(date)
**Type**: $ROLLBACK_TYPE
**Version**: ${ROLLBACK_VERSION:-N/A}

## Timeline
- Rollback initiated: $CURRENT_TIME
- Rollback completed: $(date +%H:%M:%S)

## Actions Taken
1. Identified rollback type: $ROLLBACK_TYPE
2. Executed rollback procedure
3. Verified health status
4. Checked error metrics

## Current Status
- Health Check: $(./scripts/health-check-production.sh &>/dev/null && echo "PASSED" || echo "FAILED")
- Error Rate: $CURRENT_ERROR_RATE

## Follow-up Actions
- [ ] Investigate root cause
- [ ] Update deployment procedures
- [ ] Schedule post-mortem meeting
EOF

log_info "📄 Incident report created: /var/log/dropshipping/incident_$CURRENT_TIME.md"
log_info "🔄 Rollback completed. Please investigate the root cause."