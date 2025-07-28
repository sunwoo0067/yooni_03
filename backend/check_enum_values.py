#!/usr/bin/env python3
"""
열거형 타입 값 확인
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check_enums():
    """열거형 타입 확인"""
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
        # 열거형 타입 확인
        enums = await conn.fetch("""
            SELECT n.nspname as schema_name,
                   t.typname as type_name,
                   e.enumlabel as enum_value
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid  
            JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            WHERE t.typname IN ('userrole', 'userstatus', 'wholesalertype')
            ORDER BY t.typname, e.enumsortorder
        """)
        
        print("열거형 타입 값:")
        print("-" * 50)
        current_type = None
        for enum in enums:
            if current_type != enum['type_name']:
                current_type = enum['type_name']
                print(f"\n{current_type}:")
            print(f"  - {enum['enum_value']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_enums())