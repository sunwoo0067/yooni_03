"""
기본 연결 테스트 - 간단한 데이터베이스 연결 테스트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

def test_direct_database_connection():
    """직접 데이터베이스 연결 테스트"""
    print("=== 직접 데이터베이스 연결 테스트 ===\n")
    
    # 데이터베이스 URL
    database_url = "postgresql://postgres:1234@localhost:5433/yoni_03"
    
    try:
        # 엔진 생성
        engine = create_engine(database_url)
        
        # 연결 테스트
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                print("[OK] 데이터베이스 연결 성공!")
                
                # PostgreSQL 버전 확인
                version_result = conn.execute(text("SELECT version()"))
                version = version_result.fetchone()[0]
                print(f"[OK] PostgreSQL 버전: {version}")
                
                # 테이블 목록 확인
                tables_result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                
                tables = [row[0] for row in tables_result]
                print(f"\n[OK] 발견된 테이블 수: {len(tables)}")
                
                if tables:
                    print("\n테이블 목록:")
                    for i, table in enumerate(tables, 1):
                        print(f"  {i}. {table}")
                
                return True
            else:
                print("[FAIL] 데이터베이스 연결 실패")
                return False
                
    except Exception as e:
        print(f"[FAIL] 오류 발생: {type(e).__name__}: {str(e)}")
        return False


def test_application_modules():
    """애플리케이션 모듈 import 테스트"""
    print("\n\n=== 애플리케이션 모듈 테스트 ===\n")
    
    modules_to_test = [
        ("app.core.config", "설정 모듈"),
        ("app.services.database.database", "데이터베이스 서비스"),
        ("app.models.base", "기본 모델"),
        ("app.models.user", "사용자 모델"),
        ("app.models.product", "상품 모델"),
        ("app.models.order", "주문 모델"),
    ]
    
    success_count = 0
    
    for module_name, description in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[''])
            print(f"[OK] {description} ({module_name}) - 성공")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] {description} ({module_name}) - 실패: {str(e)}")
    
    print(f"\n총 {len(modules_to_test)}개 중 {success_count}개 모듈 로드 성공")
    
    return success_count == len(modules_to_test)


def test_database_manager():
    """DatabaseManager 테스트"""
    print("\n\n=== DatabaseManager 테스트 ===\n")
    
    try:
        from app.services.database.database import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # 연결 테스트
        if db_manager.check_connection():
            print("[OK] DatabaseManager 연결 성공")
            
            # 세션 테스트
            session = db_manager.get_session()
            result = session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"[OK] 현재 데이터베이스: {db_name}")
            session.close()
            
            return True
        else:
            print("[FAIL] DatabaseManager 연결 실패")
            return False
            
    except Exception as e:
        print(f"[FAIL] DatabaseManager 테스트 실패: {str(e)}")
        return False


if __name__ == "__main__":
    print("[ROCKET] Yooni 드랍쉬핑 시스템 - 기본 연결 테스트\n")
    
    # 테스트 실행
    test_results = []
    
    # 1. 직접 연결 테스트
    test_results.append(("직접 데이터베이스 연결", test_direct_database_connection()))
    
    # 2. 모듈 import 테스트
    test_results.append(("애플리케이션 모듈", test_application_modules()))
    
    # 3. DatabaseManager 테스트
    test_results.append(("DatabaseManager", test_database_manager()))
    
    # 결과 요약
    print("\n\n" + "="*50)
    print("테스트 결과 요약")
    print("="*50)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, result in test_results if result)
    
    for test_name, result in test_results:
        status = "[OK] 성공" if result else "[FAIL] 실패"
        print(f"{test_name}: {status}")
    
    print(f"\n총 {total_tests}개 테스트 중 {passed_tests}개 성공")
    
    if passed_tests == total_tests:
        print("\n[SUCCESS] 모든 테스트가 성공했습니다!")
    else:
        print(f"\n[WARNING] {total_tests - passed_tests}개의 테스트가 실패했습니다.")