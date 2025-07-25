-- 드롭시핑 시스템 데이터베이스 초기화 스크립트

-- 확장 프로그램 설치
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 사용자 권한 설정
GRANT ALL PRIVILEGES ON DATABASE dropshipping_db TO dropshipping;

-- 스키마 생성
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS logs;

-- 감사 로그 테이블
CREATE TABLE IF NOT EXISTS audit.user_activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id INTEGER,
    old_data JSONB,
    new_data JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 시스템 로그 테이블
CREATE TABLE IF NOT EXISTS logs.system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    logger VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    module VARCHAR(100),
    function_name VARCHAR(100),
    line_number INTEGER,
    request_id UUID,
    user_id INTEGER,
    extra_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_audit_user_activities_user_id ON audit.user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_user_activities_created_at ON audit.user_activities(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_system_logs_level ON logs.system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_system_logs_created_at ON logs.system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_system_logs_request_id ON logs.system_logs(request_id);

-- 파티션 테이블 설정 (월별)
-- system_logs 테이블을 월별로 파티션
DO $$
DECLARE
    start_date DATE := DATE_TRUNC('month', CURRENT_DATE);
    end_date DATE;
    table_name TEXT;
BEGIN
    FOR i IN 0..11 LOOP  -- 현재 월부터 11개월 후까지
        end_date := start_date + INTERVAL '1 month';
        table_name := 'system_logs_' || TO_CHAR(start_date, 'YYYY_MM');
        
        -- 파티션 테이블이 존재하지 않으면 생성
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'logs' AND table_name = table_name
        ) THEN
            EXECUTE format('
                CREATE TABLE logs.%I PARTITION OF logs.system_logs
                FOR VALUES FROM (%L) TO (%L)
            ', table_name, start_date, end_date);
        END IF;
        
        start_date := end_date;
    END LOOP;
END $$;

-- 데이터 보존 정책 함수
CREATE OR REPLACE FUNCTION logs.cleanup_old_logs()
RETURNS void AS $$
BEGIN
    -- 90일 이상 된 시스템 로그 삭제
    DELETE FROM logs.system_logs 
    WHERE created_at < CURRENT_DATE - INTERVAL '90 days';
    
    -- 1년 이상 된 감사 로그 삭제
    DELETE FROM audit.user_activities 
    WHERE created_at < CURRENT_DATE - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;

-- 성능 모니터링 뷰
CREATE OR REPLACE VIEW logs.slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time,
    stddev_time
FROM pg_stat_statements
WHERE mean_time > 100  -- 100ms 이상의 쿼리
ORDER BY mean_time DESC;

-- 커넥션 모니터링 뷰
CREATE OR REPLACE VIEW logs.connection_stats AS
SELECT 
    datname as database,
    numbackends as active_connections,
    xact_commit as transactions_committed,
    xact_rollback as transactions_rolled_back,
    blks_read as blocks_read,
    blks_hit as blocks_hit,
    tup_returned as tuples_returned,
    tup_fetched as tuples_fetched,
    tup_inserted as tuples_inserted,
    tup_updated as tuples_updated,
    tup_deleted as tuples_deleted
FROM pg_stat_database
WHERE datname = 'dropshipping_db';

-- 권한 부여
GRANT USAGE ON SCHEMA audit TO dropshipping;
GRANT USAGE ON SCHEMA logs TO dropshipping;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO dropshipping;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA logs TO dropshipping;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO dropshipping;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA logs TO dropshipping;

-- 초기 설정 완료 로그
INSERT INTO logs.system_logs (level, logger, message, module) 
VALUES ('INFO', 'init_db', 'Database initialization completed', 'database');

COMMIT;