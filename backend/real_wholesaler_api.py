#!/usr/bin/env python3
"""
실제 도매처 API 구현
기존 구현을 참고하여 실제 API 연동
"""

import os
import sys
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import logging

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealOwnerClanAPI:
    """오너클랜 실제 API 연동"""
    
    def __init__(self):
        self.base_url = "https://www.ownerclan.com/V2"
        self.api_url = "https://api.ownerclan.com/v1/graphql"  # 실제 API URL 확인 필요
        self.session = None
        
        # 인증 정보 (실제 계정 필요)
        self.username = os.getenv("OWNERCLAN_USERNAME", "")
        self.password = os.getenv("OWNERCLAN_PASSWORD", "")
        self.api_key = os.getenv("OWNERCLAN_API_KEY", "")
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """상품 검색 (웹 스크래핑 또는 API)"""
        products = []
        
        # GraphQL API가 있다면 사용
        if self.api_key:
            return await self._search_via_api(keyword, limit)
        else:
            # 웹 스크래핑 (로그인 필요)
            return await self._search_via_web(keyword, limit)
            
    async def _search_via_api(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """GraphQL API를 통한 검색"""
        query = """
        query SearchProducts($keyword: String!, $first: Int!) {
            allItems(search: $keyword, first: $first) {
                edges {
                    node {
                        key
                        name
                        model
                        price
                        fixedPrice
                        stock: options {
                            quantity
                        }
                        images
                        category {
                            name
                        }
                        shippingFee
                        origin
                    }
                }
            }
        }
        """
        
        variables = {
            "keyword": keyword,
            "first": limit
        }
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
            }
            
            async with self.session.post(
                self.api_url,
                json={"query": query, "variables": variables},
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'data' in data and 'allItems' in data['data']:
                        products = []
                        for edge in data['data']['allItems']['edges']:
                            node = edge['node']
                            
                            # 재고 계산
                            total_stock = sum(opt.get('quantity', 0) for opt in node.get('stock', []))
                            
                            product = {
                                'id': node['key'],
                                'name': node['name'],
                                'model': node.get('model', ''),
                                'price': node.get('fixedPrice') or node.get('price', 0),
                                'wholesale_price': node.get('price', 0),
                                'stock': total_stock,
                                'images': node.get('images', []),
                                'category': node.get('category', {}).get('name', ''),
                                'shipping_fee': node.get('shippingFee', 0),
                                'origin': node.get('origin', ''),
                                'wholesaler': 'ownerclan',
                                'collected_at': datetime.now().isoformat()
                            }
                            products.append(product)
                            
                        logger.info(f"[오너클랜 API] {len(products)}개 상품 검색 완료")
                        return products
                else:
                    logger.error(f"[오너클랜 API] HTTP {response.status}: {await response.text()}")
                    
        except Exception as e:
            logger.error(f"[오너클랜 API] 오류: {e}")
            
        return []
        
    async def _search_via_web(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """웹 페이지를 통한 검색 (스크래핑)"""
        search_url = f"{self.base_url}/product/search.php"
        
        try:
            # 검색 요청
            params = {
                'sw': keyword,
                'page': 1
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(search_url, params=params, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # 간단한 파싱 (실제로는 BeautifulSoup 사용 권장)
                    # 여기서는 JSON 형태로 반환되는 API가 있다고 가정
                    products = self._parse_search_results(html, limit)
                    
                    logger.info(f"[오너클랜 웹] {len(products)}개 상품 검색 완료")
                    return products
                else:
                    logger.error(f"[오너클랜 웹] HTTP {response.status}")
                    
        except Exception as e:
            logger.error(f"[오너클랜 웹] 오류: {e}")
            
        return []
        
    def _parse_search_results(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """검색 결과 파싱 (실제 구현 필요)"""
        # BeautifulSoup을 사용한 실제 파싱이 필요
        # 여기서는 더미 데이터 반환
        return []


class RealDomeggookAPI:
    """도매꾹 실제 API 연동"""
    
    def __init__(self):
        self.base_url = "https://openapi.domeggook.com"
        self.api_key = os.getenv("DOMEGGOOK_API_KEY", "")
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """상품 검색"""
        products = []
        
        try:
            # 카테고리 목록 조회 (API 키 검증)
            categories = await self._get_categories()
            if not categories:
                logger.error("[도매꾹] API 키 검증 실패")
                return []
                
            # 상품 검색
            url = f"{self.base_url}/api/product/search"
            params = {
                'api_key': self.api_key,
                'version': '1.0',
                'keyword': keyword,
                'page': 1,
                'limit': limit
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('result') == 'success':
                        for item in data.get('data', {}).get('products', []):
                            product = {
                                'id': item.get('product_no', ''),
                                'name': item.get('product_name', ''),
                                'price': item.get('sale_price', 0),
                                'wholesale_price': item.get('wholesale_price', 0),
                                'stock': item.get('stock_count', 0),
                                'images': [item.get('main_image_url', '')],
                                'category': item.get('category_name', ''),
                                'brand': item.get('brand_name', ''),
                                'wholesaler': 'domeggook',
                                'collected_at': datetime.now().isoformat()
                            }
                            products.append(product)
                            
                        logger.info(f"[도매꾹] {len(products)}개 상품 검색 완료")
                    else:
                        logger.error(f"[도매꾹] API 오류: {data.get('message', 'Unknown error')}")
                else:
                    logger.error(f"[도매꾹] HTTP {response.status}")
                    
        except Exception as e:
            logger.error(f"[도매꾹] 오류: {e}")
            
        return products
        
    async def _get_categories(self) -> List[Dict[str, Any]]:
        """카테고리 목록 조회"""
        try:
            url = f"{self.base_url}/api/category/list"
            params = {
                'api_key': self.api_key,
                'version': '1.0'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('result') == 'success':
                        return data.get('data', [])
                        
        except Exception as e:
            logger.error(f"[도매꾹] 카테고리 조회 오류: {e}")
            
        return []


class RealZentradeAPI:
    """젠트레이드 실제 API 연동"""
    
    def __init__(self):
        self.base_url = "https://api.zentrade.co.kr"  # 실제 URL 확인 필요
        self.api_key = os.getenv("ZENTRADE_API_KEY", "")
        self.api_secret = os.getenv("ZENTRADE_API_SECRET", "")
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def search_products(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """상품 검색"""
        # 젠트레이드 API 구조에 맞게 구현
        # 현재는 샘플 구현
        logger.warning("[젠트레이드] API 구현 필요")
        return []


async def test_all_wholesalers(keyword: str = "이어폰"):
    """모든 도매처 테스트"""
    print("=" * 60)
    print(f"실제 도매처 API 테스트 - 검색어: '{keyword}'")
    print("=" * 60)
    
    all_products = []
    
    # 오너클랜 테스트
    print("\n[오너클랜 테스트]")
    async with RealOwnerClanAPI() as api:
        products = await api.search_products(keyword, limit=5)
        print(f"결과: {len(products)}개 상품")
        if products:
            print(f"첫 번째 상품: {json.dumps(products[0], indent=2, ensure_ascii=False)}")
        all_products.extend(products)
        
    # 도매꾹 테스트
    print("\n[도매꾹 테스트]")
    async with RealDomeggookAPI() as api:
        products = await api.search_products(keyword, limit=5)
        print(f"결과: {len(products)}개 상품")
        if products:
            print(f"첫 번째 상품: {json.dumps(products[0], indent=2, ensure_ascii=False)}")
        all_products.extend(products)
        
    # 젠트레이드 테스트
    print("\n[젠트레이드 테스트]")
    async with RealZentradeAPI() as api:
        products = await api.search_products(keyword, limit=5)
        print(f"결과: {len(products)}개 상품")
        if products:
            print(f"첫 번째 상품: {json.dumps(products[0], indent=2, ensure_ascii=False)}")
        all_products.extend(products)
        
    # 결과 저장
    print(f"\n총 {len(all_products)}개 상품 수집 완료")
    
    with open('real_wholesaler_products.json', 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
        
    print("\n결과가 real_wholesaler_products.json 파일에 저장되었습니다.")
    
    return all_products


async def integrate_with_backend():
    """백엔드 시스템과 통합"""
    from app.services.database import db_manager
    from app.models.product import Product
    from app.models.collected_product import CollectedProduct
    
    # 상품 수집
    products = await test_all_wholesalers("무선이어폰")
    
    # 데이터베이스에 저장
    async with db_manager.get_session() as session:
        for product_data in products:
            # CollectedProduct에 저장
            collected_product = CollectedProduct(
                wholesaler=product_data['wholesaler'],
                wholesaler_product_id=product_data['id'],
                name=product_data['name'],
                price=product_data['price'],
                wholesale_price=product_data.get('wholesale_price', product_data['price']),
                stock_quantity=product_data.get('stock', 0),
                main_image_url=product_data['images'][0] if product_data['images'] else None,
                category=product_data.get('category', ''),
                raw_data=json.dumps(product_data),
                last_collected_at=datetime.now()
            )
            
            session.add(collected_product)
            
        await session.commit()
        
    print(f"\n{len(products)}개 상품이 데이터베이스에 저장되었습니다.")


if __name__ == "__main__":
    # 환경 변수 확인
    print("환경 변수 확인:")
    print(f"- OWNERCLAN_API_KEY: {'설정됨' if os.getenv('OWNERCLAN_API_KEY') else '미설정'}")
    print(f"- DOMEGGOOK_API_KEY: {'설정됨' if os.getenv('DOMEGGOOK_API_KEY') else '미설정'}")
    print(f"- ZENTRADE_API_KEY: {'설정됨' if os.getenv('ZENTRADE_API_KEY') else '미설정'}")
    
    # API 테스트 실행
    asyncio.run(test_all_wholesalers())