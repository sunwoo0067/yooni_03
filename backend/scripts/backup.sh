#!/bin/bash

# 드롭시핑 시스템 백업 스크립트
# 매일 자동으로 데이터베이스 백업을 수행

set -e

# 설정
DB_HOST="db"
DB_PORT="5432"
DB_NAME="dropshipping_db"
DB_USER="dropshipping"
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# 데이터베이스 백업
echo "Starting database backup at $(date)"

# Full 백업
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    --no-password --verbose --format=custom \
    --file="$BACKUP_DIR/full_backup_$DATE.dump"

# 스키마만 백업
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    --no-password --schema-only --format=plain \
    --file="$BACKUP_DIR/schema_backup_$DATE.sql"

# 압축
gzip "$BACKUP_DIR/schema_backup_$DATE.sql"

echo "Database backup completed at $(date)"

# 오래된 백업 파일 삭제 (7일 이상)
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "*.dump" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

# 백업 목록 출력
echo "Current backups:"
ls -lah $BACKUP_DIR/

echo "Backup script completed at $(date)"

# 무한 루프로 대기 (cron job 방식이 아닌 경우)
if [ "$1" = "daemon" ]; then
    echo "Running in daemon mode - will backup every 24 hours"
    while true; do
        sleep 86400  # 24시간 대기
        
        # 백업 실행
        DATE=$(date +%Y%m%d_%H%M%S)
        
        pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
            --no-password --verbose --format=custom \
            --file="$BACKUP_DIR/full_backup_$DATE.dump"
        
        pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
            --no-password --schema-only --format=plain \
            --file="$BACKUP_DIR/schema_backup_$DATE.sql"
        
        gzip "$BACKUP_DIR/schema_backup_$DATE.sql"
        
        # 정리
        find $BACKUP_DIR -name "*.dump" -mtime +$RETENTION_DAYS -delete
        find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
        
        echo "Scheduled backup completed at $(date)"
    done
fi