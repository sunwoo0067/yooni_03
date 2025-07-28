"""
베스트셀러 수집기
- 마켓플레이스의 베스트셀러 데이터 수집
- 판매 트렌드 분석용 데이터 수집
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

try:
    from ..database.models_v2 import Base
    from ..database.connection import engine
except ImportError:
    from database.models_v2 import Base
    from database.connection import engine
    
from sqlalchemy import Column, String, Integer, DateTime, Float, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.sql import func


class BestsellerData(Base):
    """베스트셀러 데이터 모델"""
    __tablename__ = "bestseller_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    marketplace = Column(String(50), nullable=False, comment="마켓플레이스")
    rank = Column(Integer, nullable=False, comment="순위")
    category = Column(String(500), comment="카테고리")
    category_id = Column(String(100), comment="카테고리 ID")
    
    # 상품 정보
    product_id = Column(String(200), comment="마켓플레이스 상품 ID")
    product_name = Column(String(500), comment="상품명")
    brand = Column(String(200), comment="브랜드")
    price = Column(Integer, comment="판매가")
    
    # 판매 정보
    review_count = Column(Integer, comment="리뷰 수")
    rating = Column(Float, comment="평점")
    
    # 상세 정보
    if 'postgresql' in str(engine.url):
        product_data = Column(JSONB, comment="상품 상세 데이터")
    else:
        product_data = Column(JSON, comment="상품 상세 데이터")
    
    # 수집 정보
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 인덱스
    __table_args__ = (
        {'extend_existing': True}  # 테이블이 이미 있으면 확장
    )


class CoupangBestsellerCollector:
    """쿠팡 베스트셀러 수집기"""
    
    def __init__(self):
        self.base_url = "https://www.coupang.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
        }
        
    async def get_bestsellers(self, category_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """베스트셀러 수집"""
        products = []
        
        # 카테고리별 베스트셀러 URL
        if category_id:
            url = f"{self.base_url}/np/categories/{category_id}?listSize=120&brand=&offerCondition=&filterType=&isPriceRange=false&minPrice=&maxPrice=&page=1&channel=user&fromComponent=N&selectedPlpKeepFilter=&sorter=bestAsc&filter=&component=&rating=0"
        else:
            # 전체 베스트셀러
            url = f"{self.base_url}/np/bestsellers"
            
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 상품 리스트 파싱
                        product_list = soup.find_all('li', class_='baby-product')
                        
                        for idx, item in enumerate(product_list[:limit], 1):
                            try:
                                # 상품 정보 추출
                                link = item.find('a', class_='baby-product-link')
                                if not link:
                                    continue
                                    
                                product_id = link.get('href', '').split('/')[-1].split('?')[0]
                                product_name = item.find('div', class_='name').text.strip() if item.find('div', class_='name') else ''
                                
                                # 가격 정보
                                price_elem = item.find('strong', class_='price-value')
                                price = 0
                                if price_elem:
                                    price_text = price_elem.text.strip().replace(',', '').replace('원', '')
                                    price = int(price_text) if price_text.isdigit() else 0
                                
                                # 리뷰 및 평점
                                review_elem = item.find('span', class_='rating-total-count')
                                review_count = 0
                                if review_elem:
                                    review_text = review_elem.text.strip().replace('(', '').replace(')', '').replace(',', '')
                                    review_count = int(review_text) if review_text.isdigit() else 0
                                
                                rating_elem = item.find('span', class_='rating')
                                rating = 0.0
                                if rating_elem:
                                    rating_class = rating_elem.get('class', [])
                                    for cls in rating_class:
                                        if 'star' in cls:
                                            rating_match = re.search(r'star(\d+)', cls)
                                            if rating_match:
                                                rating = int(rating_match.group(1)) / 10
                                
                                product_data = {
                                    'marketplace': 'coupang',
                                    'rank': idx,
                                    'product_id': product_id,
                                    'product_name': product_name,
                                    'price': price,
                                    'review_count': review_count,
                                    'rating': rating,
                                    'product_url': f"{self.base_url}/vp/products/{product_id}",
                                    'collected_at': datetime.now().isoformat()
                                }
                                
                                products.append(product_data)
                                
                            except Exception as e:
                                print(f"상품 파싱 오류: {e}")
                                continue
                                
                    else:
                        print(f"쿠팡 베스트셀러 수집 실패: {response.status}")
                        
            except Exception as e:
                print(f"쿠팡 베스트셀러 수집 오류: {e}")
                
        return products


class NaverShoppingCollector:
    """네이버 쇼핑 인기상품 수집기"""
    
    def __init__(self):
        self.base_url = "https://search.shopping.naver.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://shopping.naver.com',
        }
        
    async def get_bestsellers(self, category: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """네이버 쇼핑 베스트셀러 수집"""
        products = []
        
        # API 엔드포인트
        api_url = f"{self.base_url}/api/search/all"
        
        params = {
            'sort': 'rel',  # 인기도순
            'pagingIndex': 1,
            'pagingSize': min(limit, 80),  # 최대 80개
            'viewType': 'list',
            'productSet': 'total',
            'deliveryFee': '',
            'deliveryTypeValue': '',
            'frm': 'NVSHATC'
        }
        
        if category:
            params['catId'] = category
            
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 상품 리스트 추출
                        items = data.get('shoppingResult', {}).get('products', [])
                        
                        for idx, item in enumerate(items[:limit], 1):
                            try:
                                product_data = {
                                    'marketplace': 'naver',
                                    'rank': idx,
                                    'product_id': item.get('productId'),
                                    'product_name': item.get('productTitle'),
                                    'price': int(item.get('price', 0)),
                                    'brand': item.get('brand', ''),
                                    'category': item.get('category1Name', ''),
                                    'review_count': int(item.get('reviewCount', 0)),
                                    'rating': float(item.get('scoreInfo', 0)) / 100,  # 500점 만점을 5점으로 변환
                                    'product_url': item.get('crUrl', ''),
                                    'mall_name': item.get('mallName', ''),
                                    'collected_at': datetime.now().isoformat()
                                }
                                
                                products.append(product_data)
                                
                            except Exception as e:
                                print(f"상품 파싱 오류: {e}")
                                continue
                                
                    else:
                        print(f"네이버 쇼핑 수집 실패: {response.status}")
                        
            except Exception as e:
                print(f"네이버 쇼핑 수집 오류: {e}")
                
        return products


# 테스트 함수
async def test_bestseller_collection():
    """베스트셀러 수집 테스트"""
    print("베스트셀러 수집 테스트 시작...")
    print("=" * 50)
    
    # 쿠팡 베스트셀러 수집
    print("\n1. 쿠팡 베스트셀러 수집 중...")
    coupang_collector = CoupangBestsellerCollector()
    coupang_products = await coupang_collector.get_bestsellers(limit=10)
    
    print(f"   수집된 상품: {len(coupang_products)}개")
    if coupang_products:
        print(f"   1위 상품: {coupang_products[0]['product_name'][:50]}...")
        print(f"   가격: {coupang_products[0]['price']:,}원")
        print(f"   리뷰: {coupang_products[0]['review_count']:,}개")
    
    # 네이버 쇼핑 수집
    print("\n2. 네이버 쇼핑 베스트셀러 수집 중...")
    naver_collector = NaverShoppingCollector()
    naver_products = await naver_collector.get_bestsellers(limit=10)
    
    print(f"   수집된 상품: {len(naver_products)}개")
    if naver_products:
        print(f"   1위 상품: {naver_products[0]['product_name'][:50]}...")
        print(f"   가격: {naver_products[0]['price']:,}원")
        print(f"   리뷰: {naver_products[0]['review_count']:,}개")
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
    
    return {
        'coupang': coupang_products,
        'naver': naver_products
    }

if __name__ == "__main__":
    asyncio.run(test_bestseller_collection())