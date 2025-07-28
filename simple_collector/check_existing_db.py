#!/usr/bin/env python3
"""
기존 yoni_03 데이터베이스 상태 확인
"""

import sys
from pathlib import Path
import psycopg2
from sqlalchemy import create_engine, inspect

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from config.settings import settings
from database.connection import engine, SessionLocal
from database.models import Product, Supplier, CollectionLog

def check_database_connection():
    """데이터베이스 연결 확인"""
    print("=== PostgreSQL 연결 테스트 ===")
    print(f"연결 정보: {settings.DATABASE_URL}")
    
    try:
        # psycopg2로 직접 연결 테스트
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            user="postgres",
            password="1234",
            database="yoni_03"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"[OK] PostgreSQL 버전: {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] 연결 실패: {e}")
        return False

def check_existing_tables():
    """기존 테이블 확인"""
    print("\n=== 기존 테이블 확인 ===")
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"총 {len(tables)}개 테이블 발견:")
        for table in sorted(tables):
            print(f"  - {table}")
            
        # simple_collector 테이블 확인
        simple_tables = ['products', 'suppliers', 'collection_logs', 'excel_uploads']
        existing_simple_tables = [t for t in simple_tables if t in tables]
        
        if existing_simple_tables:
            print(f"\nSimple Collector 테이블 발견: {existing_simple_tables}")
        else:
            print("\nSimple Collector 테이블이 없습니다. 생성이 필요합니다.")
            
        return tables
    except Exception as e:
        print(f"[ERROR] 테이블 확인 실패: {e}")
        return []

def check_products_table():
    """products 테이블 상세 확인"""
    print("\n=== Products 테이블 확인 ===")
    
    try:
        db = SessionLocal()
        
        # 테이블 존재 여부
        inspector = inspect(engine)
        if 'products' in inspector.get_table_names():
            # 컬럼 정보
            columns = inspector.get_columns('products')
            print("컬럼 정보:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
            
            # 데이터 수
            count = db.query(Product).count()
            print(f"\n총 상품 수: {count}개")
            
            # 공급사별 상품 수
            if count > 0:
                suppliers = ['zentrade', 'ownerclan', 'domeggook']
                for supplier in suppliers:
                    supplier_count = db.query(Product).filter(
                        Product.supplier == supplier
                    ).count()
                    print(f"  - {supplier}: {supplier_count}개")
        else:
            print("products 테이블이 없습니다.")
            
        db.close()
    except Exception as e:
        print(f"[ERROR] products 테이블 확인 실패: {e}")

def create_simple_tables():
    """Simple Collector 테이블 생성"""
    print("\n=== Simple Collector 테이블 생성 ===")
    
    try:
        from database.connection import create_tables
        create_tables()
        print("[OK] 테이블 생성 완료")
        
        # 기본 공급사 데이터 초기화
        db = SessionLocal()
        from database.models import init_suppliers
        init_suppliers(db)
        db.close()
        print("[OK] 공급사 데이터 초기화 완료")
        
    except Exception as e:
        print(f"[ERROR] 테이블 생성 실패: {e}")

def migrate_sqlite_data():
    """SQLite 데이터 마이그레이션"""
    print("\n=== SQLite 데이터 마이그레이션 ===")
    
    sqlite_file = Path("simple_collector.db")
    if not sqlite_file.exists():
        print("SQLite 파일이 없습니다. 마이그레이션을 건너뜁니다.")
        return
        
    try:
        # SQLite 연결
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        sqlite_engine = create_engine(f"sqlite:///{sqlite_file}")
        SqliteSession = sessionmaker(bind=sqlite_engine)
        sqlite_session = SqliteSession()
        
        # PostgreSQL 연결
        pg_session = SessionLocal()
        
        # 상품 데이터 마이그레이션
        print("상품 데이터 마이그레이션 중...")
        
        # SQLite에서 Product 모델로 데이터 읽기
        sqlite_products = sqlite_session.execute(
            "SELECT product_code, product_info, supplier, created_at, updated_at, is_active FROM products"
        ).fetchall()
        
        migrated = 0
        for row in sqlite_products:
            # PostgreSQL에 이미 있는지 확인
            exists = pg_session.query(Product).filter(
                Product.product_code == row[0]
            ).first()
            
            if not exists:
                product = Product(
                    product_code=row[0],
                    product_info=row[1],
                    supplier=row[2],
                    created_at=row[3],
                    updated_at=row[4],
                    is_active=row[5] if row[5] is not None else True
                )
                pg_session.add(product)
                migrated += 1
                
                if migrated % 10 == 0:
                    pg_session.commit()
                    print(f"  {migrated}개 마이그레이션 완료...")
                    
        pg_session.commit()
        print(f"[OK] 총 {migrated}개 상품 마이그레이션 완료")
        
        sqlite_session.close()
        pg_session.close()
        
    except Exception as e:
        print(f"[ERROR] 마이그레이션 실패: {e}")

def main():
    """메인 함수"""
    print("기존 yoni_03 데이터베이스 통합")
    print("=" * 50)
    
    # 1. 연결 테스트
    if not check_database_connection():
        print("\nPostgreSQL이 실행 중인지 확인하세요:")
        print("- 포트: 5433")
        print("- 비밀번호: 1234")
        return
    
    # 2. 기존 테이블 확인
    tables = check_existing_tables()
    
    # 3. products 테이블 확인
    check_products_table()
    
    # 4. Simple Collector 테이블이 없으면 생성
    if 'products' not in tables:
        response = input("\nSimple Collector 테이블을 생성하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            create_simple_tables()
            
            # SQLite 데이터 마이그레이션
            response = input("\nSQLite 데이터를 마이그레이션하시겠습니까? (y/n): ")
            if response.lower() == 'y':
                migrate_sqlite_data()
    else:
        print("\n기존 테이블을 그대로 사용합니다.")
        
        # SQLite 데이터만 마이그레이션
        sqlite_file = Path("simple_collector.db")
        if sqlite_file.exists():
            response = input("\nSQLite 데이터를 추가로 마이그레이션하시겠습니까? (y/n): ")
            if response.lower() == 'y':
                migrate_sqlite_data()
    
    print("\n" + "=" * 50)
    print("[완료] yoni_03 데이터베이스 통합 준비 완료!")
    print("\n다음 명령으로 서버를 시작하세요:")
    print("python main.py")

if __name__ == "__main__":
    main()