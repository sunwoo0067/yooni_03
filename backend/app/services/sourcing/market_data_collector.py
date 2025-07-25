"""마켓플레이스 판매 데이터 수집 서비스"""
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup
import json
from sqlalchemy.orm import Session

from ...models.market import MarketProduct, MarketSalesData, MarketCategory
from ...models.base import Base
from ...core.config import settings


class MarketDataCollector:
    """마켓플레이스 데이터 수집기"""
    
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.session = None
        
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
                        'marketplace': 'coupang',
                        'category': category,
                        'rank': rank,
                        'product_name': product.get('name', ''),
                        'price': self._parse_price(product.get('price', 0)),
                        'original_price': self._parse_price(product.get('original_price', 0)),
                        'discount_rate': product.get('discount_rate', 0),
                        'review_count': product.get('review_count', 0),
                        'rating': product.get('rating', 0),
                        'is_rocket': product.get('is_rocket', False),
                        'monthly_sales': self._estimate_sales(product),
                        'collected_at': datetime.now()
                    }
                    
                    all_products.append(normalized)
                    await self._save_market_product(normalized)
                    
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
                        'marketplace': 'naver',
                        'category': category,
                        'rank': rank,
                        'product_name': product.get('title', ''),
                        'price': self._parse_price(product.get('lprice', 0)),
                        'mall_count': product.get('mallCount', 0),
                        'review_count': product.get('reviewCount', 0),
                        'purchase_count': product.get('purchaseCnt', 0),
                        'product_id': product.get('productId', ''),
                        'brand': product.get('brand', ''),
                        'maker': product.get('maker', ''),
                        'collected_at': datetime.now()
                    }
                    
                    all_products.append(normalized)
                    await self._save_market_product(normalized)
                    
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
                        'marketplace': '11st',
                        'category': category,
                        'rank': rank,
                        'product_name': product.get('name', ''),
                        'price': self._parse_price(product.get('price', 0)),
                        'discount_rate': product.get('discount', 0),
                        'review_count': product.get('review_count', 0),
                        'rating': product.get('rating', 0),
                        'seller_grade': product.get('seller_grade', ''),
                        'delivery_type': product.get('delivery', ''),
                        'collected_at': datetime.now()
                    }
                    
                    all_products.append(normalized)
                    await self._save_market_product(normalized)
                    
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
        
    async def _save_market_product(self, product_data: Dict[str, Any]):
        """마켓 상품 데이터 저장"""
        try:
            market_product = MarketProduct(
                marketplace=product_data['marketplace'],
                category=product_data['category'],
                rank=product_data['rank'],
                product_name=product_data['product_name'],
                price=product_data.get('price', 0),
                review_count=product_data.get('review_count', 0),
                rating=product_data.get('rating', 0),
                raw_data=product_data,
                collected_at=product_data['collected_at']
            )
            
            self.db.add(market_product)
            self.db.commit()
            
            # 판매 데이터 추적
            sales_data = MarketSalesData(
                market_product_id=market_product.id,
                estimated_monthly_sales=product_data.get('monthly_sales', 0),
                price=product_data.get('price', 0),
                discount_rate=product_data.get('discount_rate', 0),
                recorded_at=datetime.now()
            )
            
            self.db.add(sales_data)
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"상품 데이터 저장 실패: {str(e)}")
            self.db.rollback()
            
    async def _analyze_collected_data(self, market_data: Dict[str, List]) -> Dict[str, Any]:
        """수집된 데이터 분석"""
        analysis = {
            'total_products': 0,
            'top_categories': {},
            'price_ranges': {},
            'high_potential_products': [],
            'market_trends': {}
        }
        
        # 전체 상품 수 계산
        for market, products in market_data.items():
            analysis['total_products'] += len(products)
            
            # 카테고리별 분석
            category_stats = {}
            for product in products:
                category = product.get('category', 'unknown')
                if category not in category_stats:
                    category_stats[category] = {
                        'count': 0,
                        'avg_price': 0,
                        'avg_review': 0,
                        'top_product': None
                    }
                    
                stats = category_stats[category]
                stats['count'] += 1
                stats['avg_price'] += product.get('price', 0)
                stats['avg_review'] += product.get('review_count', 0)
                
                # 최고 순위 상품
                if not stats['top_product'] or product.get('rank', 999) < stats['top_product'].get('rank', 999):
                    stats['top_product'] = product
                    
            # 평균 계산
            for category, stats in category_stats.items():
                if stats['count'] > 0:
                    stats['avg_price'] /= stats['count']
                    stats['avg_review'] /= stats['count']
                    
            analysis['top_categories'][market] = category_stats
            
        # 고잠재력 상품 식별
        analysis['high_potential_products'] = await self._identify_high_potential_products(market_data)
        
        return analysis
        
    async def _identify_high_potential_products(self, market_data: Dict[str, List]) -> List[Dict[str, Any]]:
        """고잠재력 상품 식별"""
        potential_products = []
        
        for market, products in market_data.items():
            for product in products:
                score = 0
                
                # 순위 점수 (1-10위: 10점, 11-20위: 8점...)
                rank = product.get('rank', 100)
                if rank <= 10:
                    score += 10
                elif rank <= 20:
                    score += 8
                elif rank <= 50:
                    score += 5
                elif rank <= 100:
                    score += 3
                    
                # 리뷰 수 점수
                reviews = product.get('review_count', 0)
                if reviews >= 1000:
                    score += 8
                elif reviews >= 500:
                    score += 6
                elif reviews >= 100:
                    score += 4
                elif reviews >= 50:
                    score += 2
                    
                # 가격대 점수 (중저가 선호)
                price = product.get('price', 0)
                if 10000 <= price <= 50000:
                    score += 5
                elif 5000 <= price < 10000:
                    score += 4
                elif 50000 < price <= 100000:
                    score += 3
                    
                # 할인율 점수
                discount = product.get('discount_rate', 0)
                if discount >= 30:
                    score += 3
                elif discount >= 20:
                    score += 2
                elif discount >= 10:
                    score += 1
                    
                # 평점 점수
                rating = product.get('rating', 0)
                if rating >= 4.5:
                    score += 5
                elif rating >= 4.0:
                    score += 3
                elif rating >= 3.5:
                    score += 1
                    
                product['potential_score'] = score
                
                # 점수가 15점 이상인 상품을 고잠재력으로 분류
                if score >= 15:
                    potential_products.append(product)
                    
        # 점수 순으로 정렬
        potential_products.sort(key=lambda x: x['potential_score'], reverse=True)
        
        return potential_products[:50]  # 상위 50개 반환
        
    async def track_product_history(self, product_id: str, marketplace: str) -> Dict[str, Any]:
        """특정 상품의 이력 추적"""
        history = self.db.query(MarketSalesData).join(
            MarketProduct
        ).filter(
            MarketProduct.product_id == product_id,
            MarketProduct.marketplace == marketplace
        ).order_by(
            MarketSalesData.recorded_at.desc()
        ).limit(30).all()  # 최근 30일
        
        if not history:
            return {}
            
        return {
            'product_id': product_id,
            'marketplace': marketplace,
            'price_trend': [{'date': h.recorded_at, 'price': h.price} for h in history],
            'sales_trend': [{'date': h.recorded_at, 'sales': h.estimated_monthly_sales} for h in history],
            'avg_price': sum(h.price for h in history) / len(history),
            'price_volatility': self._calculate_volatility([h.price for h in history]),
            'growth_rate': self._calculate_growth_rate(history)
        }
        
    def _calculate_volatility(self, prices: List[float]) -> float:
        """가격 변동성 계산"""
        if len(prices) < 2:
            return 0
            
        import numpy as np
        return float(np.std(prices) / np.mean(prices) * 100)
        
    def _calculate_growth_rate(self, history: List) -> float:
        """성장률 계산"""
        if len(history) < 2:
            return 0
            
        initial_sales = history[-1].estimated_monthly_sales or 1
        current_sales = history[0].estimated_monthly_sales or 1
        
        return ((current_sales - initial_sales) / initial_sales) * 100