"""백그라운드 작업 기능 테스트"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.tasks.task_queue import task_queue, TaskPriority, TaskStatus, task

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 테스트용 태스크 정의
@task(priority=TaskPriority.HIGH)
async def test_async_task(name: str, duration: int = 2):
    """비동기 테스트 태스크"""
    logger.info(f"비동기 태스크 시작: {name}")
    await asyncio.sleep(duration)
    logger.info(f"비동기 태스크 완료: {name}")
    return f"Async task {name} completed in {duration}s"


@task(priority=TaskPriority.NORMAL)
def test_sync_task(name: str, value: int):
    """동기 테스트 태스크"""
    logger.info(f"동기 태스크 시작: {name}")
    import time
    time.sleep(1)
    result = value * 2
    logger.info(f"동기 태스크 완료: {name} = {result}")
    return result


@task(max_retries=2, retry_delay=5)
async def test_failing_task(name: str, fail_times: int = 1):
    """실패하는 테스트 태스크"""
    # 태스크 실행 횟수를 추적하기 위한 전역 카운터
    if not hasattr(test_failing_task, 'counters'):
        test_failing_task.counters = {}
    
    if name not in test_failing_task.counters:
        test_failing_task.counters[name] = 0
    
    test_failing_task.counters[name] += 1
    current_count = test_failing_task.counters[name]
    
    logger.info(f"실패 태스크 시도 {current_count}/{fail_times + 1}: {name}")
    
    if current_count <= fail_times:
        raise Exception(f"의도적 실패 ({current_count}/{fail_times})")
    
    logger.info(f"실패 태스크 성공: {name}")
    return f"Finally succeeded after {current_count} attempts"


async def run_tests():
    """테스트 실행"""
    logger.info("=== 백그라운드 작업 테스트 시작 ===")
    
    # 태스크 큐 시작
    await task_queue.start()
    
    try:
        # 1. 비동기 태스크 테스트
        logger.info("\n1. 비동기 태스크 테스트")
        task_ids = []
        
        for i in range(3):
            task_id = await test_async_task.delay(f"Task-{i+1}", duration=i+1)
            task_ids.append(task_id)
            logger.info(f"비동기 태스크 큐에 추가: {task_id}")
        
        # 2. 동기 태스크 테스트
        logger.info("\n2. 동기 태스크 테스트")
        sync_task_id = await test_sync_task.delay("SyncTask", 42)
        task_ids.append(sync_task_id)
        logger.info(f"동기 태스크 큐에 추가: {sync_task_id}")
        
        # 3. 실패/재시도 태스크 테스트
        logger.info("\n3. 실패/재시도 태스크 테스트")
        fail_task_id = await test_failing_task.delay("FailTask", fail_times=1)
        task_ids.append(fail_task_id)
        logger.info(f"실패 태스크 큐에 추가: {fail_task_id}")
        
        # 4. 우선순위 테스트
        logger.info("\n4. 우선순위 테스트")
        # 낮은 우선순위 태스크를 먼저 추가
        low_priority_id = await task_queue.enqueue(
            "test_async_task",
            args=["LowPriority", 1],
            priority=TaskPriority.LOW
        )
        # 높은 우선순위 태스크를 나중에 추가
        high_priority_id = await task_queue.enqueue(
            "test_async_task",
            args=["HighPriority", 1],
            priority=TaskPriority.CRITICAL
        )
        task_ids.extend([low_priority_id, high_priority_id])
        
        # 5. 태스크 취소 테스트
        logger.info("\n5. 태스크 취소 테스트")
        cancel_task_id = await test_async_task.delay("ToCancel", 10)
        await asyncio.sleep(0.5)  # 큐에 들어갈 시간 제공
        cancelled = await task_queue.cancel_task(cancel_task_id)
        logger.info(f"태스크 취소 {'성공' if cancelled else '실패'}: {cancel_task_id}")
        
        # 태스크 완료 대기
        logger.info("\n6. 태스크 완료 대기 중...")
        await asyncio.sleep(15)  # 모든 태스크가 완료될 때까지 대기
        
        # 결과 확인
        logger.info("\n7. 태스크 결과 확인")
        for task_id in task_ids:
            task = await task_queue.get_task(task_id)
            if task:
                logger.info(f"태스크 {task_id}:")
                logger.info(f"  - 이름: {task.name}")
                logger.info(f"  - 상태: {task.status}")
                logger.info(f"  - 결과: {task.result}")
                if task.error:
                    logger.info(f"  - 에러: {task.error}")
                logger.info(f"  - 재시도: {task.retry_count}/{task.max_retries}")
        
        # 큐 통계
        logger.info("\n8. 큐 통계")
        stats = task_queue.get_stats()
        logger.info(f"큐 상태: {stats}")
        
        # 직접 호출 테스트
        logger.info("\n9. 직접 호출 테스트")
        direct_result = await test_async_task("DirectCall", 1)
        logger.info(f"직접 호출 결과: {direct_result}")
        
    finally:
        # 태스크 큐 중지
        await task_queue.stop()
        
    logger.info("\n=== 백그라운드 작업 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(run_tests())