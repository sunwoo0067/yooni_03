"""Naver Shopping marketplace data collector"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog
from urllib.parse import quote

from .base_collector import BaseCollector

logger = structlog.get_logger()


class NaverCollector(BaseCollector):
    """Collector for Naver Shopping marketplace data"""
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare Naver API headers"""
        return {
            'X-Naver-Client-Id': self.config['client_id'],
            'X-Naver-Client-Secret': self.config['client_secret'],
            'Content-Type': 'application/json'
        }
    
    async def collect_product_info(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Collect detailed product information from Naver"""
        products = []
        
        for product_id in product_ids:
            try:
                # Naver uses different API structure - search by product ID
                endpoint = f"/v1/search/shop.json"
                params = {
                    'query': product_id,
                    'display': 10,
                    'sort': 'sim'  # similarity
                }
                
                response = await self._make_request('GET', endpoint, params=params)
                data = response.json()
                
                # Find exact match by product ID
                product_data = None
                for item in data.get('items', []):
                    if item.get('productId') == product_id:
                        product_data = item
                        break
                
                if not product_data:
                    continue
                
                # Parse Naver specific data
                product_info = {
                    'marketplace': 'naver',
                    'product_id': product_id,
                    'name': product_data.get('title').replace('<b>', '').replace('</b>', ''),
                    'link': product_data.get('link'),
                    'image': product_data.get('image'),
                    'price': self._parse_price(product_data.get('lprice', '0')),
                    'high_price': self._parse_price(product_data.get('hprice', '0')),
                    'mall_name': product_data.get('mallName'),
                    'brand': product_data.get('brand'),
                    'maker': product_data.get('maker'),
                    'category1': product_data.get('category1'),
                    'category2': product_data.get('category2'),
                    'category3': product_data.get('category3'),
                    'category4': product_data.get('category4'),
                    'product_type': product_data.get('productType'),
                    'collected_at': datetime.utcnow().isoformat()
                }
                
                products.append(product_info)
                
                # Save raw data
                await self.save_raw_data(endpoint, product_data)
                
            except Exception as e:
                logger.error(
                    "naver_product_collection_failed",
                    product_id=product_id,
                    error=str(e)
                )
                continue
        
        return products
    
    async def collect_reviews(self, product_id: str, page: int = 1) -> Dict[str, Any]:
        """Collect product reviews from Naver"""
        # Note: Naver Shopping API doesn't provide direct review access
        # This would require web scraping or partner API access
        endpoint = f"/shopping/v1/products/{product_id}/reviews"
        
        try:
            # This is a placeholder - actual implementation would need proper API access
            logger.warning(
                "naver_review_api_not_available",
                product_id=product_id,
                message="Naver Shopping API doesn't provide review data. Consider web scraping."
            )
            
            return {
                'product_id': product_id,
                'total_count': 0,
                'page': page,
                'reviews': [],
                'note': 'Review data requires web scraping or partner API'
            }
            
        except Exception as e:
            logger.error(
                "naver_review_collection_failed",
                product_id=product_id,
                error=str(e)
            )
            return {'product_id': product_id, 'reviews': [], 'error': str(e)}
    
    async def collect_rankings(self, category_id: str) -> List[Dict[str, Any]]:
        """Collect category rankings from Naver"""
        endpoint = "/v1/search/shop.json"
        
        # Map category_id to Naver category query
        category_map = {
            'fashion': '패션의류',
            'beauty': '화장품/미용',
            'digital': '디지털/가전',
            'food': '식품',
            'living': '생활/건강'
        }
        
        query = category_map.get(category_id, category_id)
        
        params = {
            'query': query,
            'display': 100,  # max 100
            'sort': 'review'  # sort by review count (popularity)
        }
        
        try:
            response = await self._make_request('GET', endpoint, params=params)
            data = response.json()
            
            rankings = []
            for idx, item in enumerate(data.get('items', []), 1):
                ranking_info = {
                    'rank': idx,
                    'product_id': item.get('productId'),
                    'product_name': item.get('title').replace('<b>', '').replace('</b>', ''),
                    'price': self._parse_price(item.get('lprice', '0')),
                    'mall_name': item.get('mallName'),
                    'review_count': item.get('reviewCount', 0),
                    'category': query,
                    'category_id': category_id,
                    'collected_at': datetime.utcnow().isoformat()
                }
                rankings.append(ranking_info)
            
            # Save raw data
            await self.save_raw_data(endpoint, data)
            
            return rankings
            
        except Exception as e:
            logger.error(
                "naver_ranking_collection_failed",
                category_id=category_id,
                error=str(e)
            )
            return []
    
    async def collect_search_data(self, keywords: List[str]) -> Dict[str, Any]:
        """Collect search result data from Naver"""
        search_results = {}
        
        for keyword in keywords:
            endpoint = "/v1/search/shop.json"
            params = {
                'query': keyword,
                'display': 50,
                'sort': 'review'  # sort by popularity
            }
            
            try:
                response = await self._make_request('GET', endpoint, params=params)
                data = response.json()
                
                products = []
                for idx, item in enumerate(data.get('items', []), 1):
                    product_info = {
                        'search_rank': idx,
                        'product_id': item.get('productId'),
                        'product_name': item.get('title').replace('<b>', '').replace('</b>', ''),
                        'link': item.get('link'),
                        'image': item.get('image'),
                        'price': self._parse_price(item.get('lprice', '0')),
                        'mall_name': item.get('mallName'),
                        'product_type': item.get('productType')
                    }
                    products.append(product_info)
                
                search_results[keyword] = {
                    'total_count': data.get('total', 0),
                    'products': products,
                    'collected_at': datetime.utcnow().isoformat()
                }
                
                # Save raw data
                await self.save_raw_data(f"{endpoint}?query={keyword}", data)
                
            except Exception as e:
                logger.error(
                    "naver_search_collection_failed",
                    keyword=keyword,
                    error=str(e)
                )
                search_results[keyword] = {'error': str(e)}
        
        return search_results
    
    async def collect_trend_data(self) -> Dict[str, Any]:
        """Collect trending search keywords from Naver"""
        endpoint = "/v1/datalab/shopping/categories"
        
        try:
            # Get trending categories
            body = {
                "startDate": (datetime.utcnow().replace(day=1)).strftime("%Y-%m-%d"),
                "endDate": datetime.utcnow().strftime("%Y-%m-%d"),
                "timeUnit": "date",
                "categories": [
                    {"name": "패션의류", "param": ["50000000"]},
                    {"name": "화장품/미용", "param": ["50000002"]},
                    {"name": "디지털/가전", "param": ["50000003"]},
                    {"name": "식품", "param": ["50000006"]},
                    {"name": "생활/건강", "param": ["50000008"]}
                ]
            }
            
            response = await self._make_request('POST', endpoint, json=body)
            data = response.json()
            
            # Save raw data
            await self.save_raw_data(endpoint, data)
            
            return data
            
        except Exception as e:
            logger.error("naver_trend_collection_failed", error=str(e))
            return {'error': str(e)}
    
    async def collect_price_comparison(self, product_name: str) -> List[Dict[str, Any]]:
        """Collect price comparison data across different sellers"""
        endpoint = "/v1/search/shop.json"
        params = {
            'query': product_name,
            'display': 100,
            'sort': 'asc'  # sort by price ascending
        }
        
        try:
            response = await self._make_request('GET', endpoint, params=params)
            data = response.json()
            
            price_comparison = []
            for item in data.get('items', []):
                seller_info = {
                    'product_id': item.get('productId'),
                    'product_name': item.get('title').replace('<b>', '').replace('</b>', ''),
                    'mall_name': item.get('mallName'),
                    'price': self._parse_price(item.get('lprice', '0')),
                    'delivery_fee': 0,  # Not provided by API
                    'total_price': self._parse_price(item.get('lprice', '0')),
                    'link': item.get('link')
                }
                price_comparison.append(seller_info)
            
            # Sort by total price
            price_comparison.sort(key=lambda x: x['total_price'])
            
            return price_comparison
            
        except Exception as e:
            logger.error(
                "naver_price_comparison_failed",
                product_name=product_name,
                error=str(e)
            )
            return []