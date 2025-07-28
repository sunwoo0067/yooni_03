#!/usr/bin/env python3
"""
도매처 계정을 데이터베이스에 등록
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


def generate_uuid():
    """간단한 UUID 생성"""
    import uuid
    return str(uuid.uuid4())


def create_wholesaler_accounts():
    """도매처 계정 생성"""
    
    # SQLite 데이터베이스 연결
    db_path = Path("yooni_dropshipping.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # wholesaler_accounts 테이블 생성 (없는 경우)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wholesaler_accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                wholesaler_type TEXT NOT NULL,
                account_name TEXT NOT NULL,
                api_credentials TEXT NOT NULL,
                connection_status TEXT DEFAULT 'disconnected',
                last_connected_at TEXT,
                last_error_message TEXT,
                is_active INTEGER DEFAULT 1,
                auto_collect_enabled INTEGER DEFAULT 0,
                collect_interval_hours INTEGER DEFAULT 24,
                collect_categories TEXT,
                collect_recent_days INTEGER DEFAULT 7,
                max_products_per_collection INTEGER DEFAULT 1000,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 기존 계정 확인
        cursor.execute("SELECT COUNT(*) FROM wholesaler_accounts")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"이미 {count}개의 도매처 계정이 있습니다.")
            cursor.execute("SELECT wholesaler_type, account_name, connection_status FROM wholesaler_accounts")
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} ({row[2]})")
            
            response = input("\n기존 계정을 삭제하고 새로 만들까요? (y/n): ")
            if response.lower() == 'y':
                cursor.execute("DELETE FROM wholesaler_accounts")
                print("기존 계정 삭제 완료")
            else:
                return
        
        # 도매처 계정 정보
        now = datetime.now().isoformat()
        
        accounts = [
            {
                'id': generate_uuid(),
                'user_id': generate_uuid(),  # 실제로는 로그인한 사용자 ID
                'wholesaler_type': 'ownerclan',
                'account_name': '오너클랜 메인 계정',
                'api_credentials': json.dumps({
                    'username': os.getenv('OWNERCLAN_USERNAME'),
                    'password': os.getenv('OWNERCLAN_PASSWORD'),
                    'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
                    'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
                }),
                'connection_status': 'disconnected',
                'is_active': 1,
                'created_at': now,
                'updated_at': now
            },
            {
                'id': generate_uuid(),
                'user_id': generate_uuid(),
                'wholesaler_type': 'domeggook',
                'account_name': '도매꾹 메인 계정',
                'api_credentials': json.dumps({
                    'api_key': os.getenv('DOMEGGOOK_API_KEY'),
                    'api_url': 'https://openapi.domeggook.com'
                }),
                'connection_status': 'disconnected',
                'is_active': 1,
                'created_at': now,
                'updated_at': now
            },
            {
                'id': generate_uuid(),
                'user_id': generate_uuid(),
                'wholesaler_type': 'zentrade',
                'account_name': '젠트레이드 메인 계정',
                'api_credentials': json.dumps({
                    'api_key': os.getenv('ZENTRADE_API_KEY'),
                    'api_secret': os.getenv('ZENTRADE_API_SECRET'),
                    'api_url': 'https://api.zentrade.co.kr'
                }),
                'connection_status': 'disconnected',
                'is_active': 1,
                'created_at': now,
                'updated_at': now
            }
        ]
        
        # 계정 삽입
        for account in accounts:
            cursor.execute("""
                INSERT INTO wholesaler_accounts (
                    id, user_id, wholesaler_type, account_name,
                    api_credentials, connection_status, is_active,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account['id'], account['user_id'], account['wholesaler_type'],
                account['account_name'], account['api_credentials'],
                account['connection_status'], account['is_active'],
                account['created_at'], account['updated_at']
            ))
            
            print(f"[OK] {account['account_name']} 생성 완료")
        
        conn.commit()
        print(f"\n총 {len(accounts)}개의 도매처 계정 생성 완료!")
        
        # 생성된 계정 확인
        cursor.execute("SELECT id, wholesaler_type, account_name FROM wholesaler_accounts")
        print("\n생성된 계정:")
        for row in cursor.fetchall():
            print(f"  - ID: {row[0][:8]}...")
            print(f"    유형: {row[1]}")
            print(f"    이름: {row[2]}")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        conn.rollback()
        
    finally:
        conn.close()


def main():
    """메인 실행"""
    print("=" * 60)
    print("도매처 계정 등록")
    print("=" * 60)
    
    # 환경 변수 확인
    print("\n환경 변수 확인:")
    env_vars = [
        'OWNERCLAN_USERNAME',
        'OWNERCLAN_PASSWORD',
        'DOMEGGOOK_API_KEY',
        'ZENTRADE_API_KEY',
        'ZENTRADE_API_SECRET'
    ]
    
    all_set = True
    for var in env_vars:
        value = os.getenv(var)
        if value and not value.startswith('your-'):
            print(f"[OK] {var}: 설정됨")
        else:
            print(f"[NO] {var}: 미설정")
            all_set = False
    
    if not all_set:
        print("\n일부 환경 변수가 설정되지 않았습니다.")
        response = input("계속하시겠습니까? (y/n): ")
        if response.lower() != 'y':
            return
    
    # 계정 생성
    create_wholesaler_accounts()


if __name__ == "__main__":
    main()