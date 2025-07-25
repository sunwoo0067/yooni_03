"""
애플리케이션 시작 최적화
FastAPI 앱 시작 시간을 단축하고 리소스 사용량 최적화
"""
import asyncio
import time
import os
import gc
from typing import List, Dict, Any, Callable
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from sqlalchemy import text

from app.core.lazy_loader import lazy_loader, service_registry, warm_up_services
from app.core.performance import redis_client, performance_monitor
from app.utils.logger import get_logger

logger = get_logger("startup_optimizer")


class StartupOptimizer:
    """시작 최적화 관리자"""
    
    def __init__(self):
        self.startup_tasks: List[Callable] = []
        self.background_tasks: List[Callable] = []
        self.health_checks: List[Callable] = []
        self.startup_time = 0
        self.optimization_metrics = {}
        
    def add_startup_task(self, task: Callable, priority: int = 0):
        """시작 작업 추가 (우선순위별)"""
        self.startup_tasks.append((priority, task))
        self.startup_tasks.sort(key=lambda x: x[0])  # 우선순위 순 정렬
        
    def add_background_task(self, task: Callable):
        """백그라운드 작업 추가"""
        self.background_tasks.append(task)
        
    def add_health_check(self, check: Callable):
        """헬스체크 추가"""
        self.health_checks.append(check)
    
    async def run_startup_sequence(self):
        """시작 시퀀스 실행"""
        start_time = time.time()
        logger.info("Starting optimized startup sequence...")
        
        try:
            # 1. 긴급 시작 작업 (우선순위 0-2)
            critical_tasks = [task for priority, task in self.startup_tasks if priority <= 2]
            if critical_tasks:
                await self._run_tasks_parallel(critical_tasks, "Critical startup tasks")
            
            # 2. 필수 서비스 초기화 (우선순위 3-5)
            essential_tasks = [task for priority, task in self.startup_tasks if 3 <= priority <= 5]
            if essential_tasks:
                await self._run_tasks_parallel(essential_tasks, "Essential services")
            
            # 3. 선택적 서비스 백그라운드 로드 (우선순위 6+)
            optional_tasks = [task for priority, task in self.startup_tasks if priority > 5]
            if optional_tasks:
                asyncio.create_task(
                    self._run_tasks_parallel(optional_tasks, "Optional services")
                )
            
            # 4. 백그라운드 작업 시작
            for task in self.background_tasks:
                asyncio.create_task(task())
            
            self.startup_time = time.time() - start_time
            logger.info(f"Startup sequence completed in {self.startup_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Startup sequence failed: {e}")
            raise
    
    async def _run_tasks_parallel(self, tasks: List[Callable], description: str):
        """작업들을 병렬로 실행"""
        start_time = time.time()
        
        try:
            # ThreadPoolExecutor를 사용하여 동기 작업도 병렬 처리
            with ThreadPoolExecutor(max_workers=min(len(tasks), 5)) as executor:
                loop = asyncio.get_event_loop()
                futures = []
                
                for task in tasks:
                    if asyncio.iscoroutinefunction(task):
                        futures.append(task())
                    else:
                        futures.append(loop.run_in_executor(executor, task))
                
                results = await asyncio.gather(*futures, return_exceptions=True)
                
                # 에러 처리
                errors = [r for r in results if isinstance(r, Exception)]
                if errors:
                    logger.warning(f"{description} completed with {len(errors)} errors")
                
            execution_time = time.time() - start_time
            self.optimization_metrics[description] = {
                "tasks": len(tasks),
                "execution_time": execution_time,
                "errors": len(errors) if 'errors' in locals() else 0
            }
            
            logger.info(f"{description} completed in {execution_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Failed to run {description}: {e}")
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """헬스체크 실행"""
        results = {}
        
        for check in self.health_checks:
            try:
                check_name = check.__name__
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check):
                    result = await check()
                else:
                    result = check()
                
                execution_time = time.time() - start_time
                results[check_name] = {
                    "status": "healthy" if result else "unhealthy",
                    "execution_time": execution_time,
                    "result": result
                }
                
            except Exception as e:
                results[check.__name__] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """최적화 메트릭 반환"""
        return {
            "startup_time": self.startup_time,
            "optimization_metrics": self.optimization_metrics,
            "registered_tasks": len(self.startup_tasks),
            "background_tasks": len(self.background_tasks),
            "health_checks": len(self.health_checks)
        }


# 전역 시작 최적화 인스턴스
startup_optimizer = StartupOptimizer()


