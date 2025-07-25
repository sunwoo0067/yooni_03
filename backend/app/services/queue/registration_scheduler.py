"""
Registration Scheduler and Queue System for dropshipping
Handles batch processing, retry logic, and priority-based scheduling
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from app.models.product_registration import (
    ProductRegistrationBatch, ProductRegistration, RegistrationQueue,
    RegistrationStatus, RegistrationPriority, ImageProcessingJob
)
from app.services.registration.product_registration_engine import ProductRegistrationEngine
from app.services.image.image_processing_pipeline import ImageProcessingPipeline
from app.core.config import settings

logger = logging.getLogger(__name__)


class RegistrationScheduler:
    """High-performance registration scheduler with Redis queue management"""
    
    # Queue names
    QUEUE_NAMES = {
        RegistrationPriority.URGENT: "registration:urgent",
        RegistrationPriority.HIGH: "registration:high", 
        RegistrationPriority.MEDIUM: "registration:medium",
        RegistrationPriority.LOW: "registration:low"
    }
    
    # Processing queues
    IMAGE_PROCESSING_QUEUE = "image_processing"
    RETRY_QUEUE = "registration:retry"
    DEAD_LETTER_QUEUE = "registration:dead_letter"
    
    def __init__(
        self,
        db_session: AsyncSession,
        registration_engine: ProductRegistrationEngine,
        image_pipeline: ImageProcessingPipeline,
        redis_url: str = None
    ):
        """Initialize registration scheduler
        
        Args:
            db_session: Database session
            registration_engine: Product registration engine
            image_pipeline: Image processing pipeline
            redis_url: Redis connection URL
        """
        self.db_session = db_session
        self.registration_engine = registration_engine
        self.image_pipeline = image_pipeline
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = None
        self.is_running = False
        self.worker_tasks = []
        
        # Configuration
        self.max_workers = 5
        self.batch_size = 10
        self.retry_delays = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour
        self.max_retries = len(self.retry_delays)
    
    async def start(self):
        """Start the scheduler and worker processes"""
        if self.is_running:
            return
        
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            
            self.is_running = True
            
            # Start worker tasks
            self.worker_tasks = [
                asyncio.create_task(self._queue_worker(f"worker-{i}"))
                for i in range(self.max_workers)
            ]
            
            # Start scheduler task
            self.worker_tasks.append(
                asyncio.create_task(self._scheduler_loop())
            )
            
            # Start retry processor
            self.worker_tasks.append(
                asyncio.create_task(self._retry_processor())
            )
            
            # Start image processing worker
            self.worker_tasks.append(
                asyncio.create_task(self._image_processing_worker())
            )
            
            logger.info(f"Registration scheduler started with {self.max_workers} workers")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the scheduler and all workers"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Registration scheduler stopped")
    
    async def queue_batch_registration(
        self,
        batch_id: str,
        priority: RegistrationPriority = RegistrationPriority.MEDIUM,
        scheduled_at: Optional[datetime] = None
    ) -> bool:
        """Queue a batch for registration
        
        Args:
            batch_id: Batch ID to process
            priority: Processing priority
            scheduled_at: Optional scheduled time
            
        Returns:
            True if queued successfully
        """
        try:
            queue_name = self.QUEUE_NAMES[priority]
            
            task_data = {
                "task_type": "batch_registration",
                "batch_id": batch_id,
                "priority": priority.value,
                "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Add to appropriate priority queue
            if scheduled_at and scheduled_at > datetime.utcnow():
                # Schedule for later
                delay = (scheduled_at - datetime.utcnow()).total_seconds()
                await self.redis_client.zadd(
                    f"{queue_name}:scheduled",
                    {json.dumps(task_data): scheduled_at.timestamp()}
                )
            else:
                # Add to immediate processing queue
                await self.redis_client.lpush(queue_name, json.dumps(task_data))
            
            # Update batch status
            batch = await self.db_session.get(ProductRegistrationBatch, batch_id)
            if batch:
                batch.status = RegistrationStatus.PENDING
                await self.db_session.commit()
            
            logger.info(f"Queued batch {batch_id} with priority {priority.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue batch {batch_id}: {e}")
            return False
    
    async def queue_single_registration(
        self,
        user_id: str,
        product_data: Dict[str, Any],
        target_platforms: List[str],
        priority: RegistrationPriority = RegistrationPriority.HIGH
    ) -> bool:
        """Queue a single product registration
        
        Args:
            user_id: User ID
            product_data: Product information
            target_platforms: Target platforms
            priority: Processing priority
            
        Returns:
            True if queued successfully
        """
        try:
            queue_name = self.QUEUE_NAMES[priority]
            
            task_data = {
                "task_type": "single_registration",
                "user_id": user_id,
                "product_data": product_data,
                "target_platforms": target_platforms,
                "priority": priority.value,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.lpush(queue_name, json.dumps(task_data))
            
            logger.info(f"Queued single registration for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue single registration: {e}")
            return False
    
    async def queue_image_processing(
        self,
        product_registration_id: str,
        main_image_url: str,
        additional_images: List[str],
        target_platforms: List[str]
    ) -> bool:
        """Queue image processing job
        
        Args:
            product_registration_id: Product registration ID
            main_image_url: Main image URL
            additional_images: Additional image URLs
            target_platforms: Target platforms
            
        Returns:
            True if queued successfully
        """
        try:
            task_data = {
                "task_type": "image_processing",
                "product_registration_id": product_registration_id,
                "main_image_url": main_image_url,
                "additional_images": additional_images,
                "target_platforms": target_platforms,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.lpush(self.IMAGE_PROCESSING_QUEUE, json.dumps(task_data))
            
            logger.info(f"Queued image processing for product {product_registration_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue image processing: {e}")
            return False
    
    async def _scheduler_loop(self):
        """Main scheduler loop for processing scheduled tasks"""
        while self.is_running:
            try:
                await self._process_scheduled_tasks()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_scheduled_tasks(self):
        """Process scheduled tasks that are ready"""
        current_time = datetime.utcnow().timestamp()
        
        for priority in RegistrationPriority:
            queue_name = self.QUEUE_NAMES[priority]
            scheduled_queue = f"{queue_name}:scheduled"
            
            # Get tasks ready for processing
            ready_tasks = await self.redis_client.zrangebyscore(
                scheduled_queue,
                0,
                current_time,
                withscores=True
            )
            
            for task_json, score in ready_tasks:
                try:
                    # Move to immediate processing queue
                    await self.redis_client.lpush(queue_name, task_json)
                    await self.redis_client.zrem(scheduled_queue, task_json)
                    
                    logger.debug(f"Moved scheduled task to processing queue: {priority.value}")
                    
                except Exception as e:
                    logger.error(f"Failed to move scheduled task: {e}")
    
    async def _queue_worker(self, worker_id: str):
        """Worker process for handling registration tasks"""
        logger.info(f"Queue worker {worker_id} started")
        
        while self.is_running:
            try:
                # Check queues in priority order
                task_data = await self._get_next_task()
                
                if not task_data:
                    await asyncio.sleep(5)  # No tasks available
                    continue
                
                # Process the task
                await self._process_task(task_data, worker_id)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(10)
    
    async def _get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from priority queues"""
        # Check queues in priority order
        for priority in [
            RegistrationPriority.URGENT,
            RegistrationPriority.HIGH,
            RegistrationPriority.MEDIUM,
            RegistrationPriority.LOW
        ]:
            queue_name = self.QUEUE_NAMES[priority]
            
            # Try to get a task
            task_json = await self.redis_client.rpop(queue_name)
            if task_json:
                try:
                    return json.loads(task_json)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in queue {queue_name}: {task_json}")
                    continue
        
        return None
    
    async def _process_task(self, task_data: Dict[str, Any], worker_id: str):
        """Process a registration task"""
        task_type = task_data.get("task_type")
        
        try:
            if task_type == "batch_registration":
                await self._process_batch_registration(task_data, worker_id)
            elif task_type == "single_registration":
                await self._process_single_registration(task_data, worker_id)
            elif task_type == "retry":
                await self._process_retry_task(task_data, worker_id)
            else:
                logger.warning(f"Unknown task type: {task_type}")
                
        except Exception as e:
            logger.error(f"Task processing failed in {worker_id}: {e}")
            
            # Queue for retry if applicable
            await self._handle_task_failure(task_data, str(e))
    
    async def _process_batch_registration(self, task_data: Dict[str, Any], worker_id: str):
        """Process batch registration task"""
        batch_id = task_data["batch_id"]
        
        logger.info(f"Worker {worker_id} processing batch {batch_id}")
        
        # Process the batch
        result = await self.registration_engine.process_registration_batch(batch_id)
        
        if not result.success:
            raise Exception(f"Batch registration failed: {'; '.join(result.errors)}")
        
        logger.info(f"Worker {worker_id} completed batch {batch_id}")
    
    async def _process_single_registration(self, task_data: Dict[str, Any], worker_id: str):
        """Process single product registration task"""
        user_id = task_data["user_id"]
        product_data = task_data["product_data"]
        target_platforms = task_data["target_platforms"]
        
        logger.info(f"Worker {worker_id} processing single registration for user {user_id}")
        
        # Process the registration
        result = await self.registration_engine.register_single_product(
            user_id,
            product_data,
            target_platforms
        )
        
        if not result.success:
            raise Exception(f"Single registration failed: {'; '.join(result.errors)}")
        
        logger.info(f"Worker {worker_id} completed single registration")
    
    async def _process_retry_task(self, task_data: Dict[str, Any], worker_id: str):
        """Process retry task"""
        original_task = task_data["original_task"]
        retry_count = task_data["retry_count"]
        
        logger.info(f"Worker {worker_id} processing retry #{retry_count}")
        
        # Process the original task
        await self._process_task(original_task, worker_id)
    
    async def _handle_task_failure(self, task_data: Dict[str, Any], error: str):
        """Handle task failure and queue for retry if appropriate"""
        retry_count = task_data.get("retry_count", 0)
        
        if retry_count < self.max_retries:
            # Queue for retry
            retry_task = {
                "task_type": "retry",
                "original_task": task_data,
                "retry_count": retry_count + 1,
                "error": error,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Calculate retry delay
            delay_seconds = self.retry_delays[retry_count]
            retry_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
            
            await self.redis_client.zadd(
                f"{self.RETRY_QUEUE}:scheduled",
                {json.dumps(retry_task): retry_time.timestamp()}
            )
            
            logger.info(f"Queued task for retry #{retry_count + 1} in {delay_seconds} seconds")
        else:
            # Move to dead letter queue
            dead_letter_task = {
                **task_data,
                "final_error": error,
                "failed_at": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.lpush(
                self.DEAD_LETTER_QUEUE,
                json.dumps(dead_letter_task)
            )
            
            logger.error(f"Task moved to dead letter queue after {self.max_retries} retries")
    
    async def _retry_processor(self):
        """Process retry queue"""
        while self.is_running:
            try:
                current_time = datetime.utcnow().timestamp()
                
                # Get ready retry tasks
                ready_retries = await self.redis_client.zrangebyscore(
                    f"{self.RETRY_QUEUE}:scheduled",
                    0,
                    current_time,
                    withscores=True
                )
                
                for retry_json, score in ready_retries:
                    try:
                        # Move to retry processing queue
                        await self.redis_client.lpush(self.RETRY_QUEUE, retry_json)
                        await self.redis_client.zrem(f"{self.RETRY_QUEUE}:scheduled", retry_json)
                        
                    except Exception as e:
                        logger.error(f"Failed to move retry task: {e}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Retry processor error: {e}")
                await asyncio.sleep(60)
    
    async def _image_processing_worker(self):
        """Worker for image processing tasks"""
        logger.info("Image processing worker started")
        
        while self.is_running:
            try:
                # Get image processing task
                task_json = await self.redis_client.brpop(
                    self.IMAGE_PROCESSING_QUEUE,
                    timeout=5
                )
                
                if not task_json:
                    continue
                
                task_data = json.loads(task_json[1])
                
                # Process images
                await self._process_image_task(task_data)
                
            except Exception as e:
                logger.error(f"Image processing worker error: {e}")
                await asyncio.sleep(10)
    
    async def _process_image_task(self, task_data: Dict[str, Any]):
        """Process image processing task"""
        product_registration_id = task_data["product_registration_id"]
        main_image_url = task_data["main_image_url"]
        additional_images = task_data["additional_images"]
        target_platforms = task_data["target_platforms"]
        
        logger.info(f"Processing images for product {product_registration_id}")
        
        async with self.image_pipeline:
            result = await self.image_pipeline.process_product_images(
                product_registration_id,
                main_image_url,
                additional_images,
                target_platforms
            )
        
        # TODO: Update product registration with image processing results
        # This would require database updates
        
        logger.info(f"Completed image processing for product {product_registration_id}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {
            "queues": {},
            "workers": {
                "active": len([t for t in self.worker_tasks if not t.done()]),
                "total": len(self.worker_tasks)
            },
            "status": "running" if self.is_running else "stopped"
        }
        
        # Get queue lengths
        for priority in RegistrationPriority:
            queue_name = self.QUEUE_NAMES[priority]
            stats["queues"][priority.value] = {
                "pending": await self.redis_client.llen(queue_name),
                "scheduled": await self.redis_client.zcard(f"{queue_name}:scheduled")
            }
        
        # Special queues
        stats["queues"]["retry"] = {
            "pending": await self.redis_client.llen(self.RETRY_QUEUE),
            "scheduled": await self.redis_client.zcard(f"{self.RETRY_QUEUE}:scheduled")
        }
        
        stats["queues"]["image_processing"] = {
            "pending": await self.redis_client.llen(self.IMAGE_PROCESSING_QUEUE)
        }
        
        stats["queues"]["dead_letter"] = {
            "total": await self.redis_client.llen(self.DEAD_LETTER_QUEUE)
        }
        
        return stats
    
    async def clear_queue(self, queue_type: str) -> bool:
        """Clear specific queue
        
        Args:
            queue_type: Queue type to clear
            
        Returns:
            True if cleared successfully
        """
        try:
            if queue_type == "dead_letter":
                await self.redis_client.delete(self.DEAD_LETTER_QUEUE)
            elif queue_type == "retry":
                await self.redis_client.delete(self.RETRY_QUEUE)
                await self.redis_client.delete(f"{self.RETRY_QUEUE}:scheduled")
            elif queue_type == "image_processing":
                await self.redis_client.delete(self.IMAGE_PROCESSING_QUEUE)
            elif queue_type in [p.value for p in RegistrationPriority]:
                priority = RegistrationPriority(queue_type)
                queue_name = self.QUEUE_NAMES[priority]
                await self.redis_client.delete(queue_name)
                await self.redis_client.delete(f"{queue_name}:scheduled")
            else:
                return False
            
            logger.info(f"Cleared queue: {queue_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear queue {queue_type}: {e}")
            return False