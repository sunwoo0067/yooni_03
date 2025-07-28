#!/bin/bash
# Production health check script
# 프로덕션 헬스체크 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
API_URL="${API_URL:-https://api.yourdomain.com}"
FRONTEND_URL="${FRONTEND_URL:-https://app.yourdomain.com}"
TIMEOUT=10
MAX_RETRIES=3

# 결과 저장
HEALTH_STATUS="healthy"
FAILED_CHECKS=()

# 로깅 함수
log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# 헬스체크 함수
check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    local retry_count=0
    
    echo -n "Checking $name... "
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $TIMEOUT "$url" || echo "000")
        
        if [ "$response" = "$expected_status" ]; then
            log_success "$name is healthy (HTTP $response)"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $MAX_RETRIES ]; then
            sleep 2
        fi
    done
    
    log_error "$name is unhealthy (HTTP $response)"
    FAILED_CHECKS+=("$name")
    HEALTH_STATUS="unhealthy"
    return 1
}

# JSON 응답 검증
check_json_endpoint() {
    local name=$1
    local url=$2
    local json_path=$3
    local expected_value=$4
    
    echo -n "Checking $name... "
    
    response=$(curl -s --connect-timeout $TIMEOUT "$url" || echo "{}")
    actual_value=$(echo "$response" | jq -r "$json_path" 2>/dev/null || echo "null")
    
    if [ "$actual_value" = "$expected_value" ]; then
        log_success "$name is healthy"
        return 0
    else
        log_error "$name is unhealthy (expected: $expected_value, got: $actual_value)"
        FAILED_CHECKS+=("$name")
        HEALTH_STATUS="unhealthy"
        return 1
    fi
}

# 데이터베이스 연결 확인
check_database() {
    echo -n "Checking database connection... "
    
    if docker compose -f docker-compose.prod.yml exec -T postgres \
        pg_isready -U $POSTGRES_USER -d $POSTGRES_DB &>/dev/null; then
        
        # 추가로 쿼리 실행 테스트
        if docker compose -f docker-compose.prod.yml exec -T postgres \
            psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1" &>/dev/null; then
            log_success "Database is healthy"
            return 0
        fi
    fi
    
    log_error "Database is unhealthy"
    FAILED_CHECKS+=("database")
    HEALTH_STATUS="unhealthy"
    return 1
}

# Redis 연결 확인
check_redis() {
    echo -n "Checking Redis connection... "
    
    if docker compose -f docker-compose.prod.yml exec -T redis \
        redis-cli ping | grep -q PONG; then
        log_success "Redis is healthy"
        return 0
    fi
    
    log_error "Redis is unhealthy"
    FAILED_CHECKS+=("redis")
    HEALTH_STATUS="unhealthy"
    return 1
}

# 디스크 공간 확인
check_disk_space() {
    echo -n "Checking disk space... "
    
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ $usage -lt 80 ]; then
        log_success "Disk usage is healthy ($usage%)"
        return 0
    elif [ $usage -lt 90 ]; then
        log_warning "Disk usage is high ($usage%)"
        return 0
    else
        log_error "Disk usage is critical ($usage%)"
        FAILED_CHECKS+=("disk_space")
        HEALTH_STATUS="unhealthy"
        return 1
    fi
}

# 메모리 사용량 확인
check_memory() {
    echo -n "Checking memory usage... "
    
    local usage=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
    
    if [ $usage -lt 80 ]; then
        log_success "Memory usage is healthy ($usage%)"
        return 0
    elif [ $usage -lt 90 ]; then
        log_warning "Memory usage is high ($usage%)"
        return 0
    else
        log_error "Memory usage is critical ($usage%)"
        FAILED_CHECKS+=("memory")
        HEALTH_STATUS="unhealthy"
        return 1
    fi
}

# SSL 인증서 확인
check_ssl_certificate() {
    local domain=$1
    echo -n "Checking SSL certificate for $domain... "
    
    local expiry=$(echo | openssl s_client -servername $domain -connect $domain:443 2>/dev/null | \
        openssl x509 -noout -enddate 2>/dev/null | \
        cut -d= -f2)
    
    if [ -z "$expiry" ]; then
        log_error "Failed to check SSL certificate"
        FAILED_CHECKS+=("ssl_$domain")
        HEALTH_STATUS="unhealthy"
        return 1
    fi
    
    local expiry_epoch=$(date -d "$expiry" +%s)
    local current_epoch=$(date +%s)
    local days_left=$(( ($expiry_epoch - $current_epoch) / 86400 ))
    
    if [ $days_left -gt 30 ]; then
        log_success "SSL certificate is valid ($days_left days left)"
        return 0
    elif [ $days_left -gt 7 ]; then
        log_warning "SSL certificate expires soon ($days_left days left)"
        return 0
    else
        log_error "SSL certificate expires in $days_left days!"
        FAILED_CHECKS+=("ssl_$domain")
        HEALTH_STATUS="unhealthy"
        return 1
    fi
}

# 메인 헬스체크 실행
echo "🏥 Running production health checks..."
echo "================================"

# 1. API 엔드포인트 체크
check_endpoint "API Health" "$API_URL/health" 200
check_json_endpoint "API Status" "$API_URL/health" ".status" "healthy"

# 2. Frontend 체크
check_endpoint "Frontend" "$FRONTEND_URL" 200

# 3. 데이터베이스 체크
check_database

# 4. Redis 체크
check_redis

# 5. 시스템 리소스 체크
check_disk_space
check_memory

# 6. SSL 인증서 체크
check_ssl_certificate "api.yourdomain.com"
check_ssl_certificate "app.yourdomain.com"

# 7. 특정 API 기능 테스트
check_endpoint "Product API" "$API_URL/api/v1/products?page=1&per_page=1" 200
check_endpoint "Order API" "$API_URL/api/v1/orders?page=1&per_page=1" 401  # 인증 필요

echo "================================"

# 결과 요약
if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    
    # 성공 메트릭 전송
    if [ ! -z "$MONITORING_ENDPOINT" ]; then
        curl -X POST $MONITORING_ENDPOINT/metrics \
            -H "Content-Type: application/json" \
            -d '{
                "metric": "health_check.status",
                "value": 1,
                "tags": {"status": "healthy"}
            }' &>/dev/null || true
    fi
    
    exit 0
else
    echo -e "${RED}❌ Health check failed!${NC}"
    echo "Failed checks: ${FAILED_CHECKS[@]}"
    
    # 실패 메트릭 전송
    if [ ! -z "$MONITORING_ENDPOINT" ]; then
        curl -X POST $MONITORING_ENDPOINT/metrics \
            -H "Content-Type: application/json" \
            -d '{
                "metric": "health_check.status",
                "value": 0,
                "tags": {"status": "unhealthy", "failed": "'${FAILED_CHECKS[@]}'"}
            }' &>/dev/null || true
    fi
    
    # Slack 알림
    if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST $SLACK_WEBHOOK_URL \
            -H 'Content-Type: application/json' \
            -d '{
                "text": "❌ Production health check failed!",
                "attachments": [{
                    "color": "danger",
                    "fields": [
                        {"title": "Failed Checks", "value": "'${FAILED_CHECKS[@]}'", "short": false}
                    ]
                }]
            }' &>/dev/null || true
    fi
    
    exit 1
fi