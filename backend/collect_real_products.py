#!/usr/bin/env python3
"""
실제 도매처 상품 수집 (웹 스크래핑)
"""

import os
import sys
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()


class SimpleWholesalerCollector:
    """간단한 도매처 상품 수집기"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def collect_from_ownerclan(self, keyword="이어폰", limit=10):
        """오너클랜 상품 수집 (공개 페이지)"""
        products = []
        
        try:
            # 공개 검색 페이지
            search_url = "https://www.ownerclan.com/V2/product/search.php"
            params = {'sw': keyword, 'page': 1}
            
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 상품 목록 찾기 (실제 HTML 구조에 맞게 수정 필요)
                    # 예시 셀렉터
                    product_items = soup.select('.product_list_area .box')[:limit]
                    
                    for idx, item in enumerate(product_items):
                        try:
                            # 상품 정보 추출 (실제 구조에 맞게 수정)
                            name_elem = item.select_one('.subject a')
                            price_elem = item.select_one('.price')
                            
                            if name_elem:
                                product = {
                                    'wholesaler': 'ownerclan',
                                    'wholesaler_product_id': f'oc_{idx}_{datetime.now().timestamp()}',
                                    'name': name_elem.get_text(strip=True),
                                    'price': self._extract_price(price_elem.get_text() if price_elem else '0'),
                                    'wholesale_price': self._extract_price(price_elem.get_text() if price_elem else '0'),
                                    'stock_quantity': 0,  # 공개 페이지에서는 재고 확인 불가
                                    'category': keyword,
                                    'collected_at': datetime.now().isoformat()
                                }
                                products.append(product)
                                
                        except Exception as e:
                            print(f"상품 파싱 오류: {e}")
                            
                    print(f"[오너클랜] {len(products)}개 상품 수집")
                    
        except Exception as e:
            print(f"[오너클랜] 수집 오류: {e}")
            
        return products
        
    async def collect_from_domeggook_web(self, keyword="이어폰", limit=10):
        """도매꾹 상품 수집 (웹 페이지)"""
        products = []
        
        try:
            # 도매꾹 검색 페이지
            search_url = "https://www.domeggook.com/search/product"
            params = {'keyword': keyword}
            
            async with self.session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 상품 목록 (실제 구조에 맞게 수정)
                    product_items = soup.select('.product-item')[:limit]
                    
                    for idx, item in enumerate(product_items):
                        try:
                            name_elem = item.select_one('.product-name')
                            price_elem = item.select_one('.product-price')
                            
                            if name_elem:
                                product = {
                                    'wholesaler': 'domeggook',
                                    'wholesaler_product_id': f'dm_{idx}_{datetime.now().timestamp()}',
                                    'name': name_elem.get_text(strip=True),
                                    'price': self._extract_price(price_elem.get_text() if price_elem else '0'),
                                    'wholesale_price': self._extract_price(price_elem.get_text() if price_elem else '0'),
                                    'stock_quantity': 0,
                                    'category': keyword,
                                    'collected_at': datetime.now().isoformat()
                                }
                                products.append(product)
                                
                        except Exception as e:
                            print(f"상품 파싱 오류: {e}")
                            
                    print(f"[도매꾹] {len(products)}개 상품 수집")
                    
        except Exception as e:
            print(f"[도매꾹] 수집 오류: {e}")
            
        return products
        
    def _extract_price(self, price_text):
        """가격 텍스트에서 숫자만 추출"""
        import re
        numbers = re.findall(r'\d+', price_text.replace(',', ''))
        return int(numbers[0]) if numbers else 0
        
    async def collect_all(self, keyword="이어폰"):
        """모든 도매처에서 상품 수집"""
        all_products = []
        
        # 오너클랜
        products = await self.collect_from_ownerclan(keyword, limit=5)
        all_products.extend(products)
        
        # 도매꾹
        products = await self.collect_from_domeggook_web(keyword, limit=5)
        all_products.extend(products)
        
        return all_products


def save_to_database(products):
    """수집된 상품을 데이터베이스에 저장"""
    
    db_path = Path("yooni_dropshipping.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # collected_products 테이블이 없으면 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collected_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wholesaler TEXT NOT NULL,
                wholesaler_product_id TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                wholesale_price INTEGER,
                stock_quantity INTEGER DEFAULT 0,
                main_image_url TEXT,
                category TEXT,
                raw_data TEXT,
                last_collected_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(wholesaler, wholesaler_product_id)
            )
        """)
        
        saved_count = 0
        updated_count = 0
        
        for product in products:
            now = datetime.now().isoformat()
            
            # 중복 확인
            cursor.execute("""
                SELECT id FROM collected_products 
                WHERE wholesaler = ? AND wholesaler_product_id = ?
            """, (product['wholesaler'], product['wholesaler_product_id']))
            
            existing = cursor.fetchone()
            
            if existing:
                # 업데이트
                cursor.execute("""
                    UPDATE collected_products
                    SET name = ?, price = ?, wholesale_price = ?, 
                        stock_quantity = ?, category = ?,
                        raw_data = ?, last_collected_at = ?, updated_at = ?
                    WHERE wholesaler = ? AND wholesaler_product_id = ?
                """, (
                    product['name'], product['price'], product.get('wholesale_price', product['price']),
                    product.get('stock_quantity', 0), product.get('category', ''),
                    json.dumps(product), product['collected_at'], now,
                    product['wholesaler'], product['wholesaler_product_id']
                ))
                updated_count += 1
            else:
                # 신규 추가
                cursor.execute("""
                    INSERT INTO collected_products (
                        wholesaler, wholesaler_product_id, name, price, wholesale_price,
                        stock_quantity, category, raw_data, last_collected_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product['wholesaler'], product['wholesaler_product_id'], product['name'],
                    product['price'], product.get('wholesale_price', product['price']),
                    product.get('stock_quantity', 0), product.get('category', ''),
                    json.dumps(product), product['collected_at'], now, now
                ))
                saved_count += 1
                
        conn.commit()
        print(f"\n[데이터베이스] 신규: {saved_count}개, 업데이트: {updated_count}개")
        
        # 전체 상품 수 확인
        cursor.execute("SELECT COUNT(*) FROM collected_products")
        total_count = cursor.fetchone()[0]
        print(f"[데이터베이스] 총 상품 수: {total_count}개")
        
    except Exception as e:
        print(f"데이터베이스 오류: {e}")
        conn.rollback()
        
    finally:
        conn.close()


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("실제 도매처 상품 수집")
    print("=" * 60)
    print(f"실행 시간: {datetime.now()}")
    
    # 검색 키워드
    keywords = ["이어폰", "블루투스스피커", "무선충전기"]
    
    all_products = []
    
    async with SimpleWholesalerCollector() as collector:
        for keyword in keywords:
            print(f"\n검색어: '{keyword}'")
            print("-" * 40)
            
            products = await collector.collect_all(keyword)
            all_products.extend(products)
            
            # API 부하 방지
            await asyncio.sleep(2)
    
    print(f"\n총 {len(all_products)}개 상품 수집 완료")
    
    # 결과 저장
    if all_products:
        # JSON 파일로 저장
        filename = f'collected_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        print(f"\n결과 파일: {filename}")
        
        # 데이터베이스에 저장
        save_to_database(all_products)


if __name__ == "__main__":
    # BeautifulSoup 설치 확인
    try:
        import bs4
    except ImportError:
        print("BeautifulSoup4를 설치해주세요: pip install beautifulsoup4")
        exit(1)
        
    asyncio.run(main())