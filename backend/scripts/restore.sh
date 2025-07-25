#!/bin/bash

# 드롭시핑 시스템 복구 스크립트
# 백업 파일에서 데이터베이스를 복구합니다

set -e

# 설정
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-dropshipping_db}"
DB_USER="${DB_USER:-dropshipping}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

# 도움말 표시
show_help() {
    echo "Usage: $0 [OPTIONS] BACKUP_FILE"
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help          Show this help message"
    echo "  -f, --force         Force restore without confirmation"
    echo "  -s, --schema-only   Restore schema only"
    echo "  -d, --data-only     Restore data only"
    echo "  --clean             Clean database before restore"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 full_backup_20231201_120000.dump"
    echo "  $0 --schema-only schema_backup_20231201_120000.sql.gz"
    echo "  $0 --force --clean full_backup_20231201_120000.dump"
    echo ""
}

# 기본값 설정
FORCE=false
SCHEMA_ONLY=false
DATA_ONLY=false
CLEAN=false
BACKUP_FILE=""

# 인수 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -s|--schema-only)
            SCHEMA_ONLY=true
            shift
            ;;
        -d|--data-only)
            DATA_ONLY=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        -*)
            echo "Unknown option $1"
            show_help
            exit 1
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# 백업 파일 검증
if [ -z "$BACKUP_FILE" ]; then
    echo "Error: Backup file not specified"
    show_help
    exit 1
fi

# 백업 파일 경로 설정
if [[ "$BACKUP_FILE" != /* ]]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    echo ""
    echo "Available backup files:"
    ls -la "$BACKUP_DIR"/ | grep -E '\.(dump|sql|sql\.gz)$'
    exit 1
fi

# 데이터베이스 연결 테스트
echo "Testing database connection..."
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
    echo "Error: Cannot connect to database"
    exit 1
fi

echo "Database connection successful"

# 확인 메시지
if [ "$FORCE" = false ]; then
    echo ""
    echo "⚠️  WARNING: This will restore the database and may overwrite existing data!"
    echo ""
    echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
    echo "Backup file: $BACKUP_FILE"
    echo "Options:"
    [ "$SCHEMA_ONLY" = true ] && echo "  - Schema only"
    [ "$DATA_ONLY" = true ] && echo "  - Data only"
    [ "$CLEAN" = true ] && echo "  - Clean database before restore"
    echo ""
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Restore cancelled"
        exit 0
    fi
fi

# 백업 생성 (복구 전 현재 상태 백업)
echo "Creating pre-restore backup..."
PRE_RESTORE_BACKUP="$BACKUP_DIR/pre_restore_$(date +%Y%m%d_%H%M%S).dump"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-password --verbose --format=custom \
    --file="$PRE_RESTORE_BACKUP" || {
    echo "Warning: Failed to create pre-restore backup"
}

# 데이터베이스 정리 (필요한 경우)
if [ "$CLEAN" = true ]; then
    echo "Cleaning database..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-password -c "
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO $DB_USER;
        GRANT ALL ON SCHEMA public TO public;
    "
fi

# 복구 실행
echo "Starting database restore from: $BACKUP_FILE"
echo "Started at: $(date)"

# 파일 확장자에 따라 복구 방법 결정
if [[ "$BACKUP_FILE" == *.dump ]]; then
    # pg_dump custom format
    PG_RESTORE_OPTIONS="--verbose --no-owner --no-privileges"
    
    if [ "$SCHEMA_ONLY" = true ]; then
        PG_RESTORE_OPTIONS="$PG_RESTORE_OPTIONS --schema-only"
    elif [ "$DATA_ONLY" = true ]; then
        PG_RESTORE_OPTIONS="$PG_RESTORE_OPTIONS --data-only"
    fi
    
    if [ "$CLEAN" = true ] && [ "$SCHEMA_ONLY" != true ]; then
        PG_RESTORE_OPTIONS="$PG_RESTORE_OPTIONS --clean"
    fi
    
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-password $PG_RESTORE_OPTIONS "$BACKUP_FILE"

elif [[ "$BACKUP_FILE" == *.sql.gz ]]; then
    # 압축된 SQL 파일
    echo "Decompressing and restoring SQL file..."
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --no-password

elif [[ "$BACKUP_FILE" == *.sql ]]; then
    # 일반 SQL 파일
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-password -f "$BACKUP_FILE"

else
    echo "Error: Unsupported backup file format"
    echo "Supported formats: .dump, .sql, .sql.gz"
    exit 1
fi

# 복구 후 검증
echo ""
echo "Verifying restore..."

# 테이블 수 확인
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-password -t -c "
    SELECT COUNT(*) 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
")

echo "Tables restored: $TABLE_COUNT"

# 시퀀스 수정 (필요한 경우)
echo "Updating sequences..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-password -c "
    SELECT setval(sequence_name, COALESCE(max_value, 1))
    FROM (
        SELECT 
            pg_get_serial_sequence(table_name, column_name) as sequence_name,
            MAX(column_value::bigint) as max_value
        FROM (
            SELECT 
                table_name,
                column_name,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_default LIKE 'nextval%'
        ) t
        CROSS JOIN LATERAL (
            SELECT column_value
            FROM (
                SELECT unnest(string_to_array(
                    string_agg(quote_ident(column_name), ','), ','
                )) as column_value
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = t.table_name
                  AND column_name = t.column_name
            ) v
        ) cv
        WHERE sequence_name IS NOT NULL
        GROUP BY sequence_name
    ) seq_updates;
" || echo "Warning: Failed to update sequences"

# 인덱스 재구성
echo "Reindexing database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-password -c "REINDEX DATABASE $DB_NAME;" || echo "Warning: Reindex failed"

# 통계 업데이트
echo "Updating statistics..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-password -c "ANALYZE;" || echo "Warning: Analyze failed"

echo ""
echo "✅ Database restore completed successfully!"
echo "Completed at: $(date)"
echo ""
echo "Summary:"
echo "  - Backup file: $BACKUP_FILE"
echo "  - Tables restored: $TABLE_COUNT"
echo "  - Pre-restore backup: $PRE_RESTORE_BACKUP"
echo ""
echo "Next steps:"
echo "  1. Test your application"
echo "  2. Verify data integrity"
echo "  3. Remove pre-restore backup if not needed"
echo ""