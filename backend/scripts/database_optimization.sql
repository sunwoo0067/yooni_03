-- 드랍쉬핑 시스템 데이터베이스 최적화 SQL 스크립트
-- 실행 전 반드시 백업하세요!

-- =====================================================
-- 1. 인덱스 추가 (즉시 실행 가능)
-- =====================================================

-- 상품 검색 최적화
CREATE INDEX CONCURRENTLY idx_products_name ON products USING gin(to_tsvector('korean', name));
CREATE INDEX CONCURRENTLY idx_products_brand ON products(brand);
CREATE INDEX CONCURRENTLY idx_products_status ON products(status) WHERE status = 'active';
CREATE INDEX CONCURRENTLY idx_products_wholesale_account ON products(wholesale_account_id);

-- 주문 검색 최적화
CREATE INDEX CONCURRENTLY idx_orders_customer_email ON orders(customer_email);
CREATE INDEX CONCURRENTLY idx_orders_created_status ON orders(created_at DESC, status);
CREATE INDEX CONCURRENTLY idx_orders_platform_order_id ON orders(platform_order_id);
CREATE INDEX CONCURRENTLY idx_order_items_product_order ON order_items(product_id, order_id);

-- 재고 관리 최적화
CREATE INDEX CONCURRENTLY idx_inventory_product_warehouse ON inventory_items(product_id, warehouse_id);
CREATE INDEX CONCURRENTLY idx_inventory_movements_date ON inventory_movements(created_at DESC);

-- 벤치마크 검색 최적화
CREATE INDEX CONCURRENTLY idx_benchmark_products_name ON benchmark_products USING gin(to_tsvector('korean', product_name));
CREATE INDEX CONCURRENTLY idx_benchmark_price_history_time ON benchmark_price_history(market_product_id, recorded_at DESC);

-- 드랍쉬핑 주문 최적화
CREATE INDEX CONCURRENTLY idx_dropshipping_orders_status_created ON dropshipping_orders(status, created_at DESC);

-- =====================================================
-- 2. 파티셔닝 설정 (대용량 테이블)
-- =====================================================

