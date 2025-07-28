"""
한국 도매 사이트 상품 수집기
오너클랜, 도매매, 젠트레이드 등 지원
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
import json
from datetime import datetime
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

class WholesalerCollector:
    """도매 사이트 상품 수집 기본 클래스"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def clean_price(self, price_str: str) -> int:
        """가격 문자열을 정수로 변환"""
        # 숫자가 아닌 문자 제거 (원, 콤마 등)
        price_str = re.sub(r'[^\d]', '', price_str)
        return int(price_str) if price_str else 0
    
    def clean_text(self, text: str) -> str:
        """텍스트 정리"""
        if not text:
            return ""
        return ' '.join(text.split())


class OwnerClanCollector(WholesalerCollector):
    """오너클랜 상품 수집기"""
    
    BASE_URL = "https://www.ownerclan.com"
    
    async def search_products(self, keyword: str, page: int = 1) -> List[Dict]:
        """상품 검색"""
        products = []
        
        # 오너클랜 검색 URL
        search_url = f"{self.BASE_URL}/V2/product/search.php"
        params = {
            'keyword': keyword,
            'page': page,
            'sort': 'new',  # 최신순
            'view_type': 'list'
        }
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    text = await response.text()
                    products = self._parse_products(text)
        except Exception as e:
            print(f"오너클랜 검색 오류: {e}")
        
        return products
    
    def _parse_products(self, html: str) -> List[Dict]:
        """HTML에서 상품 정보 추출"""
        products = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 상품 목록 파싱 (실제 HTML 구조에 맞게 수정 필요)
        product_items = soup.select('.product-item')  # 셀렉터는 실제 사이트에 맞게 조정
        
        for item in product_items:
            try:
                product = {
                    'source': 'ownerclan',
                    'name': self.clean_text(item.select_one('.product-name').text),
                    'price': self.clean_price(item.select_one('.price').text),
                    'image': urljoin(self.BASE_URL, item.select_one('img')['src']),
                    'url': urljoin(self.BASE_URL, item.select_one('a')['href']),
                    'seller': self.clean_text(item.select_one('.seller-name').text) if item.select_one('.seller-name') else '',
                    'collected_at': datetime.now().isoformat()
                }
                products.append(product)
            except Exception as e:
                continue
        
        return products


class DomemeCollector(WholesalerCollector):
    """도매매 상품 수집기"""
    
    BASE_URL = "https://domeme.co.kr"
    
    async def search_products(self, keyword: str, page: int = 1) -> List[Dict]:
        """상품 검색"""
        products = []
        
        # 도매매 API 엔드포인트 (실제 API 확인 필요)
        api_url = f"{self.BASE_URL}/api/v1/products/search"
        params = {
            'q': keyword,
            'page': page,
            'size': 50,
            'sort': 'latest'
        }
        
        try:
            async with self.session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    products = self._parse_api_response(data)
        except Exception as e:
            print(f"도매매 검색 오류: {e}")
            # API가 없다면 웹 스크래핑으로 대체
            products = await self._scrape_products(keyword, page)
        
        return products
    
    def _parse_api_response(self, data: Dict) -> List[Dict]:
        """API 응답 파싱"""
        products = []
        
        for item in data.get('products', []):
            product = {
                'source': 'domeme',
                'name': item.get('name', ''),
                'price': item.get('price', 0),
                'wholesale_price': item.get('wholesale_price', 0),
                'image': item.get('image_url', ''),
                'url': f"{self.BASE_URL}/product/{item.get('id')}",
                'seller': item.get('seller', {}).get('name', ''),
                'category': item.get('category', ''),
                'min_order': item.get('min_order_quantity', 1),
                'collected_at': datetime.now().isoformat()
            }
            products.append(product)
        
        return products
    
    async def _scrape_products(self, keyword: str, page: int) -> List[Dict]:
        """웹 스크래핑 대체 방법"""
        products = []
        search_url = f"{self.BASE_URL}/search"
        params = {'keyword': keyword, 'page': page}
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    text = await response.text()
                    products = self._parse_html(text)
        except Exception as e:
            print(f"도매매 스크래핑 오류: {e}")
        
        return products
    
    def _parse_html(self, html: str) -> List[Dict]:
        """HTML 파싱"""
        products = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 실제 HTML 구조에 맞게 수정 필요
        for item in soup.select('.product-card'):
            try:
                product = {
                    'source': 'domeme',
                    'name': self.clean_text(item.select_one('.title').text),
                    'price': self.clean_price(item.select_one('.price').text),
                    'image': item.select_one('img')['src'],
                    'url': urljoin(self.BASE_URL, item.select_one('a')['href']),
                    'collected_at': datetime.now().isoformat()
                }
                products.append(product)
            except:
                continue
        
        return products


