#!/bin/bash

# 드롭시핑 시스템 헬스체크 스크립트
# 시스템의 모든 구성 요소 상태를 확인합니다

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 아이콘 정의
SUCCESS="✅"
FAILURE="❌"
WARNING="⚠️"
INFO="ℹ️"

# 설정
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# 전역 변수
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 로그 함수들
log_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

log_success() {
    echo -e "${GREEN}${SUCCESS} $1${NC}"
    ((PASSED_CHECKS++))
}

log_failure() {
    echo -e "${RED}${FAILURE} $1${NC}"
    ((FAILED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

# 헬스체크 함수
check_service() {
    local service_name="$1"
    local url="$2"
    local timeout="${3:-10}"
    
    ((TOTAL_CHECKS++))
    log_info "Checking $service_name..."
    
    if curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1; then
        log_success "$service_name is healthy"
        return 0
    else
        log_failure "$service_name is not responding"
        return 1
    fi
}

check_database() {
    ((TOTAL_CHECKS++))
    log_info "Checking PostgreSQL database..."
    
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
        log_success "PostgreSQL is healthy"
        
        # 연결 테스트
        if psql -h "$DB_HOST" -p "$DB_PORT" -U dropshipping -d dropshipping_db -c "SELECT 1;" > /dev/null 2>&1; then
            log_success "Database connection successful"
        else
            log_warning "Database is running but connection failed"
        fi
        return 0
    else
        log_failure "PostgreSQL is not responding"
        return 1
    fi
}

check_redis() {
    ((TOTAL_CHECKS++))
    log_info "Checking Redis..."
    
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
        return 0
    else
        log_failure "Redis is not responding"
        return 1
    fi
}

check_disk_space() {
    ((TOTAL_CHECKS++))
    log_info "Checking disk space..."
    
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -lt 80 ]; then
        log_success "Disk usage: ${usage}% (OK)"
        return 0
    elif [ "$usage" -lt 90 ]; then
        log_warning "Disk usage: ${usage}% (Warning)"
        return 1
    else
        log_failure "Disk usage: ${usage}% (Critical)"
        return 1
    fi
}

check_memory() {
    ((TOTAL_CHECKS++))
    log_info "Checking memory usage..."
    
    local usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    
    if [ "$usage" -lt 80 ]; then
        log_success "Memory usage: ${usage}% (OK)"
        return 0
    elif [ "$usage" -lt 90 ]; then
        log_warning "Memory usage: ${usage}% (Warning)"
        return 1
    else
        log_failure "Memory usage: ${usage}% (Critical)"
        return 1
    fi
}

check_cpu() {
    ((TOTAL_CHECKS++))
    log_info "Checking CPU usage..."
    
    local usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2+$4}' | sed 's/%us,//' | cut -d'%' -f1)
    
    if (( $(echo "$usage < 80" | bc -l) )); then
        log_success "CPU usage: ${usage}% (OK)"
        return 0
    elif (( $(echo "$usage < 90" | bc -l) )); then
        log_warning "CPU usage: ${usage}% (Warning)"
        return 1
    else
        log_failure "CPU usage: ${usage}% (Critical)"
        return 1
    fi
}

check_docker_containers() {
    ((TOTAL_CHECKS++))
    log_info "Checking Docker containers..."
    
    if command -v docker > /dev/null 2>&1; then
        local unhealthy=$(docker ps --filter "health=unhealthy" -q | wc -l)
        local total=$(docker ps -q | wc -l)
        
        if [ "$unhealthy" -eq 0 ]; then
            log_success "All $total Docker containers are healthy"
            return 0
        else
            log_failure "$unhealthy out of $total Docker containers are unhealthy"
            return 1
        fi
    else
        log_warning "Docker not available"
        return 1
    fi
}

check_ssl_certificate() {
    ((TOTAL_CHECKS++))
    log_info "Checking SSL certificate..."
    
    local domain=$(echo "$BACKEND_URL" | sed -e 's|^[^/]*//||' -e 's|/.*$||')
    
    if [[ "$BACKEND_URL" == https* ]]; then
        local expiry=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
        local expiry_epoch=$(date -d "$expiry" +%s)
        local current_epoch=$(date +%s)
        local days_left=$(( (expiry_epoch - current_epoch) / 86400 ))
        
        if [ "$days_left" -gt 30 ]; then
            log_success "SSL certificate expires in $days_left days"
            return 0
        elif [ "$days_left" -gt 7 ]; then
            log_warning "SSL certificate expires in $days_left days"
            return 1
        else
            log_failure "SSL certificate expires in $days_left days (Critical)"
            return 1
        fi
    else
        log_warning "No SSL certificate (HTTP only)"
        return 1
    fi
}

check_log_files() {
    ((TOTAL_CHECKS++))
    log_info "Checking log files..."
    
    local log_dir="./logs"
    if [ -d "$log_dir" ]; then
        local large_logs=$(find "$log_dir" -name "*.log" -size +100M | wc -l)
        
        if [ "$large_logs" -eq 0 ]; then
            log_success "Log files are within normal size"
            return 0
        else
            log_warning "$large_logs log files are larger than 100MB"
            return 1
        fi
    else
        log_warning "Log directory not found"
        return 1
    fi
}

check_backup_status() {
    ((TOTAL_CHECKS++))
    log_info "Checking backup status..."
    
    local backup_dir="./backups"
    if [ -d "$backup_dir" ]; then
        local latest_backup=$(find "$backup_dir" -name "*.dump" -mtime -1 | wc -l)
        
        if [ "$latest_backup" -gt 0 ]; then
            log_success "Recent backup found (within 24 hours)"
            return 0
        else
            log_warning "No recent backup found"
            return 1
        fi
    else
        log_warning "Backup directory not found"
        return 1
    fi
}

# API 엔드포인트 상세 체크
check_api_endpoints() {
    log_info "Checking API endpoints..."
    
    local endpoints=(
        "/health:Health check"
        "/docs:API documentation"
        "/api/auth/me:Authentication (requires token)"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint="${endpoint_info%%:*}"
        local description="${endpoint_info##*:}"
        
        ((TOTAL_CHECKS++))
        if curl -f -s --max-time 5 "$BACKEND_URL$endpoint" > /dev/null 2>&1; then
            log_success "$description is accessible"
        else
            if [[ "$endpoint" == *"/me" ]]; then
                log_warning "$description (expected - requires authentication)"
            else
                log_failure "$description is not accessible"
            fi
        fi
    done
}

# 메트릭 확인
check_metrics() {
    log_info "Checking system metrics..."
    
    if curl -f -s --max-time 5 "$BACKEND_URL/metrics" > /dev/null 2>&1; then
        ((TOTAL_CHECKS++))
        log_success "Prometheus metrics are available"
        
        # 특정 메트릭 확인
        local http_requests=$(curl -s "$BACKEND_URL/metrics" | grep "http_requests_total" | wc -l)
        if [ "$http_requests" -gt 0 ]; then
            log_success "HTTP request metrics are being collected"
        else
            log_warning "HTTP request metrics not found"
        fi
    else
        ((TOTAL_CHECKS++))
        log_failure "Prometheus metrics are not available"
    fi
}

# 메인 함수
main() {
    echo "============================================"
    echo "     Dropshipping System Health Check"
    echo "============================================"
    echo ""
    echo "Timestamp: $(date)"
    echo ""
    
    # 핵심 서비스 체크
    echo "🔍 Core Services"
    echo "----------------"
    check_service "Backend API" "$BACKEND_URL/health"
    check_database
    check_redis
    echo ""
    
    # 시스템 리소스 체크
    echo "💻 System Resources"
    echo "-------------------"
    check_disk_space
    check_memory
    check_cpu
    echo ""
    
    # 인프라 체크
    echo "🐳 Infrastructure"
    echo "-----------------"
    check_docker_containers
    check_ssl_certificate
    echo ""
    
    # 애플리케이션 체크
    echo "🚀 Application"
    echo "--------------"
    check_api_endpoints
    check_metrics
    echo ""
    
    # 운영 체크
    echo "🔧 Operations"
    echo "-------------"
    check_log_files
    check_backup_status
    echo ""
    
    # 모니터링 시스템 체크 (선택적)
    if curl -f -s --max-time 3 "$PROMETHEUS_URL/-/healthy" > /dev/null 2>&1; then
        check_service "Prometheus" "$PROMETHEUS_URL/-/healthy"
    fi
    
    if curl -f -s --max-time 3 "$GRAFANA_URL/api/health" > /dev/null 2>&1; then
        check_service "Grafana" "$GRAFANA_URL/api/health"
    fi
    
    # 결과 요약
    echo ""
    echo "============================================"
    echo "              HEALTH CHECK SUMMARY"
    echo "============================================"
    echo ""
    echo "Total checks: $TOTAL_CHECKS"
    echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
    echo ""
    
    local success_rate=$(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))
    
    if [ "$FAILED_CHECKS" -eq 0 ]; then
        echo -e "${GREEN}🎉 All systems are healthy! ($success_rate%)${NC}"
        exit 0
    elif [ "$success_rate" -ge 80 ]; then
        echo -e "${YELLOW}⚠️  Some issues detected but system is mostly healthy ($success_rate%)${NC}"
        exit 1
    else
        echo -e "${RED}🚨 Critical issues detected! System health is poor ($success_rate%)${NC}"
        exit 2
    fi
}

# 도움말
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  --backend-url URL   Backend API URL (default: http://localhost:8000)"
    echo "  --prometheus-url URL Prometheus URL (default: http://localhost:9090)"
    echo "  --grafana-url URL   Grafana URL (default: http://localhost:3000)"
    echo ""
    echo "Environment variables:"
    echo "  BACKEND_URL         Backend API URL"
    echo "  PROMETHEUS_URL      Prometheus URL"
    echo "  GRAFANA_URL         Grafana URL"
    echo "  DB_HOST            Database host (default: localhost)"
    echo "  DB_PORT            Database port (default: 5432)"
    echo "  REDIS_HOST         Redis host (default: localhost)"
    echo "  REDIS_PORT         Redis port (default: 6379)"
    exit 0
fi

# 옵션 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --prometheus-url)
            PROMETHEUS_URL="$2"
            shift 2
            ;;
        --grafana-url)
            GRAFANA_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 메인 실행
main