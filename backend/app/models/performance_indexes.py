"""
성능 최적화를 위한 데이터베이스 인덱스 정의
복합 인덱스, 부분 인덱스, 함수 기반 인덱스 포함
"""

from sqlalchemy import Index, text
from sqlalchemy.schema import CreateIndex
from app.models.product import Product, ProductVariant, PlatformListing, ProductPriceHistory
from app.models.order_core import Order, OrderItem
from app.models.user import User
from app.models.platform_account import PlatformAccount


# ======================
# 주문(Order) 관련 인덱스
# ======================

# 1. 주문 조회 최적화 (복합 인덱스)
order_status_created_idx = Index(
    'idx_order_status_created',
    Order.status,
    Order.created_at.desc(),
    postgresql_include=['customer_name', 'platform_type', 'total_amount']
)

# 2. 플랫폼별 주문 조회
order_platform_created_idx = Index(
    'idx_order_platform_created',
    Order.platform_type,
    Order.created_at.desc(),
    postgresql_where=Order.status.in_(['pending', 'processing', 'shipped'])
)

# 3. 고객별 주문 히스토리
order_customer_idx = Index(
    'idx_order_customer_history',
    Order.customer_phone,
    Order.customer_email,
    Order.created_at.desc(),
    postgresql_include=['order_number', 'total_amount', 'status']
)

# 4. 주문 번호 고속 검색
order_number_idx = Index(
    'idx_order_number_unique',
    Order.order_number,
    unique=True,
    postgresql_include=['id', 'status', 'created_at']
)

# 5. 배송 추적 최적화
order_tracking_idx = Index(
    'idx_order_tracking',
    Order.tracking_number,
    postgresql_where=Order.tracking_number.is_not(None),
    postgresql_include=['order_number', 'status', 'shipped_at']
)

# 6. 일별 주문 집계 최적화 (함수 기반 인덱스)
order_date_aggregation_idx = Index(
    'idx_order_date_aggregation',
    text('DATE(created_at)'),
    Order.status,
    postgresql_include=['id']
)


# ======================
# 주문항목(OrderItem) 관련 인덱스
# ======================

# 1. 주문-상품 조인 최적화
order_item_order_product_idx = Index(
    'idx_order_item_order_product',
    OrderItem.order_id,
    OrderItem.product_id,
    postgresql_include=['quantity', 'price']
)

# 2. 상품별 주문 통계
order_item_product_stats_idx = Index(
    'idx_order_item_product_stats',
    OrderItem.product_id,
    text('(price * quantity)'),  # 총액 계산 최적화
    postgresql_include=['order_id', 'quantity']
)


# ======================
# 상품(Product) 관련 인덱스
# ======================

# 1. 상품 검색 최적화 (전문 검색)
product_search_idx = Index(
    'idx_product_search',
    Product.name,
    Product.sku,
    Product.brand,
    postgresql_using='gin',
    postgresql_ops={
        'name': 'gin_trgm_ops',
        'sku': 'gin_trgm_ops',
        'brand': 'gin_trgm_ops'
    }
)

# 2. 상품 상태별 조회
product_status_created_idx = Index(
    'idx_product_status_created',
    Product.status,
    Product.created_at.desc(),
    postgresql_include=['sku', 'name', 'retail_price', 'stock_quantity']
)

# 3. 재고 관리 최적화
product_stock_management_idx = Index(
    'idx_product_stock_management',
    Product.stock_quantity,
    Product.min_stock_level,
    postgresql_where=Product.status == 'active',
    postgresql_include=['sku', 'name', 'wholesale_price']
)

# 4. 가격 범위 검색
product_price_range_idx = Index(
    'idx_product_price_range',
    Product.retail_price,
    Product.status,
    postgresql_where=Product.retail_price.is_not(None),
    postgresql_include=['sku', 'name', 'brand']
)

# 5. 브랜드별 상품 조회
product_brand_category_idx = Index(
    'idx_product_brand_category',
    Product.brand,
    Product.category_path,
    Product.status,
    postgresql_include=['sku', 'name', 'retail_price']
)

# 6. 플랫폼 계정별 상품
product_platform_account_idx = Index(
    'idx_product_platform_account',
    Product.platform_account_id,
    Product.status,
    Product.created_at.desc(),
    postgresql_include=['sku', 'name']
)

# 7. 도매처별 상품 관리
product_wholesaler_idx = Index(
    'idx_product_wholesaler',
    Product.wholesaler_id,
    Product.wholesaler_product_id,
    Product.is_dropshipping,
    postgresql_include=['sku', 'name', 'wholesale_price', 'stock_quantity']
)

