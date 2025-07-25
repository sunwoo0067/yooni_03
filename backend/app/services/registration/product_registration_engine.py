"""
Product Registration Engine for multi-platform dropshipping
Handles batch registration, error recovery, and platform prioritization
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.platform_account import PlatformAccount, PlatformType, AccountStatus
from app.models.product_registration import (
    ProductRegistrationBatch, ProductRegistration, PlatformProductRegistration,
    RegistrationStatus, RegistrationPriority, RegistrationQueue, ImageProcessingJob,
    ImageProcessingStatus
)
from app.services.account.market_account_manager import MarketAccountManager
from app.services.platforms.platform_manager import PlatformManager
from app.core.config import settings

logger = logging.getLogger(__name__)


class RegistrationResult:
    """Registration result container"""
    
    def __init__(self):
        self.success = False
        self.platform_results = {}
        self.errors = []
        self.warnings = []
        self.total_registered = 0
        self.total_failed = 0
        self.processing_time = 0
    
    def add_platform_result(self, platform: str, success: bool, data: dict = None, error: str = None):
        """Add result for a specific platform"""
        self.platform_results[platform] = {
            "success": success,
            "data": data,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            self.total_registered += 1
        else:
            self.total_failed += 1
            if error:
                self.errors.append(f"{platform}: {error}")
    
    def get_summary(self) -> dict:
        """Get registration summary"""
        return {
            "success": self.success,
            "total_registered": self.total_registered,
            "total_failed": self.total_failed,
            "platform_results": self.platform_results,
            "errors": self.errors,
            "warnings": self.warnings,
            "processing_time_seconds": self.processing_time
        }


class ProductRegistrationEngine:
    """High-performance product registration engine with batch support"""
    
    def __init__(
        self,
        db_session: AsyncSession,
        account_manager: MarketAccountManager,
        platform_manager: PlatformManager,
        redis_client=None
    ):
        """Initialize registration engine
        
        Args:
            db_session: Database session
            account_manager: Market account manager
            platform_manager: Platform manager
            redis_client: Redis client for queuing
        """
        self.db_session = db_session
        self.account_manager = account_manager
        self.platform_manager = platform_manager
        self.redis_client = redis_client
        self.max_concurrent_registrations = 10
        self.retry_delays = [30, 60, 120, 300]  # Exponential backoff in seconds
    
    async def create_registration_batch(
        self,
        user_id: str,
        batch_name: str,
        products: List[Dict[str, Any]],
        target_platforms: List[str],
        priority: RegistrationPriority = RegistrationPriority.MEDIUM,
        batch_settings: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[datetime] = None
    ) -> ProductRegistrationBatch:
        """Create a new product registration batch
        
        Args:
            user_id: User ID
            batch_name: Name for the batch
            products: List of product data
            target_platforms: Target platform types
            priority: Registration priority
            batch_settings: Optional batch-specific settings
            scheduled_at: Optional scheduling time
            
        Returns:
            Created registration batch
        """
        try:
            # Create batch record
            batch = ProductRegistrationBatch(
                user_id=user_id,
                batch_name=batch_name,
                target_platforms=target_platforms,
                priority=priority,
                total_products=len(products),
                scheduled_at=scheduled_at or datetime.utcnow(),
                batch_settings=batch_settings or {}
            )
            
            self.db_session.add(batch)
            await self.db_session.flush()  # Get batch ID
            
            # Create individual product registrations
            product_registrations = []
            for product_data in products:
                registration = ProductRegistration(
                    batch_id=batch.id,
                    source_product_id=product_data.get("source_product_id"),
                    product_name=product_data["name"],
                    product_description=product_data.get("description"),
                    category_id=product_data.get("category_id"),
                    brand=product_data.get("brand"),
                    original_price=product_data.get("original_price"),
                    sale_price=product_data["price"],
                    cost_price=product_data.get("cost_price"),
                    stock_quantity=product_data.get("stock_quantity", 0),
                    weight=product_data.get("weight"),
                    dimensions=product_data.get("dimensions"),
                    main_image_url=product_data.get("main_image_url"),
                    additional_images=product_data.get("additional_images"),
                    attributes=product_data.get("attributes"),
                    keywords=product_data.get("keywords"),
                    tags=product_data.get("tags"),
                    scheduled_at=scheduled_at or datetime.utcnow()
                )
                product_registrations.append(registration)
            
            self.db_session.add_all(product_registrations)
            await self.db_session.commit()
            await self.db_session.refresh(batch)
            
            logger.info(f"Created registration batch {batch.id} with {len(products)} products")
            return batch
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to create registration batch: {e}")
            raise
    
    async def process_registration_batch(
        self,
        batch_id: str,
        force_process: bool = False
    ) -> RegistrationResult:
        """Process a registration batch
        
        Args:
            batch_id: Batch ID to process
            force_process: Force processing even if already processed
            
        Returns:
            Registration results
        """
        start_time = datetime.utcnow()
        result = RegistrationResult()
        
        try:
            # Load batch with products
            batch = await self._load_batch_with_products(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")
            
            # Check if already processed
            if not force_process and batch.status in [
                RegistrationStatus.COMPLETED,
                RegistrationStatus.PARTIALLY_COMPLETED
            ]:
                result.warnings.append("Batch already processed")
                return result
            
            # Update batch status
            batch.status = RegistrationStatus.IN_PROGRESS
            batch.started_at = datetime.utcnow()
            await self.db_session.commit()
            
            # Get active accounts for target platforms
            platform_types = [PlatformType(p) for p in batch.target_platforms]
            accounts = await self.account_manager.get_active_accounts(
                batch.user_id,
                platforms=platform_types,
                prioritized=True
            )
            
            if not accounts:
                raise ValueError("No active accounts available for target platforms")
            
            # Process products in parallel with concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_registrations)
            tasks = []
            
            for product in batch.product_registrations:
                if product.overall_status == RegistrationStatus.PENDING:
                    task = self._process_single_product_with_semaphore(
                        semaphore, product, accounts, result
                    )
                    tasks.append(task)
            
            # Wait for all registrations to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update batch completion status
            await self._update_batch_completion_status(batch)
            
            # Calculate processing time
            result.processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.success = batch.status == RegistrationStatus.COMPLETED
            
            logger.info(f"Processed batch {batch_id}: {result.total_registered} success, {result.total_failed} failed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process batch {batch_id}: {e}")
            result.errors.append(str(e))
            
            # Update batch status to failed
            try:
                batch = await self.db_session.get(ProductRegistrationBatch, batch_id)
                if batch:
                    batch.status = RegistrationStatus.FAILED
                    batch.last_error_message = str(e)
                    await self.db_session.commit()
            except Exception:
                pass
            
            return result
    
    async def register_single_product(
        self,
        user_id: str,
        product_data: Dict[str, Any],
        target_platforms: List[str],
        priority: RegistrationPriority = RegistrationPriority.HIGH
    ) -> RegistrationResult:
        """Register a single product across platforms
        
        Args:
            user_id: User ID
            product_data: Product information
            target_platforms: Target platform types
            priority: Registration priority
            
        Returns:
            Registration results
        """
        # Create a single-product batch
        batch = await self.create_registration_batch(
            user_id=user_id,
            batch_name=f"Single Product: {product_data['name']}",
            products=[product_data],
            target_platforms=target_platforms,
            priority=priority
        )
        
        # Process immediately
        return await self.process_registration_batch(str(batch.id))
    
    async def retry_failed_registrations(
        self,
        batch_id: str,
        platform_filter: Optional[List[str]] = None
    ) -> RegistrationResult:
        """Retry failed registrations in a batch
        
        Args:
            batch_id: Batch ID
            platform_filter: Optional platform filter for retries
            
        Returns:
            Retry results
        """
        result = RegistrationResult()
        
        try:
            # Load batch with failed registrations
            batch = await self._load_batch_with_products(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")
            
            # Find failed platform registrations
            failed_registrations = []
            for product in batch.product_registrations:
                for platform_reg in product.platform_registrations:
                    if (platform_reg.status == RegistrationStatus.FAILED and
                        platform_reg.can_retry(batch.max_retry_attempts) and
                        (not platform_filter or platform_reg.platform_type in platform_filter)):
                        failed_registrations.append(platform_reg)
            
            if not failed_registrations:
                result.warnings.append("No failed registrations found for retry")
                return result
            
            # Get active accounts
            platform_types = list(set(reg.platform_type for reg in failed_registrations))
            accounts = await self.account_manager.get_active_accounts(
                batch.user_id,
                platforms=[PlatformType(p) for p in platform_types],
                prioritized=True
            )
            
            # Retry registrations
            semaphore = asyncio.Semaphore(self.max_concurrent_registrations)
            tasks = []
            
            for platform_reg in failed_registrations:
                account = next((a for a in accounts if a.platform_type.value == platform_reg.platform_type), None)
                if account:
                    task = self._retry_platform_registration_with_semaphore(
                        semaphore, platform_reg, account, result
                    )
                    tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update batch status
            await self._update_batch_completion_status(batch)
            
            result.success = True
            return result
            
        except Exception as e:
            logger.error(f"Failed to retry registrations for batch {batch_id}: {e}")
            result.errors.append(str(e))
            return result
    
    async def _process_single_product_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        product: ProductRegistration,
        accounts: List[PlatformAccount],
        result: RegistrationResult
    ):
        """Process single product with concurrency control"""
        async with semaphore:
            await self._process_single_product(product, accounts, result)
    
    async def _process_single_product(
        self,
        product: ProductRegistration,
        accounts: List[PlatformAccount],
        result: RegistrationResult
    ):
        """Process registration for a single product"""
        try:
            product.overall_status = RegistrationStatus.IN_PROGRESS
            product.started_at = datetime.utcnow()
            await self.db_session.commit()
            
            # Create platform registrations
            platform_registrations = []
            for account in accounts:
                platform_reg = PlatformProductRegistration(
                    product_registration_id=product.id,
                    platform_account_id=account.id,
                    platform_type=account.platform_type.value,
                    platform_product_data=await self._transform_product_for_platform(
                        product, account.platform_type
                    ),
                    scheduled_at=datetime.utcnow()
                )
                platform_registrations.append(platform_reg)
            
            self.db_session.add_all(platform_registrations)
            await self.db_session.commit()
            
            # Process each platform registration
            tasks = []
            for platform_reg in platform_registrations:
                account = next(a for a in accounts if a.id == platform_reg.platform_account_id)
                task = self._register_on_platform(platform_reg, account, result)
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update product overall status
            await self._update_product_overall_status(product)
            
        except Exception as e:
            logger.error(f"Failed to process product {product.id}: {e}")
            product.overall_status = RegistrationStatus.FAILED
            await self.db_session.commit()
            result.errors.append(f"Product {product.product_name}: {str(e)}")
    
    async def _register_on_platform(
        self,
        platform_reg: PlatformProductRegistration,
        account: PlatformAccount,
        result: RegistrationResult
    ):
        """Register product on a specific platform"""
        try:
            platform_reg.status = RegistrationStatus.IN_PROGRESS
            platform_reg.started_at = datetime.utcnow()
            await self.db_session.commit()
            
            # Get platform API
            api = await self.platform_manager.get_platform_api(
                account.platform_type,
                str(account.id)
            )
            
            # Make API call
            api_response = await api.create_product(platform_reg.platform_product_data)
            platform_reg.api_response_data = api_response
            platform_reg.api_call_count += 1
            
            # Extract product ID from response
            platform_product_id = self._extract_platform_product_id(
                api_response,
                account.platform_type
            )
            
            if platform_product_id:
                platform_reg.platform_product_id = platform_product_id
                platform_reg.status = RegistrationStatus.COMPLETED
                platform_reg.completed_at = datetime.utcnow()
                
                result.add_platform_result(
                    account.platform_type.value,
                    True,
                    {"product_id": platform_product_id}
                )
                
                # Update account API usage
                await self.account_manager.update_api_usage(
                    str(account.id),
                    1,
                    success=True
                )
            else:
                raise Exception("Failed to extract product ID from response")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to register on {account.platform_type.value}: {error_msg}")
            
            platform_reg.status = RegistrationStatus.FAILED
            platform_reg.error_message = error_msg
            platform_reg.retry_count += 1
            
            result.add_platform_result(
                account.platform_type.value,
                False,
                error=error_msg
            )
            
            # Update account API usage
            await self.account_manager.update_api_usage(
                str(account.id),
                1,
                success=False
            )
        
        finally:
            await self.db_session.commit()
    
    async def _retry_platform_registration_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        platform_reg: PlatformProductRegistration,
        account: PlatformAccount,
        result: RegistrationResult
    ):
        """Retry platform registration with concurrency control"""
        async with semaphore:
            await self._register_on_platform(platform_reg, account, result)
    
    async def _transform_product_for_platform(
        self,
        product: ProductRegistration,
        platform_type: PlatformType
    ) -> Dict[str, Any]:
        """Transform product data for specific platform"""
        base_data = {
            "name": product.product_name,
            "description": product.product_description,
            "price": float(product.sale_price),
            "original_price": float(product.original_price) if product.original_price else None,
            "stock_quantity": product.stock_quantity,
            "weight": float(product.weight) if product.weight else None,
            "category_id": product.category_id,
            "brand": product.brand,
            "main_image_url": product.main_image_url,
            "additional_images": product.additional_images or [],
            "attributes": product.attributes or {},
            "keywords": product.keywords or [],
            "tags": product.tags or []
        }
        
        # Use platform manager's transformation logic
        return self.platform_manager._transform_product_data_for_platform(
            base_data,
            platform_type
        )
    
    def _extract_platform_product_id(
        self,
        api_response: Dict[str, Any],
        platform_type: PlatformType
    ) -> Optional[str]:
        """Extract product ID from platform API response"""
        return self.platform_manager._extract_product_id(api_response, platform_type)
    
    async def _load_batch_with_products(self, batch_id: str) -> Optional[ProductRegistrationBatch]:
        """Load batch with all related products and platform registrations"""
        query = select(ProductRegistrationBatch).where(
            ProductRegistrationBatch.id == batch_id
        ).options(
            selectinload(ProductRegistrationBatch.product_registrations).selectinload(
                ProductRegistration.platform_registrations
            )
        )
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def _update_product_overall_status(self, product: ProductRegistration):
        """Update product overall status based on platform results"""
        # Refresh platform registrations
        await self.db_session.refresh(product, ["platform_registrations"])
        
        if not product.platform_registrations:
            return
        
        statuses = [reg.status for reg in product.platform_registrations]
        
        if all(s == RegistrationStatus.COMPLETED for s in statuses):
            product.overall_status = RegistrationStatus.COMPLETED
            product.completed_at = datetime.utcnow()
        elif all(s == RegistrationStatus.FAILED for s in statuses):
            product.overall_status = RegistrationStatus.FAILED
        elif any(s == RegistrationStatus.IN_PROGRESS for s in statuses):
            product.overall_status = RegistrationStatus.IN_PROGRESS
        elif any(s == RegistrationStatus.COMPLETED for s in statuses):
            product.overall_status = RegistrationStatus.PARTIALLY_COMPLETED
        
        await self.db_session.commit()
    
    async def _update_batch_completion_status(self, batch: ProductRegistrationBatch):
        """Update batch completion status"""
        # Refresh products
        await self.db_session.refresh(batch, ["product_registrations"])
        
        total_products = len(batch.product_registrations)
        completed_products = sum(
            1 for p in batch.product_registrations
            if p.overall_status in [RegistrationStatus.COMPLETED, RegistrationStatus.PARTIALLY_COMPLETED]
        )
        failed_products = sum(
            1 for p in batch.product_registrations
            if p.overall_status == RegistrationStatus.FAILED
        )
        
        batch.completed_products = completed_products
        batch.failed_products = failed_products
        batch.calculate_progress()
        
        if completed_products == total_products:
            batch.status = RegistrationStatus.COMPLETED
            batch.completed_at = datetime.utcnow()
        elif completed_products > 0:
            batch.status = RegistrationStatus.PARTIALLY_COMPLETED
        elif failed_products == total_products:
            batch.status = RegistrationStatus.FAILED
        
        await self.db_session.commit()
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get detailed status of a registration batch"""
        batch = await self._load_batch_with_products(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        platform_summary = {}
        for product in batch.product_registrations:
            for platform_reg in product.platform_registrations:
                platform = platform_reg.platform_type
                if platform not in platform_summary:
                    platform_summary[platform] = {
                        "total": 0,
                        "completed": 0,
                        "failed": 0,
                        "in_progress": 0
                    }
                
                platform_summary[platform]["total"] += 1
                if platform_reg.status == RegistrationStatus.COMPLETED:
                    platform_summary[platform]["completed"] += 1
                elif platform_reg.status == RegistrationStatus.FAILED:
                    platform_summary[platform]["failed"] += 1
                elif platform_reg.status == RegistrationStatus.IN_PROGRESS:
                    platform_summary[platform]["in_progress"] += 1
        
        return {
            "batch_id": str(batch.id),
            "batch_name": batch.batch_name,
            "status": batch.status.value,
            "total_products": batch.total_products,
            "completed_products": batch.completed_products,
            "failed_products": batch.failed_products,
            "progress_percentage": float(batch.progress_percentage),
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "platform_summary": platform_summary
        }
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a pending or in-progress batch"""
        try:
            batch = await self.db_session.get(ProductRegistrationBatch, batch_id)
            if not batch:
                return False
            
            if batch.status in [RegistrationStatus.COMPLETED, RegistrationStatus.CANCELLED]:
                return False
            
            batch.status = RegistrationStatus.CANCELLED
            await self.db_session.commit()
            
            logger.info(f"Cancelled batch {batch_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel batch {batch_id}: {e}")
            return False