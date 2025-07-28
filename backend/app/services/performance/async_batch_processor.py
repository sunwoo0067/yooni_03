"""
비동기 배치 처리 시스템
외부 API 호출 최적화, 연결 풀링, 병렬 처리
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager
import weakref

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BatchProcessingStrategy(Enum):
    """배치 처리 전략"""
    PARALLEL = "parallel"  # 병렬 처리
    SEQUENTIAL = "sequential"  # 순차 처리
    RATE_LIMITED = "rate_limited"  # 속도 제한
    CHUNKED = "chunked"  # 청크 단위 처리


@dataclass
class BatchConfig:
    """배치 처리 설정"""
    batch_size: int = 100
    max_concurrent: int = 10
    strategy: BatchProcessingStrategy = BatchProcessingStrategy.PARALLEL
    rate_limit_per_second: Optional[float] = None
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class BatchResult(Generic[T]):
    """배치 처리 결과"""
    success_count: int = 0
    error_count: int = 0
    total_count: int = 0
    results: List[T] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    execution_time: float = 0.0
    throughput: float = 0.0


class ConnectionPoolManager:
    """연결 풀 매니저"""
    
    def __init__(self):
        self._pools: Dict[str, aiohttp.ClientSession] = {}
        self._pool_configs: Dict[str, Dict[str, Any]] = {}
        
    async def get_session(self, pool_name: str = "default") -> aiohttp.ClientSession:
        """연결 풀에서 세션 반환"""
        if pool_name not in self._pools:
            await self._create_pool(pool_name)
        
        return self._pools[pool_name]
    
    async def _create_pool(self, pool_name: str):
        """연결 풀 생성"""
        config = self._pool_configs.get(pool_name, {})
        
        # 기본 설정
        connector = aiohttp.TCPConnector(
            limit=config.get("max_connections", 100),
            limit_per_host=config.get("max_connections_per_host", 20),
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=config.get("total_timeout", 30),
            connect=config.get("connect_timeout", 10),
            sock_read=config.get("read_timeout", 10)
        )
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=config.get("default_headers", {}),
            trust_env=True
        )
        
        self._pools[pool_name] = session
        logger.info(f"Created connection pool: {pool_name}")
    
    def configure_pool(self, pool_name: str, **config):
        """연결 풀 설정"""
        self._pool_configs[pool_name] = config
    
    async def close_all(self):
        """모든 연결 풀 닫기"""
        for pool_name, session in self._pools.items():
            await session.close()
            logger.info(f"Closed connection pool: {pool_name}")
        
        self._pools.clear()


class AsyncBatchProcessor:
    """비동기 배치 처리기"""
    
    def __init__(self, connection_manager: ConnectionPoolManager):
        self.connection_manager = connection_manager
        self.active_batches: Dict[str, asyncio.Task] = {}
        
    async def process_batch(
        self,
        items: List[Any],
        processor_func: Callable,
        config: BatchConfig,
        batch_id: Optional[str] = None
    ) -> BatchResult:
        """배치 처리 실행"""
        
        batch_id = batch_id or f"batch_{int(time.time())}"
        start_time = time.time()
        
        logger.info(f"Starting batch {batch_id} with {len(items)} items")
        
        try:
            # 전략에 따른 처리
            if config.strategy == BatchProcessingStrategy.PARALLEL:
                results = await self._process_parallel(items, processor_func, config)
            elif config.strategy == BatchProcessingStrategy.SEQUENTIAL:
                results = await self._process_sequential(items, processor_func, config)
            elif config.strategy == BatchProcessingStrategy.RATE_LIMITED:
                results = await self._process_rate_limited(items, processor_func, config)
            elif config.strategy == BatchProcessingStrategy.CHUNKED:
                results = await self._process_chunked(items, processor_func, config)
            else:
                raise ValueError(f"Unknown strategy: {config.strategy}")
            
            execution_time = time.time() - start_time
            throughput = len(items) / execution_time if execution_time > 0 else 0
            
            batch_result = BatchResult(
                success_count=len(results.results),
                error_count=len(results.errors),
                total_count=len(items),
                results=results.results,
                errors=results.errors,
                execution_time=execution_time,
                throughput=throughput
            )
            
            logger.info(
                f"Batch {batch_id} completed: {batch_result.success_count} success, "
                f"{batch_result.error_count} errors, {throughput:.2f} items/sec"
            )
            
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch {batch_id} failed: {str(e)}")
            raise
        finally:
            if batch_id in self.active_batches:
                del self.active_batches[batch_id]
    
    async def _process_parallel(
        self,
        items: List[Any],
        processor_func: Callable,
        config: BatchConfig
    ) -> BatchResult:
        """병렬 처리"""
        semaphore = asyncio.Semaphore(config.max_concurrent)
        
        async def process_item_with_semaphore(item):
            async with semaphore:
                return await self._process_single_item(item, processor_func, config)
        
        tasks = [process_item_with_semaphore(item) for item in items]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._collect_results(raw_results)
    
    async def _process_sequential(
        self,
        items: List[Any],
        processor_func: Callable,
        config: BatchConfig
    ) -> BatchResult:
        """순차 처리"""
        results = []
        errors = []
        
        for item in items:
            try:
                result = await self._process_single_item(item, processor_func, config)
                results.append(result)
            except Exception as e:
                errors.append({
                    "item": str(item),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
        
        return BatchResult(results=results, errors=errors)
    
    async def _process_rate_limited(
        self,
        items: List[Any],
        processor_func: Callable,
        config: BatchConfig
    ) -> BatchResult:
        """속도 제한 처리"""
        if not config.rate_limit_per_second:
            raise ValueError("Rate limit must be specified for rate_limited strategy")
        
        results = []
        errors = []
        delay = 1.0 / config.rate_limit_per_second
        
        for item in items:
            try:
                result = await self._process_single_item(item, processor_func, config)
                results.append(result)
            except Exception as e:
                errors.append({
                    "item": str(item),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            
            await asyncio.sleep(delay)
        
        return BatchResult(results=results, errors=errors)
    
    async def _process_chunked(
        self,
        items: List[Any],
        processor_func: Callable,
        config: BatchConfig
    ) -> BatchResult:
        """청크 단위 처리"""
        all_results = []
        all_errors = []
        
        # 청크로 분할
        for i in range(0, len(items), config.batch_size):
            chunk = items[i:i + config.batch_size]
            
            # 청크 내에서 병렬 처리
            chunk_result = await self._process_parallel(chunk, processor_func, config)
            
            all_results.extend(chunk_result.results)
            all_errors.extend(chunk_result.errors)
            
            # 청크 간 짧은 대기
            if i + config.batch_size < len(items):
                await asyncio.sleep(0.1)
        
        return BatchResult(results=all_results, errors=all_errors)
    
    async def _process_single_item(
        self,
        item: Any,
        processor_func: Callable,
        config: BatchConfig
    ) -> Any:
        """단일 아이템 처리 (재시도 포함)"""
        last_exception = None
        
        for attempt in range(config.retry_attempts):
            try:
                if asyncio.iscoroutinefunction(processor_func):
                    result = await asyncio.wait_for(
                        processor_func(item, self.connection_manager),
                        timeout=config.timeout_seconds
                    )
                else:
                    result = processor_func(item, self.connection_manager)
                
                return result
                
            except Exception as e:
                last_exception = e
                if attempt < config.retry_attempts - 1:
                    delay = config.retry_delay * (2 ** attempt)  # 지수 백오프
                    await asyncio.sleep(delay)
                    logger.warning(f"Retry {attempt + 1} for item {item}: {str(e)}")
        
        raise last_exception
    
    def _collect_results(self, raw_results: List[Any]) -> BatchResult:
        """결과 수집"""
        results = []
        errors = []
        
        for result in raw_results:
            if isinstance(result, Exception):
                errors.append({
                    "error": str(result),
                    "error_type": type(result).__name__
                })
            else:
                results.append(result)
        
        return BatchResult(results=results, errors=errors)


class WholesalerAPIBatchProcessor:
    """도매처 API 배치 처리 전문"""
    
    def __init__(self):
        self.connection_manager = ConnectionPoolManager()
        self.batch_processor = AsyncBatchProcessor(self.connection_manager)
        self._setup_connection_pools()
    
    def _setup_connection_pools(self):
        """도매처별 연결 풀 설정"""
        # 오너클랜 풀
        self.connection_manager.configure_pool(
            "ownerclan",
            max_connections=20,
            max_connections_per_host=10,
            total_timeout=30,
            default_headers={
                "Content-Type": "application/json",
                "User-Agent": "Yooni-Dropshipping/1.0"
            }
        )
        
        # 젠트레이드 풀
        self.connection_manager.configure_pool(
            "zentrade",
            max_connections=15,
            max_connections_per_host=8,
            total_timeout=45,
            default_headers={
                "Content-Type": "application/xml; charset=euc-kr"
            }
        )
        
        # 도매꾹 풀
        self.connection_manager.configure_pool(
            "domeggook",
            max_connections=25,
            max_connections_per_host=12,
            total_timeout=20,
            default_headers={
                "Content-Type": "application/json"
            }
        )
    
    async def batch_collect_products(
        self,
        wholesaler_configs: List[Dict[str, Any]],
        max_products_per_wholesaler: int = 1000
    ) -> Dict[str, BatchResult]:
        """여러 도매처에서 배치로 상품 수집"""
        
        tasks = {}
        
        for config in wholesaler_configs:
            wholesaler_type = config["type"]
            
            # 도매처별 설정
            batch_config = BatchConfig(
                batch_size=50,
                max_concurrent=5,
                strategy=BatchProcessingStrategy.CHUNKED,
                timeout_seconds=30,
                retry_attempts=2
            )
            
            # 상품 수집 태스크 생성
            task = self._collect_products_from_wholesaler(
                config, max_products_per_wholesaler, batch_config
            )
            tasks[wholesaler_type] = task
        
        # 모든 도매처 병렬 처리
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # 결과 매핑
        final_results = {}
        for (wholesaler_type, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                final_results[wholesaler_type] = BatchResult(
                    errors=[{"error": str(result), "error_type": type(result).__name__}]
                )
            else:
                final_results[wholesaler_type] = result
        
        return final_results
    
    async def _collect_products_from_wholesaler(
        self,
        config: Dict[str, Any],
        max_products: int,
        batch_config: BatchConfig
    ) -> BatchResult:
        """특정 도매처에서 상품 수집"""
        
        wholesaler_type = config["type"]
        
        # 도매처별 수집 함수
        if wholesaler_type == "ownerclan":
            collector = self._collect_ownerclan_products
        elif wholesaler_type == "zentrade":
            collector = self._collect_zentrade_products
        elif wholesaler_type == "domeggook":
            collector = self._collect_domeggook_products
        else:
            raise ValueError(f"Unknown wholesaler type: {wholesaler_type}")
        
        # 페이지 단위로 수집 작업 생성
        pages = list(range(1, (max_products // 100) + 2))  # 100개씩 페이지 처리
        
        return await self.batch_processor.process_batch(
            items=pages,
            processor_func=lambda page, conn_mgr: collector(config, page, conn_mgr),
            config=batch_config,
            batch_id=f"{wholesaler_type}_collection"
        )
    
    async def _collect_ownerclan_products(
        self,
        config: Dict[str, Any],
        page: int,
        connection_manager: ConnectionPoolManager
    ) -> List[Dict[str, Any]]:
        """오너클랜 상품 수집"""
        session = await connection_manager.get_session("ownerclan")
        
        # GraphQL 쿼리
        query = """
        query GetProducts($first: Int, $after: String) {
            allItems(first: $first, after: $after) {
                edges {
                    node {
                        key
                        name
                        price
                        status
                        images
                        category { name }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        
        variables = {"first": 100, "after": None}
        
        headers = {
            "Authorization": f"Bearer {config.get('token', '')}"
        }
        
        async with session.post(
            config["api_url"],
            json={"query": query, "variables": variables},
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                products = []
                
                for edge in data.get("data", {}).get("allItems", {}).get("edges", []):
                    node = edge["node"]
                    products.append({
                        "id": node["key"],
                        "name": node["name"],
                        "price": node["price"],
                        "status": node["status"],
                        "images": node.get("images", []),
                        "category": node.get("category", {}).get("name", ""),
                        "wholesaler": "ownerclan"
                    })
                
                return products
            else:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status
                )
    
    async def _collect_zentrade_products(
        self,
        config: Dict[str, Any],
        page: int,
        connection_manager: ConnectionPoolManager
    ) -> List[Dict[str, Any]]:
        """젠트레이드 상품 수집"""
        session = await connection_manager.get_session("zentrade")
        
        # XML API 호출
        params = {
            "cmd": "item_list",
            "page": page,
            "limit": 100,
            "access_key": config.get("access_key", ""),
            "secret_key": config.get("secret_key", "")
        }
        
        async with session.get(config["api_url"], params=params) as response:
            if response.status == 200:
                # XML 파싱 로직 (간단화)
                text = await response.text(encoding="euc-kr")
                
                # 실제로는 XML 파서 사용
                products = []
                # XML 파싱 결과를 products에 추가
                
                return products
            else:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status
                )
    
    async def _collect_domeggook_products(
        self,
        config: Dict[str, Any],
        page: int,
        connection_manager: ConnectionPoolManager
    ) -> List[Dict[str, Any]]:
        """도매꾹 상품 수집 (샘플 데이터)"""
        # 샘플 데이터 반환
        await asyncio.sleep(0.1)  # API 호출 시뮬레이션
        
        return [
            {
                "id": f"DOMEGGOOK_{page}_{i}",
                "name": f"도매꾹 상품 {page}-{i}",
                "price": 10000 + (i * 1000),
                "status": "available",
                "images": [f"https://example.com/image_{page}_{i}.jpg"],
                "category": "전자제품",
                "wholesaler": "domeggook"
            }
            for i in range(1, 21)  # 페이지당 20개
        ]
    
    async def batch_update_stock(
        self,
        stock_updates: List[Dict[str, Any]]
    ) -> BatchResult:
        """배치 재고 업데이트"""
        
        batch_config = BatchConfig(
            batch_size=50,
            max_concurrent=10,
            strategy=BatchProcessingStrategy.CHUNKED,
            timeout_seconds=10,
            retry_attempts=2
        )
        
        return await self.batch_processor.process_batch(
            items=stock_updates,
            processor_func=self._update_single_stock,
            config=batch_config,
            batch_id="stock_update"
        )
    
    async def _update_single_stock(
        self,
        stock_update: Dict[str, Any],
        connection_manager: ConnectionPoolManager
    ) -> Dict[str, Any]:
        """단일 재고 업데이트"""
        wholesaler_type = stock_update["wholesaler_type"]
        product_id = stock_update["product_id"]
        
        session = await connection_manager.get_session(wholesaler_type)
        
        # 도매처별 재고 확인 API 호출
        # 실제 구현은 도매처 API에 따라 다름
        
        return {
            "product_id": product_id,
            "previous_stock": stock_update.get("current_stock", 0),
            "new_stock": stock_update.get("new_stock", 0),
            "updated_at": time.time()
        }
    
    async def cleanup(self):
        """리소스 정리"""
        await self.connection_manager.close_all()


# 글로벌 인스턴스
wholesaler_batch_processor = WholesalerAPIBatchProcessor()


class PerformanceMonitor:
    """성능 모니터링"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.active_operations: Dict[str, float] = {}
    
    @asynccontextmanager
    async def track_operation(self, operation_name: str):
        """작업 성능 추적"""
        start_time = time.time()
        self.active_operations[operation_name] = start_time
        
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            
            if operation_name not in self.metrics:
                self.metrics[operation_name] = []
            
            self.metrics[operation_name].append(execution_time)
            
            if operation_name in self.active_operations:
                del self.active_operations[operation_name]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        report = {}
        
        for operation, times in self.metrics.items():
            if times:
                report[operation] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "total_time": sum(times)
                }
        
        report["active_operations"] = len(self.active_operations)
        return report
    
    def clear_metrics(self):
        """메트릭 초기화"""
        self.metrics.clear()


# 글로벌 모니터
performance_monitor = PerformanceMonitor()