class GentradeCollector(WholesalerCollector):
    """젠트레이드 상품 수집기"""
    
    BASE_URL = "https://www.gentrade.co.kr"
    
    async def search_products(self, keyword: str, page: int = 1) -> List[Dict]:
        """상품 검색"""
        products = []
        
        # 젠트레이드 검색 URL
        search_url = f"{self.BASE_URL}/shop/goods/goods_search.php"
        data = {
            'sword': keyword,
            'page': page,
            'pageNum': 40
        }
        
        try:
            async with self.session.post(search_url, data=data) as response:
                if response.status == 200:
                    text = await response.text()
                    products = self._parse_products(text)
        except Exception as e:
            print(f"젠트레이드 검색 오류: {e}")
        
        return products
    
    def _parse_products(self, html: str) -> List[Dict]:
        """HTML에서 상품 정보 추출"""
        products = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 실제 HTML 구조에 맞게 수정 필요
        for item in soup.select('.goods-list-item'):
            try:
                # 가격 정보 추출
                price_elem = item.select_one('.price')
                price_text = price_elem.text if price_elem else "0"
                
                product = {
                    'source': 'gentrade',
                    'name': self.clean_text(item.select_one('.goods-name').text),
                    'price': self.clean_price(price_text),
                    'image': item.select_one('img')['src'],
                    'url': urljoin(self.BASE_URL, item.select_one('a')['href']),
                    'brand': self.clean_text(item.select_one('.brand').text) if item.select_one('.brand') else '',
                    'collected_at': datetime.now().isoformat()
                }
                products.append(product)
            except:
                continue
        
        return products


class KoreanWholesalerCollector:
    """한국 도매 사이트 통합 수집기"""
    
    def __init__(self):
        self.collectors = {
            'ownerclan': OwnerClanCollector,
            'domeme': DomemeCollector,
            'gentrade': GentradeCollector
        }
    
    async def collect_products(self, source: str, keyword: str, page: int = 1) -> List[Dict]:
        """지정된 도매 사이트에서 상품 수집"""
        if source not in self.collectors:
            raise ValueError(f"지원하지 않는 도매 사이트: {source}")
        
        collector_class = self.collectors[source]
        
        async with collector_class() as collector:
            products = await collector.search_products(keyword, page)
            return products
    
    async def collect_from_all(self, keyword: str, page: int = 1) -> Dict[str, List[Dict]]:
        """모든 도매 사이트에서 상품 수집"""
        results = {}
        
        tasks = []
        for source in self.collectors:
            task = self.collect_products(source, keyword, page)
            tasks.append((source, task))
        
        for source, task in tasks:
            try:
                products = await task
                results[source] = products
            except Exception as e:
                print(f"{source} 수집 실패: {e}")
                results[source] = []
        
        return results


# 사용 예시
async def main():
    collector = KoreanWholesalerCollector()
    
    # 단일 사이트에서 수집
    products = await collector.collect_products('domeme', '여성의류', page=1)
    print(f"도매매에서 {len(products)}개 상품 수집")
    
    # 모든 사이트에서 수집
    all_products = await collector.collect_from_all('가방', page=1)
    for source, products in all_products.items():
        print(f"{source}: {len(products)}개 상품")


if __name__ == "__main__":
    asyncio.run(main())