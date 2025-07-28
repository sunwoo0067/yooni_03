#!/usr/bin/env python3
"""
데이터베이스 구조 확인
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check_structure():
    """데이터베이스 구조 확인"""
    database_url = os.getenv('DATABASE_URL')
    
    # PostgreSQL URL 파싱
    db_parts = database_url.replace('postgresql://', '').split('@')
    user_pass = db_parts[0].split(':')
    host_db = db_parts[1].split('/')
    host_port = host_db[0].split(':')
    
    conn = await asyncpg.connect(
        user=user_pass[0],
        password=user_pass[1],
        database=host_db[1],
        host=host_port[0],
        port=int(host_port[1])
    )
    
    try:
        # users 테이블 구조 확인
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        print("Users 테이블 구조:")
        print("-" * 80)
        for col in columns:
            print(f"{col['column_name']:20} {col['data_type']:15} {col['is_nullable']:5} {col['column_default'] or ''}")
            
        # 기존 사용자 확인
        users = await conn.fetch("SELECT id, email, username FROM users")
        print(f"\n기존 사용자 수: {len(users)}")
        for user in users:
            print(f"  - {user['username']} ({user['email']})")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_structure())