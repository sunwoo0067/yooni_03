"""Coupang marketplace data collector"""
import hashlib
import hmac
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import structlog

from .base_collector import BaseCollector

logger = structlog.get_logger()


class CoupangCollector(BaseCollector):
    """Collector for Coupang marketplace data"""
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare Coupang API headers with HMAC authentication"""
        return {
            'Content-Type': 'application/json',
            'User-Agent': 'DropshipAI/1.0'
        }
    
    def _generate_hmac_signature(self, method: str, url: str, params: Dict = None) -> str:
        """Generate HMAC signature for Coupang API"""
        # Coupang HMAC authentication implementation
        datetime_str = datetime.utcnow().strftime('%y%m%d')
        message = f"{datetime_str}{method}{url}"
        
        if params:
            message += urlencode(sorted(params.items()))
        
        signature = hmac.new(
            self.config['secret_key'].encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def collect_product_info(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Collect detailed product information from Coupang"""
        products = []
        
        for product_id in product_ids:
            try:
                endpoint = f"/v2/providers/affiliate_open_api/apis/openapi/products/{product_id}"
                
                # Add authentication
                self.headers['Authorization'] = f"CEA algorithm=HmacSHA256, access-key={self.config['api_key']}, signed-date={datetime.utcnow().strftime('%y%m%d')}, signature={self._generate_hmac_signature('GET', endpoint)}"
                
                response = await self._make_request('GET', endpoint)
                data = response.json()
                
                # Parse Coupang specific data
                product_info = {
                    'marketplace': 'coupang',
                    'product_id': product_id,
                    'name': data.get('productName'),
                    'price': self._parse_price(str(data.get('salePrice', 0))),
                    'original_price': self._parse_price(str(data.get('originalPrice', 0))),
                    'discount_rate': data.get('discountRate', 0),
                    'rating': data.get('ratingInfo', {}).get('rating', 0),
                    'review_count': data.get('ratingInfo', {}).get('ratingCount', 0),
                    'is_rocket': data.get('isRocket', False),
                    'is_free_shipping': data.get('isFreeShipping', False),
                    'category': data.get('categoryName'),
                    'brand': data.get('brand'),
                    'images': data.get('productImage', []),
                    'options': data.get('productOptions', []),
                    'collected_at': datetime.utcnow().isoformat()
                }
                
                products.append(product_info)
                
                # Save raw data
                await self.save_raw_data(endpoint, data)
                
            except Exception as e:
                logger.error(
                    "coupang_product_collection_failed",
                    product_id=product_id,
                    error=str(e)
                )
                continue
        
        return products
    
    async def collect_reviews(self, product_id: str, page: int = 1) -> Dict[str, Any]:
        """Collect product reviews from Coupang"""
        endpoint = f"/v2/providers/affiliate_open_api/apis/openapi/products/{product_id}/reviews"
        params = {
            'page': page,
            'size': 50,
            'sortBy': 'DATE_DESC'
        }
        
        try:
            response = await self._make_request('GET', endpoint, params=params)
            data = response.json()
            
            reviews = []
            for review_data in data.get('data', []):
                review = {
                    'review_id': review_data.get('reviewId'),
                    'rating': review_data.get('rating'),
                    'title': review_data.get('reviewTitle'),
                    'content': review_data.get('reviewContent'),
                    'reviewer_name': review_data.get('writerMemberId', '').replace(review_data.get('writerMemberId', '')[2:-2], '***') if review_data.get('writerMemberId') else 'Anonymous',
                    'purchase_option': review_data.get('purchaseOption'),
                    'verified_purchase': True,  # Coupang only shows verified purchases
                    'helpful_count': review_data.get('helpfulCount', 0),
                    'images': review_data.get('reviewImages', []),
                    'created_at': review_data.get('createdAt')
                }
                reviews.append(review)
            
            result = {
                'product_id': product_id,
                'total_count': data.get('totalCount', 0),
                'page': page,
                'reviews': reviews
            }
            
            # Save raw data
            await self.save_raw_data(endpoint, data)
            
            return result
            
        except Exception as e:
            logger.error(
                "coupang_review_collection_failed",
                product_id=product_id,
                error=str(e)
            )
            return {'product_id': product_id, 'reviews': [], 'error': str(e)}
    
    async def collect_rankings(self, category_id: str) -> List[Dict[str, Any]]:
        """Collect category rankings from Coupang"""
        endpoint = f"/v2/providers/affiliate_open_api/apis/openapi/categories/{category_id}/products"
        params = {
            'limit': 100,
            'subId': 'dropship-ai'
        }
        
        try:
            response = await self._make_request('GET', endpoint, params=params)
            data = response.json()
            
            rankings = []
            for idx, product in enumerate(data.get('data', []), 1):
                ranking_info = {
                    'rank': idx,
                    'product_id': product.get('productId'),
                    'product_name': product.get('productName'),
                    'price': self._parse_price(str(product.get('salePrice', 0))),
                    'rating': product.get('productRating', 0),
                    'review_count': product.get('reviewCount', 0),
                    'is_rocket': product.get('isRocket', False),
                    'category_id': category_id,
                    'collected_at': datetime.utcnow().isoformat()
                }
                rankings.append(ranking_info)
            
            # Save raw data
            await self.save_raw_data(endpoint, data)
            
            return rankings
            
        except Exception as e:
            logger.error(
                "coupang_ranking_collection_failed",
                category_id=category_id,
                error=str(e)
            )
            return []
    
    async def collect_search_data(self, keywords: List[str]) -> Dict[str, Any]:
        """Collect search result data from Coupang"""
        search_results = {}
        
        for keyword in keywords:
            endpoint = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
            params = {
                'keyword': keyword,
                'limit': 50,
                'subId': 'dropship-ai'
            }
            
            try:
                response = await self._make_request('GET', endpoint, params=params)
                data = response.json()
                
                products = []
                for idx, product in enumerate(data.get('data', []), 1):
                    product_info = {
                        'search_rank': idx,
                        'product_id': product.get('productId'),
                        'product_name': product.get('productName'),
                        'price': self._parse_price(str(product.get('salePrice', 0))),
                        'rating': product.get('productRating', 0),
                        'review_count': product.get('reviewCount', 0),
                        'is_rocket': product.get('isRocket', False),
                        'is_ad': product.get('isAd', False)
                    }
                    products.append(product_info)
                
                search_results[keyword] = {
                    'total_count': data.get('totalCount', 0),
                    'products': products,
                    'collected_at': datetime.utcnow().isoformat()
                }
                
                # Save raw data
                await self.save_raw_data(f"{endpoint}?keyword={keyword}", data)
                
            except Exception as e:
                logger.error(
                    "coupang_search_collection_failed",
                    keyword=keyword,
                    error=str(e)
                )
                search_results[keyword] = {'error': str(e)}
        
        return search_results
    
    async def collect_competitor_data(self, product_id: str) -> List[Dict[str, Any]]:
        """Collect competitor product data"""
        # Get product info first to identify category
        product_info = await self.collect_product_info([product_id])
        if not product_info:
            return []
        
        category_id = product_info[0].get('category_id')
        if not category_id:
            return []
        
        # Get products from same category
        rankings = await self.collect_rankings(category_id)
        
        # Filter competitors (exclude our product)
        competitors = [
            product for product in rankings 
            if product['product_id'] != product_id
        ][:10]  # Top 10 competitors
        
        return competitors