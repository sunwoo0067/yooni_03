"""
Unified Dropshipping Service
Integrates all components for complete dropshipping automation
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.services.account.market_account_manager import MarketAccountManager
from app.services.registration.product_registration_engine import ProductRegistrationEngine
from app.services.queue.registration_scheduler import RegistrationScheduler
from app.services.image.image_processing_pipeline import ImageProcessingPipeline
from app.services.platforms.enhanced_platform_factory import EnhancedPlatformFactory, get_platform_factory
from app.services.monitoring.error_handler import ErrorHandler, get_error_handler
from app.models.platform_account import PlatformType
from app.models.product_registration import RegistrationPriority
from app.core.config import settings

logger = logging.getLogger(__name__)


class DropshippingService:
    """
    Unified dropshipping service that orchestrates all components
    Provides high-level API for dropshipping operations
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        supabase_client=None
    ):
        """Initialize dropshipping service
        
        Args:
            db_session: Database session
            redis_client: Redis client for queuing
            supabase_client: Supabase client for image storage
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self.supabase_client = supabase_client
        
        # Initialize core services
        self.account_manager = MarketAccountManager(db_session, redis_client)
        self.platform_factory = get_platform_factory()
        self.error_handler = get_error_handler()
        
        # Initialize processing services
        self.image_pipeline = ImageProcessingPipeline(supabase_client)
        self.registration_engine = None  # Will be initialized when platform_manager is ready
        self.scheduler = None
        
        # Service state
        self.is_initialized = False
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Initialize all services and dependencies"""
        try:
            logger.info("Initializing dropshipping service...")
            
            # Initialize platform manager (would need actual implementation)
            # For now, we'll create a placeholder
            from app.services.platforms.platform_manager import PlatformManager
            platform_manager = PlatformManager(self.db_session)
            
            # Initialize registration engine
            self.registration_engine = ProductRegistrationEngine(
                self.db_session,
                self.account_manager,
                platform_manager,
                self.redis_client
            )
            
            # Initialize scheduler
            if self.redis_client:
                self.scheduler = RegistrationScheduler(
                    self.db_session,
                    self.registration_engine,
                    self.image_pipeline,
                    settings.REDIS_URL
                )
            
            self.is_initialized = True
            logger.info("Dropshipping service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize dropshipping service: {e}")
            await self.error_handler.handle_error(e, {"component": "service_initialization"})
            return False
    
    async def start(self) -> bool:
        """Start all background services"""
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        try:
            # Start scheduler if available
            if self.scheduler:
                await self.scheduler.start()
            
            self.is_running = True
            logger.info("Dropshipping service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start dropshipping service: {e}")
            await self.error_handler.handle_error(e, {"component": "service_startup"})
            return False
    
    async def stop(self) -> bool:
        """Stop all background services"""
        try:
            # Stop scheduler
            if self.scheduler:
                await self.scheduler.stop()
            
            # Cleanup platform factory
            await self.platform_factory.cleanup_instances()
            
            self.is_running = False
            logger.info("Dropshipping service stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop dropshipping service: {e}")
            return False
    
    async def register_products_batch(
        self,
        user_id: str,
        batch_name: str,
        products: List[Dict[str, Any]],
        target_platforms: List[str],
        priority: str = "medium",
        scheduled_at: Optional[datetime] = None,
        batch_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register multiple products across platforms
        
        Args:
            user_id: User ID
            batch_name: Name for the batch
            products: List of product data
            target_platforms: Target platform types
            priority: Registration priority
            scheduled_at: Optional scheduling time
            batch_settings: Optional batch-specific settings
            
        Returns:
            Batch registration result
        """
        try:
            if not self.is_initialized:
                raise Exception("Service not initialized")
            
            # Validate platforms
            valid_platforms = [p.value for p in PlatformType]
            invalid_platforms = [p for p in target_platforms if p not in valid_platforms]
            if invalid_platforms:
                raise ValueError(f"Invalid platforms: {invalid_platforms}")
            
            # Check user accounts
            platform_types = [PlatformType(p) for p in target_platforms]
            accounts = await self.account_manager.get_active_accounts(
                user_id,
                platforms=platform_types,
                prioritized=True
            )
            
            if not accounts:
                raise ValueError("No active accounts found for target platforms")
            
            # Create batch
            batch = await self.registration_engine.create_registration_batch(
                user_id=user_id,
                batch_name=batch_name,
                products=products,
                target_platforms=target_platforms,
                priority=RegistrationPriority(priority),
                batch_settings=batch_settings,
                scheduled_at=scheduled_at
            )
            
            # Queue for processing
            if self.scheduler:
                await self.scheduler.queue_batch_registration(
                    str(batch.id),
                    RegistrationPriority(priority),
                    scheduled_at
                )
            
            return {
                "success": True,
                "batch_id": str(batch.id),
                "batch_name": batch.batch_name,
                "total_products": batch.total_products,
                "target_platforms": target_platforms,
                "message": "Batch created and queued for processing"
            }
            
        except Exception as e:
            logger.error(f"Failed to register products batch: {e}")
            await self.error_handler.handle_error(
                e,
                {"user_id": user_id, "batch_name": batch_name, "platforms": target_platforms}
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    async def register_single_product(
        self,
        user_id: str,
        product_data: Dict[str, Any],
        target_platforms: List[str],
        priority: str = "high"
    ) -> Dict[str, Any]:
        """
        Register a single product across platforms
        
        Args:
            user_id: User ID
            product_data: Product information
            target_platforms: Target platform types
            priority: Registration priority
            
        Returns:
            Registration result
        """
        try:
            if not self.is_initialized:
                raise Exception("Service not initialized")
            
            # Queue for immediate processing
            if self.scheduler:
                await self.scheduler.queue_single_registration(
                    user_id,
                    product_data,
                    target_platforms,
                    RegistrationPriority(priority)
                )
            
            return {
                "success": True,
                "message": "Single product registration queued for processing",
                "target_platforms": target_platforms
            }
            
        except Exception as e:
            logger.error(f"Failed to register single product: {e}")
            await self.error_handler.handle_error(
                e,
                {"user_id": user_id, "product": product_data.get("name"), "platforms": target_platforms}
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get detailed status of a registration batch"""
        try:
            if not self.registration_engine:
                raise Exception("Registration engine not available")
            
            return await self.registration_engine.get_batch_status(batch_id)
            
        except Exception as e:
            logger.error(f"Failed to get batch status: {e}")
            await self.error_handler.handle_error(e, {"batch_id": batch_id})
            return {
                "error": str(e)
            }
    
    async def retry_failed_registrations(
        self,
        batch_id: str,
        platform_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Retry failed registrations in a batch"""
        try:
            if not self.registration_engine:
                raise Exception("Registration engine not available")
            
            result = await self.registration_engine.retry_failed_registrations(
                batch_id,
                platform_filter
            )
            
            return {
                "success": result.success,
                "total_registered": result.total_registered,
                "total_failed": result.total_failed,
                "platform_results": result.platform_results
            }
            
        except Exception as e:
            logger.error(f"Failed to retry batch registrations: {e}")
            await self.error_handler.handle_error(
                e,
                {"batch_id": batch_id, "platform_filter": platform_filter}
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cancel_batch(self, batch_id: str) -> Dict[str, Any]:
        """Cancel a pending or in-progress batch"""
        try:
            if not self.registration_engine:
                raise Exception("Registration engine not available")
            
            success = await self.registration_engine.cancel_batch(batch_id)
            
            return {
                "success": success,
                "message": "Batch cancelled successfully" if success else "Batch cannot be cancelled"
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel batch: {e}")
            await self.error_handler.handle_error(e, {"batch_id": batch_id})
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_product_images(
        self,
        product_registration_id: str,
        main_image_url: str,
        additional_images: List[str],
        target_platforms: List[str]
    ) -> Dict[str, Any]:
        """Process images for product registration"""
        try:
            async with self.image_pipeline:
                result = await self.image_pipeline.process_product_images(
                    product_registration_id,
                    main_image_url,
                    additional_images,
                    target_platforms
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process product images: {e}")
            await self.error_handler.handle_error(
                e,
                {"product_registration_id": product_registration_id, "platforms": target_platforms}
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_account_health(self, user_id: str) -> Dict[str, Any]:
        """Get health status of user's platform accounts"""
        try:
            return await self.account_manager.bulk_health_check(user_id)
            
        except Exception as e:
            logger.error(f"Failed to get account health: {e}")
            await self.error_handler.handle_error(e, {"user_id": user_id})
            return {
                "error": str(e)
            }
    
    async def get_optimal_distribution(
        self,
        user_id: str,
        product_count: int,
        target_platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get optimal account distribution for batch registration"""
        try:
            platform_types = None
            if target_platforms:
                platform_types = [PlatformType(p) for p in target_platforms]
            
            return await self.account_manager.get_optimal_account_distribution(
                user_id,
                product_count,
                platform_types
            )
            
        except Exception as e:
            logger.error(f"Failed to get optimal distribution: {e}")
            await self.error_handler.handle_error(
                e,
                {"user_id": user_id, "product_count": product_count, "platforms": target_platforms}
            )
            return {
                "error": str(e)
            }
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get registration queue statistics"""
        try:
            if not self.scheduler:
                return {"error": "Scheduler not available"}
            
            return await self.scheduler.get_queue_stats()
            
        except Exception as e:
            logger.error(f"Failed to get queue statistics: {e}")
            await self.error_handler.handle_error(e)
            return {
                "error": str(e)
            }
    
    async def get_platform_health(self) -> Dict[str, Any]:
        """Get health status of all platforms"""
        try:
            return await self.platform_factory.health_check_all_platforms()
            
        except Exception as e:
            logger.error(f"Failed to get platform health: {e}")
            await self.error_handler.handle_error(e)
            return {
                "error": str(e)
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            return {
                "service_status": {
                    "initialized": self.is_initialized,
                    "running": self.is_running,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "platform_factory": self.platform_factory.get_factory_stats(),
                "queue_stats": await self.get_queue_statistics() if self.scheduler else None,
                "platform_health": await self.get_platform_health(),
                "error_stats": await self.error_handler.get_error_statistics()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global service instance
_dropshipping_service: Optional[DropshippingService] = None


async def get_dropshipping_service(
    db_session: AsyncSession,
    redis_client: Optional[redis.Redis] = None,
    supabase_client=None
) -> DropshippingService:
    """Get or create dropshipping service instance"""
    global _dropshipping_service
    
    if _dropshipping_service is None:
        _dropshipping_service = DropshippingService(
            db_session,
            redis_client,
            supabase_client
        )
        
        # Initialize if not already done
        if not _dropshipping_service.is_initialized:
            await _dropshipping_service.initialize()
    
    return _dropshipping_service


async def cleanup_dropshipping_service():
    """Cleanup global dropshipping service"""
    global _dropshipping_service
    
    if _dropshipping_service:
        await _dropshipping_service.stop()
        _dropshipping_service = None