# 핵심 시작 작업들
async def initialize_database_pool():
    """데이터베이스 연결 풀 초기화"""
    try:
        from app.api.v1.dependencies.database import get_db
        # 연결 테스트
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection pool initialized")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def initialize_cache_system():
    """캐시 시스템 초기화"""
    try:
        # Redis 연결 테스트
        redis_client.ping()
        
        # 기본 캐시 키 설정
        redis_client.set("system:startup", int(time.time()), ex=3600)
        
        logger.info("Cache system initialized")
        return True
    except Exception as e:
        logger.error(f"Cache system initialization failed: {e}")
        return False


def initialize_performance_monitoring():
    """성능 모니터링 초기화"""
    try:
        # 성능 모니터 설정
        performance_monitor.query_stats.clear()
        logger.info("Performance monitoring initialized")
        return True
    except Exception as e:
        logger.error(f"Performance monitoring initialization failed: {e}")
        return False


def optimize_python_runtime():
    """Python 런타임 최적화"""
    try:
        # 가비지 컬레션 임계값 조정
        gc.set_threshold(700, 10, 10)
        
        # 초기 가비지 컬렉션 실행
        collected = gc.collect()
        
        logger.info(f"Python runtime optimized, collected {collected} objects")
        return True
    except Exception as e:
        logger.error(f"Python runtime optimization failed: {e}")
        return False


async def preload_critical_modules():
    """중요 모듈 사전 로드"""
    try:
        critical_modules = [
            "app.models.product",
            "app.models.wholesaler",
            "app.services.product_service"
        ]
        
        for module_path in critical_modules:
            lazy_loader.get_module(module_path, module_path)
        
        logger.info(f"Preloaded {len(critical_modules)} critical modules")
        return True
    except Exception as e:
        logger.error(f"Module preloading failed: {e}")
        return False


# 헬스체크 함수들
def check_database_health():
    """데이터베이스 헬스체크"""
    try:
        from app.api.v1.dependencies.database import get_db
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except:
        return False


def check_cache_health():
    """캐시 헬스체크"""
    try:
        redis_client.ping()
        return True
    except:
        return False


def check_memory_health():
    """메모리 헬스체크"""
    try:
        import psutil
        memory_percent = psutil.virtual_memory().percent
        return memory_percent < 85  # 85% 미만이면 건강
    except:
        return True  # psutil이 없으면 건강하다고 가정


# 시작 작업 등록
startup_optimizer.add_startup_task(optimize_python_runtime, priority=0)
startup_optimizer.add_startup_task(initialize_database_pool, priority=1)
startup_optimizer.add_startup_task(initialize_cache_system, priority=2)
startup_optimizer.add_startup_task(initialize_performance_monitoring, priority=3)
startup_optimizer.add_startup_task(preload_critical_modules, priority=4)
startup_optimizer.add_background_task(warm_up_services)

# 헬스체크 등록
startup_optimizer.add_health_check(check_database_health)
startup_optimizer.add_health_check(check_cache_health)
startup_optimizer.add_health_check(check_memory_health)


@asynccontextmanager
async def optimized_lifespan(app: FastAPI):
    """최적화된 애플리케이션 라이프사이클"""
    
    # 시작
    logger.info("Application startup with optimization...")
    start_time = time.time()
    
    try:
        await startup_optimizer.run_startup_sequence()
        
        total_startup_time = time.time() - start_time
        logger.info(f"Application started successfully in {total_startup_time:.3f}s")
        
        # 시작 메트릭 저장
        app.state.startup_metrics = startup_optimizer.get_metrics()
        app.state.startup_time = total_startup_time
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    finally:
        # 종료
        logger.info("Application shutdown...")
        
        # 리소스 정리
        try:
            service_registry.clear_services()
            lazy_loader.clear_unused_modules()
            
            # 최종 가비지 컬렉션
            collected = gc.collect()
            logger.info(f"Shutdown cleanup: collected {collected} objects")
            
        except Exception as e:
            logger.error(f"Shutdown cleanup failed: {e}")
        
        logger.info("Application shutdown completed")


def get_startup_info() -> Dict[str, Any]:
    """시작 정보 반환"""
    return {
        "optimizer_metrics": startup_optimizer.get_metrics(),
        "lazy_loader_stats": lazy_loader.get_stats(),
        "service_registry_info": {
            "registered_services": len(service_registry._factories),
            "active_singletons": len(service_registry._services)
        }
    }