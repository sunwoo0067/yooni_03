#!/usr/bin/env python3
"""
데이터베이스에서 도매처 계정 정보 확인
"""

import sqlite3
import json
from pathlib import Path


def check_wholesaler_accounts():
    """도매처 계정 정보 확인"""
    
    # SQLite 데이터베이스 경로
    db_path = Path("yooni_dropshipping.db")
    
    if not db_path.exists():
        print(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 테이블 확인
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='wholesaler_accounts'
        """)
        
        if not cursor.fetchone():
            print("wholesaler_accounts 테이블이 없습니다.")
            
            # 모든 테이블 목록 출력
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print("\n사용 가능한 테이블:")
            for table in tables:
                print(f"  - {table[0]}")
            return
        
        # 도매처 계정 조회
        cursor.execute("""
            SELECT id, wholesaler_type, account_name, 
                   connection_status, is_active, 
                   created_at, updated_at
            FROM wholesaler_accounts
        """)
        
        accounts = cursor.fetchall()
        
        if accounts:
            print(f"\n총 {len(accounts)}개의 도매처 계정이 있습니다:")
            print("-" * 60)
            
            for account in accounts:
                print(f"ID: {account[0]}")
                print(f"유형: {account[1]}")
                print(f"계정명: {account[2]}")
                print(f"연결 상태: {account[3]}")
                print(f"활성화: {account[4]}")
                print(f"생성일: {account[5]}")
                print(f"수정일: {account[6]}")
                print("-" * 60)
        else:
            print("\n등록된 도매처 계정이 없습니다.")
            
            # 샘플 데이터 추가 옵션
            print("\n샘플 도매처 계정을 추가하시겠습니까? (y/n)")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        
    finally:
        conn.close()


def check_collected_products():
    """수집된 상품 확인"""
    
    db_path = Path("yooni_dropshipping.db")
    
    if not db_path.exists():
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # collected_products 테이블 확인
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%collect%'
        """)
        
        tables = cursor.fetchall()
        if tables:
            print("\n수집 관련 테이블:")
            for table in tables:
                print(f"  - {table[0]}")
                
                # 각 테이블의 레코드 수 확인
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"    레코드 수: {count}")
                
    except Exception as e:
        print(f"오류: {e}")
        
    finally:
        conn.close()


def main():
    """메인 실행"""
    print("=" * 60)
    print("도매처 계정 정보 확인")
    print("=" * 60)
    
    check_wholesaler_accounts()
    check_collected_products()
    
    print("\n[참고]")
    print("1. 도매처 계정은 웹 인터페이스나 API를 통해 등록해야 합니다.")
    print("2. API 인증 정보는 암호화되어 저장됩니다.")
    print("3. 실제 API 키는 각 도매처에서 발급받아야 합니다.")


if __name__ == "__main__":
    main()