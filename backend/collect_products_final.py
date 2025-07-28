#!/usr/bin/env python3
"""
도매처 상품 수집 및 PostgreSQL 저장 (최종 버전)
"""

import os
import sys
import asyncio
import json
import aiohttp
import requests
from datetime import datetime
import asyncpg
from xml.etree import ElementTree as ET

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class FinalProductCollector:
    """최종 상품 수집기"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.conn = None
        
    async def connect_db(self):
        """데이터베이스 연결"""
        # PostgreSQL URL 파싱
        db_parts = self.database_url.replace('postgresql://', '').split('@')
        user_pass = db_parts[0].split(':')
        host_db = db_parts[1].split('/')
        host_port = host_db[0].split(':')
        
        self.conn = await asyncpg.connect(
            user=user_pass[0],
            password=user_pass[1],
            database=host_db[1],
            host=host_port[0],
            port=int(host_port[1])
        )
        print("데이터베이스 연결 성공")
        
    async def close_db(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            await self.conn.close()
            
    async def setup_tables(self):
        """간단한 테이블 생성"""
        # 간단한 수집용 테이블 생성
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS simple_collected_products (
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
        
        # 인덱스 생성
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_simple_collected_products_wholesaler 
            ON simple_collected_products(wholesaler_name)
        """)
        
        print("테이블 설정 완료")
        
    async def collect_ownerclan_products(self):
        """OwnerClan 상품 수집"""
        print("\n[OwnerClan] 상품 수집 시작...")
        
        try:
            # GraphQL 로그인
            login_url = "https://ownerclan.com/api/v1/graphql"
            login_query = """
            mutation Login($username: String!, $password: String!) {
                login(username: $username, password: $password) {
                    token
                }
            }
            """
            
            async with aiohttp.ClientSession() as session:
                # 로그인
                async with session.post(
                    login_url,
                    json={
                        "query": login_query,
                        "variables": {
                            "username": os.getenv('OWNERCLAN_USERNAME'),
                            "password": os.getenv('OWNERCLAN_PASSWORD')
                        }
                    }
                ) as response:
                    # Plain text token 처리
                    token_text = await response.text()
                    token = token_text.strip()
                    
                    if not token.startswith('eyJ'):
                        print("로그인 실패")
                        return 0
                        
                    print("로그인 성공")
                
                # 상품 조회
                headers = {"Authorization": f"Bearer {token}"}
                products_query = """
                query {
                    searchProduct(
                        searchType: SUPPLIER
                        filter: { displayYn: Y }
                        pageable: { page: 1, size: 20 }
                    ) {
                        totalElements
                        content {
                            productId
                            name
                            salePrice
                            stockCnt
                            images { url }
                            category { name }
                            status
                        }
                    }
                }
                """
                
                async with session.post(
                    login_url,
                    headers=headers,
                    json={"query": products_query}
                ) as response:
                    result = await response.json()
                    
                    if 'data' in result and result['data']['searchProduct']:
                        products = result['data']['searchProduct']['content']
                        count = 0
                        
                        for product in products:
                            try:
                                await self.conn.execute("""
                                    INSERT INTO collected_products 
                                    (wholesaler_name, product_id, product_name, price, 
                                     stock_quantity, category, image_url, is_active, raw_data)
                                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                                    ON CONFLICT (wholesaler_name, product_id) 
                                    DO UPDATE SET 
                                        product_name = EXCLUDED.product_name,
                                        price = EXCLUDED.price,
                                        stock_quantity = EXCLUDED.stock_quantity,
                                        is_active = EXCLUDED.is_active,
                                        updated_at = CURRENT_TIMESTAMP
                                """,
                                'OwnerClan',
                                product['productId'],
                                product['name'],
                                int(product['salePrice']),
                                product.get('stockCnt', 0),
                                product['category']['name'] if product.get('category') else None,
                                product['images'][0]['url'] if product.get('images') else None,
                                product.get('status') == 'ACTIVE',
                                json.dumps(product)
                                )
                                count += 1
                                print(f"저장: {product['name']}")
                            except Exception as e:
                                print(f"상품 저장 오류: {e}")
                                continue
                        
                        print(f"[OwnerClan] {count}개 상품 처리 완료")
                        return count
                    else:
                        print("상품 조회 실패")
                        return 0
                        
        except Exception as e:
            print(f"[OwnerClan] 오류: {e}")
            return 0
            
    async def collect_zentrade_products(self):
        """Zentrade 상품 수집"""
        print("\n[Zentrade] 상품 수집 시작...")
        
        try:
            # API 호출
            url = "http://zentrade.co.kr/_prozentrade/data/product_list.php"
            params = {
                'product_key': os.getenv('ZENTRADE_API_KEY'),
                'api_key': os.getenv('ZENTRADE_API_SECRET')
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                # XML 파싱
                content = response.content.decode('euc-kr')
                root = ET.fromstring(content)
                
                count = 0
                products_elem = root.find('.//products')
                
                if products_elem is not None:
                    for product_elem in products_elem.findall('product')[:20]:  # 최대 20개
                        try:
                            product_data = {
                                'id': product_elem.findtext('product_id', ''),
                                'name': product_elem.findtext('product_name', ''),
                                'price': product_elem.findtext('product_price', '0'),
                                'stock': product_elem.findtext('product_stock', '0'),
                                'image': product_elem.findtext('product_image', ''),
                                'category': product_elem.findtext('product_category', ''),
                                'status': product_elem.findtext('product_status', '')
                            }
                            
                            await self.conn.execute("""
                                INSERT INTO collected_products 
                                (wholesaler_name, product_id, product_name, price, 
                                 stock_quantity, category, image_url, is_active, raw_data)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                                ON CONFLICT (wholesaler_name, product_id) 
                                DO UPDATE SET 
                                    product_name = EXCLUDED.product_name,
                                    price = EXCLUDED.price,
                                    stock_quantity = EXCLUDED.stock_quantity,
                                    is_active = EXCLUDED.is_active,
                                    updated_at = CURRENT_TIMESTAMP
                            """,
                            'Zentrade',
                            product_data['id'],
                            product_data['name'],
                            int(product_data['price']),
                            int(product_data['stock']),
                            product_data['category'],
                            product_data['image'],
                            product_data['status'] == '판매중',
                            json.dumps(product_data)
                            )
                            count += 1
                            print(f"저장: {product_data['name']}")
                        except Exception as e:
                            print(f"상품 저장 오류: {e}")
                            continue
                    
                    print(f"[Zentrade] {count}개 상품 처리 완료")
                    return count
                else:
                    print("상품 데이터 없음")
                    return 0
            else:
                print(f"API 호출 실패: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"[Zentrade] 오류: {e}")
            return 0
            
    async def main(self):
        """메인 실행 함수"""
        print("="*60)
        print("도매처 상품 수집 시작 (최종)")
        print(f"시작 시간: {datetime.now()}")
        print("="*60)
        
        try:
            # 데이터베이스 연결
            await self.connect_db()
            
            # 테이블 설정
            await self.setup_tables()
            
            # 각 도매처별 수집
            results = {
                'ownerclan': await self.collect_ownerclan_products(),
                'zentrade': await self.collect_zentrade_products()
            }
            
            # 결과 출력
            print("\n" + "="*60)
            print("수집 완료!")
            print(f"OwnerClan: {results['ownerclan']}개")
            print(f"Zentrade: {results['zentrade']}개")
            print(f"총 수집: {sum(results.values())}개")
            
            # 데이터베이스 통계
            total_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM collected_products"
            )
            print(f"\n데이터베이스 총 상품 수: {total_count}개")
            
            # 도매처별 통계
            stats = await self.conn.fetch(
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
            
            # 샘플 데이터 출력
            samples = await self.conn.fetch(
                """
                SELECT wholesaler_name, product_name, price, stock_quantity
                FROM simple_collected_products
                ORDER BY created_at DESC
                LIMIT 5
                """
            )
            
            print("\n최근 수집된 상품 (5개):")
            for sample in samples:
                print(f"  [{sample['wholesaler_name']}] {sample['product_name']}")
                print(f"    가격: {sample['price']:,}원, 재고: {sample['stock_quantity']}개")
            
            # 결과 파일 저장
            with open('collection_result_final.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': results,
                    'total_count': total_count,
                    'stats': [dict(s) for s in stats]
                }, f, ensure_ascii=False, indent=2)
                
            print("\n결과가 collection_result_final.json에 저장되었습니다.")
            print("PostgreSQL 데이터베이스에 상품이 저장되었습니다!")
            
        except Exception as e:
            print(f"오류 발생: {e}")
            raise
        finally:
            await self.close_db()


if __name__ == "__main__":
    collector = FinalProductCollector()
    asyncio.run(collector.main())