"""Task scheduler for automated operations"""
import asyncio
import schedule
import time
from datetime import datetime
import yaml
from pathlib import Path
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import db_manager
from src.collectors.data_aggregator import DataAggregator
from src.optimizers.rotation_manager import RotationManager
from src.predictors.sales_predictor import SalesPredictor
from src.analyzers.review_analyzer import ReviewAnalyzer
from src.dashboard.metrics_calculator import MetricsCalculator
from src.dashboard.alert_manager import AlertManager

# Load configuration
config_path = Path(__file__).parent.parent / "configs" / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

logger = structlog.get_logger()


class TaskScheduler:
    """Manages scheduled tasks for the system"""
    
    def __init__(self):
        self.config = config
        self.running = False
    
    async def initialize(self):
        """Initialize database connection"""
        await db_manager.initialize()
    
    async def shutdown(self):
        """Cleanup resources"""
        await db_manager.close()
    
    async def collect_marketplace_data(self):
        """Scheduled task: Collect data from all marketplaces"""
        logger.info("Starting marketplace data collection")
        
        async with db_manager.get_session() as session:
            try:
                # Get all active products
                from src.database.models import Product
                from sqlalchemy import select
                
                stmt = select(Product).where(Product.status == 'active')
                result = await session.execute(stmt)
                products = result.scalars().all()
                
                product_ids = [p.product_code for p in products]
                
                # Collect data
                aggregator = DataAggregator(self.config, session)
                results = await aggregator.collect_all_marketplace_data(product_ids)
                
                logger.info(
                    "Data collection completed",
                    products_count=len(product_ids),
                    successful=results['summary']['successful_collections']
                )
                
            except Exception as e:
                logger.error(f"Data collection failed: {str(e)}")
    
    async def analyze_reviews(self):
        """Scheduled task: Analyze new reviews"""
        logger.info("Starting review analysis")
        
        async with db_manager.get_session() as session:
            try:
                analyzer = ReviewAnalyzer(self.config, session)
                
                # Get products with unanalyzed reviews
                from src.database.models import Product, Review, ReviewAnalytics
                from sqlalchemy import select, and_
                
                stmt = select(Product).join(
                    Review,
                    Product.id == Review.product_id
                ).outerjoin(
                    ReviewAnalytics,
                    Review.id == ReviewAnalytics.review_id
                ).where(
                    ReviewAnalytics.id.is_(None)
                ).distinct()
                
                result = await session.execute(stmt)
                products = result.scalars().all()
                
                total_analyzed = 0
                for product in products:
                    results = await analyzer.analyze_batch_reviews(product.id)
                    total_analyzed += results['analyzed_count']
                
                logger.info(f"Review analysis completed: {total_analyzed} reviews analyzed")
                
            except Exception as e:
                logger.error(f"Review analysis failed: {str(e)}")
    
    async def check_rotation_candidates(self):
        """Scheduled task: Check for products needing rotation"""
        logger.info("Checking rotation candidates")
        
        async with db_manager.get_session() as session:
            try:
                manager = RotationManager(self.config, session)
                candidates = await manager.evaluate_rotation_candidates()
                
                logger.info(f"Found {len(candidates)} rotation candidates")
                
                # Auto-rotate high priority candidates
                for candidate in candidates[:5]:  # Top 5 candidates
                    if candidate['priority'] > 0.8:
                        result = await manager.rotate_product(
                            candidate['product_id'],
                            candidate['strategy'],
                            candidate['marketplace']
                        )
                        
                        if result['success']:
                            logger.info(
                                f"Auto-rotated product {candidate['product_id']} "
                                f"using {candidate['strategy']} strategy"
                            )
                
            except Exception as e:
                logger.error(f"Rotation check failed: {str(e)}")
    
    async def update_predictions(self):
        """Scheduled task: Update ML predictions"""
        logger.info("Updating predictions")
        
        async with db_manager.get_session() as session:
            try:
                predictor = SalesPredictor(self.config, session)
                
                # Get active products
                from src.database.models import Product
                from sqlalchemy import select
                
                stmt = select(Product).where(Product.status == 'active').limit(50)
                result = await session.execute(stmt)
                products = result.scalars().all()
                
                prediction_count = 0
                for product in products:
                    for marketplace in ['coupang', 'naver']:
                        try:
                            await predictor.predict_sales(product.id, marketplace)
                            prediction_count += 1
                        except Exception as e:
                            logger.warning(
                                f"Prediction failed for product {product.id} "
                                f"on {marketplace}: {str(e)}"
                            )
                
                logger.info(f"Updated {prediction_count} predictions")
                
            except Exception as e:
                logger.error(f"Prediction update failed: {str(e)}")
    
    async def calculate_daily_metrics(self):
        """Scheduled task: Calculate daily dashboard metrics"""
        logger.info("Calculating daily metrics")
        
        async with db_manager.get_session() as session:
            try:
                calculator = MetricsCalculator(session)
                metrics = await calculator.calculate_daily_metrics()
                
                logger.info("Daily metrics calculated successfully")
                
            except Exception as e:
                logger.error(f"Metrics calculation failed: {str(e)}")
    
    async def check_system_alerts(self):
        """Scheduled task: Check for system alerts"""
        logger.info("Checking system alerts")
        
        async with db_manager.get_session() as session:
            try:
                alert_manager = AlertManager(self.config, session)
                alerts = await alert_manager.check_all_alerts()
                
                logger.info(f"Alert check completed: {len(alerts)} new alerts")
                
            except Exception as e:
                logger.error(f"Alert check failed: {str(e)}")
    
    def setup_schedule(self):
        """Setup scheduled tasks based on configuration"""
        schedules = self.config['data_collection']['schedule']
        
        # Data collection tasks
        schedule.every(30).minutes.do(
            lambda: asyncio.create_task(self.collect_marketplace_data())
        )
        
        # Review analysis
        schedule.every(2).hours.do(
            lambda: asyncio.create_task(self.analyze_reviews())
        )
        
        # Rotation checks
        schedule.every(6).hours.do(
            lambda: asyncio.create_task(self.check_rotation_candidates())
        )
        
        # Prediction updates
        schedule.every().day.at("02:00").do(
            lambda: asyncio.create_task(self.update_predictions())
        )
        
        # Daily metrics
        schedule.every().day.at("00:30").do(
            lambda: asyncio.create_task(self.calculate_daily_metrics())
        )
        
        # Alert checks
        schedule.every(15).minutes.do(
            lambda: asyncio.create_task(self.check_system_alerts())
        )
        
        logger.info("Task schedule configured")
    
    async def run(self):
        """Run the scheduler"""
        self.running = True
        self.setup_schedule()
        
        logger.info("Task scheduler started")
        
        # Run initial tasks
        await self.collect_marketplace_data()
        await self.check_system_alerts()
        
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Task scheduler stopped")


async def main():
    """Main entry point"""
    scheduler = TaskScheduler()
    
    try:
        await scheduler.initialize()
        await scheduler.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        scheduler.stop()
        await scheduler.shutdown()


if __name__ == "__main__":
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    asyncio.run(main())