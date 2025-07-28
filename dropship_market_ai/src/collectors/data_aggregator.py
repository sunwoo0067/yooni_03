"""Data aggregator for combining data from multiple marketplaces"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog

from .coupang_collector import CoupangCollector
from .naver_collector import NaverCollector
from ..database.models import (
    Product, MarketplaceProduct, ProductPerformance, 
    Review, MarketRawData
)
from ..utils.cache import RedisCache

logger = structlog.get_logger()


class DataAggregator:
    """Aggregates data from multiple marketplace collectors"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.cache = RedisCache(config['redis'])
        
        # Initialize collectors
        self.collectors = {
            'coupang': CoupangCollector(config['marketplace']['coupang'], session),
            'naver': NaverCollector(config['marketplace']['naver'], session),
            # Add more collectors as needed
        }
    
    async def collect_all_marketplace_data(
        self, 
        product_ids: List[str],
        marketplaces: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Collect data from all configured marketplaces"""
        if marketplaces is None:
            marketplaces = list(self.collectors.keys())
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'marketplaces': {},
            'summary': {
                'total_products': len(product_ids),
                'successful_collections': 0,
                'failed_collections': 0
            }
        }
        
        # Collect data from each marketplace in parallel
        tasks = []
        for marketplace in marketplaces:
            if marketplace in self.collectors:
                collector = self.collectors[marketplace]
                task = self._collect_marketplace_data(
                    collector, 
                    product_ids, 
                    marketplace
                )
                tasks.append(task)
        
        # Wait for all collections to complete
        marketplace_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for marketplace, result in zip(marketplaces, marketplace_results):
            if isinstance(result, Exception):
                logger.error(
                    "marketplace_collection_failed",
                    marketplace=marketplace,
                    error=str(result)
                )
                results['marketplaces'][marketplace] = {'error': str(result)}
                results['summary']['failed_collections'] += 1
            else:
                results['marketplaces'][marketplace] = result
                results['summary']['successful_collections'] += 1
        
        return results
    
    async def _collect_marketplace_data(
        self,
        collector: Any,
        product_ids: List[str],
        marketplace: str
    ) -> Dict[str, Any]:
        """Collect data from a single marketplace"""
        async with collector:
            data = await collector.collect_all_data(product_ids)
            
            # Process and store collected data
            await self._process_collected_data(data, marketplace)
            
            return data
    
    async def _process_collected_data(
        self,
        data: Dict[str, Any],
        marketplace: str
    ) -> None:
        """Process and store collected data in the database"""
        try:
            # Process product information
            for product_info in data.get('product_info', []):
                await self._update_product_info(product_info, marketplace)
            
            # Process reviews
            for product_id, review_data in data.get('reviews', {}).items():
                await self._process_reviews(product_id, review_data, marketplace)
            
            # Process rankings
            await self._process_rankings(data.get('rankings', {}), marketplace)
            
            await self.session.commit()
            
        except Exception as e:
            logger.error(
                "data_processing_failed",
                marketplace=marketplace,
                error=str(e)
            )
            await self.session.rollback()
            raise
    
    async def _update_product_info(
        self,
        product_info: Dict[str, Any],
        marketplace: str
    ) -> None:
        """Update product information in database"""
        # Check if product exists
        stmt = select(Product).where(
            Product.product_code == product_info['product_id']
        )
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            # Create new product
            product = Product(
                product_code=product_info['product_id'],
                name=product_info['name'],
                category=product_info.get('category'),
                brand=product_info.get('brand'),
                status='active'
            )
            self.session.add(product)
            await self.session.flush()
        
        # Update marketplace product
        stmt = select(MarketplaceProduct).where(
            and_(
                MarketplaceProduct.product_id == product.id,
                MarketplaceProduct.marketplace == marketplace
            )
        )
        result = await self.session.execute(stmt)
        mp_product = result.scalar_one_or_none()
        
        if not mp_product:
            mp_product = MarketplaceProduct(
                product_id=product.id,
                marketplace=marketplace,
                marketplace_product_id=product_info['product_id']
            )
            self.session.add(mp_product)
        
        # Update current info
        mp_product.current_price = product_info.get('price', 0)
        mp_product.listing_url = product_info.get('link', '')
        mp_product.last_updated = datetime.utcnow()
        
        # Create performance record
        today = datetime.utcnow().date()
        stmt = select(ProductPerformance).where(
            and_(
                ProductPerformance.product_id == product.id,
                ProductPerformance.marketplace == marketplace,
                ProductPerformance.date == today
            )
        )
        result = await self.session.execute(stmt)
        performance = result.scalar_one_or_none()
        
        if not performance:
            performance = ProductPerformance(
                product_id=product.id,
                marketplace=marketplace,
                date=today
            )
            self.session.add(performance)
        
        # Update performance metrics
        performance.views = product_info.get('views', 0)
        performance.wish_count = product_info.get('wish_count', 0)
        performance.category_ranking = product_info.get('ranking', 0)
    
    async def _process_reviews(
        self,
        product_id: str,
        review_data: Dict[str, Any],
        marketplace: str
    ) -> None:
        """Process and store review data"""
        # Get product
        stmt = select(Product).where(Product.product_code == product_id)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            return
        
        for review_info in review_data.get('reviews', []):
            # Check if review exists
            stmt = select(Review).where(
                and_(
                    Review.marketplace == marketplace,
                    Review.review_id == review_info['review_id']
                )
            )
            result = await self.session.execute(stmt)
            review = result.scalar_one_or_none()
            
            if not review:
                review = Review(
                    product_id=product.id,
                    marketplace=marketplace,
                    review_id=review_info['review_id'],
                    rating=review_info['rating'],
                    title=review_info.get('title', ''),
                    content=review_info.get('content', ''),
                    reviewer_name=review_info.get('reviewer_name', 'Anonymous'),
                    verified_purchase=review_info.get('verified_purchase', False),
                    helpful_count=review_info.get('helpful_count', 0),
                    created_at=datetime.fromisoformat(review_info['created_at']) if review_info.get('created_at') else datetime.utcnow()
                )
                self.session.add(review)
    
    async def _process_rankings(
        self,
        rankings_data: Dict[str, Any],
        marketplace: str
    ) -> None:
        """Process ranking data"""
        for category_id, rankings in rankings_data.items():
            for ranking_info in rankings:
                # Update product performance with ranking
                stmt = select(Product).where(
                    Product.product_code == ranking_info['product_id']
                )
                result = await self.session.execute(stmt)
                product = result.scalar_one_or_none()
                
                if product:
                    today = datetime.utcnow().date()
                    stmt = select(ProductPerformance).where(
                        and_(
                            ProductPerformance.product_id == product.id,
                            ProductPerformance.marketplace == marketplace,
                            ProductPerformance.date == today
                        )
                    )
                    result = await self.session.execute(stmt)
                    performance = result.scalar_one_or_none()
                    
                    if performance:
                        performance.category_ranking = ranking_info['rank']
    
    async def get_aggregated_metrics(
        self,
        product_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get aggregated metrics across all marketplaces"""
        # Get product
        stmt = select(Product).where(Product.product_code == product_id)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            return {}
        
        # Calculate date range
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Get performance data
        stmt = select(ProductPerformance).where(
            and_(
                ProductPerformance.product_id == product.id,
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        ).order_by(ProductPerformance.date)
        
        result = await self.session.execute(stmt)
        performances = result.scalars().all()
        
        # Aggregate metrics
        metrics = {
            'product_id': product_id,
            'product_name': product.name,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'marketplaces': {},
            'totals': {
                'views': 0,
                'clicks': 0,
                'conversions': 0,
                'revenue': 0,
                'avg_ranking': 0
            }
        }
        
        # Process by marketplace
        marketplace_data = {}
        for perf in performances:
            if perf.marketplace not in marketplace_data:
                marketplace_data[perf.marketplace] = {
                    'views': 0,
                    'clicks': 0,
                    'conversions': 0,
                    'revenue': 0,
                    'rankings': []
                }
            
            mp_data = marketplace_data[perf.marketplace]
            mp_data['views'] += perf.views or 0
            mp_data['clicks'] += perf.clicks or 0
            mp_data['conversions'] += perf.conversions or 0
            mp_data['revenue'] += float(perf.revenue or 0)
            if perf.category_ranking:
                mp_data['rankings'].append(perf.category_ranking)
        
        # Calculate marketplace metrics
        for marketplace, data in marketplace_data.items():
            avg_ranking = sum(data['rankings']) / len(data['rankings']) if data['rankings'] else 0
            
            metrics['marketplaces'][marketplace] = {
                'views': data['views'],
                'clicks': data['clicks'],
                'conversions': data['conversions'],
                'revenue': data['revenue'],
                'avg_ranking': avg_ranking,
                'conversion_rate': data['conversions'] / data['clicks'] if data['clicks'] > 0 else 0
            }
            
            # Add to totals
            metrics['totals']['views'] += data['views']
            metrics['totals']['clicks'] += data['clicks']
            metrics['totals']['conversions'] += data['conversions']
            metrics['totals']['revenue'] += data['revenue']
        
        # Calculate total average ranking
        all_rankings = []
        for data in marketplace_data.values():
            all_rankings.extend(data['rankings'])
        
        metrics['totals']['avg_ranking'] = sum(all_rankings) / len(all_rankings) if all_rankings else 0
        metrics['totals']['conversion_rate'] = (
            metrics['totals']['conversions'] / metrics['totals']['clicks'] 
            if metrics['totals']['clicks'] > 0 else 0
        )
        
        return metrics