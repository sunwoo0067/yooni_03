#!/usr/bin/env python3
"""
데이터베이스 초기화 및 테이블 생성
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# .env 파일 로드
load_dotenv()

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')


def init_database():
    """데이터베이스 초기화 및 테이블 생성"""
    database_url = os.getenv('DATABASE_URL')
    print(f"데이터베이스 연결: {database_url}")
    
    # SQLAlchemy 엔진 생성
    engine = create_engine(database_url)
    
    # 테이블 생성 SQL
    create_tables_sql = """
    -- 사용자 테이블
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) UNIQUE NOT NULL,
        username VARCHAR(100) UNIQUE NOT NULL,
        full_name VARCHAR(255),
        hashed_password VARCHAR(255) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        is_superuser BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 도매처 계정 테이블
    CREATE TABLE IF NOT EXISTS wholesaler_accounts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id),
        wholesaler_type VARCHAR(50) NOT NULL,
        account_name VARCHAR(100) NOT NULL,
        api_credentials TEXT NOT NULL,
        connection_status VARCHAR(50) DEFAULT 'disconnected',
        last_connected_at TIMESTAMP,
        last_error_message TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        auto_collect_enabled BOOLEAN DEFAULT FALSE,
        collect_interval_hours INTEGER DEFAULT 24,
        collect_categories JSONB,
        collect_recent_days INTEGER DEFAULT 7,
        max_products_per_collection INTEGER DEFAULT 1000,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 도매처 상품 테이블
    CREATE TABLE IF NOT EXISTS wholesaler_products (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        wholesaler_account_id UUID REFERENCES wholesaler_accounts(id),
        wholesaler_product_id VARCHAR(100) NOT NULL,
        wholesaler_sku VARCHAR(100),
        name VARCHAR(500) NOT NULL,
        description TEXT,
        category_path VARCHAR(500),
        wholesale_price INTEGER NOT NULL,
        retail_price INTEGER,
        discount_rate INTEGER,
        stock_quantity INTEGER DEFAULT 0,
        is_in_stock BOOLEAN DEFAULT TRUE,
        main_image_url VARCHAR(1000),
        additional_images JSONB,
        options JSONB,
        variants JSONB,
        shipping_info JSONB,
        raw_data JSONB,
        is_active BOOLEAN DEFAULT TRUE,
        is_collected BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(wholesaler_account_id, wholesaler_product_id)
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_wholesaler_products_account_id ON wholesaler_products(wholesaler_account_id);
    CREATE INDEX IF NOT EXISTS idx_wholesaler_products_product_id ON wholesaler_products(wholesaler_product_id);
    CREATE INDEX IF NOT EXISTS idx_wholesaler_products_active ON wholesaler_products(is_active);
    """
    
    try:
        with engine.connect() as conn:
            # 테이블 생성
            conn.execute(text(create_tables_sql))
            conn.commit()
            print("테이블 생성 완료!")
            
            # 테이블 확인
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'wholesaler_accounts', 'wholesaler_products')
                ORDER BY table_name;
            """))
            
            print("\n생성된 테이블:")
            for row in result:
                print(f"  - {row[0]}")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    init_database()