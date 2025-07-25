"""마켓플레이스 판매 데이터 수집 서비스 (벤치마크 테이블 연동)"""
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup
import json
from sqlalchemy.orm import Session

from ...models.market import MarketProduct, MarketSalesData, MarketCategory
from ...models.benchmark import BenchmarkProduct, BenchmarkPriceHistory, BenchmarkKeyword
from ...services.benchmark.benchmark_manager import BenchmarkManager
from ...models.base import Base
from ...core.config import settings


class MarketDataCollector:
    """마켓플레이스 데이터 수집기 (벤치마크 테이블 통합)"""
    
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.session = None
        self.benchmark_manager = BenchmarkManager(db)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def collect_all_markets(self) -> Dict[str, Any]:
        """모든 마켓플레이스 데이터 수집"""
        results = {
            'coupang': await self.collect_coupang_bestsellers(),
            'naver': await self.collect_naver_bestsellers(),
            '11st': await self.collect_11st_bestsellers()
        }
        
        # 수집된 데이터 분석
        analysis = await self._analyze_collected_data(results)
        
        return {
            'collected_at': datetime.now(),
            'market_data': results,
            'analysis': analysis
        }
        
    async def collect_coupang_bestsellers(self, categories: List[str] = None) -> List[Dict[str, Any]]:
        """쿠팡 베스트셀러 데이터 수집"""
        if not categories:
            # 초보 셀러를 위한 추천 카테고리
            categories = [
                '패션의류', '뷰티', '식품', '생활용품', 
                '디지털/가전', '스포츠/레저', '완구/취미'
            ]
            
        all_products = []
        
        for category in categories:
            try:
                products = await self._scrape_coupang_category(category)
                
                # 데이터 정규화 및 저장
                for rank, product in enumerate(products, 1):
                    normalized = {
                        'product_id': product.get('product_id', ''),
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'main_category': category,
                        'sub_category': product.get('sub_category', ''),
                        'original_price': self._parse_price(product.get('original_price', 0)),
                        'sale_price': self._parse_price(product.get('price', 0)),
                        'discount_rate': product.get('discount_rate', 0),
                        'delivery_fee': product.get('delivery_fee', 0),
                        'review_count': product.get('review_count', 0),
                        'rating': product.get('rating', 0),
                        'monthly_sales': self._estimate_sales(product),
                        'bestseller_rank': rank,
                        'seller_name': product.get('seller_name', ''),
                        'seller_grade': product.get('seller_grade', ''),
                        'is_power_seller': product.get('is_rocket', False),
                        'keywords': self._extract_keywords(product.get('name', '')),
                        'options': product.get('options', []),
                        'attributes': {
                            'is_rocket': product.get('is_rocket', False),
                            'is_fresh': product.get('is_fresh', False),
                            'has_coupon': product.get('has_coupon', False)
                        }
                    }
                    
                    all_products.append(normalized)
                    
                    # 벤치마크 테이블에 저장
                    await self.benchmark_manager.save_product_data(normalized, 'coupang')
                    
            except Exception as e:
                self.logger.error(f"쿠팡 {category} 수집 실패: {str(e)}")
                
        return all_products
        
    async def collect_naver_bestsellers(self, categories: List[str] = None) -> List[Dict[str, Any]]:
        """네이버 쇼핑 베스트셀러 데이터 수집"""
        if not categories:
            categories = [
                '패션잡화', '화장품/미용', '식품', '생활/건강',
                '디지털/가전', '스포츠/레저', '출산/육아'
            ]
            
        all_products = []
        
        # 네이버 쇼핑 인사이트 API 활용 (가능한 경우)
        for category in categories:
            try:
                products = await self._fetch_naver_shopping_data(category)
                
                for rank, product in enumerate(products, 1):
                    normalized = {
                        'product_id': product.get('productId', ''),
                        'name': product.get('title', ''),
                        'brand': product.get('brand', ''),
                        'main_category': category,
                        'sub_category': product.get('category2', ''),
                        'original_price': self._parse_price(product.get('hprice', 0)),
                        'sale_price': self._parse_price(product.get('lprice', 0)),
                        'discount_rate': self._calculate_discount_rate(
                            product.get('hprice', 0), 
                            product.get('lprice', 0)
                        ),
                        'delivery_fee': 0,  # 네이버는 판매처별로 다름
                        'review_count': product.get('reviewCount', 0),
                        'rating': 0,  # 네이버는 평점 제공 안함
                        'monthly_sales': product.get('purchaseCnt', 0) * 30,  # 구매수 기반 추정
                        'bestseller_rank': rank,
                        'seller_name': '',  # 여러 판매처
                        'seller_grade': '',
                        'is_power_seller': False,
                        'keywords': self._extract_keywords(product.get('title', '')),
                        'options': [],
                        'attributes': {
                            'mall_count': product.get('mallCount', 0),
                            'maker': product.get('maker', ''),
                            'category1': product.get('category1', ''),
                            'category2': product.get('category2', ''),
                            'category3': product.get('category3', ''),
                            'category4': product.get('category4', '')
                        }
                    }
                    
                    all_products.append(normalized)
                    
                    # 벤치마크 테이블에 저장
                    await self.benchmark_manager.save_product_data(normalized, 'naver')
                    
            except Exception as e:
                self.logger.error(f"네이버 {category} 수집 실패: {str(e)}")
                
        return all_products
        
    async def collect_11st_bestsellers(self, categories: List[str] = None) -> List[Dict[str, Any]]:
        """11번가 베스트셀러 데이터 수집"""
        if not categories:
            categories = [
                '패션', '뷰티', '식품/건강', '생활/가전',
                '디지털', '스포츠/자동차', '유아'
            ]
            
        all_products = []
        
        for category in categories:
            try:
                products = await self._scrape_11st_category(category)
                
                for rank, product in enumerate(products, 1):
                    normalized = {
                        'product_id': product.get('product_no', ''),
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'main_category': category,
                        'sub_category': product.get('sub_category', ''),
                        'original_price': self._parse_price(product.get('original_price', 0)),
                        'sale_price': self._parse_price(product.get('price', 0)),
                        'discount_rate': product.get('discount', 0),
                        'delivery_fee': self._parse_price(product.get('delivery_fee', 0)),
                        'review_count': product.get('review_count', 0),
                        'rating': product.get('rating', 0),
                        'monthly_sales': self._estimate_sales(product),
                        'bestseller_rank': rank,
                        'seller_name': product.get('seller_name', ''),
                        'seller_grade': product.get('seller_grade', ''),
                        'is_power_seller': product.get('is_best_shop', False),
                        'keywords': self._extract_keywords(product.get('name', '')),
                        'options': product.get('options', []),
                        'attributes': {
                            'delivery_type': product.get('delivery', ''),
                            'is_shocking_deal': product.get('is_shocking_deal', False),
                            'benefit_badge': product.get('benefit_badge', [])
                        }
                    }
                    
                    all_products.append(normalized)
                    
                    # 벤치마크 테이블에 저장
                    await self.benchmark_manager.save_product_data(normalized, '11st')
                    
            except Exception as e:
                self.logger.error(f"11번가 {category} 수집 실패: {str(e)}")
                
        return all_products
        
    async def _scrape_coupang_category(self, category: str) -> List[Dict[str, Any]]:
        """쿠팡 카테고리별 베스트셀러 스크래핑"""
        # 실제 구현 시에는 적절한 스크래핑 방법 사용
        # 여기서는 예시 구조만 제공
        products = []
        
        # 쿠팡 베스트셀러 URL 구성
        category_map = {
            '패션의류': '1001',
            '뷰티': '1002',
            '식품': '1003',
            # ... 카테고리 매핑
        }
        
        # 스크래핑 로직 (실제로는 더 복잡함)
        # products = await self._scrape_page(url)
        
        return products
        
    async def _fetch_naver_shopping_data(self, category: str) -> List[Dict[str, Any]]:
        """네이버 쇼핑 API를 통한 데이터 수집"""
        # 네이버 쇼핑 API 활용
        # 실제 구현 시 API 키 필요
        products = []
        
        return products
        
    async def _scrape_11st_category(self, category: str) -> List[Dict[str, Any]]:
        """11번가 카테고리별 베스트셀러 스크래핑"""
        products = []
        
        return products
        
    def _parse_price(self, price_str: Any) -> int:
        """가격 문자열을 정수로 변환"""
        if isinstance(price_str, (int, float)):
            return int(price_str)
            
        # 문자열에서 숫자만 추출
        import re
        numbers = re.findall(r'\d+', str(price_str))
        if numbers:
            return int(''.join(numbers))
        return 0
        
    def _calculate_discount_rate(self, original: Any, sale: Any) -> float:
        """할인율 계산"""
        original_price = self._parse_price(original)
        sale_price = self._parse_price(sale)
        
        if original_price > 0 and sale_price < original_price:
            return round((original_price - sale_price) / original_price * 100, 1)
        return 0.0
        
    def _estimate_sales(self, product: Dict[str, Any]) -> int:
        """리뷰 수와 평점을 기반으로 월 판매량 추정"""
        review_count = product.get('review_count', 0)
        rating = product.get('rating', 0)
        
        # 간단한 추정 공식 (실제로는 더 정교한 모델 필요)
        if review_count == 0:
            return 0
            
        # 리뷰 작성률을 5%로 가정
        estimated_sales = review_count * 20
        
        # 평점에 따른 보정
        if rating >= 4.5:
            estimated_sales *= 1.2
        elif rating < 3.5:
            estimated_sales *= 0.8
            
        return int(estimated_sales)
        
    def _extract_keywords(self, product_name: str) -> List[str]:
        """상품명에서 키워드 추출"""
        import re
        # 특수문자 제거
        clean_name = re.sub(r'[^\w\s]', ' ', product_name)
        # 단어 분리
        words = clean_name.split()
        # 2글자 이상 키워드만 추출
        keywords = [w.lower() for w in words if len(w) >= 2]
        # 중복 제거
        return list(set(keywords))[:10]  # 최대 10개
        
    async def _analyze_collected_data(self, market_data: Dict[str, List]) -> Dict[str, Any]:
        """수집된 데이터 분석"""
        total_products = sum(len(products) for products in market_data.values())
        
        # 카테고리별 베스트 상품
        category_best = {}
        for market, products in market_data.items():
            for product in products[:10]:  # 상위 10개만
                category = product.get('main_category', 'Unknown')
                if category not in category_best:
                    category_best[category] = []
                category_best[category].append({
                    'market': market,
                    'name': product.get('name', ''),
                    'price': product.get('sale_price', 0),
                    'sales': product.get('monthly_sales', 0)
                })
        
        # 가격대별 분포
        price_ranges = {
            'under_10k': 0,
            '10k_30k': 0,
            '30k_50k': 0,
            '50k_100k': 0,
            'over_100k': 0
        }
        
        for products in market_data.values():
            for product in products:
                price = product.get('sale_price', 0)
                if price < 10000:
                    price_ranges['under_10k'] += 1
                elif price < 30000:
                    price_ranges['10k_30k'] += 1
                elif price < 50000:
                    price_ranges['30k_50k'] += 1
                elif price < 100000:
                    price_ranges['50k_100k'] += 1
                else:
                    price_ranges['over_100k'] += 1
        
        return {
            'total_products_collected': total_products,
            'category_best_products': category_best,
            'price_distribution': price_ranges,
            'collection_timestamp': datetime.now()
        }