# 8. 저재고 상품 알림
product_low_stock_idx = Index(
    'idx_product_low_stock',
    Product.stock_quantity,
    postgresql_where=text('stock_quantity <= min_stock_level AND status = \'active\''),
    postgresql_include=['sku', 'name', 'min_stock_level', 'platform_account_id']
)

# 9. AI 최적화 상품
product_ai_optimized_idx = Index(
    'idx_product_ai_optimized',
    Product.ai_optimized,
    Product.performance_score,
    postgresql_where=Product.ai_optimized == True,
    postgresql_include=['sku', 'name', 'search_rank']
)


# ======================
# 상품 변형(ProductVariant) 관련 인덱스
# ======================

# 1. 상품별 변형 조회
variant_product_idx = Index(
    'idx_variant_product',
    ProductVariant.product_id,
    ProductVariant.is_active,
    postgresql_include=['variant_sku', 'sale_price', 'stock_quantity']
)

# 2. 변형 SKU 고속 검색
variant_sku_idx = Index(
    'idx_variant_sku_unique',
    ProductVariant.variant_sku,
    unique=True,
    postgresql_include=['product_id', 'sale_price', 'stock_quantity']
)


# ======================
# 플랫폼 리스팅(PlatformListing) 관련 인덱스
# ======================

# 1. 상품-플랫폼 매핑
listing_product_platform_idx = Index(
    'idx_listing_product_platform',
    PlatformListing.product_id,
    PlatformListing.platform_account_id,
    PlatformListing.is_published,
    postgresql_include=['platform_product_id', 'listed_price', 'sync_status']
)

# 2. 플랫폼별 리스팅 관리
listing_platform_status_idx = Index(
    'idx_listing_platform_status',
    PlatformListing.platform_account_id,
    PlatformListing.is_published,
    PlatformListing.sync_status,
    postgresql_include=['product_id', 'listed_price', 'last_synced_at']
)

# 3. 동기화 최적화
listing_sync_optimization_idx = Index(
    'idx_listing_sync_optimization',
    PlatformListing.sync_status,
    PlatformListing.last_synced_at,
    postgresql_where=PlatformListing.is_active == True,
    postgresql_include=['product_id', 'platform_account_id']
)

# 4. 성과 분석
listing_performance_idx = Index(
    'idx_listing_performance',
    PlatformListing.views,
    PlatformListing.clicks,
    PlatformListing.orders,
    postgresql_include=['product_id', 'platform_account_id', 'conversion_rate']
)


# ======================
# 가격 히스토리(ProductPriceHistory) 관련 인덱스
# ======================

# 1. 상품별 가격 히스토리
price_history_product_idx = Index(
    'idx_price_history_product',
    ProductPriceHistory.product_id,
    ProductPriceHistory.created_at.desc(),
    postgresql_include=['sale_price', 'cost_price', 'changed_by']
)

# 2. 시장 가격 분석
price_history_market_idx = Index(
    'idx_price_history_market',
    ProductPriceHistory.market_average,
    ProductPriceHistory.created_at,
    postgresql_where=ProductPriceHistory.market_average.is_not(None),
    postgresql_include=['product_id', 'sale_price']
)


# ======================
# 사용자(User) 관련 인덱스
# ======================

# 1. 이메일 로그인 최적화
user_email_idx = Index(
    'idx_user_email_unique',
    User.email,
    unique=True,
    postgresql_include=['id', 'is_active', 'last_login_at']
)

# 2. 사용자 활동 추적
user_activity_idx = Index(
    'idx_user_activity',
    User.is_active,
    User.last_login_at.desc(),
    postgresql_include=['email', 'created_at']
)


# ======================
# 플랫폼 계정(PlatformAccount) 관련 인덱스
# ======================

# 1. 플랫폼 타입별 계정
platform_account_type_idx = Index(
    'idx_platform_account_type',
    PlatformAccount.platform_type,
    PlatformAccount.is_active,
    postgresql_include=['account_name', 'api_credentials']
)

# 2. 사용자별 플랫폼 계정
platform_account_user_idx = Index(
    'idx_platform_account_user',
    PlatformAccount.user_id,
    PlatformAccount.is_active,
    postgresql_include=['platform_type', 'account_name']
)


# ======================
# 복합 비즈니스 로직 인덱스
# ======================

# 1. 주문 처리 파이프라인 최적화
order_processing_pipeline_idx = Index(
    'idx_order_processing_pipeline',
    Order.status,
    Order.platform_type,
    Order.created_at,
    postgresql_where=Order.status.in_(['pending', 'processing']),
    postgresql_include=['id', 'customer_name', 'total_amount']
)

# 2. 재고 동기화 최적화
inventory_sync_idx = Index(
    'idx_inventory_sync',
    Product.wholesaler_id,
    Product.stock_quantity,
    Product.last_synced_at,
    postgresql_where=text('is_dropshipping = true AND status = \'active\''),
    postgresql_include=['wholesaler_product_id', 'sku']
)

