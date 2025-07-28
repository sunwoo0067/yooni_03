"""Automated market optimization system with A/B testing"""
import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import numpy as np
from scipy import stats
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog

from ..database.models import (
    Product, MarketplaceProduct, ProductPerformance,
    MarketOptimization, AIPrediction
)
from ..predictors.price_optimizer import PriceOptimizer
from ..analyzers.review_analyzer import ReviewAnalyzer
from ..utils.cache import RedisCache

logger = structlog.get_logger()


class OptimizationType(Enum):
    """Types of optimization"""
    TITLE = "title"
    PRICE = "price"
    IMAGE = "image"
    KEYWORD = "keyword"
    DESCRIPTION = "description"


class MarketOptimizer:
    """Automated marketplace optimization with A/B testing"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.cache = RedisCache(config['redis'])
        self.optimization_config = config['optimization']
        
        # Initialize sub-components
        self.price_optimizer = PriceOptimizer(config, session)
        self.review_analyzer = ReviewAnalyzer(config, session)
    
    async def create_ab_test(
        self,
        product_id: int,
        marketplace: str,
        optimization_type: OptimizationType,
        test_name: str,
        variants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a new A/B test"""
        
        # Get current product state as control
        control_variant = await self._get_current_state(product_id, marketplace, optimization_type)
        
        # Validate variants
        if not variants:
            return {'error': 'No test variants provided'}
        
        # Create optimization record
        optimization = MarketOptimization(
            product_id=product_id,
            marketplace=marketplace,
            optimization_type=optimization_type.value,
            test_name=test_name,
            control_variant=control_variant,
            test_variants=variants,
            status='running',
            started_at=datetime.utcnow()
        )
        
        self.session.add(optimization)
        await self.session.commit()
        
        logger.info(
            "ab_test_created",
            optimization_id=str(optimization.optimization_id),
            product_id=product_id,
            type=optimization_type.value,
            variants_count=len(variants)
        )
        
        return {
            'optimization_id': str(optimization.optimization_id),
            'product_id': product_id,
            'marketplace': marketplace,
            'type': optimization_type.value,
            'test_name': test_name,
            'control': control_variant,
            'variants': variants,
            'status': 'running'
        }
    
    async def _get_current_state(
        self,
        product_id: int,
        marketplace: str,
        optimization_type: OptimizationType
    ) -> Dict[str, Any]:
        """Get current state for control variant"""
        
        stmt = select(Product, MarketplaceProduct).join(
            MarketplaceProduct,
            and_(
                MarketplaceProduct.product_id == Product.id,
                MarketplaceProduct.marketplace == marketplace
            )
        ).where(Product.id == product_id)
        
        result = await self.session.execute(stmt)
        product_data = result.one_or_none()
        
        if not product_data:
            raise ValueError(f"Product {product_id} not found on {marketplace}")
        
        product, mp_product = product_data
        
        if optimization_type == OptimizationType.TITLE:
            return {'title': product.name}
        elif optimization_type == OptimizationType.PRICE:
            return {'price': float(mp_product.current_price)}
        elif optimization_type == OptimizationType.DESCRIPTION:
            return {'description': product.description if hasattr(product, 'description') else ''}
        else:
            return {}
    
    async def generate_optimization_suggestions(
        self,
        product_id: int,
        marketplace: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate AI-powered optimization suggestions"""
        
        suggestions = {
            'title': [],
            'price': [],
            'keywords': [],
            'description': []
        }
        
        # Get product data
        stmt = select(Product, MarketplaceProduct).join(
            MarketplaceProduct,
            and_(
                MarketplaceProduct.product_id == Product.id,
                MarketplaceProduct.marketplace == marketplace
            )
        ).where(Product.id == product_id)
        
        result = await self.session.execute(stmt)
        product_data = result.one_or_none()
        
        if not product_data:
            return suggestions
        
        product, mp_product = product_data
        
        # Title optimization suggestions
        title_suggestions = await self._generate_title_suggestions(product, marketplace)
        suggestions['title'] = title_suggestions
        
        # Price optimization suggestions
        price_recommendation = await self.price_optimizer.optimize_price(
            product_id, marketplace
        )
        
        if 'error' not in price_recommendation:
            suggestions['price'] = [{
                'current_price': price_recommendation['current_price'],
                'suggested_price': price_recommendation['optimal_price'],
                'expected_revenue_increase': price_recommendation['expected_revenue_increase'],
                'confidence': price_recommendation['confidence_score']
            }]
        
        # Keyword suggestions based on search trends
        keyword_suggestions = await self._generate_keyword_suggestions(product, marketplace)
        suggestions['keywords'] = keyword_suggestions
        
        # Description optimization based on review insights
        review_insights = await self.review_analyzer.generate_review_insights(product_id)
        
        if 'error' not in review_insights:
            description_suggestions = await self._generate_description_suggestions(
                product, review_insights
            )
            suggestions['description'] = description_suggestions
        
        return suggestions
    
    async def _generate_title_suggestions(
        self,
        product: Product,
        marketplace: str
    ) -> List[Dict[str, Any]]:
        """Generate optimized title suggestions"""
        
        suggestions = []
        current_title = product.name
        
        # Get top performing competitors
        competitors = await self._get_top_competitors(product.category, marketplace)
        
        # Extract common patterns from successful titles
        title_patterns = self._analyze_title_patterns(competitors)
        
        # Generate variations
        base_suggestions = [
            {
                'variant': 'keyword_front',
                'title': f"{product.brand} {product.category} - {current_title}",
                'reason': 'Brand and category keywords at front improve search visibility'
            },
            {
                'variant': 'benefit_focused',
                'title': self._create_benefit_focused_title(product),
                'reason': 'Highlighting key benefits increases click-through rate'
            },
            {
                'variant': 'urgency',
                'title': f"[한정특가] {current_title} - 무료배송",
                'reason': 'Urgency and free shipping increase conversion'
            }
        ]
        
        # Add pattern-based suggestions
        for pattern in title_patterns[:2]:
            suggestion = {
                'variant': f'pattern_{pattern["type"]}',
                'title': self._apply_title_pattern(current_title, pattern),
                'reason': f'Common pattern in top {pattern["count"]} products'
            }
            base_suggestions.append(suggestion)
        
        return base_suggestions
    
    async def _generate_keyword_suggestions(
        self,
        product: Product,
        marketplace: str
    ) -> List[Dict[str, Any]]:
        """Generate keyword optimization suggestions"""
        
        # Get search volume data (simulated - would use actual API)
        trending_keywords = await self._get_trending_keywords(product.category, marketplace)
        
        suggestions = []
        
        for keyword in trending_keywords[:5]:
            suggestions.append({
                'keyword': keyword['term'],
                'search_volume': keyword['volume'],
                'competition': keyword['competition'],
                'relevance_score': keyword['relevance']
            })
        
        return suggestions
    
    async def _generate_description_suggestions(
        self,
        product: Product,
        review_insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate description optimization based on reviews"""
        
        suggestions = []
        
        # Address weaknesses identified in reviews
        if review_insights.get('weaknesses'):
            for weakness in review_insights['weaknesses']:
                suggestions.append({
                    'type': 'address_concern',
                    'content': f"개선된 {weakness['aspect']} - 고객님들의 의견을 반영하여 품질을 향상시켰습니다.",
                    'reason': f"Reviews show dissatisfaction with {weakness['aspect']}"
                })
        
        # Highlight strengths
        if review_insights.get('strengths'):
            for strength in review_insights['strengths']:
                suggestions.append({
                    'type': 'highlight_strength',
                    'content': f"✓ 뛰어난 {strength['aspect']} - 고객 만족도 {strength['score']*100:.0f}%",
                    'reason': f"Leverage positive feedback on {strength['aspect']}"
                })
        
        return suggestions
    
    async def run_optimization_test(
        self,
        optimization_id: str,
        duration_days: int = 7
    ) -> Dict[str, Any]:
        """Run and monitor an optimization test"""
        
        # Get optimization record
        stmt = select(MarketOptimization).where(
            MarketOptimization.optimization_id == optimization_id
        )
        result = await self.session.execute(stmt)
        optimization = result.scalar_one_or_none()
        
        if not optimization:
            return {'error': 'Optimization not found'}
        
        if optimization.status != 'running':
            return {'error': f'Test is {optimization.status}'}
        
        # Check if test duration has elapsed
        elapsed_days = (datetime.utcnow() - optimization.started_at).days
        
        if elapsed_days < duration_days:
            # Collect interim metrics
            metrics = await self._collect_test_metrics(optimization)
            
            return {
                'optimization_id': optimization_id,
                'status': 'running',
                'elapsed_days': elapsed_days,
                'remaining_days': duration_days - elapsed_days,
                'interim_metrics': metrics
            }
        
        # Test complete - analyze results
        return await self.complete_optimization_test(optimization_id)
    
    async def complete_optimization_test(
        self,
        optimization_id: str
    ) -> Dict[str, Any]:
        """Complete test and determine winner"""
        
        # Get optimization
        stmt = select(MarketOptimization).where(
            MarketOptimization.optimization_id == optimization_id
        )
        result = await self.session.execute(stmt)
        optimization = result.scalar_one_or_none()
        
        if not optimization:
            return {'error': 'Optimization not found'}
        
        # Collect final metrics
        metrics = await self._collect_test_metrics(optimization)
        
        # Determine winner using statistical significance
        winner, significance = await self._determine_winner(metrics)
        
        # Update optimization record
        optimization.status = 'completed'
        optimization.ended_at = datetime.utcnow()
        optimization.winner_variant = winner
        optimization.metrics = metrics
        optimization.statistical_significance = significance
        
        await self.session.commit()
        
        # Generate recommendations
        recommendations = self._generate_test_recommendations(
            optimization, metrics, winner, significance
        )
        
        return {
            'optimization_id': optimization_id,
            'status': 'completed',
            'test_duration_days': (optimization.ended_at - optimization.started_at).days,
            'winner': winner,
            'statistical_significance': significance,
            'metrics': metrics,
            'recommendations': recommendations
        }
    
    async def _collect_test_metrics(
        self,
        optimization: MarketOptimization
    ) -> Dict[str, Any]:
        """Collect performance metrics for all variants"""
        
        metrics = {}
        
        # Define metric collection period
        start_date = optimization.started_at.date()
        end_date = datetime.utcnow().date()
        
        # Collect control metrics
        control_metrics = await self._collect_variant_metrics(
            optimization.product_id,
            optimization.marketplace,
            'control',
            start_date,
            end_date
        )
        metrics['control'] = control_metrics
        
        # Collect test variant metrics
        for i, variant in enumerate(optimization.test_variants):
            variant_name = variant.get('name', f'variant_{i+1}')
            variant_metrics = await self._collect_variant_metrics(
                optimization.product_id,
                optimization.marketplace,
                variant_name,
                start_date,
                end_date
            )
            metrics[variant_name] = variant_metrics
        
        return metrics
    
    async def _collect_variant_metrics(
        self,
        product_id: int,
        marketplace: str,
        variant_name: str,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """Collect metrics for a specific variant"""
        
        # In real implementation, this would track variant-specific performance
        # For now, simulate with random variations
        
        base_metrics = {
            'impressions': random.randint(1000, 5000),
            'clicks': random.randint(50, 300),
            'conversions': random.randint(5, 50),
            'revenue': random.randint(50000, 500000)
        }
        
        # Add calculated metrics
        base_metrics['ctr'] = base_metrics['clicks'] / base_metrics['impressions']
        base_metrics['conversion_rate'] = base_metrics['conversions'] / base_metrics['clicks']
        base_metrics['avg_order_value'] = base_metrics['revenue'] / base_metrics['conversions']
        
        return base_metrics
    
    async def _determine_winner(
        self,
        metrics: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Determine winning variant using statistical significance"""
        
        # Use conversion rate as primary metric
        control_conversions = metrics['control']['conversions']
        control_clicks = metrics['control']['clicks']
        
        best_variant = 'control'
        best_significance = 0.0
        
        for variant_name, variant_metrics in metrics.items():
            if variant_name == 'control':
                continue
            
            variant_conversions = variant_metrics['conversions']
            variant_clicks = variant_metrics['clicks']
            
            # Perform chi-square test
            observed = np.array([
                [control_conversions, control_clicks - control_conversions],
                [variant_conversions, variant_clicks - variant_conversions]
            ])
            
            chi2, p_value = stats.chi2_contingency(observed)[:2]
            significance = 1 - p_value
            
            # Check if variant is better and significant
            variant_rate = variant_conversions / variant_clicks if variant_clicks > 0 else 0
            control_rate = control_conversions / control_clicks if control_clicks > 0 else 0
            
            if variant_rate > control_rate and significance > best_significance:
                best_variant = variant_name
                best_significance = significance
        
        return best_variant, best_significance
    
    def _generate_test_recommendations(
        self,
        optimization: MarketOptimization,
        metrics: Dict[str, Any],
        winner: str,
        significance: float
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Statistical significance recommendation
        if significance >= 0.95:
            recommendations.append({
                'type': 'implement',
                'priority': 'high',
                'action': f"Implement {winner} variant",
                'reason': f"Statistically significant improvement (p < {1-significance:.3f})"
            })
        elif significance >= 0.90:
            recommendations.append({
                'type': 'extend_test',
                'priority': 'medium',
                'action': "Extend test for more data",
                'reason': f"Marginally significant (p = {1-significance:.3f})"
            })
        else:
            recommendations.append({
                'type': 'no_change',
                'priority': 'low',
                'action': "Keep current version",
                'reason': f"No significant difference (p = {1-significance:.3f})"
            })
        
        # Performance-based recommendations
        if winner != 'control':
            winner_metrics = metrics[winner]
            control_metrics = metrics['control']
            
            revenue_lift = (
                (winner_metrics['revenue'] - control_metrics['revenue']) / 
                control_metrics['revenue'] * 100
            )
            
            if revenue_lift > 10:
                recommendations.append({
                    'type': 'scale',
                    'priority': 'high',
                    'action': "Apply optimization to similar products",
                    'reason': f"Revenue increased by {revenue_lift:.1f}%"
                })
        
        return recommendations
    
    async def _get_top_competitors(
        self,
        category: str,
        marketplace: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top performing competitors in category"""
        
        # Query top products by performance
        stmt = select(
            Product,
            MarketplaceProduct,
            func.avg(ProductPerformance.sales_volume).label('avg_sales')
        ).join(
            MarketplaceProduct,
            and_(
                MarketplaceProduct.product_id == Product.id,
                MarketplaceProduct.marketplace == marketplace
            )
        ).join(
            ProductPerformance,
            ProductPerformance.product_id == Product.id
        ).where(
            and_(
                Product.category == category,
                ProductPerformance.date >= datetime.utcnow().date() - timedelta(days=30)
            )
        ).group_by(
            Product.id,
            MarketplaceProduct.id
        ).order_by(
            func.avg(ProductPerformance.sales_volume).desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        
        competitors = []
        for product, mp_product, avg_sales in result:
            competitors.append({
                'product_id': product.id,
                'name': product.name,
                'price': float(mp_product.current_price),
                'avg_sales': float(avg_sales) if avg_sales else 0
            })
        
        return competitors
    
    def _analyze_title_patterns(
        self,
        competitors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze common patterns in competitor titles"""
        
        patterns = []
        
        # Common prefixes
        prefix_counts = {}
        for comp in competitors:
            title = comp['name']
            if '[' in title and ']' in title:
                prefix = title[title.find('[')+1:title.find(']')]
                prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
        
        for prefix, count in sorted(prefix_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 2:
                patterns.append({
                    'type': 'prefix',
                    'pattern': f'[{prefix}]',
                    'count': count
                })
        
        # Common keywords
        keyword_counts = {}
        for comp in competitors:
            words = comp['name'].split()
            for word in words:
                if len(word) > 2:
                    keyword_counts[word] = keyword_counts.get(word, 0) + 1
        
        for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            if count >= 3:
                patterns.append({
                    'type': 'keyword',
                    'pattern': keyword,
                    'count': count
                })
        
        return patterns
    
    def _create_benefit_focused_title(self, product: Product) -> str:
        """Create benefit-focused title variant"""
        
        benefits = {
            'fashion': '스타일리시한',
            'beauty': '피부개선',
            'digital': '고성능',
            'food': '건강한',
            'living': '편리한'
        }
        
        benefit = benefits.get(product.category, '프리미엄')
        
        return f"{benefit} {product.name} - 만족도 높은 베스트셀러"
    
    def _apply_title_pattern(
        self,
        current_title: str,
        pattern: Dict[str, Any]
    ) -> str:
        """Apply pattern to title"""
        
        if pattern['type'] == 'prefix':
            return f"{pattern['pattern']} {current_title}"
        elif pattern['type'] == 'keyword':
            if pattern['pattern'] not in current_title:
                return f"{current_title} {pattern['pattern']}"
        
        return current_title
    
    async def _get_trending_keywords(
        self,
        category: str,
        marketplace: str
    ) -> List[Dict[str, Any]]:
        """Get trending keywords (simulated)"""
        
        # In real implementation, this would use search API data
        base_keywords = {
            'fashion': ['신상', '트렌드', '인기', '데일리', '코디'],
            'beauty': ['수분', '미백', '주름개선', '천연', '민감성'],
            'digital': ['최신', '고사양', '무선', '스마트', '휴대용'],
            'food': ['유기농', '무첨가', '건강', '다이어트', '프리미엄'],
            'living': ['편리한', '실용적', '인테리어', '수납', '친환경']
        }
        
        keywords = base_keywords.get(category, ['베스트', '인기', '추천'])
        
        trending = []
        for keyword in keywords:
            trending.append({
                'term': keyword,
                'volume': random.randint(1000, 10000),
                'competition': random.choice(['low', 'medium', 'high']),
                'relevance': random.uniform(0.7, 1.0)
            })
        
        return sorted(trending, key=lambda x: x['volume'], reverse=True)