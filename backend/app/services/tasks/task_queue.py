"""
간단한 태스크 큐 시스템 구현 (Celery 대체)
백그라운드 작업 처리를 위한 경량 솔루션
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """태스크 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """태스크 우선순위"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Task(BaseModel):
    """태스크 모델"""
    id: str
    name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: int = 60  # seconds
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


class TaskQueue:
    """비동기 태스크 큐"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.handlers: Dict[str, Callable] = {}
        self.running_tasks: Set[str] = set()
        self._running = False
        
    def register_handler(self, name: str, handler: Callable):
        """태스크 핸들러 등록"""
        self.handlers[name] = handler
        logger.info(f"핸들러 등록: {name}")
        
    async def enqueue(
        self,
        name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        retry_delay: int = 60
    ) -> str:
        """태스크 큐에 추가"""
        if name not in self.handlers:
            raise ValueError(f"등록되지 않은 태스크: {name}")
            
        task = Task(
            id=str(uuid4()),
            name=name,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            created_at=datetime.utcnow()
        )
        
        self.tasks[task.id] = task
        await self.pending_queue.put((task.priority.value * -1, task.id))  # 우선순위 역순
        
        logger.info(f"태스크 큐에 추가: {task.id} ({name})")
        return task.id
        
    async def get_task(self, task_id: str) -> Optional[Task]:
        """태스크 조회"""
        return self.tasks.get(task_id)
        
    async def cancel_task(self, task_id: str) -> bool:
        """태스크 취소"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            logger.info(f"태스크 취소됨: {task_id}")
            return True
            
        return False
        
    async def start(self):
        """태스크 큐 시작"""
        if self._running:
            return
            
        self._running = True
        logger.info(f"태스크 큐 시작 (workers: {self.max_workers})")
        
        # 워커 생성
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
            
    async def stop(self):
        """태스크 큐 중지"""
        self._running = False
        
        # 모든 워커 종료 대기
        for worker in self.workers:
            worker.cancel()
            
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info("태스크 큐 중지됨")
        
    async def _worker(self, worker_id: int):
        """워커 프로세스"""
        logger.info(f"워커 {worker_id} 시작")
        
        while self._running:
            try:
                # 태스크 가져오기 (1초 타임아웃)
                priority, task_id = await asyncio.wait_for(
                    self.pending_queue.get(),
                    timeout=1.0
                )
                
                task = self.tasks.get(task_id)
                if not task or task.status == TaskStatus.CANCELLED:
                    continue
                    
                # 태스크 실행
                await self._execute_task(task, worker_id)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"워커 {worker_id} 오류: {e}")
                
        logger.info(f"워커 {worker_id} 종료")
        
    async def _execute_task(self, task: Task, worker_id: int):
        """태스크 실행"""
        handler = self.handlers.get(task.name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"핸들러를 찾을 수 없음: {task.name}"
            task.completed_at = datetime.utcnow()
            return
            
        try:
            # 실행 중 표시
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            self.running_tasks.add(task.id)
            
            logger.info(f"워커 {worker_id} - 태스크 실행: {task.id} ({task.name})")
            
            # 핸들러 실행
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*task.args, **task.kwargs)
            else:
                result = await asyncio.to_thread(handler, *task.args, **task.kwargs)
                
            # 성공
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            
            logger.info(f"태스크 완료: {task.id}")
            
        except Exception as e:
            # 실패
            task.error = str(e)
            task.traceback = traceback.format_exc()
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # 재시도
                task.status = TaskStatus.RETRYING
                retry_time = datetime.utcnow() + timedelta(seconds=task.retry_delay)
                
                logger.warning(
                    f"태스크 재시도 예정: {task.id} "
                    f"({task.retry_count}/{task.max_retries}) - {retry_time}"
                )
                
                # 재시도 스케줄링
                asyncio.create_task(self._schedule_retry(task, retry_time))
            else:
                # 최종 실패
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                
                logger.error(f"태스크 최종 실패: {task.id} - {e}")
                
        finally:
            self.running_tasks.remove(task.id)
            
    async def _schedule_retry(self, task: Task, retry_time: datetime):
        """재시도 스케줄링"""
        delay = (retry_time - datetime.utcnow()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
            
        task.status = TaskStatus.PENDING
        await self.pending_queue.put((task.priority.value * -1, task.id))
        
    def get_stats(self) -> Dict[str, Any]:
        """큐 상태 통계"""
        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
            
        return {
            "total_tasks": len(self.tasks),
            "pending": self.pending_queue.qsize(),
            "running": len(self.running_tasks),
            "workers": len(self.workers),
            "status_counts": status_counts
        }


# 전역 태스크 큐 인스턴스
task_queue = TaskQueue()


# 데코레이터
def task(
    name: Optional[str] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    retry_delay: int = 60
):
    """태스크 데코레이터"""
    def decorator(func: Callable):
        task_name = name or func.__name__
        
        # 핸들러 등록
        task_queue.register_handler(task_name, func)
        
        # 래퍼 함수
        async def wrapper(*args, **kwargs):
            # 직접 호출 시 즉시 실행
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
                
        # 비동기 실행 메서드 추가
        async def delay(*args, **kwargs) -> str:
            return await task_queue.enqueue(
                task_name,
                args=args,
                kwargs=kwargs,
                priority=priority,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
            
        wrapper.delay = delay
        wrapper.task_name = task_name
        
        return wrapper
        
    return decorator


# 예제 태스크
@task(priority=TaskPriority.HIGH)
async def send_email(to: str, subject: str, body: str):
    """이메일 전송 태스크"""
    logger.info(f"이메일 전송: {to} - {subject}")
    # 실제 이메일 전송 로직
    await asyncio.sleep(2)  # 시뮬레이션
    return {"status": "sent", "to": to}


@task(max_retries=5, retry_delay=30)
async def process_image(image_path: str, resize: tuple):
    """이미지 처리 태스크"""
    logger.info(f"이미지 처리: {image_path} -> {resize}")
    # 실제 이미지 처리 로직
    await asyncio.sleep(3)  # 시뮬레이션
    return {"status": "processed", "path": image_path}


@task()
def cleanup_old_files(days: int = 30):
    """오래된 파일 정리 태스크"""
    logger.info(f"{days}일 이상 된 파일 정리")
    # 실제 파일 정리 로직
    import time
    time.sleep(1)  # 시뮬레이션
    return {"deleted": 10, "freed_space": "1.2GB"}