-- 주문 테이블 월별 파티셔닝 (새 테이블로 마이그레이션 필요)
CREATE TABLE orders_partitioned (
    LIKE orders INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 2024년 파티션 생성
CREATE TABLE orders_2024_01 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE orders_2024_02 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE orders_2024_03 PARTITION OF orders_partitioned
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
-- ... 필요한 만큼 추가

-- 재고 이동 이력 파티셔닝
CREATE TABLE inventory_movements_partitioned (
    LIKE inventory_movements INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- =====================================================
-- 3. 뷰 생성 (자주 사용되는 복잡한 쿼리)
-- =====================================================

-- 활성 상품 요약 뷰
CREATE OR REPLACE VIEW v_active_products_summary AS
SELECT 
    p.id,
    p.name,
    p.brand,
    p.selling_price,
    p.wholesale_price,
    p.selling_price - p.wholesale_price as profit,
    ((p.selling_price - p.wholesale_price) / NULLIF(p.wholesale_price, 0) * 100) as profit_margin,
    wa.name as wholesaler_name,
    COUNT(DISTINCT oi.id) as total_orders,
    SUM(oi.quantity) as total_sold
FROM products p
LEFT JOIN wholesaler_accounts wa ON p.wholesale_account_id = wa.id
LEFT JOIN order_items oi ON p.id = oi.product_id
WHERE p.status = 'active'
GROUP BY p.id, wa.name;

-- 일일 판매 요약 뷰
CREATE OR REPLACE VIEW v_daily_sales_summary AS
SELECT 
    DATE(o.created_at) as sale_date,
    o.platform,
    COUNT(DISTINCT o.id) as order_count,
    SUM(o.total_amount) as total_revenue,
    AVG(o.total_amount) as avg_order_value,
    COUNT(DISTINCT o.customer_email) as unique_customers
FROM orders o
WHERE o.status IN ('completed', 'shipped', 'delivered')
GROUP BY DATE(o.created_at), o.platform;

-- =====================================================
-- 4. 함수 생성 (비즈니스 로직)
-- =====================================================

-- 상품 마진 계산 함수
CREATE OR REPLACE FUNCTION calculate_product_margin(
    selling_price DECIMAL,
    wholesale_price DECIMAL,
    platform_fee_rate DECIMAL DEFAULT 0.1
) RETURNS TABLE(
    gross_margin DECIMAL,
    net_margin DECIMAL,
    margin_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        selling_price - wholesale_price as gross_margin,
        selling_price - wholesale_price - (selling_price * platform_fee_rate) as net_margin,
        CASE 
            WHEN wholesale_price > 0 THEN 
                ((selling_price - wholesale_price - (selling_price * platform_fee_rate)) / wholesale_price * 100)
            ELSE 0 
        END as margin_rate;
END;
$$ LANGUAGE plpgsql;

-- 재고 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION update_inventory_on_order() RETURNS TRIGGER AS $$
BEGIN
    -- 주문 생성 시 재고 감소
    IF TG_OP = 'INSERT' AND NEW.status = 'confirmed' THEN
        UPDATE inventory_items 
        SET quantity = quantity - NEW.quantity,
            updated_at = NOW()
        WHERE product_id = NEW.product_id;
        
        -- 재고 이동 기록
        INSERT INTO inventory_movements (
            product_id, quantity, movement_type, 
            reference_type, reference_id, created_at
        ) VALUES (
            NEW.product_id, -NEW.quantity, 'sale',
            'order', NEW.order_id::text, NOW()
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
CREATE TRIGGER trigger_update_inventory_on_order
AFTER INSERT ON order_items
FOR EACH ROW
EXECUTE FUNCTION update_inventory_on_order();

-- =====================================================
-- 5. 성능 최적화 설정
-- =====================================================

-- 통계 수집 빈도 증가 (활발한 테이블)
ALTER TABLE products SET (autovacuum_analyze_scale_factor = 0.02);
ALTER TABLE orders SET (autovacuum_analyze_scale_factor = 0.02);
ALTER TABLE inventory_items SET (autovacuum_analyze_scale_factor = 0.02);

-- 큰 테이블의 vacuum 설정
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE order_items SET (autovacuum_vacuum_scale_factor = 0.1);

-- =====================================================
-- 6. 보안 강화
-- =====================================================

-- 민감한 데이터 암호화를 위한 확장 기능
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- API 키 암호화 함수
CREATE OR REPLACE FUNCTION encrypt_api_key(api_key TEXT) RETURNS TEXT AS $$
BEGIN
    RETURN encode(pgp_sym_encrypt(api_key, current_setting('app.encryption_key')), 'base64');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrypt_api_key(encrypted_key TEXT) RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(decode(encrypted_key, 'base64'), current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 7. 모니터링 뷰
-- =====================================================

-- 슬로우 쿼리 모니터링
CREATE OR REPLACE VIEW v_slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time,
    stddev_time
FROM pg_stat_statements
WHERE mean_time > 100  -- 100ms 이상
ORDER BY mean_time DESC
LIMIT 50;

-- 테이블 크기 모니터링
CREATE OR REPLACE VIEW v_table_sizes AS
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- =====================================================
-- 8. 데이터 정리 (아카이빙)
-- =====================================================

-- 오래된 로그 데이터 아카이빙 테이블
CREATE TABLE archived_logs (
    LIKE logs INCLUDING ALL
);

-- 6개월 이상 된 로그 이동
INSERT INTO archived_logs 
SELECT * FROM logs 
WHERE created_at < NOW() - INTERVAL '6 months';

DELETE FROM logs 
WHERE created_at < NOW() - INTERVAL '6 months';

-- =====================================================
-- 9. 통계 정보 갱신
-- =====================================================

-- 주요 테이블 통계 갱신
ANALYZE products;
ANALYZE orders;
ANALYZE order_items;
ANALYZE inventory_items;
ANALYZE benchmark_products;