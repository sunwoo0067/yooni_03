#!/usr/bin/env python3
"""
실제 도매처 API 테스트
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from datetime import datetime

class RealWholesalerCollector:
    """실제 도매처 사이트 수집기"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def collect_from_ownerclan(self, keyword: str, limit: int = 10):
        """오너클랜 실제 상품 수집"""
        print(f"\n[오너클랜] '{keyword}' 검색 중...")
        
        # 오너클랜 검색 URL
        search_url = f"https://www.ownerclan.com/V2/product/search.php?sw={keyword}"
        
        products = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 상품 목록 파싱 (오너클랜 HTML 구조에 맞게 수정 필요)
                        product_items = soup.find_all('div', class_='product-item')[:limit]
                        
                        for item in product_items:
                            try:
                                # 실제 HTML 구조에 맞게 파싱
                                product = {
                                    'name': item.find('div', class_='product-name').text.strip() if item.find('div', class_='product-name') else 'N/A',
                                    'price': self._extract_price(item),
                                    'wholesaler': 'ownerclan',
                                    'collected_at': datetime.now().isoformat(),
                                    'url': 'https://www.ownerclan.com' + item.find('a')['href'] if item.find('a') else ''
                                }
                                products.append(product)
                            except Exception as e:
                                print(f"상품 파싱 에러: {e}")
                                continue
                        
                        print(f"[오너클랜] {len(products)}개 상품 수집 완료")
                    else:
                        print(f"[오너클랜] HTTP 에러: {response.status}")
                        
        except Exception as e:
            print(f"[오너클랜] 수집 에러: {e}")
        
        return products
    
    async def collect_from_domeggook(self, keyword: str, limit: int = 10):
        """도매꾹 실제 상품 수집"""
        print(f"\n[도매꾹] '{keyword}' 검색 중...")
        
        # 도매꾹 API 엔드포인트 (GraphQL)
        api_url = "https://api.domeggook.com/graphql"
        
        # GraphQL 쿼리
        query = """
        query SearchProducts($keyword: String!, $limit: Int!) {
            searchProducts(keyword: $keyword, limit: $limit) {
                id
                name
                price
                wholesalePrice
                minimumQuantity
                imageUrl
                seller {
                    name
                }
            }
        }
        """
        
        variables = {
            "keyword": keyword,
            "limit": limit
        }
        
        products = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    json={"query": query, "variables": variables},
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'data' in data and 'searchProducts' in data['data']:
                            for item in data['data']['searchProducts']:
                                product = {
                                    'name': item['name'],
                                    'price': item['wholesalePrice'] or item['price'],
                                    'min_quantity': item['minimumQuantity'],
                                    'image_url': item['imageUrl'],
                                    'seller': item['seller']['name'] if item.get('seller') else 'Unknown',
                                    'wholesaler': 'domeggook',
                                    'collected_at': datetime.now().isoformat()
                                }
                                products.append(product)
                        
                        print(f"[도매꾹] {len(products)}개 상품 수집 완료")
                    else:
                        print(f"[도매꾹] HTTP 에러: {response.status}")
                        
        except Exception as e:
            print(f"[도매꾹] 수집 에러: {e}")
        
        return products
    
    def _extract_price(self, element):
        """가격 추출 헬퍼 함수"""
        try:
            price_text = element.find('span', class_='price').text
            # 숫자만 추출
            price = ''.join(filter(str.isdigit, price_text))
            return int(price) if price else 0
        except:
            return 0
    
    async def test_all_wholesalers(self, keyword: str = "이어폰"):
        """모든 도매처 테스트"""
        print("=" * 60)
        print(f"실제 도매처 API 테스트 - 검색어: '{keyword}'")
        print("=" * 60)
        
        # 오너클랜 테스트
        ownerclan_products = await self.collect_from_ownerclan(keyword, limit=5)
        print(f"\n[결과] 오너클랜: {len(ownerclan_products)}개 상품")
        if ownerclan_products:
            print(f"첫 번째 상품: {json.dumps(ownerclan_products[0], indent=2, ensure_ascii=False)}")
        
        # 도매꾹 테스트
        domeggook_products = await self.collect_from_domeggook(keyword, limit=5)
        print(f"\n[결과] 도매꾹: {len(domeggook_products)}개 상품")
        if domeggook_products:
            print(f"첫 번째 상품: {json.dumps(domeggook_products[0], indent=2, ensure_ascii=False)}")
        
        # 전체 결과
        total_products = ownerclan_products + domeggook_products
        print(f"\n총 {len(total_products)}개 상품 수집 완료")
        
        return total_products


async def main():
    """메인 실행 함수"""
    collector = RealWholesalerCollector()
    
    # 다양한 키워드로 테스트
    keywords = ["무선이어폰", "블루투스스피커", "스마트워치"]
    
    for keyword in keywords:
        print(f"\n{'='*60}")
        products = await collector.test_all_wholesalers(keyword)
        
        # 결과 저장
        with open(f'collected_products_{keyword}.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"\n결과가 collected_products_{keyword}.json 파일에 저장되었습니다.")
        
        # API 부하 방지를 위한 대기
        await asyncio.sleep(2)


if __name__ == "__main__":
    # BeautifulSoup 설치 확인
    try:
        import bs4
    except ImportError:
        print("BeautifulSoup4를 설치해주세요: pip install beautifulsoup4")
        exit(1)
    
    # 실행
    asyncio.run(main())