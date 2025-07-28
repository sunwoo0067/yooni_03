#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 설정 및 마이그레이션
"""

import sys
from pathlib import Path
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from config.settings import settings
from database.connection import create_tables, engine
from database.models import init_suppliers, Product
from utils.logger import app_logger

def create_database():
    """PostgreSQL 데이터베이스 생성"""
    print("=== PostgreSQL 데이터베이스 생성 ===")
    
    # DATABASE_URL 파싱
    # postgresql://user:password@host:port/dbname
    url_parts = settings.DATABASE_URL.replace('postgresql://', '').split('@')
    user_pass = url_parts[0].split(':')
    host_port_db = url_parts[1].split('/')
    host_port = host_port_db[0].split(':')
    
    user = user_pass[0]
    password = user_pass[1]
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else '5432'
    dbname = host_port_db[1]
    
    try:
        # postgres 데이터베이스에 연결 (기본 데이터베이스)
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 데이터베이스 존재 확인
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (dbname,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            # 데이터베이스 생성
            cursor.execute(f'CREATE DATABASE {dbname}')
            print(f"[OK] 데이터베이스 '{dbname}' 생성 완료")
        else:
            print(f"[INFO] 데이터베이스 '{dbname}'가 이미 존재합니다")
            
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"[ERROR] PostgreSQL 연결 실패: {e}")
        print("\n다음을 확인하세요:")
        print("1. PostgreSQL이 실행 중인지 확인")
        print("2. docker-compose up -d postgres 실행")
        print("3. 연결 정보 확인:")
        print(f"   - Host: {host}")
        print(f"   - Port: {port}")
        print(f"   - User: {user}")
        print(f"   - Database: {dbname}")
        return False
        
    return True

def init_alembic():
    """Alembic 초기화"""
    print("\n=== Alembic 마이그레이션 초기화 ===")
    
    # alembic 디렉토리가 없으면 초기화
    alembic_dir = Path("alembic")
    if not alembic_dir.exists():
        try:
            subprocess.run(["alembic", "init", "alembic"], check=True)
            print("[OK] Alembic 초기화 완료")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Alembic 초기화 실패: {e}")
            return False
    else:
        print("[INFO] Alembic이 이미 초기화되어 있습니다")
        
    return True

def create_initial_migration():
    """초기 마이그레이션 생성"""
    print("\n=== 초기 마이그레이션 생성 ===")
    
    try:
        # 마이그레이션 생성
        subprocess.run([
            "alembic", "revision", "--autogenerate", 
            "-m", "Initial migration"
        ], check=True)
        print("[OK] 마이그레이션 파일 생성 완료")
        
        # 마이그레이션 적용
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        print("[OK] 마이그레이션 적용 완료")
        
    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Alembic 마이그레이션 실패: {e}")
        print("대신 SQLAlchemy로 테이블을 생성합니다...")
        
        # SQLAlchemy로 직접 테이블 생성
        create_tables()
        print("[OK] 테이블 생성 완료")
        
    return True

def migrate_from_sqlite():
    """SQLite에서 PostgreSQL로 데이터 마이그레이션"""
    print("\n=== SQLite 데이터 마이그레이션 ===")
    
    sqlite_db = Path("simple_collector.db")
    if not sqlite_db.exists():
        print("[INFO] SQLite 데이터베이스가 없습니다. 마이그레이션을 건너뜁니다.")
        return True
        
    try:
        # SQLite 연결
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        sqlite_engine = create_engine(f"sqlite:///{sqlite_db}")
        SqliteSession = sessionmaker(bind=sqlite_engine)
        sqlite_session = SqliteSession()
        
        # PostgreSQL 연결
        from database.connection import SessionLocal
        pg_session = SessionLocal()
        
        # 상품 데이터 마이그레이션
        print("상품 데이터 마이그레이션 중...")
        products = sqlite_session.query(Product).all()
        
        migrated_count = 0
        for product in products:
            # PostgreSQL에 이미 있는지 확인
            existing = pg_session.query(Product).filter(
                Product.product_code == product.product_code
            ).first()
            
            if not existing:
                new_product = Product(
                    product_code=product.product_code,
                    product_info=product.product_info,
                    supplier=product.supplier,
                    created_at=product.created_at,
                    updated_at=product.updated_at,
                    is_active=product.is_active
                )
                pg_session.add(new_product)
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    pg_session.commit()
                    print(f"  {migrated_count}개 마이그레이션 완료...")
                    
        pg_session.commit()
        print(f"[OK] 총 {migrated_count}개 상품 마이그레이션 완료")
        
        sqlite_session.close()
        pg_session.close()
        
    except Exception as e:
        print(f"[ERROR] 마이그레이션 실패: {e}")
        return False
        
    return True

def test_connection():
    """PostgreSQL 연결 테스트"""
    print("\n=== PostgreSQL 연결 테스트 ===")
    
    try:
        from database.connection import SessionLocal
        db = SessionLocal()
        
        # 간단한 쿼리 실행
        result = db.execute("SELECT version()").fetchone()
        print(f"[OK] PostgreSQL 버전: {result[0]}")
        
        # 테이블 목록 확인
        tables = db.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """).fetchall()
        
        print("\n설치된 테이블:")
        for table in tables:
            print(f"  - {table[0]}")
            
        # 상품 수 확인
        product_count = db.query(Product).count()
        print(f"\n총 상품 수: {product_count}개")
        
        db.close()
        
    except Exception as e:
        print(f"[ERROR] 연결 테스트 실패: {e}")
        return False
        
    return True

def main():
    """메인 함수"""
    print("PostgreSQL 데이터베이스 설정")
    print("=" * 50)
    
    # 1. 데이터베이스 생성
    if not create_database():
        return
        
    # 2. 테이블 생성
    print("\n=== 테이블 생성 ===")
    create_tables()
    print("[OK] 테이블 생성 완료")
    
    # 3. 기본 데이터 초기화
    print("\n=== 기본 데이터 초기화 ===")
    db = SessionLocal()
    init_suppliers(db)
    db.close()
    print("[OK] 공급사 데이터 초기화 완료")
    
    # 4. SQLite 데이터 마이그레이션
    migrate_from_sqlite()
    
    # 5. 연결 테스트
    test_connection()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] PostgreSQL 설정 완료!")
    print("\n다음 명령으로 서버를 시작하세요:")
    print("python main.py")

if __name__ == "__main__":
    # SessionLocal import 추가
    from database.connection import SessionLocal
    main()