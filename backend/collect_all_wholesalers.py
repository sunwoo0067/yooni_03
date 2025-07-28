#!/usr/bin/env python3
"""
모든 도매처 (OwnerClan, Zentrade, Domeggook) 통합 수집
"""

import os
import sys
import asyncio
import json
from datetime import datetime
import asyncpg

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


class AllWholesalersCollector:
    """모든 도매처 통합 수집기"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.conn = None
        
    async def connect_db(self):
        """데이터베이스 연결"""
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
            
    async def collect_ownerclan_products(self):
        """OwnerClan 상품 수집"""
        print("\n[OwnerClan] 상품 수집 시작...")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # 1. 인증
                username = os.getenv('OWNERCLAN_USERNAME')
                password = os.getenv('OWNERCLAN_PASSWORD')
                
                auth_url = 'https://auth.ownerclan.com/auth'
                auth_data = {
                    "service": "ownerclan",
                    "userType": "seller",
                    "username": username,
                    "password": password
                }
                
                async with session.post(auth_url, json=auth_data) as response:
                    if response.status == 200:
                        token = await response.text()
                        token = token.strip()
                        print("✓ 로그인 성공")
                    else:
                        print("✗ 로그인 실패")
                        return []
                        
                # 2. 상품 조회
                api_url = 'https://api.ownerclan.com/v1/graphql'
                query = """
                query GetAllItems($first: Int) {
                    allItems(first: $first) {
                        edges {
                            node {
                                key
                                name
                                price
                                status
                                quantity
                                vendor {
                                    name
                                }
                                tags
                                productType
                            }
                        }
                    }
                }
                """
                
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                }
                
                payload = {
                    'query': query,
                    'variables': {'first': 10}
                }
                
                async with session.post(api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'errors' in data:
                            print(f"✗ GraphQL 오류: {data['errors']}")
                            return []
                            
                        edges = data.get('data', {}).get('allItems', {}).get('edges', [])
                        products = []
                        
                        for edge in edges:
                            node = edge.get('node', {})
                            products.append({
                                'wholesaler_name': 'OwnerClan',
                                'product_id': node.get('key', ''),
                                'product_name': node.get('name', ''),
                                'price': int(node.get('price', 0)),
                                'stock_quantity': int(node.get('quantity', 0)),
                                'category': node.get('productType', ''),
                                'is_active': node.get('status') == 'available',
                                'raw_data': json.dumps(node)
                            })
                        
                        print(f"[OwnerClan] {len(products)}개 상품 수집 완료")
                        return products
                    else:
                        print(f"✗ API 호출 실패: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"[OwnerClan] 오류: {e}")
            return []
            
    async def collect_zentrade_products(self):
        """Zentrade 상품 수집"""
        print("\n[Zentrade] 상품 수집 시작...")
        
        try:
            import requests
            from xml.etree import ElementTree as ET
            
            url = "http://zentrade.co.kr/_prozentrade/data/product_list.php"
            
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/xml',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'product_key': os.getenv('ZENTRADE_API_KEY'),
                'api_key': os.getenv('ZENTRADE_API_SECRET')
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                content = response.content.decode('euc-kr')
                root = ET.fromstring(content)
                
                products = []
                product_elements = root.findall('.//product')
                
                for elem in product_elements[:10]:  # 최대 10개
                    products.append({
                        'wholesaler_name': 'Zentrade',
                        'product_id': elem.findtext('no', ''),
                        'product_name': elem.findtext('name', ''),
                        'price': int(elem.findtext('price', '0')),
                        'stock_quantity': int(elem.findtext('stock', '0')),
                        'category': elem.findtext('category1_name', ''),
                        'is_active': elem.findtext('status', '') == '판매중',
                        'raw_data': json.dumps({
                            'no': elem.findtext('no', ''),
                            'name': elem.findtext('name', ''),
                            'price': elem.findtext('price', '0'),
                            'stock': elem.findtext('stock', '0'),
                            'status': elem.findtext('status', ''),
                            'category': elem.findtext('category1_name', '')
                        })
                    })
                
                print(f"[Zentrade] {len(products)}개 상품 수집 완료")
                return products
            else:
                print(f"API 호출 실패: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[Zentrade] 오류: {e}")
            return []
            
    def get_domeggook_sample_products(self):
        """Domeggook 샘플 상품 (API 실패로 인한 대체)"""
        print("\n[Domeggook] 샘플 상품 사용...")
        
        products = [
            {
                'wholesaler_name': 'Domeggook',
                'product_id': 'DG001',
                'product_name': '여성 블라우스 - 실크 소재',
                'price': 12000,
                'stock_quantity': 150,
                'category': '의류/여성의류',
                'is_active': True,
                'raw_data': json.dumps({
                    'supplier': '패션플러스',
                    'material': '실크 100%',
                    'size': 'S, M, L'
                })
            },
            {
                'wholesaler_name': 'Domeggook',
                'product_id': 'DG002',
                'product_name': '가죽 크로스백 - 브라운',
                'price': 18000,
                'stock_quantity': 80,
                'category': '가방/지갑',
                'is_active': True,
                'raw_data': json.dumps({
                    'supplier': '백앤백',
                    'material': '소가죽',
                    'color': '브라운, 블랙'
                })
            },
            {
                'wholesaler_name': 'Domeggook',
                'product_id': 'DG003',
                'product_name': '실버 체인 목걸이',
                'price': 8500,
                'stock_quantity': 200,
                'category': '액세서리/주얼리',
                'is_active': True,
                'raw_data': json.dumps({
                    'supplier': '쥬얼리하우스',
                    'material': '925 실버'
                })
            },
            {
                'wholesaler_name': 'Domeggook',
                'product_id': 'DG004',
                'product_name': '러닝화 - 에어쿠션',
                'price': 35000,
                'stock_quantity': 50,
                'category': '신발/운동화',
                'is_active': True,
                'raw_data': json.dumps({
                    'supplier': '슈즈마켓',
                    'size': '250-280'
                })
            },
            {
                'wholesaler_name': 'Domeggook',
                'product_id': 'DG005',
                'product_name': '스킨케어 5종 세트',
                'price': 25000,
                'stock_quantity': 100,
                'category': '뷰티/화장품',
                'is_active': True,
                'raw_data': json.dumps({
                    'supplier': '뷰티서플라이',
                    'components': '토너, 에센스, 로션, 크림, 마스크팩'
                })
            }
        ]
        
        print(f"[Domeggook] {len(products)}개 샘플 상품 준비 완료")
        return products
        
    async def save_products_to_db(self, products):
        """상품을 데이터베이스에 저장"""
        saved_count = 0
        
        for product in products:
            try:
                await self.conn.execute("""
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
                        raw_data = EXCLUDED.raw_data,
                        updated_at = CURRENT_TIMESTAMP
                """,
                product['wholesaler_name'],
                product['product_id'],
                product['product_name'],
                product['price'],
                product['stock_quantity'],
                product.get('category', ''),
                product['is_active'],
                product.get('raw_data', '{}')
                )
                saved_count += 1
            except Exception as e:
                print(f"상품 저장 오류 ({product['product_name']}): {e}")
                
        return saved_count
        
    async def main(self):
        """메인 실행 함수"""
        print("=" * 60)
        print("모든 도매처 상품 수집")
        print(f"시작 시간: {datetime.now()}")
        print("=" * 60)
        
        try:
            # 데이터베이스 연결
            await self.connect_db()
            
            # 각 도매처에서 상품 수집
            all_products = []
            
            # OwnerClan
            ownerclan_products = await self.collect_ownerclan_products()
            all_products.extend(ownerclan_products)
            
            # Zentrade
            zentrade_products = await self.collect_zentrade_products()
            all_products.extend(zentrade_products)
            
            # Domeggook (샘플)
            domeggook_products = self.get_domeggook_sample_products()
            all_products.extend(domeggook_products)
            
            # 데이터베이스에 저장
            print(f"\n총 {len(all_products)}개 상품을 데이터베이스에 저장 중...")
            saved_count = await self.save_products_to_db(all_products)
            print(f"✓ {saved_count}개 상품 저장 완료")
            
            # 통계 출력
            stats = await self.conn.fetch("""
                SELECT 
                    wholesaler_name,
                    COUNT(*) as count,
                    AVG(price) as avg_price,
                    SUM(stock_quantity) as total_stock
                FROM simple_collected_products
                GROUP BY wholesaler_name
                ORDER BY wholesaler_name
            """)
            
            print("\n" + "=" * 60)
            print("도매처별 통계")
            print("=" * 60)
            for stat in stats:
                print(f"\n[{stat['wholesaler_name']}]")
                print(f"  총 상품 수: {stat['count']}개")
                print(f"  평균 가격: {stat['avg_price']:,.0f}원")
                print(f"  총 재고: {stat['total_stock']:,}개")
            
            # 최근 수집 상품 샘플
            recent = await self.conn.fetch("""
                SELECT wholesaler_name, product_name, price, stock_quantity
                FROM simple_collected_products
                ORDER BY updated_at DESC
                LIMIT 10
            """)
            
            print("\n최근 수집된 상품 (10개):")
            for item in recent:
                print(f"  [{item['wholesaler_name']}] {item['product_name'][:40]}... - {item['price']:,}원 (재고: {item['stock_quantity']})")
            
            # 결과 저장
            with open('all_wholesalers_collection_result.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_products': len(all_products),
                    'by_wholesaler': {
                        'ownerclan': len(ownerclan_products),
                        'zentrade': len(zentrade_products),
                        'domeggook': len(domeggook_products)
                    },
                    'saved_count': saved_count,
                    'note': 'Domeggook은 API 연동 실패로 샘플 데이터 사용'
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\n완료 시간: {datetime.now()}")
            print("\n결과가 all_wholesalers_collection_result.json에 저장되었습니다.")
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_db()


if __name__ == "__main__":
    collector = AllWholesalersCollector()
    asyncio.run(collector.main())