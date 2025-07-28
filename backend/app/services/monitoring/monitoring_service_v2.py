"""
Enhanced monitoring service with metrics collection.
메트릭 수집이 포함된 향상된 모니터링 서비스.
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import psutil
import json

from app.core.logging_utils import get_logger
from app.core.cache_utils import CacheService
from app.core.constants import Limits


class MetricsCollector:
    """메트릭 수집기"""
    
    def __init__(self, window_size: int = 300):  # 5분 윈도우
        self.window_size = window_size
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.logger = get_logger(self.__class__.__name__)
        
    def record(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """메트릭 기록"""
        timestamp = time.time()
        
        metric_data = {
            "timestamp": timestamp,
            "value": value,
            "tags": tags or {}
        }
        
        # 메트릭 이름과 태그로 키 생성
        key = self._make_key(metric_name, tags)
        self.metrics[key].append(metric_data)
        
    def _make_key(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """메트릭 키 생성"""
        if not tags:
            return metric_name
            
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name},{tag_str}"
        
    def get_metrics(
        self, 
        metric_name: str, 
        tags: Optional[Dict[str, str]] = None,
        last_seconds: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """메트릭 조회"""
        key = self._make_key(metric_name, tags)
        
        if key not in self.metrics:
            return []
            
        metrics = list(self.metrics[key])
        
        if last_seconds:
            cutoff_time = time.time() - last_seconds
            metrics = [m for m in metrics if m["timestamp"] >= cutoff_time]
            
        return metrics
        
    def calculate_stats(
        self, 
        metric_name: str, 
        tags: Optional[Dict[str, str]] = None,
        last_seconds: int = 60
    ) -> Dict[str, float]:
        """메트릭 통계 계산"""
        metrics = self.get_metrics(metric_name, tags, last_seconds)
        
        if not metrics:
            return {
                "count": 0,
                "sum": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "p50": 0,
                "p90": 0,
                "p99": 0
            }
            
        values = [m["value"] for m in metrics]
        values.sort()
        
        count = len(values)
        total = sum(values)
        
        return {
            "count": count,
            "sum": total,
            "avg": total / count,
            "min": values[0],
            "max": values[-1],
            "p50": self._percentile(values, 50),
            "p90": self._percentile(values, 90),
            "p99": self._percentile(values, 99)
        }
        
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """백분위수 계산"""
        if not sorted_values:
            return 0
            
        index = (len(sorted_values) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_values):
            return sorted_values[lower]
            
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


class SystemMonitor:
    """시스템 리소스 모니터"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.logger = get_logger(self.__class__.__name__)
        
    async def collect_system_metrics(self):
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metrics.record("system.cpu.usage", cpu_percent)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            self.metrics.record("system.memory.usage", memory.percent)
            self.metrics.record("system.memory.available", memory.available)
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            self.metrics.record("system.disk.usage", disk.percent)
            self.metrics.record("system.disk.free", disk.free)
            
            # 네트워크 I/O
            net_io = psutil.net_io_counters()
            self.metrics.record("system.network.bytes_sent", net_io.bytes_sent)
            self.metrics.record("system.network.bytes_recv", net_io.bytes_recv)
            
            # 프로세스 정보
            process = psutil.Process()
            self.metrics.record("process.cpu.usage", process.cpu_percent())
            self.metrics.record("process.memory.rss", process.memory_info().rss)
            self.metrics.record("process.threads", process.num_threads())
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")


