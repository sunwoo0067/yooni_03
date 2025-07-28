#!/bin/bash
# Production backup script
# 프로덕션 백업 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 설정
BACKUP_DIR="/var/backups/dropshipping"
S3_BUCKET="s3://dropshipping-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 로깅 함수
log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR/{database,redis,media,logs}

log_info "🔄 Starting production backup..."

# 1. PostgreSQL 백업
log_info "💾 Backing up PostgreSQL database..."
DB_BACKUP_FILE="$BACKUP_DIR/database/dropshipping_prod_$TIMESTAMP.sql"

docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U $POSTGRES_USER -d $POSTGRES_DB \
    --verbose --no-owner --no-acl \
    --exclude-table-data='*.log_*' \
    > $DB_BACKUP_FILE

# 압축
gzip -9 $DB_BACKUP_FILE
DB_BACKUP_FILE="$DB_BACKUP_FILE.gz"

log_info "Database backup size: $(du -h $DB_BACKUP_FILE | cut -f1)"

# 2. Redis 백업
log_info "💾 Backing up Redis..."
REDIS_BACKUP_FILE="$BACKUP_DIR/redis/redis_$TIMESTAMP.rdb"

docker compose -f docker-compose.prod.yml exec -T redis \
    redis-cli --rdb $REDIS_BACKUP_FILE

# 압축
gzip -9 $REDIS_BACKUP_FILE
REDIS_BACKUP_FILE="$REDIS_BACKUP_FILE.gz"

# 3. 미디어 파일 백업
log_info "💾 Backing up media files..."
MEDIA_BACKUP_FILE="$BACKUP_DIR/media/media_$TIMESTAMP.tar.gz"

docker run --rm \
    -v dropshipping_media_volume:/data \
    -v $BACKUP_DIR/media:/backup \
    alpine \
    tar czf /backup/media_$TIMESTAMP.tar.gz -C /data .

# 4. 설정 파일 백업
log_info "💾 Backing up configuration..."
CONFIG_BACKUP_FILE="$BACKUP_DIR/config_$TIMESTAMP.tar.gz"

tar czf $CONFIG_BACKUP_FILE \
    .env.production \
    docker-compose.prod.yml \
    nginx/ \
    scripts/ \
    --exclude='*.log' \
    --exclude='__pycache__'

# 5. S3 업로드
if command -v aws &> /dev/null; then
    log_info "☁️ Uploading to S3..."
    
    # 데이터베이스
    aws s3 cp $DB_BACKUP_FILE \
        $S3_BUCKET/database/$(basename $DB_BACKUP_FILE) \
        --storage-class GLACIER_IR
    
    # Redis
    aws s3 cp $REDIS_BACKUP_FILE \
        $S3_BUCKET/redis/$(basename $REDIS_BACKUP_FILE) \
        --storage-class STANDARD_IA
    
    # 미디어 파일
    aws s3 cp $MEDIA_BACKUP_FILE \
        $S3_BUCKET/media/$(basename $MEDIA_BACKUP_FILE) \
        --storage-class GLACIER_IR
    
    # 설정 파일
    aws s3 cp $CONFIG_BACKUP_FILE \
        $S3_BUCKET/config/$(basename $CONFIG_BACKUP_FILE) \
        --storage-class STANDARD_IA
    
    log_info "✅ S3 upload completed"
else
    log_warn "AWS CLI not found, skipping S3 upload"
fi

# 6. 백업 검증
log_info "🔍 Verifying backups..."

# 데이터베이스 백업 검증
if gunzip -t $DB_BACKUP_FILE 2>/dev/null; then
    log_info "✓ Database backup verified"
else
    log_error "✗ Database backup verification failed!"
    exit 1
fi

# 7. 오래된 백업 정리
log_info "🧹 Cleaning up old backups..."

# 로컬 정리
find $BACKUP_DIR -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -type f -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# S3 정리 (lifecycle policy가 없는 경우)
if command -v aws &> /dev/null; then
    # 30일 이상 된 백업 삭제
    aws s3 ls $S3_BUCKET/database/ | \
        awk '{print $4}' | \
        while read file; do
            FILE_DATE=$(echo $file | grep -oE '[0-9]{8}')
            if [ ! -z "$FILE_DATE" ]; then
                FILE_AGE=$(( ($(date +%s) - $(date -d $FILE_DATE +%s)) / 86400 ))
                if [ $FILE_AGE -gt $RETENTION_DAYS ]; then
                    aws s3 rm $S3_BUCKET/database/$file
                    log_info "Deleted old backup: $file"
                fi
            fi
        done
fi

# 8. 백업 보고서 생성
REPORT_FILE="$BACKUP_DIR/backup_report_$TIMESTAMP.txt"
cat > $REPORT_FILE <<EOF
Backup Report - $(date)
================================

Database Backup: $(basename $DB_BACKUP_FILE)
Size: $(du -h $DB_BACKUP_FILE | cut -f1)

Redis Backup: $(basename $REDIS_BACKUP_FILE)
Size: $(du -h $REDIS_BACKUP_FILE | cut -f1)

Media Backup: $(basename $MEDIA_BACKUP_FILE)
Size: $(du -h $MEDIA_BACKUP_FILE | cut -f1)

Config Backup: $(basename $CONFIG_BACKUP_FILE)
Size: $(du -h $CONFIG_BACKUP_FILE | cut -f1)

Total Backup Size: $(du -sh $BACKUP_DIR | cut -f1)
S3 Upload: $(command -v aws &> /dev/null && echo "Completed" || echo "Skipped")

Retention Policy: $RETENTION_DAYS days
================================
EOF

log_info "📊 Backup report: $REPORT_FILE"

# 9. 모니터링 메트릭 전송
if [ ! -z "$MONITORING_ENDPOINT" ]; then
    curl -X POST $MONITORING_ENDPOINT/metrics \
        -H "Content-Type: application/json" \
        -d '{
            "metric": "backup.completed",
            "value": 1,
            "tags": {
                "type": "production",
                "timestamp": "'$TIMESTAMP'"
            }
        }' || log_warn "Failed to send monitoring metric"
fi

log_info "✅ Backup completed successfully!"
log_info "Backup location: $BACKUP_DIR"
log_info "Timestamp: $TIMESTAMP"

# 백업 완료 알림
if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST $SLACK_WEBHOOK_URL \
        -H 'Content-Type: application/json' \
        -d '{
            "text": "✅ Production backup completed",
            "attachments": [{
                "color": "good",
                "fields": [
                    {"title": "Timestamp", "value": "'$TIMESTAMP'", "short": true},
                    {"title": "Total Size", "value": "'$(du -sh $BACKUP_DIR | cut -f1)'", "short": true}
                ]
            }]
        }' || log_warn "Failed to send Slack notification"
fi