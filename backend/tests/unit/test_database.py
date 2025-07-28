"""
데이터베이스 연결 및 기본 동작 유닛 테스트
"""

import pytest
from sqlalchemy import text
from app.services.database.database import DatabaseManager, get_db
from app.core.config import get_settings


class TestDatabase:
    """데이터베이스 연결 테스트"""
    
    def test_database_connection(self):
        """데이터베이스 연결 테스트"""
        db_manager = DatabaseManager()
        
        # 연결 테스트
        assert db_manager.check_connection() == True, "데이터베이스 연결 실패"
        
        print("✅ 데이터베이스 연결 성공")
    
    def test_database_query(self):
        """기본 쿼리 실행 테스트"""
        db = next(get_db())
        
        try:
            # 간단한 쿼리 실행
            result = db.execute(text("SELECT 1 as test")).fetchone()
            assert result.test == 1, "쿼리 결과가 예상과 다름"
            
            # PostgreSQL 버전 확인
            version_result = db.execute(text("SELECT version()")).fetchone()
            print(f"✅ PostgreSQL 버전: {version_result[0]}")
            
        finally:
            db.close()
    
    def test_table_existence(self):
        """테이블 존재 여부 확인"""
        db = next(get_db())
        
        expected_tables = [
            'users', 'platform_accounts', 'products', 'orders',
            'inventory_items', 'wholesaler_accounts', 'ai_logs'
        ]
        
        try:
            # 테이블 목록 조회
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            
            existing_tables = [row[0] for row in result]
            
            # 각 테이블 확인
            for table in expected_tables:
                assert table in existing_tables, f"테이블 '{table}'이 존재하지 않습니다"
                print(f"✅ 테이블 '{table}' 확인됨")
            
            print(f"\n총 {len(existing_tables)}개의 테이블이 존재합니다.")
            
        finally:
            db.close()


if __name__ == "__main__":
    # 직접 실행
    test = TestDatabase()
    print("=== 데이터베이스 테스트 시작 ===\n")
    
    test.test_database_connection()
    test.test_database_query()
    test.test_table_existence()
    
    print("\n=== 데이터베이스 테스트 완료 ===")