class ApplicationMonitor:
    """애플리케이션 메트릭 모니터"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.logger = get_logger(self.__class__.__name__)
        
    def record_request(
        self, 
        endpoint: str, 
        method: str, 
        status_code: int,
        response_time: float
    ):
        """HTTP 요청 메트릭 기록"""
        tags = {
            "endpoint": endpoint,
            "method": method,
            "status": str(status_code)
        }
        
        # 응답 시간
        self.metrics.record("http.request.duration", response_time, tags)
        
        # 요청 수
        self.metrics.record("http.request.count", 1, tags)
        
        # 에러율
        if status_code >= 400:
            self.metrics.record("http.request.error", 1, tags)
            
    def record_database_query(
        self,
        operation: str,
        table: str,
        duration: float,
        success: bool = True
    ):
        """데이터베이스 쿼리 메트릭 기록"""
        tags = {
            "operation": operation,
            "table": table,
            "status": "success" if success else "error"
        }
        
        self.metrics.record("db.query.duration", duration, tags)
        self.metrics.record("db.query.count", 1, tags)
        
    def record_cache_operation(
        self,
        operation: str,
        hit: bool,
        duration: float
    ):
        """캐시 작업 메트릭 기록"""
        tags = {
            "operation": operation,
            "result": "hit" if hit else "miss"
        }
        
        self.metrics.record("cache.operation.duration", duration, tags)
        self.metrics.record("cache.operation.count", 1, tags)
        
    def record_business_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """비즈니스 메트릭 기록"""
        self.metrics.record(f"business.{metric_name}", value, tags)


class AlertManager:
    """알림 관리자"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.logger = get_logger(self.__class__.__name__)
        self.alert_rules = []
        self.alert_history = deque(maxlen=1000)
        
    def add_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,  # "gt", "lt", "eq"
        threshold: float,
        duration: int = 60,  # 조건이 유지되어야 하는 시간(초)
        tags: Optional[Dict[str, str]] = None
    ):
        """알림 규칙 추가"""
        self.alert_rules.append({
            "name": name,
            "metric_name": metric_name,
            "condition": condition,
            "threshold": threshold,
            "duration": duration,
            "tags": tags,
            "triggered_at": None
        })
        
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """알림 조건 확인"""
        triggered_alerts = []
        
        for rule in self.alert_rules:
            stats = self.metrics.calculate_stats(
                rule["metric_name"],
                rule["tags"],
                rule["duration"]
            )
            
            if stats["count"] == 0:
                continue
                
            # 조건 확인
            value = stats["avg"]
            triggered = False
            
            if rule["condition"] == "gt" and value > rule["threshold"]:
                triggered = True
            elif rule["condition"] == "lt" and value < rule["threshold"]:
                triggered = True
            elif rule["condition"] == "eq" and value == rule["threshold"]:
                triggered = True
                
            if triggered:
                alert = {
                    "name": rule["name"],
                    "metric": rule["metric_name"],
                    "value": value,
                    "threshold": rule["threshold"],
                    "condition": rule["condition"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                triggered_alerts.append(alert)
                self.alert_history.append(alert)
                
                self.logger.warning(
                    f"Alert triggered: {rule['name']}",
                    extra=alert
                )
                
        return triggered_alerts


class MonitoringServiceV2:
    """통합 모니터링 서비스"""
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service
        self.metrics_collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.app_monitor = ApplicationMonitor(self.metrics_collector)
        self.alert_manager = AlertManager(self.metrics_collector)
        self.logger = get_logger(self.__class__.__name__)
        
        # 기본 알림 규칙 설정
        self._setup_default_alerts()
        
    def _setup_default_alerts(self):
        """기본 알림 규칙 설정"""
        # CPU 사용률 경고
        self.alert_manager.add_rule(
            name="High CPU Usage",
            metric_name="system.cpu.usage",
            condition="gt",
            threshold=80.0,
            duration=300  # 5분
        )
        
        # 메모리 사용률 경고
        self.alert_manager.add_rule(
            name="High Memory Usage",
            metric_name="system.memory.usage",
            condition="gt",
            threshold=90.0,
            duration=300
        )
        
        # API 에러율 경고
        self.alert_manager.add_rule(
            name="High Error Rate",
            metric_name="http.request.error",
            condition="gt",
            threshold=10.0,  # 분당 10개 이상
            duration=60
        )
        
        # 응답 시간 경고
        self.alert_manager.add_rule(
            name="Slow Response Time",
            metric_name="http.request.duration",
            condition="gt",
            threshold=1000.0,  # 1초
            duration=300
        )
        
    async def start_monitoring(self):
        """모니터링 시작"""
        self.logger.info("Starting monitoring service")
        
        while True:
            try:
                # 시스템 메트릭 수집
                await self.system_monitor.collect_system_metrics()
                
                # 알림 확인
                alerts = await self.alert_manager.check_alerts()
                if alerts:
                    await self._handle_alerts(alerts)
                    
                # 메트릭 캐싱 (선택적)
                if self.cache_service:
                    await self._cache_metrics()
                    
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                
            await asyncio.sleep(10)  # 10초마다 수집
            
    async def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """알림 처리"""
        # 여기에 알림 발송 로직 구현 (이메일, Slack 등)
        for alert in alerts:
            self.logger.warning(f"Alert: {alert['name']} - {alert['metric']} = {alert['value']}")
            
    async def _cache_metrics(self):
        """메트릭 캐싱"""
        # 최근 메트릭을 캐시에 저장
        metrics_summary = self.get_metrics_summary()
        await self.cache_service.set(
            "monitoring:metrics:latest",
            metrics_summary,
            ttl=60
        )
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약 조회"""
        return {
            "system": {
                "cpu": self.metrics_collector.calculate_stats("system.cpu.usage", last_seconds=60),
                "memory": self.metrics_collector.calculate_stats("system.memory.usage", last_seconds=60),
                "disk": self.metrics_collector.calculate_stats("system.disk.usage", last_seconds=60)
            },
            "application": {
                "requests": self.metrics_collector.calculate_stats("http.request.count", last_seconds=60),
                "errors": self.metrics_collector.calculate_stats("http.request.error", last_seconds=60),
                "response_time": self.metrics_collector.calculate_stats("http.request.duration", last_seconds=60),
                "database": self.metrics_collector.calculate_stats("db.query.duration", last_seconds=60),
                "cache": self.metrics_collector.calculate_stats("cache.operation.count", last_seconds=60)
            },
            "alerts": list(self.alert_manager.alert_history)[-10:]  # 최근 10개 알림
        }
        
    def export_metrics(self, format: str = "prometheus") -> str:
        """메트릭 내보내기"""
        if format == "prometheus":
            return self._export_prometheus()
        elif format == "json":
            return self._export_json()
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def _export_prometheus(self) -> str:
        """Prometheus 형식으로 내보내기"""
        lines = []
        
        for key, metrics in self.metrics_collector.metrics.items():
            if not metrics:
                continue
                
            # 메트릭 이름과 태그 파싱
            parts = key.split(",", 1)
            metric_name = parts[0].replace(".", "_")
            tags = parts[1] if len(parts) > 1 else ""
            
            # 최신 값
            latest = metrics[-1]
            value = latest["value"]
            
            # Prometheus 형식
            if tags:
                line = f'{metric_name}{{{tags}}} {value}'
            else:
                line = f'{metric_name} {value}'
                
            lines.append(line)
            
        return "\n".join(lines)
        
    def _export_json(self) -> str:
        """JSON 형식으로 내보내기"""
        return json.dumps(self.get_metrics_summary(), indent=2)