# 3. 수익성 분석 최적화
profitability_analysis_idx = Index(
    'idx_profitability_analysis',
    Product.cost_price,
    Product.retail_price,
    Product.status,
    postgresql_where=text('cost_price IS NOT NULL AND retail_price IS NOT NULL'),
    postgresql_include=['sku', 'name', 'brand', 'category_path']
)

# 4. 드롭쉬핑 관리 최적화
dropshipping_management_idx = Index(
    'idx_dropshipping_management',
    Product.is_dropshipping,
    Product.wholesaler_id,
    Product.status,
    Product.stock_quantity,
    postgresql_where=Product.is_dropshipping == True,
    postgresql_include=['sku', 'wholesaler_product_id', 'selling_price']
)


# ======================
# 인덱스 생성 함수
# ======================

def create_performance_indexes(engine):
    """모든 성능 인덱스 생성"""
    
    indexes_to_create = [
        # Order indexes
        order_status_created_idx,
        order_platform_created_idx,
        order_customer_idx,
        order_number_idx,
        order_tracking_idx,
        order_date_aggregation_idx,
        
        # OrderItem indexes
        order_item_order_product_idx,
        order_item_product_stats_idx,
        
        # Product indexes
        product_search_idx,
        product_status_created_idx,
        product_stock_management_idx,
        product_price_range_idx,
        product_brand_category_idx,
        product_platform_account_idx,
        product_wholesaler_idx,
        product_low_stock_idx,
        product_ai_optimized_idx,
        
        # ProductVariant indexes
        variant_product_idx,
        variant_sku_idx,
        
        # PlatformListing indexes
        listing_product_platform_idx,
        listing_platform_status_idx,
        listing_sync_optimization_idx,
        listing_performance_idx,
        
        # ProductPriceHistory indexes
        price_history_product_idx,
        price_history_market_idx,
        
        # User indexes
        user_email_idx,
        user_activity_idx,
        
        # PlatformAccount indexes
        platform_account_type_idx,
        platform_account_user_idx,
        
        # Business logic indexes
        order_processing_pipeline_idx,
        inventory_sync_idx,
        profitability_analysis_idx,
        dropshipping_management_idx,
    ]
    
    created_count = 0
    errors = []
    
    with engine.connect() as conn:
        for index in indexes_to_create:
            try:
                # PostgreSQL 전용 인덱스는 PostgreSQL에서만 생성
                if hasattr(index, 'postgresql_where') and 'postgresql' not in str(engine.url):
                    continue
                    
                create_stmt = CreateIndex(index, if_not_exists=True)
                conn.execute(create_stmt)
                created_count += 1
                print(f"Created index: {index.name}")
                
            except Exception as e:
                error_msg = f"Failed to create index {index.name}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)
    
    return {
        "created_count": created_count,
        "total_indexes": len(indexes_to_create),
        "errors": errors
    }


def get_index_usage_stats(engine):
    """인덱스 사용 통계 조회 (PostgreSQL 전용)"""
    
    if 'postgresql' not in str(engine.url):
        return {"message": "Index usage stats only available for PostgreSQL"}
    
    query = """
    SELECT 
        schemaname,
        tablename,
        indexname,
        idx_tup_read,
        idx_tup_fetch,
        idx_scan,
        idx_tup_read::float / GREATEST(idx_scan, 1) as avg_tuples_per_scan
    FROM pg_stat_user_indexes 
    WHERE schemaname = 'public'
    ORDER BY idx_scan DESC, idx_tup_read DESC;
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(row) for row in result]


def analyze_slow_queries(engine):
    """느린 쿼리 분석 (PostgreSQL 전용)"""
    
    if 'postgresql' not in str(engine.url):
        return {"message": "Slow query analysis only available for PostgreSQL"}
    
    # pg_stat_statements 확장이 필요
    query = """
    SELECT 
        query,
        calls,
        total_time,
        mean_time,
        rows,
        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
    FROM pg_stat_statements 
    WHERE query NOT LIKE '%pg_stat%'
    ORDER BY mean_time DESC 
    LIMIT 20;
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row) for row in result]
    except Exception as e:
        return {"error": f"pg_stat_statements extension may not be enabled: {str(e)}"}


def get_table_sizes(engine):
    """테이블 크기 분석"""
    
    if 'postgresql' in str(engine.url):
        query = """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
    else:
        # SQLite의 경우 다른 방법 사용
        query = """
        SELECT 
            name as tablename,
            'N/A' as size,
            0 as size_bytes
        FROM sqlite_master 
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%';
        """
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(row) for row in result]