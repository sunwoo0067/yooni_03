"""
대량 데이터 처리를 위한 배치 시스템
메모리 효율적인 처리와 병렬 처리 지원
"""

import asyncio
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, AsyncIterator
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db_context

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """배치 작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchResult(BaseModel):
    """배치 작업 결과"""
    batch_id: str
    status: BatchStatus
    total_items: int
    processed_items: int
    success_items: int
    failed_items: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    errors: List[Dict[str, Any]] = []
    
    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.processed_items == 0:
            return 0.0
        return (self.success_items / self.processed_items) * 100


class BatchProcessor:
    """배치 처리 프로세서"""
    
    def __init__(
        self,
        batch_size: int = 100,
        max_workers: int = 5,
        error_threshold: float = 0.1,  # 10% 에러율 허용
        retry_failed: bool = True,
        retry_attempts: int = 3
    ):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.error_threshold = error_threshold
        self.retry_failed = retry_failed
        self.retry_attempts = retry_attempts
        self.results: Dict[str, BatchResult] = {}
        
    async def process_batch(
        self,
        items: Union[List[Any], AsyncIterator[Any]],
        processor: Callable[[Any], Any],
        batch_id: Optional[str] = None,
        progress_callback: Optional[Callable[[BatchResult], None]] = None
    ) -> BatchResult:
        """배치 처리 실행"""
        batch_id = batch_id or str(uuid4())
        
        # 결과 초기화
        result = BatchResult(
            batch_id=batch_id,
            status=BatchStatus.RUNNING,
            total_items=0,
            processed_items=0,
            success_items=0,
            failed_items=0,
            start_time=datetime.utcnow(),
            end_time=None
        )
        
        self.results[batch_id] = result
        
        try:
            # 아이템 수집
            if isinstance(items, list):
                all_items = items
                result.total_items = len(all_items)
            else:
                # AsyncIterator인 경우
                all_items = []
                async for item in items:
                    all_items.append(item)
                result.total_items = len(all_items)
                
            logger.info(f"배치 작업 시작: {batch_id} (총 {result.total_items}개 항목)")
            
            # 배치 분할
            batches = [
                all_items[i:i + self.batch_size]
                for i in range(0, len(all_items), self.batch_size)
            ]
            
            # 세마포어로 동시 실행 제한
            semaphore = asyncio.Semaphore(self.max_workers)
            
            async def process_single_batch(batch: List[Any]):
                """단일 배치 처리"""
                async with semaphore:
                    batch_errors = []
                    
                    for item in batch:
                        try:
                            # 프로세서 실행
                            if asyncio.iscoroutinefunction(processor):
                                await processor(item)
                            else:
                                await asyncio.to_thread(processor, item)
                                
                            result.success_items += 1
                            
                        except Exception as e:
                            result.failed_items += 1
                            error_info = {
                                "item": str(item)[:100],  # 항목 정보 제한
                                "error": str(e),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            batch_errors.append(error_info)
                            logger.error(f"배치 항목 처리 실패: {e}")
                            
                        finally:
                            result.processed_items += 1
                            
                        # 진행 상황 콜백
                        if progress_callback and result.processed_items % 10 == 0:
                            await asyncio.to_thread(progress_callback, result)
                            
                    return batch_errors
                    
            # 모든 배치 병렬 처리
            tasks = [process_single_batch(batch) for batch in batches]
            batch_errors_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 에러 수집
            for batch_errors in batch_errors_list:
                if isinstance(batch_errors, list):
                    result.errors.extend(batch_errors)
                    
            # 에러율 확인
            error_rate = result.failed_items / result.total_items if result.total_items > 0 else 0
            if error_rate > self.error_threshold:
                result.status = BatchStatus.FAILED
                logger.error(f"배치 작업 실패: 에러율 {error_rate:.2%} > {self.error_threshold:.2%}")
            else:
                result.status = BatchStatus.COMPLETED
                logger.info(f"배치 작업 완료: {batch_id}")
                
        except asyncio.CancelledError:
            result.status = BatchStatus.CANCELLED
            logger.warning(f"배치 작업 취소됨: {batch_id}")
            raise
            
        except Exception as e:
            result.status = BatchStatus.FAILED
            logger.error(f"배치 작업 실패: {batch_id} - {e}")
            raise
            
        finally:
            result.end_time = datetime.utcnow()
            result.duration_seconds = (
                result.end_time - result.start_time
            ).total_seconds()
            
            # 최종 진행 상황 콜백
            if progress_callback:
                await asyncio.to_thread(progress_callback, result)
                
        return result
        
    async def process_database_batch(
        self,
        query,
        processor: Callable[[Any], Any],
        db_session: Optional[AsyncSession] = None,
        batch_id: Optional[str] = None,
        update_processed: bool = True
    ) -> BatchResult:
        """데이터베이스 배치 처리"""
        
        async def fetch_items():
            """데이터베이스에서 항목 스트리밍"""
            if db_session:
                async for row in db_session.stream(query):
                    yield row[0] if len(row) == 1 else row
            else:
                async with get_async_db_context() as db:
                    async for row in db.stream(query):
                        yield row[0] if len(row) == 1 else row
                        
        # 배치 처리 실행
        return await self.process_batch(
            fetch_items(),
            processor,
            batch_id=batch_id
        )
        
    def get_result(self, batch_id: str) -> Optional[BatchResult]:
        """배치 결과 조회"""
        return self.results.get(batch_id)
        
    def get_all_results(self) -> Dict[str, BatchResult]:
        """모든 배치 결과 조회"""
        return self.results.copy()
        
    def clear_results(self):
        """결과 초기화"""
        self.results.clear()


class BatchJobManager:
    """배치 작업 관리자"""
    
    def __init__(self):
        self.processors: Dict[str, BatchProcessor] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}
        
    def create_processor(
        self,
        name: str,
        batch_size: int = 100,
        max_workers: int = 5,
        **kwargs
    ) -> BatchProcessor:
        """배치 프로세서 생성"""
        processor = BatchProcessor(
            batch_size=batch_size,
            max_workers=max_workers,
            **kwargs
        )
        self.processors[name] = processor
        return processor
        
    async def submit_job(
        self,
        name: str,
        items: Union[List[Any], AsyncIterator[Any]],
        processor: Callable[[Any], Any],
        job_id: Optional[str] = None
    ) -> str:
        """배치 작업 제출"""
        if name not in self.processors:
            raise ValueError(f"프로세서를 찾을 수 없음: {name}")
            
        job_id = job_id or str(uuid4())
        batch_processor = self.processors[name]
        
        # 작업 태스크 생성
        task = asyncio.create_task(
            batch_processor.process_batch(
                items,
                processor,
                batch_id=job_id
            )
        )
        
        self.running_jobs[job_id] = task
        
        # 완료 시 정리
        task.add_done_callback(
            lambda t: self.running_jobs.pop(job_id, None)
        )
        
        return job_id
        
    async def cancel_job(self, job_id: str) -> bool:
        """배치 작업 취소"""
        task = self.running_jobs.get(job_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
        
    def get_job_status(self, job_id: str) -> Optional[BatchStatus]:
        """작업 상태 조회"""
        # 실행 중인 작업 확인
        if job_id in self.running_jobs:
            task = self.running_jobs[job_id]
            if not task.done():
                return BatchStatus.RUNNING
                
        # 완료된 작업 결과 확인
        for processor in self.processors.values():
            result = processor.get_result(job_id)
            if result:
                return result.status
                
        return None
        
    def get_job_result(self, job_id: str) -> Optional[BatchResult]:
        """작업 결과 조회"""
        for processor in self.processors.values():
            result = processor.get_result(job_id)
            if result:
                return result
        return None


# 전역 배치 작업 관리자
batch_manager = BatchJobManager()


# 예제 사용법
async def example_usage():
    """배치 처리 예제"""
    
    # 1. 간단한 리스트 배치 처리
    processor = BatchProcessor(batch_size=50, max_workers=3)
    
    items = list(range(1000))
    
    async def process_item(item: int):
        """항목 처리 함수"""
        await asyncio.sleep(0.01)  # 시뮬레이션
        if item % 100 == 99:  # 1% 실패율
            raise ValueError(f"처리 실패: {item}")
        return item * 2
        
    result = await processor.process_batch(
        items,
        process_item,
        progress_callback=lambda r: print(
            f"진행률: {r.processed_items}/{r.total_items} "
            f"({r.processed_items/r.total_items*100:.1f}%)"
        )
    )
    
    print(f"배치 결과: {result.dict()}")
    
    
    # 2. 데이터베이스 배치 처리
    from app.models.product import Product
    
    # 모든 제품 가격 10% 인상
    async def update_product_price(product: Product):
        product.price = product.price * 1.1
        # 실제로는 DB 업데이트 로직
        
    db_processor = BatchProcessor(batch_size=100)
    
    async with get_async_db_context() as db:
        query = select(Product).where(Product.is_active == True)
        
        result = await db_processor.process_database_batch(
            query,
            update_product_price,
            db_session=db
        )
        
    print(f"데이터베이스 배치 결과: {result.success_rate:.1f}% 성공")
    
    
    # 3. 배치 작업 관리자 사용
    batch_manager.create_processor("image_processor", batch_size=10)
    
    image_paths = ["image1.jpg", "image2.jpg", "image3.jpg"]
    
    async def resize_image(path: str):
        """이미지 리사이즈"""
        logger.info(f"이미지 처리: {path}")
        await asyncio.sleep(0.5)  # 시뮬레이션
        
    job_id = await batch_manager.submit_job(
        "image_processor",
        image_paths,
        resize_image
    )
    
    # 작업 상태 확인
    status = batch_manager.get_job_status(job_id)
    print(f"작업 상태: {status}")
    
    # 결과 대기
    await asyncio.sleep(2)
    
    # 결과 조회
    result = batch_manager.get_job_result(job_id)
    if result:
        print(f"작업 완료: {result.processed_items}개 처리됨")