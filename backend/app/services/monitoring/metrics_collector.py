"""
메트릭 수집기 모듈
API 응답 시간, DB 쿼리 성능, 캐시 히트율, 비즈니스 메트릭 추적
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
import asyncio
from functools import wraps
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.order_core import Order
from app.models.payment import Payment
from app.core.logger import logger


class MetricsCollector:
    """메트릭 수집 및 관리 클래스"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))  # 최근 1000개 메트릭만 유지
        self.counters = defaultdict(int)
        self.timings = defaultdict(list)
        self._start_time = time.time()
        
    def record_timing(self, metric_name: str, duration: float):
        """타이밍 메트릭 기록"""
        self.timings[metric_name].append({
            'timestamp': datetime.utcnow(),
            'duration': duration
        })
        # 24시간 이상 된 데이터 정리
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.timings[metric_name] = [
            t for t in self.timings[metric_name] 
            if t['timestamp'] > cutoff
        ]
        
    def increment_counter(self, metric_name: str, value: int = 1):
        """카운터 메트릭 증가"""
        self.counters[metric_name] += value
        
    def record_gauge(self, metric_name: str, value: float):
        """게이지 메트릭 기록"""
        self.metrics[metric_name].append({
            'timestamp': datetime.utcnow(),
            'value': value
        })
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약 정보 반환"""
        summary = {
            'uptime_seconds': time.time() - self._start_time,
            'counters': dict(self.counters),
            'timings': {},
            'gauges': {}
        }
        
        # 타이밍 메트릭 통계
        for name, timings in self.timings.items():
            if timings:
                durations = [t['duration'] for t in timings]
                summary['timings'][name] = {
                    'count': len(durations),
                    'mean': statistics.mean(durations),
                    'median': statistics.median(durations),
                    'p95': self._percentile(durations, 95),
                    'p99': self._percentile(durations, 99),
                    'min': min(durations),
                    'max': max(durations)
                }
                
        # 게이지 메트릭 현재값
        for name, values in self.metrics.items():
            if values:
                summary['gauges'][name] = {
                    'current': values[-1]['value'],
                    'timestamp': values[-1]['timestamp'].isoformat()
                }
                
        return summary
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        size = len(data)
        if size == 0:
            return 0
        sorted_data = sorted(data)
        index = int(size * percentile / 100)
        return sorted_data[min(index, size - 1)]


# 전역 메트릭 수집기 인스턴스
metrics_collector = MetricsCollector()


def track_time(metric_name: str):
    """함수 실행 시간 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics_collector.record_timing(metric_name, duration)
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics_collector.record_timing(metric_name, duration)
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class APIMetrics:
    """API 관련 메트릭 수집"""
    
    @staticmethod
    def record_request(method: str, path: str, status_code: int, duration: float):
        """API 요청 메트릭 기록"""
        # 응답 시간 기록
        metrics_collector.record_timing(f"api.request.{method.lower()}.{path}", duration)
        
        # 상태 코드별 카운터
        metrics_collector.increment_counter(f"api.status.{status_code}")
        
        # 메서드별 카운터
        metrics_collector.increment_counter(f"api.method.{method.lower()}")
        
        # 에러율 계산용
        if status_code >= 400:
            metrics_collector.increment_counter("api.errors.total")
            if status_code >= 500:
                metrics_collector.increment_counter("api.errors.5xx")
            else:
                metrics_collector.increment_counter("api.errors.4xx")


class DatabaseMetrics:
    """데이터베이스 관련 메트릭 수집"""
    
    @staticmethod
    @track_time("db.query.duration")
    async def track_query(query_type: str, table_name: str, duration: float):
        """DB 쿼리 메트릭 기록"""
        metrics_collector.record_timing(f"db.{query_type}.{table_name}", duration)
        metrics_collector.increment_counter(f"db.queries.{query_type}")


class CacheMetrics:
    """캐시 관련 메트릭 수집"""
    
    @staticmethod
    async def record_hit():
        """캐시 히트 기록"""
        metrics_collector.increment_counter("cache.hits")
        
    @staticmethod
    async def record_miss():
        """캐시 미스 기록"""
        metrics_collector.increment_counter("cache.misses")
        
    @staticmethod
    def get_hit_rate() -> float:
        """캐시 히트율 계산"""
        hits = metrics_collector.counters.get("cache.hits", 0)
        misses = metrics_collector.counters.get("cache.misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0


class BusinessMetrics:
    """비즈니스 메트릭 수집"""
    
    @staticmethod
    async def collect_order_metrics(db: AsyncSession):
        """주문 관련 메트릭 수집"""
        try:
            # 오늘 주문 수
            today = datetime.utcnow().date()
            today_orders = await db.execute(
                select(func.count(Order.id)).where(
                    func.date(Order.created_at) == today
                )
            )
            order_count = today_orders.scalar()
            metrics_collector.record_gauge("business.orders.today", order_count)
            
            # 오늘 매출
            today_revenue = await db.execute(
                select(func.sum(Order.total_amount)).where(
                    func.date(Order.created_at) == today,
                    Order.status == "COMPLETED"
                )
            )
            revenue = today_revenue.scalar() or 0
            metrics_collector.record_gauge("business.revenue.today", float(revenue))
            
            # 평균 주문 금액
            if order_count > 0:
                avg_order_value = revenue / order_count
                metrics_collector.record_gauge("business.orders.avg_value", avg_order_value)
                
        except Exception as e:
            logger.error(f"Failed to collect order metrics: {e}")
            
    @staticmethod
    async def collect_payment_metrics(db: AsyncSession):
        """결제 관련 메트릭 수집"""
        try:
            # 결제 성공률
            today = datetime.utcnow().date()
            total_payments = await db.execute(
                select(func.count(Payment.id)).where(
                    func.date(Payment.created_at) == today
                )
            )
            total_count = total_payments.scalar()
            
            success_payments = await db.execute(
                select(func.count(Payment.id)).where(
                    func.date(Payment.created_at) == today,
                    Payment.status == "COMPLETED"
                )
            )
            success_count = success_payments.scalar()
            
            if total_count > 0:
                success_rate = (success_count / total_count) * 100
                metrics_collector.record_gauge("business.payments.success_rate", success_rate)
                
        except Exception as e:
            logger.error(f"Failed to collect payment metrics: {e}")


async def collect_system_metrics():
    """시스템 메트릭 주기적 수집"""
    while True:
        try:
            # Redis 연결 상태
            redis = await get_redis()
            if redis:
                await redis.ping()
                metrics_collector.record_gauge("system.redis.connected", 1)
            else:
                metrics_collector.record_gauge("system.redis.connected", 0)
                
            # 메모리 사용량 (간단한 예제)
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            metrics_collector.record_gauge("system.memory.mb", memory_mb)
            
            # CPU 사용률
            cpu_percent = process.cpu_percent(interval=1)
            metrics_collector.record_gauge("system.cpu.percent", cpu_percent)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            
        await asyncio.sleep(60)  # 1분마다 수집


# 메트릭 수집 시작 함수
async def start_metrics_collection():
    """백그라운드 메트릭 수집 시작"""
    asyncio.create_task(collect_system_metrics())
    logger.info("Metrics collection started")