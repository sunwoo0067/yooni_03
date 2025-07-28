"""Product rotation management system"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
import structlog
from enum import Enum

from ..database.models import (
    Product, MarketplaceProduct, ProductPerformance,
    RotationHistory, MarketOptimization
)
from ..collectors.data_aggregator import DataAggregator
from ..utils.cache import RedisCache, CacheKey

logger = structlog.get_logger()


class RotationStrategy(Enum):
    """Rotation strategy types"""
    RANKING_BASED = "ranking_based"
    PERFORMANCE_BASED = "performance_based"
    SEASONAL = "seasonal"
    AB_TEST = "ab_test"
    SCHEDULED = "scheduled"


class RotationManager:
    """Manages product rotation strategies across marketplaces"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.cache = RedisCache(config['redis'])
        self.rotation_config = config['product_rotation']
        self.data_aggregator = DataAggregator(config, session)
    
    async def evaluate_rotation_candidates(
        self,
        marketplace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate products that need rotation"""
        candidates = []
        
        # Get all active products
        stmt = select(Product).where(Product.status == 'active')
        result = await self.session.execute(stmt)
        products = result.scalars().all()
        
        for product in products:
            # Evaluate each strategy
            for strategy_config in self.rotation_config['strategies']:
                strategy = RotationStrategy(strategy_config['name'])
                
                if await self._needs_rotation(product, strategy, strategy_config, marketplace):
                    candidates.append({
                        'product_id': product.id,
                        'product_code': product.product_code,
                        'product_name': product.name,
                        'strategy': strategy.value,
                        'reason': await self._get_rotation_reason(product, strategy, strategy_config),
                        'priority': await self._calculate_rotation_priority(product, strategy),
                        'marketplace': marketplace
                    })
        
        # Sort by priority
        candidates.sort(key=lambda x: x['priority'], reverse=True)
        
        return candidates
    
    async def _needs_rotation(
        self,
        product: Product,
        strategy: RotationStrategy,
        config: Dict[str, Any],
        marketplace: Optional[str] = None
    ) -> bool:
        """Check if product needs rotation based on strategy"""
        
        if strategy == RotationStrategy.RANKING_BASED:
            return await self._check_ranking_based_rotation(product, config, marketplace)
        elif strategy == RotationStrategy.PERFORMANCE_BASED:
            return await self._check_performance_based_rotation(product, config, marketplace)
        elif strategy == RotationStrategy.SEASONAL:
            return await self._check_seasonal_rotation(product, config)
        elif strategy == RotationStrategy.SCHEDULED:
            return await self._check_scheduled_rotation(product, config, marketplace)
        
        return False
    
    async def _check_ranking_based_rotation(
        self,
        product: Product,
        config: Dict[str, Any],
        marketplace: Optional[str] = None
    ) -> bool:
        """Check if product needs rotation based on ranking"""
        threshold_rank = config['threshold_rank']
        
        # Get recent performance
        stmt = select(ProductPerformance).where(
            and_(
                ProductPerformance.product_id == product.id,
                ProductPerformance.date >= datetime.utcnow().date() - timedelta(days=7)
            )
        )
        
        if marketplace:
            stmt = stmt.where(ProductPerformance.marketplace == marketplace)
        
        result = await self.session.execute(stmt)
        performances = result.scalars().all()
        
        if not performances:
            return False
        
        # Check average ranking
        avg_ranking = sum(p.category_ranking or 999 for p in performances) / len(performances)
        
        return avg_ranking > threshold_rank
    
    async def _check_performance_based_rotation(
        self,
        product: Product,
        config: Dict[str, Any],
        marketplace: Optional[str] = None
    ) -> bool:
        """Check if product needs rotation based on performance"""
        min_conversion_rate = config['min_conversion_rate']
        
        # Get recent performance
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        
        stmt = select(
            func.sum(ProductPerformance.conversions).label('total_conversions'),
            func.sum(ProductPerformance.clicks).label('total_clicks')
        ).where(
            and_(
                ProductPerformance.product_id == product.id,
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        )
        
        if marketplace:
            stmt = stmt.where(ProductPerformance.marketplace == marketplace)
        
        result = await self.session.execute(stmt)
        data = result.one()
        
        if not data.total_clicks or data.total_clicks == 0:
            return False
        
        conversion_rate = data.total_conversions / data.total_clicks
        
        return conversion_rate < min_conversion_rate
    
    async def _check_seasonal_rotation(
        self,
        product: Product,
        config: Dict[str, Any]
    ) -> bool:
        """Check if product needs seasonal rotation"""
        current_month = datetime.utcnow().month
        seasons = config['seasons']
        
        # Determine current season
        current_season = None
        for season, months in seasons.items():
            if current_month in months:
                current_season = season
                break
        
        # Check if product category matches season
        # This is a simplified example - you'd want more sophisticated logic
        seasonal_categories = {
            'summer': ['swimwear', 'sunglasses', 'fans'],
            'winter': ['coats', 'heaters', 'gloves'],
            'spring': ['gardening', 'allergy', 'rain'],
            'fall': ['sweaters', 'boots', 'halloween']
        }
        
        if current_season and product.category:
            relevant_categories = seasonal_categories.get(current_season, [])
            return not any(cat in product.category.lower() for cat in relevant_categories)
        
        return False
    
    async def _check_scheduled_rotation(
        self,
        product: Product,
        config: Dict[str, Any],
        marketplace: Optional[str] = None
    ) -> bool:
        """Check if product needs scheduled rotation"""
        rotation_interval_hours = config.get('rotation_interval_hours', 168)  # 1 week default
        
        # Get last rotation
        stmt = select(RotationHistory).where(
            RotationHistory.product_id == product.id
        )
        
        if marketplace:
            stmt = stmt.where(RotationHistory.marketplace == marketplace)
        
        stmt = stmt.order_by(desc(RotationHistory.rotated_at)).limit(1)
        
        result = await self.session.execute(stmt)
        last_rotation = result.scalar_one_or_none()
        
        if not last_rotation:
            # Never rotated, check creation date
            return (datetime.utcnow() - product.created_at).total_seconds() / 3600 > rotation_interval_hours
        
        # Check time since last rotation
        hours_since_rotation = (datetime.utcnow() - last_rotation.rotated_at).total_seconds() / 3600
        
        return hours_since_rotation > rotation_interval_hours
    
    async def _get_rotation_reason(
        self,
        product: Product,
        strategy: RotationStrategy,
        config: Dict[str, Any]
    ) -> str:
        """Get human-readable rotation reason"""
        if strategy == RotationStrategy.RANKING_BASED:
            return f"Ranking dropped below {config['threshold_rank']}"
        elif strategy == RotationStrategy.PERFORMANCE_BASED:
            return f"Conversion rate below {config['min_conversion_rate'] * 100}%"
        elif strategy == RotationStrategy.SEASONAL:
            return "Product not aligned with current season"
        elif strategy == RotationStrategy.SCHEDULED:
            return f"Scheduled rotation after {config.get('rotation_interval_hours', 168)} hours"
        
        return "Unknown reason"
    
    async def _calculate_rotation_priority(
        self,
        product: Product,
        strategy: RotationStrategy
    ) -> float:
        """Calculate rotation priority (higher = more urgent)"""
        base_priority = {
            RotationStrategy.RANKING_BASED: 0.8,
            RotationStrategy.PERFORMANCE_BASED: 0.9,
            RotationStrategy.SEASONAL: 0.6,
            RotationStrategy.AB_TEST: 0.7,
            RotationStrategy.SCHEDULED: 0.5
        }
        
        priority = base_priority.get(strategy, 0.5)
        
        # Adjust based on product performance
        metrics = await self.data_aggregator.get_aggregated_metrics(
            product.product_code,
            days=7
        )
        
        if metrics:
            # Lower conversion rate = higher priority
            conversion_rate = metrics['totals'].get('conversion_rate', 0)
            if conversion_rate < 0.01:
                priority += 0.2
            elif conversion_rate < 0.02:
                priority += 0.1
            
            # Higher revenue = higher priority
            revenue = metrics['totals'].get('revenue', 0)
            if revenue > 1000000:  # 1M KRW
                priority += 0.15
            elif revenue > 500000:
                priority += 0.1
        
        return min(priority, 1.0)  # Cap at 1.0
    
    async def rotate_product(
        self,
        product_id: int,
        strategy: RotationStrategy,
        marketplace: str,
        changes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute product rotation"""
        try:
            # Get product
            stmt = select(Product).where(Product.id == product_id)
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()
            
            if not product:
                raise ValueError(f"Product {product_id} not found")
            
            # Get current marketplace product
            stmt = select(MarketplaceProduct).where(
                and_(
                    MarketplaceProduct.product_id == product_id,
                    MarketplaceProduct.marketplace == marketplace
                )
            )
            result = await self.session.execute(stmt)
            mp_product = result.scalar_one_or_none()
            
            if not mp_product:
                raise ValueError(f"Product not listed on {marketplace}")
            
            # Get current performance metrics
            current_metrics = await self._get_current_metrics(product_id, marketplace)
            
            # Prepare rotation changes
            if not changes:
                changes = await self._generate_rotation_changes(product, strategy, marketplace)
            
            # Execute rotation (this would integrate with marketplace APIs)
            new_listing_id = await self._execute_marketplace_rotation(
                mp_product,
                changes,
                marketplace
            )
            
            # Record rotation history
            rotation = RotationHistory(
                product_id=product_id,
                marketplace=marketplace,
                rotation_strategy=strategy.value,
                previous_rank=current_metrics.get('ranking'),
                previous_sales_7d=current_metrics.get('sales_7d'),
                old_listing_id=mp_product.marketplace_product_id,
                new_listing_id=new_listing_id,
                changes_made=changes,
                rotated_at=datetime.utcnow()
            )
            
            self.session.add(rotation)
            
            # Update marketplace product
            mp_product.marketplace_product_id = new_listing_id
            mp_product.last_updated = datetime.utcnow()
            
            await self.session.commit()
            
            logger.info(
                "product_rotated",
                product_id=product_id,
                marketplace=marketplace,
                strategy=strategy.value,
                changes=changes
            )
            
            return {
                'success': True,
                'rotation_id': rotation.id,
                'old_listing_id': rotation.old_listing_id,
                'new_listing_id': rotation.new_listing_id,
                'changes': changes
            }
            
        except Exception as e:
            logger.error(
                "rotation_failed",
                product_id=product_id,
                marketplace=marketplace,
                error=str(e)
            )
            await self.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_current_metrics(
        self,
        product_id: int,
        marketplace: str
    ) -> Dict[str, Any]:
        """Get current product metrics"""
        # Get latest performance
        stmt = select(ProductPerformance).where(
            and_(
                ProductPerformance.product_id == product_id,
                ProductPerformance.marketplace == marketplace
            )
        ).order_by(desc(ProductPerformance.date)).limit(1)
        
        result = await self.session.execute(stmt)
        latest_performance = result.scalar_one_or_none()
        
        # Get 7-day sales
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        
        stmt = select(
            func.sum(ProductPerformance.sales_volume)
        ).where(
            and_(
                ProductPerformance.product_id == product_id,
                ProductPerformance.marketplace == marketplace,
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        )
        
        result = await self.session.execute(stmt)
        sales_7d = result.scalar() or 0
        
        return {
            'ranking': latest_performance.category_ranking if latest_performance else None,
            'sales_7d': sales_7d,
            'conversion_rate': (
                latest_performance.conversions / latest_performance.clicks
                if latest_performance and latest_performance.clicks > 0
                else 0
            )
        }
    
    async def _generate_rotation_changes(
        self,
        product: Product,
        strategy: RotationStrategy,
        marketplace: str
    ) -> Dict[str, Any]:
        """Generate changes for rotation based on strategy"""
        changes = {
            'title': False,
            'description': False,
            'images': False,
            'price': False,
            'keywords': False
        }
        
        if strategy == RotationStrategy.RANKING_BASED:
            # Focus on SEO improvements
            changes['title'] = True
            changes['keywords'] = True
            changes['description'] = True
            
        elif strategy == RotationStrategy.PERFORMANCE_BASED:
            # Focus on conversion improvements
            changes['images'] = True
            changes['description'] = True
            changes['price'] = True
            
        elif strategy == RotationStrategy.SEASONAL:
            # Update for seasonal relevance
            changes['title'] = True
            changes['description'] = True
            changes['images'] = True
            
        elif strategy == RotationStrategy.SCHEDULED:
            # Refresh all elements
            changes = {k: True for k in changes}
        
        return changes
    
    async def _execute_marketplace_rotation(
        self,
        mp_product: MarketplaceProduct,
        changes: Dict[str, Any],
        marketplace: str
    ) -> str:
        """Execute rotation on marketplace (placeholder)"""
        # This would integrate with actual marketplace APIs
        # For now, return a simulated new listing ID
        
        import uuid
        new_listing_id = f"{marketplace}_{uuid.uuid4().hex[:8]}"
        
        # In real implementation:
        # 1. Create new listing with changes
        # 2. Deactivate old listing
        # 3. Return new listing ID
        
        logger.info(
            "marketplace_rotation_executed",
            marketplace=marketplace,
            old_id=mp_product.marketplace_product_id,
            new_id=new_listing_id,
            changes=changes
        )
        
        return new_listing_id
    
    async def evaluate_rotation_results(
        self,
        rotation_id: int,
        evaluation_days: int = 7
    ) -> Dict[str, Any]:
        """Evaluate the results of a rotation"""
        # Get rotation record
        stmt = select(RotationHistory).where(RotationHistory.id == rotation_id)
        result = await self.session.execute(stmt)
        rotation = result.scalar_one_or_none()
        
        if not rotation:
            return {'error': 'Rotation not found'}
        
        # Check if enough time has passed
        days_since_rotation = (datetime.utcnow() - rotation.rotated_at).days
        if days_since_rotation < evaluation_days:
            return {
                'status': 'pending',
                'message': f"Need {evaluation_days - days_since_rotation} more days for evaluation"
            }
        
        # Get post-rotation metrics
        post_metrics = await self._get_current_metrics(
            rotation.product_id,
            rotation.marketplace
        )
        
        # Calculate improvements
        results = {
            'rotation_id': rotation_id,
            'product_id': rotation.product_id,
            'marketplace': rotation.marketplace,
            'strategy': rotation.rotation_strategy,
            'evaluation_period': evaluation_days,
            'metrics': {
                'ranking': {
                    'before': rotation.previous_rank,
                    'after': post_metrics['ranking'],
                    'improvement': (
                        rotation.previous_rank - post_metrics['ranking']
                        if rotation.previous_rank and post_metrics['ranking']
                        else None
                    )
                },
                'sales': {
                    'before': rotation.previous_sales_7d,
                    'after': post_metrics['sales_7d'],
                    'improvement_rate': (
                        (post_metrics['sales_7d'] - rotation.previous_sales_7d) / rotation.previous_sales_7d
                        if rotation.previous_sales_7d > 0
                        else None
                    )
                }
            },
            'success': self._evaluate_success(rotation, post_metrics)
        }
        
        # Update rotation record
        rotation.new_rank = post_metrics['ranking']
        rotation.new_sales_7d = post_metrics['sales_7d']
        rotation.performance_change = results['metrics']['sales']['improvement_rate']
        rotation.evaluated_at = datetime.utcnow()
        
        await self.session.commit()
        
        return results
    
    def _evaluate_success(
        self,
        rotation: RotationHistory,
        post_metrics: Dict[str, Any]
    ) -> bool:
        """Determine if rotation was successful"""
        # Ranking improvement
        if rotation.previous_rank and post_metrics['ranking']:
            if post_metrics['ranking'] < rotation.previous_rank:
                return True
        
        # Sales improvement
        if rotation.previous_sales_7d and post_metrics['sales_7d']:
            if post_metrics['sales_7d'] > rotation.previous_sales_7d * 1.1:  # 10% improvement
                return True
        
        return False