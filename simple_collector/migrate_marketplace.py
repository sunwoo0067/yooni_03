"""
마켓플레이스 지원을 위한 데이터베이스 마이그레이션
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import engine, SessionLocal
from database.models import Base, init_suppliers, ApiCredential

def migrate_database():
    """데이터베이스 마이그레이션"""
    print("데이터베이스 마이그레이션 시작...")
    
    with engine.connect() as conn:
        # 트랜잭션 시작
        trans = conn.begin()
        
        try:
            # 1. products 테이블에 새 컬럼 추가
            columns_to_add = [
                ("product_id", "VARCHAR(200)"),
                ("product_name", "VARCHAR(500)"),
                ("price", "INTEGER"),
                ("original_price", "INTEGER"),
                ("stock", "INTEGER DEFAULT 0"),
                ("marketplace", "VARCHAR(50)"),
                ("category", "VARCHAR(500)"),
                ("brand", "VARCHAR(200)"),
                ("image_url", "TEXT"),
                ("product_url", "TEXT"),
                ("status", "VARCHAR(50)")
            ]
            
            # 기존 컬럼 확인 (PostgreSQL)
            if 'postgresql' in str(engine.url):
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'products'
                """))
                existing_columns = [row[0] for row in result]
            else:
                # SQLite용 처리
                result = conn.execute(text("PRAGMA table_info(products)"))
                existing_columns = [row[1] for row in result]
            
            for column_name, column_type in columns_to_add:
                if column_name not in existing_columns:
                    print(f"Adding column: {column_name}")
                    conn.execute(text(f"""
                        ALTER TABLE products 
                        ADD COLUMN {column_name} {column_type}
                    """))
            
            # 2. product_id에 인덱스 추가
            if "product_id" not in existing_columns:
                conn.execute(text("""
                    CREATE UNIQUE INDEX idx_product_id ON products(product_id)
                """))
            
            # 3. 새 테이블 생성 (api_credentials)
            if 'postgresql' in str(engine.url):
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'api_credentials'
                    )
                """))
            else:
                # SQLite용 처리
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='api_credentials'
                """))
                result = [True] if result.fetchone() else [False]
            
            table_exists = result.scalar() if 'postgresql' in str(engine.url) else bool(result[0])
            
            if not table_exists:
                print("Creating api_credentials table...")
                Base.metadata.tables['api_credentials'].create(engine, checkfirst=True)
            
            trans.commit()
            print("마이그레이션 완료!")
            
        except Exception as e:
            trans.rollback()
            print(f"마이그레이션 실패: {e}")
            raise
    
    # 4. 공급사 데이터 초기화
    db = SessionLocal()
    try:
        init_suppliers(db)
        print("공급사 데이터 초기화 완료!")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_database()