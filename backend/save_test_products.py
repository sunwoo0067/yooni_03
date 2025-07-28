#!/usr/bin/env python3
"""
테스트 상품 데이터를 PostgreSQL에 저장
"""

import os
import sys
import asyncio
import json
from datetime import datetime
import asyncpg

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


async def save_test_products():
    """테스트 상품 데이터 저장"""
    
    # 데이터베이스 연결
    database_url = os.getenv('DATABASE_URL')
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
    
    print("데이터베이스 연결 성공")
    
    try:
        # 테이블이 존재하는지 확인
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'simple_collected_products'
            )
        """)
        
        if not table_exists:
            print("테이블이 없습니다. 생성합니다...")
            await conn.execute("""
                CREATE TABLE simple_collected_products (
                    id SERIAL PRIMARY KEY,
                    wholesaler_name VARCHAR(50) NOT NULL,
                    product_id VARCHAR(100) NOT NULL,
                    product_name VARCHAR(500) NOT NULL,
                    price INTEGER NOT NULL,
                    stock_quantity INTEGER DEFAULT 0,
                    category VARCHAR(200),
                    image_url VARCHAR(1000),
                    is_active BOOLEAN DEFAULT TRUE,
                    raw_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(wholesaler_name, product_id)
                )
            """)
            
            await conn.execute("""
                CREATE INDEX idx_simple_collected_products_wholesaler 
                ON simple_collected_products(wholesaler_name)
            """)
            print("테이블 생성 완료")
        
        # 테스트 데이터
        test_products = [
            # OwnerClan 상품
            {
                'wholesaler': 'OwnerClan',
                'products': [
                    {
                        'id': 'WFJ59ER',
                        'name': '925실버 로즈 장식 타원 후프귀걸이',
                        'price': 79860,
                        'stock': 50,
                        'category': '주얼리'
                    },
                    {
                        'id': 'WFJ59EQ',
                        'name': '925실버 매듭 디자인 미니 귀걸이',
                        'price': 21780,
                        'stock': 100,
                        'category': '주얼리'
                    },
                    {
                        'id': 'WFJ59EP',
                        'name': '925실버 미니 볼륨 하트 목걸이',
                        'price': 31460,
                        'stock': 75,
                        'category': '주얼리'
                    },
                    {
                        'id': 'WFJ59EO',
                        'name': '925실버 커팅 쉐입 미니 이어커프',
                        'price': 26620,
                        'stock': 30,
                        'category': '주얼리'
                    },
                    {
                        'id': 'WFJ59EN',
                        'name': '925실버 볼드 물방울 귀걸이',
                        'price': 48400,
                        'stock': 20,
                        'category': '주얼리'
                    }
                ]
            },
            # Zentrade 상품
            {
                'wholesaler': 'Zentrade',
                'products': [
                    {
                        'id': '5009',
                        'name': 'PP 미니 소분 스페출라 10P',
                        'price': 220,
                        'stock': 500,
                        'category': '주방용품'
                    },
                    {
                        'id': '5007',
                        'name': '옻칠 계란말이 뒤집개',
                        'price': 2330,
                        'stock': 200,
                        'category': '주방용품'
                    },
                    {
                        'id': '5006',
                        'name': '띄움 실리콘 주방집게',
                        'price': 3630,
                        'stock': 150,
                        'category': '주방용품'
                    },
                    {
                        'id': '5005',
                        'name': '네오 스푼 양념통 380ml',
                        'price': 1680,
                        'stock': 300,
                        'category': '주방용품'
                    },
                    {
                        'id': '5004',
                        'name': '컬러 파티컵 4P',
                        'price': 2350,
                        'stock': 250,
                        'category': '주방용품'
                    }
                ]
            }
        ]
        
        # 데이터 저장
        total_count = 0
        for wholesaler_data in test_products:
            wholesaler_name = wholesaler_data['wholesaler']
            print(f"\n[{wholesaler_name}] 상품 저장 시작...")
            
            for product in wholesaler_data['products']:
                try:
                    await conn.execute("""
                        INSERT INTO simple_collected_products 
                        (wholesaler_name, product_id, product_name, price, 
                         stock_quantity, category, is_active, raw_data)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (wholesaler_name, product_id) 
                        DO UPDATE SET 
                            product_name = EXCLUDED.product_name,
                            price = EXCLUDED.price,
                            stock_quantity = EXCLUDED.stock_quantity,
                            category = EXCLUDED.category,
                            is_active = EXCLUDED.is_active,
                            updated_at = CURRENT_TIMESTAMP
                    """,
                    wholesaler_name,
                    product['id'],
                    product['name'],
                    product['price'],
                    product['stock'],
                    product['category'],
                    True,
                    json.dumps(product)
                    )
                    total_count += 1
                    print(f"  ✓ {product['name']}")
                except Exception as e:
                    print(f"  ✗ 오류: {e}")
        
        # 결과 확인
        print("\n" + "="*60)
        print("저장 완료!")
        print(f"총 {total_count}개 상품 저장")
        
        # 데이터베이스 통계
        db_total = await conn.fetchval(
            "SELECT COUNT(*) FROM simple_collected_products"
        )
        print(f"\n데이터베이스 총 상품 수: {db_total}개")
        
        # 도매처별 통계
        stats = await conn.fetch(
            """
            SELECT wholesaler_name, COUNT(*) as count
            FROM simple_collected_products
            GROUP BY wholesaler_name
            ORDER BY wholesaler_name
            """
        )
        
        print("\n도매처별 상품 수:")
        for stat in stats:
            print(f"  {stat['wholesaler_name']}: {stat['count']}개")
        
        # 샘플 데이터 확인
        samples = await conn.fetch(
            """
            SELECT wholesaler_name, product_name, price, stock_quantity, category
            FROM simple_collected_products
            ORDER BY wholesaler_name, product_id
            """
        )
        
        print("\n저장된 상품 목록:")
        for sample in samples:
            print(f"  [{sample['wholesaler_name']}] {sample['product_name']}")
            print(f"    카테고리: {sample['category']}, 가격: {sample['price']:,}원, 재고: {sample['stock_quantity']}개")
        
        print(f"\n완료 시간: {datetime.now()}")
        print("\nPostgreSQL 데이터베이스에 테스트 상품이 성공적으로 저장되었습니다!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(save_test_products())