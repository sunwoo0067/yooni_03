"""AI-based price optimization system using XGBoost"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog

from ..database.models import (
    Product, ProductPerformance, MarketplaceProduct,
    AIPrediction, MarketOptimization
)

logger = structlog.get_logger()


class PriceOptimizer:
    """XGBoost-based price optimization system"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.optimization_config = config['optimization']['price']
        self.model_config = config['ml_models']['price_optimization']
        
        self.models = {}
        self.feature_importance = {}
    
    async def prepare_training_data(
        self,
        marketplace: str,
        days: int = 180
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data for price optimization"""
        
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Query performance data with price changes
        stmt = select(
            ProductPerformance,
            Product,
            MarketplaceProduct
        ).join(
            Product,
            ProductPerformance.product_id == Product.id
        ).join(
            MarketplaceProduct,
            and_(
                MarketplaceProduct.product_id == Product.id,
                MarketplaceProduct.marketplace == marketplace
            )
        ).where(
            and_(
                ProductPerformance.marketplace == marketplace,
                ProductPerformance.date >= start_date,
                ProductPerformance.date <= end_date
            )
        )
        
        result = await self.session.execute(stmt)
        data_rows = result.all()
        
        # Prepare features
        features_list = []
        targets = []
        
        for perf, product, mp_product in data_rows:
            if not perf.revenue or not perf.sales_volume:
                continue
            
            # Calculate features
            features = {
                'cost': float(product.cost_price or 0),
                'current_price': float(mp_product.current_price or 0),
                'margin': (float(mp_product.current_price or 0) - float(product.cost_price or 0)) / float(mp_product.current_price or 1),
                'category_avg_price': await self._get_category_avg_price(product.category, marketplace),
                'competitor_min_price': await self._get_competitor_prices(product.id, marketplace)['min'],
                'competitor_avg_price': await self._get_competitor_prices(product.id, marketplace)['avg'],
                'demand_elasticity': await self._calculate_demand_elasticity(product.id, marketplace),
                'inventory_level': 100,  # Placeholder - would come from inventory system
                'days_listed': (perf.date - product.created_at.date()).days,
                'review_score': await self._get_avg_review_score(product.id),
                'season_factor': self._get_season_factor(perf.date),
                'weekday': perf.date.weekday(),
                'month': perf.date.month,
                'ranking': perf.category_ranking or 999,
                'conversion_rate': perf.conversions / perf.clicks if perf.clicks > 0 else 0
            }
            
            # Target is the revenue
            target = float(perf.revenue)
            
            features_list.append(features)
            targets.append(target)
        
        if not features_list:
            raise ValueError(f"No training data available for {marketplace}")
        
        X = pd.DataFrame(features_list)
        y = pd.Series(targets)
        
        return X, y
    
    async def train_model(
        self,
        marketplace: str,
        optimize_hyperparameters: bool = True
    ) -> Dict[str, Any]:
        """Train XGBoost model for price optimization"""
        logger.info(f"Training price optimization model for {marketplace}")
        
        # Prepare data
        X, y = await self.prepare_training_data(marketplace)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        if optimize_hyperparameters:
            # Hyperparameter optimization
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.05, 0.1],
                'subsample': [0.8, 0.9, 1.0],
                'colsample_bytree': [0.8, 0.9, 1.0]
            }
            
            xgb_model = xgb.XGBRegressor(
                objective='reg:squarederror',
                random_state=42
            )
            
            grid_search = GridSearchCV(
                xgb_model,
                param_grid,
                cv=5,
                scoring='neg_mean_absolute_error',
                n_jobs=-1,
                verbose=1
            )
            
            grid_search.fit(X_train, y_train)
            model = grid_search.best_estimator_
            
            logger.info(f"Best parameters: {grid_search.best_params_}")
        else:
            # Use default parameters
            model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective='reg:squarederror',
                random_state=42
            )
            
            model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        self.feature_importance[marketplace] = feature_importance
        
        # Save model
        self.models[marketplace] = model
        joblib.dump(model, f'models/{marketplace}_price_optimizer.pkl')
        
        return {
            'marketplace': marketplace,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'mae': float(mae),
            'r2_score': float(r2),
            'top_features': feature_importance.head(5).to_dict('records')
        }
    
    async def optimize_price(
        self,
        product_id: int,
        marketplace: str,
        current_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Optimize price for a specific product"""
        
        # Load model if not in memory
        if marketplace not in self.models:
            try:
                self.models[marketplace] = joblib.load(
                    f'models/{marketplace}_price_optimizer.pkl'
                )
            except FileNotFoundError:
                return {'error': f'No model available for {marketplace}'}
        
        model = self.models[marketplace]
        
        # Get product information
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
            return {'error': 'Product not found'}
        
        product, mp_product = product_data
        
        # Prepare current features
        current_features = {
            'cost': float(product.cost_price or 0),
            'current_price': float(mp_product.current_price or 0),
            'margin': (float(mp_product.current_price or 0) - float(product.cost_price or 0)) / float(mp_product.current_price or 1),
            'category_avg_price': await self._get_category_avg_price(product.category, marketplace),
            'competitor_min_price': await self._get_competitor_prices(product.id, marketplace)['min'],
            'competitor_avg_price': await self._get_competitor_prices(product.id, marketplace)['avg'],
            'demand_elasticity': await self._calculate_demand_elasticity(product.id, marketplace),
            'inventory_level': current_conditions.get('inventory_level', 100) if current_conditions else 100,
            'days_listed': (datetime.utcnow().date() - product.created_at.date()).days,
            'review_score': await self._get_avg_review_score(product.id),
            'season_factor': self._get_season_factor(datetime.utcnow().date()),
            'weekday': datetime.utcnow().weekday(),
            'month': datetime.utcnow().month,
            'ranking': current_conditions.get('ranking', 50) if current_conditions else 50,
            'conversion_rate': current_conditions.get('conversion_rate', 0.02) if current_conditions else 0.02
        }
        
        # Test different price points
        price_range = await self._get_price_test_range(product, mp_product, marketplace)
        
        results = []
        for test_price in price_range:
            # Update features with test price
            test_features = current_features.copy()
            test_features['current_price'] = test_price
            test_features['margin'] = (test_price - float(product.cost_price or 0)) / test_price
            
            # Predict revenue
            X_test = pd.DataFrame([test_features])
            predicted_revenue = model.predict(X_test)[0]
            
            # Calculate profit
            predicted_sales = predicted_revenue / test_price
            profit = (test_price - float(product.cost_price or 0)) * predicted_sales
            
            results.append({
                'price': test_price,
                'predicted_revenue': predicted_revenue,
                'predicted_sales': predicted_sales,
                'predicted_profit': profit,
                'margin': test_features['margin']
            })
        
        # Find optimal price
        optimal_result = max(results, key=lambda x: x['predicted_profit'])
        
        # Calculate price adjustment
        current_price = float(mp_product.current_price or 0)
        price_change = optimal_result['price'] - current_price
        price_change_pct = (price_change / current_price * 100) if current_price > 0 else 0
        
        # Prepare recommendation
        recommendation = {
            'product_id': product_id,
            'marketplace': marketplace,
            'current_price': current_price,
            'optimal_price': optimal_result['price'],
            'price_change': price_change,
            'price_change_percentage': price_change_pct,
            'expected_revenue_increase': optimal_result['predicted_revenue'] - results[0]['predicted_revenue'],
            'expected_profit_increase': optimal_result['predicted_profit'] - results[0]['predicted_profit'],
            'confidence_score': await self._calculate_confidence_score(product_id, marketplace),
            'constraints': {
                'min_margin': self.optimization_config['min_margin'],
                'max_margin': self.optimization_config['max_margin'],
                'competitor_threshold': self.optimization_config['competitor_threshold']
            },
            'analysis': {
                'all_results': results[:10],  # Top 10 results
                'feature_impact': self.feature_importance.get(marketplace, pd.DataFrame()).head(5).to_dict('records')
            }
        }
        
        # Save prediction
        await self._save_price_prediction(product_id, marketplace, recommendation)
        
        return recommendation
    
    async def _get_category_avg_price(
        self,
        category: str,
        marketplace: str
    ) -> float:
        """Get average price in category"""
        if not category:
            return 0.0
        
        stmt = select(
            func.avg(MarketplaceProduct.current_price)
        ).join(
            Product,
            MarketplaceProduct.product_id == Product.id
        ).where(
            and_(
                Product.category == category,
                MarketplaceProduct.marketplace == marketplace,
                MarketplaceProduct.listing_status == 'active'
            )
        )
        
        result = await self.session.execute(stmt)
        avg_price = result.scalar()
        
        return float(avg_price) if avg_price else 0.0
    
    async def _get_competitor_prices(
        self,
        product_id: int,
        marketplace: str
    ) -> Dict[str, float]:
        """Get competitor price statistics"""
        # Get product category
        stmt = select(Product.category).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        category = result.scalar()
        
        if not category:
            return {'min': 0.0, 'avg': 0.0, 'max': 0.0}
        
        # Get competitor prices
        stmt = select(
            func.min(MarketplaceProduct.current_price).label('min_price'),
            func.avg(MarketplaceProduct.current_price).label('avg_price'),
            func.max(MarketplaceProduct.current_price).label('max_price')
        ).join(
            Product,
            MarketplaceProduct.product_id == Product.id
        ).where(
            and_(
                Product.category == category,
                Product.id != product_id,
                MarketplaceProduct.marketplace == marketplace,
                MarketplaceProduct.listing_status == 'active'
            )
        )
        
        result = await self.session.execute(stmt)
        data = result.one()
        
        return {
            'min': float(data.min_price) if data.min_price else 0.0,
            'avg': float(data.avg_price) if data.avg_price else 0.0,
            'max': float(data.max_price) if data.max_price else 0.0
        }
    
    async def _calculate_demand_elasticity(
        self,
        product_id: int,
        marketplace: str
    ) -> float:
        """Calculate price elasticity of demand"""
        # Get historical price and sales data
        stmt = select(
            MarketplaceProduct.current_price,
            ProductPerformance.sales_volume,
            ProductPerformance.date
        ).join(
            ProductPerformance,
            and_(
                ProductPerformance.product_id == MarketplaceProduct.product_id,
                ProductPerformance.marketplace == marketplace
            )
        ).where(
            and_(
                MarketplaceProduct.product_id == product_id,
                MarketplaceProduct.marketplace == marketplace,
                ProductPerformance.sales_volume > 0
            )
        ).order_by(ProductPerformance.date.desc()).limit(30)
        
        result = await self.session.execute(stmt)
        data = result.all()
        
        if len(data) < 10:
            return -1.0  # Default elasticity
        
        # Simple elasticity calculation
        prices = [float(d.current_price) for d in data]
        quantities = [d.sales_volume for d in data]
        
        if len(set(prices)) < 2:  # No price variation
            return -1.0
        
        # Calculate percentage changes
        price_changes = []
        quantity_changes = []
        
        for i in range(1, len(data)):
            if prices[i-1] != prices[i]:
                price_pct_change = (prices[i] - prices[i-1]) / prices[i-1]
                quantity_pct_change = (quantities[i] - quantities[i-1]) / quantities[i-1] if quantities[i-1] > 0 else 0
                
                if price_pct_change != 0:
                    elasticity = quantity_pct_change / price_pct_change
                    if -5 < elasticity < 0:  # Reasonable range
                        price_changes.append(price_pct_change)
                        quantity_changes.append(quantity_pct_change)
        
        if not price_changes:
            return -1.0
        
        # Average elasticity
        elasticities = [q/p for q, p in zip(quantity_changes, price_changes) if p != 0]
        
        return np.mean(elasticities) if elasticities else -1.0
    
    async def _get_avg_review_score(self, product_id: int) -> float:
        """Get average review score"""
        stmt = select(
            func.avg(func.cast(Review.rating, Float))
        ).where(Review.product_id == product_id)
        
        result = await self.session.execute(stmt)
        avg_score = result.scalar()
        
        return float(avg_score) if avg_score else 3.5
    
    def _get_season_factor(self, date: datetime.date) -> float:
        """Get seasonal factor based on date"""
        month = date.month
        
        # Simple seasonal factors (would be more sophisticated in production)
        seasonal_factors = {
            1: 0.8,   # January - Post holiday slowdown
            2: 0.85,  # February
            3: 0.9,   # March
            4: 0.95,  # April
            5: 1.0,   # May
            6: 1.05,  # June
            7: 1.1,   # July - Summer peak
            8: 1.1,   # August
            9: 1.0,   # September
            10: 1.05, # October
            11: 1.2,  # November - Black Friday
            12: 1.3   # December - Holiday season
        }
        
        return seasonal_factors.get(month, 1.0)
    
    async def _get_price_test_range(
        self,
        product: Product,
        mp_product: MarketplaceProduct,
        marketplace: str
    ) -> List[float]:
        """Generate price points to test"""
        current_price = float(mp_product.current_price or 0)
        cost_price = float(product.cost_price or 0)
        
        # Get constraints
        min_margin = self.optimization_config['min_margin']
        max_margin = self.optimization_config['max_margin']
        
        # Calculate price bounds
        min_price = cost_price * (1 + min_margin)
        max_price = cost_price * (1 + max_margin)
        
        # Get competitor prices
        competitor_prices = await self._get_competitor_prices(product.id, marketplace)
        
        # Adjust based on competitor threshold
        competitor_threshold = self.optimization_config['competitor_threshold']
        if competitor_prices['min'] > 0:
            competitive_max = competitor_prices['avg'] * (1 + competitor_threshold)
            max_price = min(max_price, competitive_max)
        
        # Generate test prices
        adjustment_step = self.optimization_config['adjustment_step']
        
        test_prices = []
        price = min_price
        while price <= max_price:
            test_prices.append(round(price, -2))  # Round to nearest 100 won
            price *= (1 + adjustment_step)
        
        # Always include current price
        if current_price not in test_prices:
            test_prices.append(current_price)
        
        return sorted(test_prices)
    
    async def _calculate_confidence_score(
        self,
        product_id: int,
        marketplace: str
    ) -> float:
        """Calculate confidence in price recommendation"""
        # Factors affecting confidence:
        # 1. Amount of historical data
        # 2. Price stability
        # 3. Model performance
        
        # Get historical data count
        stmt = select(func.count(ProductPerformance.id)).where(
            and_(
                ProductPerformance.product_id == product_id,
                ProductPerformance.marketplace == marketplace
            )
        )
        
        result = await self.session.execute(stmt)
        data_points = result.scalar() or 0
        
        # Data confidence (more data = higher confidence)
        data_confidence = min(data_points / 100, 1.0)
        
        # Price stability confidence
        price_variance = await self._calculate_price_variance(product_id, marketplace)
        stability_confidence = max(0, 1 - (price_variance / 0.5))  # 50% variance = 0 confidence
        
        # Model confidence (would come from model evaluation metrics)
        model_confidence = 0.85  # Placeholder
        
        # Weighted average
        confidence = (
            data_confidence * 0.3 +
            stability_confidence * 0.3 +
            model_confidence * 0.4
        )
        
        return min(max(confidence, 0.1), 0.95)  # Bound between 0.1 and 0.95
    
    async def _calculate_price_variance(
        self,
        product_id: int,
        marketplace: str
    ) -> float:
        """Calculate price variance coefficient"""
        stmt = select(MarketplaceProduct.current_price).join(
            ProductPerformance,
            and_(
                ProductPerformance.product_id == MarketplaceProduct.product_id,
                ProductPerformance.marketplace == marketplace
            )
        ).where(
            MarketplaceProduct.product_id == product_id
        ).order_by(ProductPerformance.date.desc()).limit(30)
        
        result = await self.session.execute(stmt)
        prices = [float(r[0]) for r in result if r[0]]
        
        if len(prices) < 2:
            return 0.0
        
        mean_price = np.mean(prices)
        if mean_price == 0:
            return 0.0
        
        return np.std(prices) / mean_price
    
    async def _save_price_prediction(
        self,
        product_id: int,
        marketplace: str,
        recommendation: Dict[str, Any]
    ):
        """Save price optimization prediction"""
        prediction = AIPrediction(
            product_id=product_id,
            prediction_type='price_optimization',
            model_name='xgboost_price_optimizer',
            model_version='1.0',
            predictions={
                'marketplace': marketplace,
                'recommendation': recommendation
            },
            confidence_score=recommendation['confidence_score'],
            prediction_date=datetime.utcnow().date(),
            predicted_at=datetime.utcnow()
        )
        
        self.session.add(prediction)
        await self.session.commit()