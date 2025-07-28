#!/usr/bin/env python3
"""
도매처 상품 수집 및 PostgreSQL 저장 (간단 버전)
"""

import os
import sys
import asyncio
import json
import aiohttp
import requests
import uuid
from datetime import datetime
from dotenv import load_dotenv
import asyncpg
from xml.etree import ElementTree as ET

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()


class SimpleProductCollector:
    """간단한 상품 수집기"""
    
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
            
    async def get_or_create_user(self):
        """시스템 사용자 생성 또는 조회"""
        # 기존 사용자 확인
        user = await self.conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            "system@yooni.com"
        )
        
        if not user:
            # 새 사용자 생성
            user_id = await self.conn.fetchval(
                """
                INSERT INTO users (id, email, username, full_name, hashed_password, is_active, 
                                 is_verified, role, status, failed_login_attempts, 
                                 password_changed_at, timezone, language, is_deleted,
                                 created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING id
                """,
                uuid.uuid4(), "system@yooni.com", "system", "System User", "dummy_password", True,
                True, 'ADMIN', 'ACTIVE', 0, 
                datetime.now(), 'Asia/Seoul', 'ko', False,
                datetime.now(), datetime.now()
            )
            print("시스템 사용자 생성")
            return user_id
        
        return user['id']
        
    async def get_or_create_wholesaler(self, user_id, wholesaler_type, name):
        """도매처 계정 생성 또는 조회"""
        # 기존 도매처 확인
        wholesaler = await self.conn.fetchrow(
            "SELECT id FROM wholesaler_accounts WHERE wholesaler_type = $1 AND user_id = $2",
            wholesaler_type, user_id
        )
        
        if not wholesaler:
            # 새 도매처 생성
            credentials = {
                'ownerclan': {
                    'username': os.getenv('OWNERCLAN_USERNAME'),
                    'password': os.getenv('OWNERCLAN_PASSWORD')
                },
                'zentrade': {
                    'api_key': os.getenv('ZENTRADE_API_KEY'),
                    'api_secret': os.getenv('ZENTRADE_API_SECRET')
                }
            }
            
            wholesaler_id = await self.conn.fetchval(
                """
                INSERT INTO wholesaler_accounts 
                (id, user_id, wholesaler_type, account_name, api_credentials, is_active, 
                 auto_collect_enabled, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                uuid.uuid4(), user_id, wholesaler_type, f"{name} 기본 계정", 
                json.dumps(credentials.get(wholesaler_type.lower(), {})), True, True,
                datetime.now(), datetime.now()
            )
            print(f"{name} 도매처 계정 생성")
            return wholesaler_id
            
        return wholesaler['id']
        
    async def collect_ownerclan_products(self, user_id):
        """OwnerClan 상품 수집"""
        print("\n[OwnerClan] 상품 수집 시작...")
        
        try:
            # 도매처 계정 확인/생성
            wholesaler_id = await self.get_or_create_wholesaler(user_id, 'OWNERCLAN', '오너클랜')
            
            # GraphQL 로그인
            login_url = "https://b2b.ownerclan.com/v1/graphql"
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
                    result = await response.json()
                    
                    if 'data' in result and result['data']['login']:
                        token = result['data']['login']['token']
                        print("로그인 성공")
                    else:
                        # Plain text token 처리
                        async with session.post(
                            login_url,
                            json={
                                "query": login_query,
                                "variables": {
                                    "username": os.getenv('OWNERCLAN_USERNAME'),
                                    "password": os.getenv('OWNERCLAN_PASSWORD')
                                }
                            }
                        ) as retry_response:
                            token_text = await retry_response.text()
                            token = token_text.strip()
                            if token.startswith('eyJ'):
                                print("로그인 성공 (plain text token)")
                            else:
                                print("로그인 실패")
                                return 0
                
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
                            # 기존 상품 확인
                            existing = await self.conn.fetchrow(
                                """
                                SELECT id FROM wholesaler_products 
                                WHERE wholesaler_account_id = $1 AND wholesaler_product_id = $2
                                """,
                                wholesaler_id, product['productId']
                            )
                            
                            if existing:
                                # 업데이트
                                await self.conn.execute(
                                    """
                                    UPDATE wholesaler_products 
                                    SET name = $1, wholesale_price = $2, stock_quantity = $3, 
                                        is_in_stock = $4, is_active = $5, updated_at = $6
                                    WHERE id = $7
                                    """,
                                    product['name'], 
                                    int(product['salePrice']),
                                    product.get('stockCnt', 0),
                                    product.get('stockCnt', 0) > 0,
                                    product.get('status') == 'ACTIVE',
                                    datetime.utcnow(),
                                    existing['id']
                                )
                                print(f"업데이트: {product['name']}")
                            else:
                                # 신규 생성
                                await self.conn.execute(
                                    """
                                    INSERT INTO wholesaler_products 
                                    (wholesaler_account_id, wholesaler_product_id, name, wholesale_price, 
                                     retail_price, stock_quantity, is_in_stock, category_path, 
                                     main_image_url, is_active, raw_data)
                                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                                    """,
                                    wholesaler_id,
                                    product['productId'],
                                    product['name'],
                                    int(product['salePrice']),
                                    int(product['salePrice']),
                                    product.get('stockCnt', 0),
                                    product.get('stockCnt', 0) > 0,
                                    product['category']['name'] if product.get('category') else None,
                                    product['images'][0]['url'] if product.get('images') else None,
                                    product.get('status') == 'ACTIVE',
                                    json.dumps(product)
                                )
                                print(f"추가: {product['name']}")
                            
                            count += 1
                        
                        print(f"[OwnerClan] {count}개 상품 처리 완료")
                        return count
                    else:
                        print("상품 조회 실패")
                        return 0
                        
        except Exception as e:
            print(f"[OwnerClan] 오류: {e}")
            return 0
            
    async def collect_zentrade_products(self, user_id):
        """Zentrade 상품 수집"""
        print("\n[Zentrade] 상품 수집 시작...")
        
        try:
            # 도매처 계정 확인/생성
            wholesaler_id = await self.get_or_create_wholesaler(user_id, 'ZENTRADE', '젠트레이드')
            
            # API 호출
            url = "https://zentrade.co.kr/api/product/product_api.php"
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
                        product_data = {
                            'id': product_elem.findtext('product_id', ''),
                            'name': product_elem.findtext('product_name', ''),
                            'price': product_elem.findtext('product_price', '0'),
                            'stock': product_elem.findtext('product_stock', '0'),
                            'image': product_elem.findtext('product_image', ''),
                            'category': product_elem.findtext('product_category', ''),
                            'status': product_elem.findtext('product_status', '')
                        }
                        
                        # 기존 상품 확인
                        existing = await self.conn.fetchrow(
                            """
                            SELECT id FROM wholesaler_products 
                            WHERE wholesaler_account_id = $1 AND wholesaler_product_id = $2
                            """,
                            wholesaler_id, product_data['id']
                        )
                        
                        if existing:
                            # 업데이트
                            await self.conn.execute(
                                """
                                UPDATE wholesaler_products 
                                SET name = $1, wholesale_price = $2, stock_quantity = $3, 
                                    is_in_stock = $4, is_active = $5, updated_at = $6
                                WHERE id = $7
                                """,
                                product_data['name'],
                                int(product_data['price']),
                                int(product_data['stock']),
                                int(product_data['stock']) > 0,
                                product_data['status'] == '판매중',
                                datetime.utcnow(),
                                existing['id']
                            )
                            print(f"업데이트: {product_data['name']}")
                        else:
                            # 신규 생성
                            await self.conn.execute(
                                """
                                INSERT INTO wholesaler_products 
                                (wholesaler_account_id, wholesaler_product_id, name, wholesale_price, 
                                 retail_price, stock_quantity, is_in_stock, category_path, 
                                 main_image_url, is_active, raw_data)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                                """,
                                wholesaler_id,
                                product_data['id'],
                                product_data['name'],
                                int(product_data['price']),
                                int(product_data['price']),
                                int(product_data['stock']),
                                int(product_data['stock']) > 0,
                                product_data['category'],
                                product_data['image'],
                                product_data['status'] == '판매중',
                                json.dumps(product_data)
                            )
                            print(f"추가: {product_data['name']}")
                        
                        count += 1
                    
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
        print("도매처 상품 수집 시작")
        print(f"시작 시간: {datetime.now()}")
        print("="*60)
        
        try:
            # 데이터베이스 연결
            await self.connect_db()
            
            # 시스템 사용자 확인/생성
            user_id = await self.get_or_create_user()
            
            # 각 도매처별 수집
            results = {
                'ownerclan': await self.collect_ownerclan_products(user_id),
                'zentrade': await self.collect_zentrade_products(user_id)
            }
            
            # 결과 출력
            print("\n" + "="*60)
            print("수집 완료!")
            print(f"OwnerClan: {results['ownerclan']}개")
            print(f"Zentrade: {results['zentrade']}개")
            print(f"총 수집: {sum(results.values())}개")
            
            # 데이터베이스 통계
            total_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM wholesaler_products"
            )
            print(f"\n데이터베이스 총 상품 수: {total_count}개")
            
            # 도매처별 통계
            stats = await self.conn.fetch(
                """
                SELECT wa.account_name, COUNT(wp.id) as count
                FROM wholesaler_accounts wa
                LEFT JOIN wholesaler_products wp ON wa.id = wp.wholesaler_account_id
                GROUP BY wa.account_name
                """
            )
            
            for stat in stats:
                print(f"{stat['account_name']}: {stat['count']}개")
            
            # 결과 파일 저장
            with open('collection_result_simple.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': results,
                    'total_count': total_count
                }, f, ensure_ascii=False, indent=2)
                
            print("\n결과가 collection_result_simple.json에 저장되었습니다.")
            
        except Exception as e:
            print(f"오류 발생: {e}")
            raise
        finally:
            await self.close_db()


if __name__ == "__main__":
    collector = SimpleProductCollector()
    asyncio.run(collector.main())