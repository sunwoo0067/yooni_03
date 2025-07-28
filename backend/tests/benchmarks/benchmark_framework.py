"""
Performance benchmark framework.
성능 벤치마크 프레임워크.
"""
import time
import asyncio
import statistics
from typing import Callable, Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import csv
from pathlib import Path

from app.core.logging_utils import get_logger


@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    name: str
    iterations: int
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    std_dev: float
    percentiles: Dict[int, float]
    throughput: float  # operations per second
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class Benchmark:
    """벤치마크 실행기"""
    
    def __init__(self, name: str, warmup_iterations: int = 5):
        self.name = name
        self.warmup_iterations = warmup_iterations
        self.logger = get_logger(f"Benchmark.{name}")
        self.results: List[BenchmarkResult] = []
        
    def run_sync(
        self, 
        func: Callable, 
        iterations: int = 100,
        *args, 
        **kwargs
    ) -> BenchmarkResult:
        """동기 함수 벤치마크"""
        # 워밍업
        self.logger.info(f"Warming up {self.name} ({self.warmup_iterations} iterations)")
        for _ in range(self.warmup_iterations):
            func(*args, **kwargs)
            
        # 실제 측정
        self.logger.info(f"Running {self.name} ({iterations} iterations)")
        times = []
        
        for i in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
            
            if (i + 1) % (iterations // 10) == 0:
                self.logger.debug(f"Progress: {(i + 1) / iterations * 100:.0f}%")
                
        return self._calculate_results(times, iterations)
        
    async def run_async(
        self,
        func: Callable,
        iterations: int = 100,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """비동기 함수 벤치마크"""
        # 워밍업
        self.logger.info(f"Warming up {self.name} ({self.warmup_iterations} iterations)")
        for _ in range(self.warmup_iterations):
            await func(*args, **kwargs)
            
        # 실제 측정
        self.logger.info(f"Running {self.name} ({iterations} iterations)")
        times = []
        
        for i in range(iterations):
            start = time.perf_counter()
            await func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
            
            if (i + 1) % (iterations // 10) == 0:
                self.logger.debug(f"Progress: {(i + 1) / iterations * 100:.0f}%")
                
        return self._calculate_results(times, iterations)
        
    async def run_concurrent(
        self,
        func: Callable,
        iterations: int = 100,
        concurrency: int = 10,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """동시성 벤치마크"""
        self.logger.info(
            f"Running concurrent {self.name} "
            f"({iterations} iterations, {concurrency} concurrent)"
        )
        
        async def run_batch(batch_size: int) -> List[float]:
            tasks = []
            for _ in range(batch_size):
                task_start = time.perf_counter()
                task = asyncio.create_task(func(*args, **kwargs))
                tasks.append((task, task_start))
                
            results = []
            for task, task_start in tasks:
                await task
                task_end = time.perf_counter()
                results.append(task_end - task_start)
                
            return results
            
        # 배치로 실행
        all_times = []
        batches = (iterations + concurrency - 1) // concurrency
        
        start_time = time.perf_counter()
        
        for i in range(batches):
            batch_size = min(concurrency, iterations - i * concurrency)
            batch_times = await run_batch(batch_size)
            all_times.extend(batch_times)
            
            if (i + 1) % (batches // 10 or 1) == 0:
                self.logger.debug(f"Progress: {(i + 1) / batches * 100:.0f}%")
                
        total_time = time.perf_counter() - start_time
        
        result = self._calculate_results(all_times, iterations)
        # 동시성 메타데이터 추가
        result.metadata["concurrency"] = concurrency
        result.metadata["total_wall_time"] = total_time
        result.metadata["concurrent_throughput"] = iterations / total_time
        
        return result
        
    def _calculate_results(
        self, 
        times: List[float], 
        iterations: int
    ) -> BenchmarkResult:
        """결과 계산"""
        times.sort()
        
        result = BenchmarkResult(
            name=self.name,
            iterations=iterations,
            total_time=sum(times),
            min_time=times[0],
            max_time=times[-1],
            avg_time=statistics.mean(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            percentiles={
                50: self._percentile(times, 50),
                90: self._percentile(times, 90),
                95: self._percentile(times, 95),
                99: self._percentile(times, 99)
            },
            throughput=iterations / sum(times)
        )
        
        self.results.append(result)
        return result
        
    def _percentile(self, sorted_data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_data):
            return sorted_data[lower]
            
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
        
    def compare(self, other: 'Benchmark') -> Dict[str, Any]:
        """다른 벤치마크와 비교"""
        if not self.results or not other.results:
            raise ValueError("No results to compare")
            
        self_latest = self.results[-1]
        other_latest = other.results[-1]
        
        improvement = (other_latest.avg_time - self_latest.avg_time) / other_latest.avg_time * 100
        
        return {
            "baseline": {
                "name": other.name,
                "avg_time": other_latest.avg_time,
                "throughput": other_latest.throughput
            },
            "current": {
                "name": self.name,
                "avg_time": self_latest.avg_time,
                "throughput": self_latest.throughput
            },
            "improvement_percent": improvement,
            "speedup": other_latest.avg_time / self_latest.avg_time
        }


class BenchmarkSuite:
    """벤치마크 스위트"""
    
    def __init__(self, name: str):
        self.name = name
        self.benchmarks: Dict[str, Benchmark] = {}
        self.logger = get_logger(f"BenchmarkSuite.{name}")
        
    def add_benchmark(self, benchmark: Benchmark):
        """벤치마크 추가"""
        self.benchmarks[benchmark.name] = benchmark
        
    async def run_all(self) -> Dict[str, BenchmarkResult]:
        """모든 벤치마크 실행"""
        results = {}
        
        for name, benchmark in self.benchmarks.items():
            self.logger.info(f"Running benchmark: {name}")
            # 벤치마크 타입에 따라 실행
            # 여기서는 예제로 async 실행
            results[name] = benchmark.results[-1] if benchmark.results else None
            
        return results
        
    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """보고서 생성"""
        report = {
            "suite": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "benchmarks": {}
        }
        
        for name, benchmark in self.benchmarks.items():
            if benchmark.results:
                latest = benchmark.results[-1]
                report["benchmarks"][name] = {
                    "iterations": latest.iterations,
                    "avg_time_ms": latest.avg_time * 1000,
                    "min_time_ms": latest.min_time * 1000,
                    "max_time_ms": latest.max_time * 1000,
                    "median_time_ms": latest.median_time * 1000,
                    "std_dev_ms": latest.std_dev * 1000,
                    "percentiles": {
                        f"p{k}": v * 1000 for k, v in latest.percentiles.items()
                    },
                    "throughput_ops": latest.throughput,
                    "metadata": latest.metadata
                }
                
        report_json = json.dumps(report, indent=2)
        
        if output_path:
            output_path.write_text(report_json)
            self.logger.info(f"Report saved to {output_path}")
            
        return report_json
        
    def export_csv(self, output_path: Path):
        """CSV로 내보내기"""
        rows = []
        
        for name, benchmark in self.benchmarks.items():
            for result in benchmark.results:
                rows.append({
                    "benchmark": name,
                    "timestamp": result.timestamp,
                    "iterations": result.iterations,
                    "avg_time_ms": result.avg_time * 1000,
                    "min_time_ms": result.min_time * 1000,
                    "max_time_ms": result.max_time * 1000,
                    "median_time_ms": result.median_time * 1000,
                    "p90_ms": result.percentiles.get(90, 0) * 1000,
                    "p99_ms": result.percentiles.get(99, 0) * 1000,
                    "throughput_ops": result.throughput
                })
                
        if rows:
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                
            self.logger.info(f"CSV exported to {output_path}")


# 벤치마크 데코레이터
def benchmark(name: str = None, iterations: int = 100):
    """함수 벤치마크 데코레이터"""
    def decorator(func):
        benchmark_name = name or func.__name__
        bench = Benchmark(benchmark_name)
        
        if asyncio.iscoroutinefunction(func):
            async def wrapper(*args, **kwargs):
                # 벤치마크 실행 옵션
                if kwargs.pop("_benchmark", False):
                    return await bench.run_async(func, iterations, *args, **kwargs)
                return await func(*args, **kwargs)
        else:
            def wrapper(*args, **kwargs):
                # 벤치마크 실행 옵션
                if kwargs.pop("_benchmark", False):
                    return bench.run_sync(func, iterations, *args, **kwargs)
                return func(*args, **kwargs)
                
        wrapper._benchmark = bench
        return wrapper
    return decorator


# 메모리 사용량 측정
class MemoryBenchmark:
    """메모리 사용량 벤치마크"""
    
    def __init__(self):
        import psutil
        self.process = psutil.Process()
        
    def measure(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """메모리 사용량 측정"""
        import gc
        
        # GC 실행
        gc.collect()
        
        # 시작 메모리
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # 함수 실행
        if asyncio.iscoroutinefunction(func):
            result = asyncio.run(func(*args, **kwargs))
        else:
            result = func(*args, **kwargs)
            
        # 종료 메모리
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_increase_mb": end_memory - start_memory,
            "result": result
        }