"""
지연 로딩(Lazy Loading) 시스템
모듈과 서비스를 필요할 때만 로드하여 시작 시간 단축
"""
import importlib
import threading
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime
import asyncio
import weakref

from app.utils.logger import get_logger

logger = get_logger("lazy_loader")


class LazyLoader:
    """지연 로딩 관리자"""
    
    def __init__(self):
        self._modules: Dict[str, Any] = {}
        self._loading_locks: Dict[str, threading.Lock] = {}
        self._load_times: Dict[str, float] = {}
        self._access_counts: Dict[str, int] = {}
        self._callbacks: Dict[str, list] = {}
        
    def register_module(self, name: str, import_path: str, 
                       callback: Optional[Callable] = None) -> None:
        """모듈 등록"""
        self._loading_locks[name] = threading.Lock()
        self._access_counts[name] = 0
        
        if callback:
            if name not in self._callbacks:
                self._callbacks[name] = []
            self._callbacks[name].append(callback)
        
        logger.debug(f"Registered lazy module: {name} -> {import_path}")
    
    def get_module(self, name: str, import_path: str) -> Any:
        """모듈 지연 로딩"""
        if name in self._modules:
            self._access_counts[name] += 1
            return self._modules[name]
        
        with self._loading_locks.get(name, threading.Lock()):
            # 이중 확인 패턴
            if name in self._modules:
                self._access_counts[name] += 1
                return self._modules[name]
            
            try:
                start_time = datetime.now()
                module = importlib.import_module(import_path)
                end_time = datetime.now()
                
                load_time = (end_time - start_time).total_seconds()
                self._load_times[name] = load_time
                self._modules[name] = module
                self._access_counts[name] = 1
                
                # 콜백 실행
                if name in self._callbacks:
                    for callback in self._callbacks[name]:
                        try:
                            callback(module)
                        except Exception as e:
                            logger.error(f"Callback error for {name}: {e}")
                
                logger.info(f"Lazy loaded {name} in {load_time:.3f}s")
                return module
                
            except ImportError as e:
                logger.error(f"Failed to lazy load {name} from {import_path}: {e}")
                raise
    
    def preload_modules(self, module_names: list) -> None:
        """모듈 사전 로딩"""
        for name in module_names:
            if name not in self._modules:
                try:
                    # 등록된 경로에서 로드 시도
                    logger.info(f"Preloading module: {name}")
                except Exception as e:
                    logger.warning(f"Failed to preload {name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """로딩 통계 반환"""
        return {
            "loaded_modules": len(self._modules),
            "total_modules": len(self._loading_locks),
            "load_times": dict(self._load_times),
            "access_counts": dict(self._access_counts),
            "average_load_time": sum(self._load_times.values()) / max(len(self._load_times), 1)
        }
    
    def clear_unused_modules(self, min_access_count: int = 1) -> int:
        """사용되지 않는 모듈 정리"""
        cleared = 0
        modules_to_clear = []
        
        for name, access_count in self._access_counts.items():
            if access_count < min_access_count and name in self._modules:
                modules_to_clear.append(name)
        
        for name in modules_to_clear:
            if name in self._modules:
                del self._modules[name]
                cleared += 1
                logger.debug(f"Cleared unused module: {name}")
        
        return cleared


# 전역 지연 로더 인스턴스
lazy_loader = LazyLoader()


def lazy_import(import_path: str, attribute: Optional[str] = None):
    """지연 import 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                module = lazy_loader.get_module(import_path, import_path)
                
                if attribute:
                    service = getattr(module, attribute)
                    return func(service, *args, **kwargs)
                else:
                    return func(module, *args, **kwargs)
                    
            except Exception as e:
                logger.error(f"Lazy import failed for {import_path}: {e}")
                raise
        
        return wrapper
    return decorator


class ServiceRegistry:
    """서비스 레지스트리 - 싱글톤 패턴으로 서비스 관리"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._services = {}
                    cls._instance._factories = {}
                    cls._instance._singletons = set()
        return cls._instance
    
    def register_service(self, name: str, factory: Callable, singleton: bool = True):
        """서비스 팩토리 등록"""
        self._factories[name] = factory
        if singleton:
            self._singletons.add(name)
        
        logger.debug(f"Registered service: {name} (singleton: {singleton})")
    
    def get_service(self, name: str) -> Any:
        """서비스 인스턴스 반환"""
        if name in self._singletons and name in self._services:
            return self._services[name]
        
        if name not in self._factories:
            raise ValueError(f"Service {name} not registered")
        
        try:
            service = self._factories[name]()
            
            if name in self._singletons:
                self._services[name] = service
            
            logger.debug(f"Created service instance: {name}")
            return service
            
        except Exception as e:
            logger.error(f"Failed to create service {name}: {e}")
            raise
    
    def clear_services(self):
        """모든 서비스 정리"""
        cleared = len(self._services)
        self._services.clear()
        logger.info(f"Cleared {cleared} service instances")
        return cleared


# 전역 서비스 레지스트리
service_registry = ServiceRegistry()


def service_provider(name: str, singleton: bool = True):
    """서비스 프로바이더 데코레이터"""
    def decorator(factory_func):
        service_registry.register_service(name, factory_func, singleton)
        return factory_func
    return decorator


def inject_service(service_name: str):
    """서비스 주입 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            service = service_registry.get_service(service_name)
            return func(service, *args, **kwargs)
        return wrapper
    return decorator


class ModuleCache:
    """모듈 캐시 관리"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache = {}
        self._access_times = {}
        self._lock = threading.Lock()
    
    def get(self, key: str, loader: Callable) -> Any:
        """캐시에서 모듈 가져오기 또는 로드"""
        with self._lock:
            if key in self._cache:
                self._access_times[key] = datetime.now()
                return self._cache[key]
            
            # 캐시 크기 확인
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            # 새로운 모듈 로드
            module = loader()
            self._cache[key] = module
            self._access_times[key] = datetime.now()
            
            return module
    
    def _evict_oldest(self):
        """가장 오래된 모듈 제거"""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times.keys(), 
                        key=lambda k: self._access_times[k])
        
        if oldest_key in self._cache:
            del self._cache[oldest_key]
        del self._access_times[oldest_key]
        
        logger.debug(f"Evicted module from cache: {oldest_key}")
    
    def clear(self):
        """캐시 정리"""
        with self._lock:
            cleared = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            return cleared


# 전역 모듈 캐시
module_cache = ModuleCache()


async def warm_up_services():
    """주요 서비스 워밍업"""
    logger.info("Starting service warm-up...")
    
    # 주요 서비스들을 백그라운드에서 로드
    critical_services = [
        "app.services.product_service",
        "app.services.platforms.platform_manager",
        "app.services.wholesale.analysis_service",
        "app.core.performance"
    ]
    
    tasks = []
    for service_path in critical_services:
        task = asyncio.create_task(
            asyncio.to_thread(lazy_loader.get_module, service_path, service_path)
        )
        tasks.append(task)
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Service warm-up completed")
    except Exception as e:
        logger.error(f"Service warm-up failed: {e}")


def optimize_imports():
    """Import 최적화 실행"""
    
    # 1. 중요한 모듈들 사전 등록
    critical_modules = {
        "product_service": "app.services.product_service",
        "platform_manager": "app.services.platforms.platform_manager", 
        "analysis_service": "app.services.wholesale.analysis_service",
        "performance": "app.core.performance",
        "database": "app.api.v1.dependencies.database"
    }
    
    for name, path in critical_modules.items():
        lazy_loader.register_module(name, path)
    
    # 2. 서비스 팩토리 등록
    @service_provider("product_service")
    def create_product_service():
        from app.services.product_service import ProductService
        return ProductService()
    
    @service_provider("platform_manager")
    def create_platform_manager():
        from app.services.platforms.platform_manager import PlatformManager
        return PlatformManager()
    
    logger.info("Import optimization configured")


# 초기화
optimize_imports()