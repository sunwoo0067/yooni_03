"""Base collector class for marketplace data collection"""
import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ..database.models import MarketRawData
from ..utils.rate_limiter import RateLimiter

logger = structlog.get_logger()


class BaseCollector(ABC):
    """Abstract base class for marketplace data collectors"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.marketplace_name = self.__class__.__name__.replace('Collector', '').lower()
        self.rate_limiter = RateLimiter(
            max_calls=config.get('rate_limit', 60),
            time_window=60  # 1 minute
        )
        self.client = None
        self.headers = self._prepare_headers()
    
    @abstractmethod
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare API headers including authentication"""
        pass
    
    @abstractmethod
    async def collect_product_info(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Collect detailed product information"""
        pass
    
    @abstractmethod
    async def collect_reviews(self, product_id: str, page: int = 1) -> Dict[str, Any]:
        """Collect product reviews"""
        pass
    
    @abstractmethod
    async def collect_rankings(self, category_id: str) -> List[Dict[str, Any]]:
        """Collect category rankings"""
        pass
    
    @abstractmethod
    async def collect_search_data(self, keywords: List[str]) -> Dict[str, Any]:
        """Collect search result data"""
        pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=self.config.get('timeout', 30),
            follow_redirects=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic"""
        await self.rate_limiter.acquire()
        
        url = f"{self.config['base_url']}{endpoint}"
        
        logger.info(
            "making_api_request",
            marketplace=self.marketplace_name,
            method=method,
            endpoint=endpoint
        )
        
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        
        return response
    
    async def save_raw_data(
        self, 
        endpoint: str, 
        data: Dict[str, Any]
    ) -> MarketRawData:
        """Save raw API response to database"""
        raw_data = MarketRawData(
            marketplace=self.marketplace_name,
            api_endpoint=endpoint,
            raw_data=data,
            collected_at=datetime.utcnow()
        )
        
        self.session.add(raw_data)
        await self.session.commit()
        
        logger.info(
            "saved_raw_data",
            marketplace=self.marketplace_name,
            endpoint=endpoint,
            data_size=len(json.dumps(data))
        )
        
        return raw_data
    
    async def collect_all_data(self, product_ids: List[str]) -> Dict[str, Any]:
        """Collect all available data for given products"""
        results = {
            'product_info': [],
            'reviews': {},
            'rankings': {},
            'search_data': {},
            'errors': []
        }
        
        # Collect product info
        try:
            results['product_info'] = await self.collect_product_info(product_ids)
        except Exception as e:
            logger.error("product_info_collection_failed", error=str(e))
            results['errors'].append({'type': 'product_info', 'error': str(e)})
        
        # Collect reviews for each product
        for product_id in product_ids:
            try:
                reviews = await self.collect_reviews(product_id)
                results['reviews'][product_id] = reviews
            except Exception as e:
                logger.error(
                    "review_collection_failed", 
                    product_id=product_id,
                    error=str(e)
                )
                results['errors'].append({
                    'type': 'reviews',
                    'product_id': product_id,
                    'error': str(e)
                })
        
        return results
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float"""
        if not price_str:
            return 0.0
        
        # Remove currency symbols and commas
        price_str = price_str.replace('원', '').replace(',', '').strip()
        
        try:
            return float(price_str)
        except ValueError:
            logger.warning("price_parse_failed", price_str=price_str)
            return 0.0
    
    def _parse_rating(self, rating_str: str) -> float:
        """Parse rating string to float"""
        if not rating_str:
            return 0.0
        
        try:
            return float(rating_str)
        except ValueError:
            logger.warning("rating_parse_failed", rating_str=rating_str)
            return 0.0