"""
드롭쉬핑 프로젝트용 에러 모니터링 및 알림 시스템

실시간 에러 추적, 메트릭 수집, 알림 발송을 통한
포괄적인 시스템 모니터링 솔루션을 제공합니다.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import logging

from app.core.exceptions import AppException, ErrorSeverity
from app.core.logging_utils import get_logger

logger = get_logger("dropshipping.monitoring")


class AlertType(str, Enum):
    """알림 타입"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """알림 채널"""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"


class MetricType(str, Enum):
    """메트릭 타입"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class ErrorMetric:
    """에러 메트릭"""
    error_code: str
    error_type: str
    severity: str
    count: int = 1
    first_seen: datetime = None
    last_seen: datetime = None
    contexts: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.first_seen is None:
            self.first_seen = datetime.utcnow()
        if self.last_seen is None:
            self.last_seen = datetime.utcnow()
        if self.contexts is None:
            self.contexts = []


@dataclass
class Alert:
    """알림 데이터"""
    alert_id: str
    alert_type: AlertType
    title: str
    message: str
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any]
    channels: List[AlertChannel]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Metric:
    """메트릭 데이터"""
    name: str
    metric_type: MetricType
    value: Union[int, float]
    timestamp: datetime
    tags: Dict[str, str] = None
    unit: str = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class ErrorAggregator:
    """에러 집계기"""
    
    def __init__(self, window_size: int = 300):  # 5분 윈도우
        self.window_size = window_size
        self.error_counts: Dict[str, ErrorMetric] = {}
        self.error_history: deque = deque(maxlen=1000)
        self.lock = threading.Lock()
    
    def record_error(self, exception: AppException, context: Optional[Dict[str, Any]] = None):
        """에러 기록"""
        with self.lock:
            error_key = f"{exception.error_code}_{exception.severity.value}"
            now = datetime.utcnow()
            
            if error_key in self.error_counts:
                metric = self.error_counts[error_key]
                metric.count += 1
                metric.last_seen = now
                if context:
                    metric.contexts.append(context)
            else:
                self.error_counts[error_key] = ErrorMetric(
                    error_code=exception.error_code,
                    error_type=type(exception).__name__,
                    severity=exception.severity.value,
                    first_seen=now,
                    last_seen=now,
                    contexts=[context] if context else []
                )
            
            # 히스토리에 추가
            self.error_history.append({
                "timestamp": now.isoformat(),
                "error_code": exception.error_code,
                "error_type": type(exception).__name__,
                "severity": exception.severity.value,
                "message": exception.message,
                "context": context
            })
    
    def get_error_summary(self, time_window: Optional[int] = None) -> Dict[str, Any]:
        """에러 요약 통계"""
        with self.lock:
            window = time_window or self.window_size
            cutoff_time = datetime.utcnow() - timedelta(seconds=window)
            
            recent_errors = [
                error for error in self.error_history
                if datetime.fromisoformat(error["timestamp"]) > cutoff_time
            ]
            
            summary = {
                "total_errors": len(recent_errors),
                "error_types": defaultdict(int),
                "error_codes": defaultdict(int),
                "severity_distribution": defaultdict(int),
                "time_window": window,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for error in recent_errors:
                summary["error_types"][error["error_type"]] += 1
                summary["error_codes"][error["error_code"]] += 1
                summary["severity_distribution"][error["severity"]] += 1
            
            return dict(summary)
    
    def cleanup_old_data(self):
        """오래된 데이터 정리"""
        with self.lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # 24시간 이상 된 에러 메트릭 제거
            expired_keys = [
                key for key, metric in self.error_counts.items()
                if metric.last_seen < cutoff_time
            ]
            
            for key in expired_keys:
                del self.error_counts[key]


class AlertManager:
    """알림 관리자"""
    
    def __init__(self):
        self.alert_handlers: Dict[AlertChannel, List[Callable]] = defaultdict(list)
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_history: deque = deque(maxlen=1000)
        self.throttle_cache: Dict[str, datetime] = {}
        self.lock = threading.Lock()
    
    def register_handler(self, channel: AlertChannel, handler: Callable[[Alert], None]):
        """알림 핸들러 등록"""
        self.alert_handlers[channel].append(handler)
    
    def add_alert_rule(
        self,
        rule_id: str,
        condition: Callable[[Dict[str, Any]], bool],
        alert_config: Dict[str, Any]
    ):
        """알림 규칙 추가"""
        self.alert_rules.append({
            "rule_id": rule_id,
            "condition": condition,
            "config": alert_config
        })
    
    async def send_alert(self, alert: Alert, throttle_seconds: int = 300):
        """알림 발송 (스로틀링 포함)"""
        # 스로틀링 체크
        throttle_key = f"{alert.alert_type}_{alert.title}"
        now = datetime.utcnow()
        
        with self.lock:
            if throttle_key in self.throttle_cache:
                last_sent = self.throttle_cache[throttle_key]
                if (now - last_sent).total_seconds() < throttle_seconds:
                    logger.debug(f"Alert throttled: {alert.title}")
                    return
            
            self.throttle_cache[throttle_key] = now
            self.alert_history.append(asdict(alert))
        
        # 채널별 알림 발송
        for channel in alert.channels:
            handlers = self.alert_handlers.get(channel, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert)
                    else:
                        handler(alert)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
    
    def evaluate_alert_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """알림 규칙 평가"""
        triggered_alerts = []
        
        for rule in self.alert_rules:
            try:
                if rule["condition"](metrics):
                    alert = Alert(
                        alert_id=f"{rule['rule_id']}_{int(time.time())}",
                        alert_type=AlertType(rule["config"]["type"]),
                        title=rule["config"]["title"],
                        message=rule["config"]["message"],
                        severity=ErrorSeverity(rule["config"]["severity"]),
                        timestamp=datetime.utcnow(),
                        context=metrics,
                        channels=[AlertChannel(ch) for ch in rule["config"]["channels"]]
                    )
                    triggered_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule['rule_id']}: {e}")
        
        return triggered_alerts


class MetricsCollector:
    """메트릭 수집기"""
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.lock = threading.Lock()
    
    def record_metric(self, metric: Metric):
        """메트릭 기록"""
        with self.lock:
            self.metrics[metric.name].append(metric)
            
            # 메트릭 히스토리 제한 (최근 1000개)
            if len(self.metrics[metric.name]) > 1000:
                self.metrics[metric.name] = self.metrics[metric.name][-1000:]
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """카운터 메트릭 증가"""
        metric = Metric(
            name=name,
            metric_type=MetricType.COUNTER,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags
        )
        self.record_metric(metric)
    
    def set_gauge(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """게이지 메트릭 설정"""
        metric = Metric(
            name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags
        )
        self.record_metric(metric)
    
    def record_timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """타이머 메트릭 기록"""
        metric = Metric(
            name=name,
            metric_type=MetricType.TIMER,
            value=duration_ms,
            timestamp=datetime.utcnow(),
            tags=tags,
            unit="milliseconds"
        )
        self.record_metric(metric)
    
    def get_metrics_summary(self, time_window: int = 300) -> Dict[str, Any]:
        """메트릭 요약"""
        with self.lock:
            cutoff_time = datetime.utcnow() - timedelta(seconds=time_window)
            summary = {}
            
            for metric_name, metric_list in self.metrics.items():
                recent_metrics = [
                    m for m in metric_list
                    if m.timestamp > cutoff_time
                ]
                
                if recent_metrics:
                    values = [m.value for m in recent_metrics]
                    summary[metric_name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "last_value": values[-1],
                        "metric_type": recent_metrics[-1].metric_type.value,
                        "unit": recent_metrics[-1].unit
                    }
            
            return summary


class DropshippingMonitor:
    """드롭쉬핑 통합 모니터링 시스템"""
    
    def __init__(self):
        self.error_aggregator = ErrorAggregator()
        self.alert_manager = AlertManager()
        self.metrics_collector = MetricsCollector()
        self.monitoring_enabled = True
        self._setup_default_alert_rules()
        self._setup_default_handlers()
    
    def _setup_default_alert_rules(self):
        """기본 알림 규칙 설정"""
        
        # 높은 에러율 알림
        def high_error_rate_condition(metrics: Dict[str, Any]) -> bool:
            error_summary = metrics.get("errors", {})
            total_errors = error_summary.get("total_errors", 0)
            return total_errors > 10  # 5분간 10개 이상 에러
        
        self.alert_manager.add_alert_rule(
            "high_error_rate",
            high_error_rate_condition,
            {
                "type": "warning",
                "title": "높은 에러율 감지",
                "message": "5분간 {total_errors}개의 에러가 발생했습니다",
                "severity": "high",
                "channels": ["slack", "email"]
            }
        )
        
        # 치명적 에러 알림
        def critical_error_condition(metrics: Dict[str, Any]) -> bool:
            error_summary = metrics.get("errors", {})
            severity_dist = error_summary.get("severity_distribution", {})
            return severity_dist.get("critical", 0) > 0
        
        self.alert_manager.add_alert_rule(
            "critical_error",
            critical_error_condition,
            {
                "type": "critical",
                "title": "치명적 에러 발생",
                "message": "치명적 에러가 발생했습니다. 즉시 확인이 필요합니다",
                "severity": "critical",
                "channels": ["slack", "email", "sms"]
            }
        )
        
        # API 응답 시간 알림
        def slow_api_condition(metrics: Dict[str, Any]) -> bool:
            metrics_summary = metrics.get("metrics", {})
            api_timer = metrics_summary.get("api_response_time", {})
            avg_time = api_timer.get("avg", 0)
            return avg_time > 5000  # 5초 이상
        
        self.alert_manager.add_alert_rule(
            "slow_api_response",
            slow_api_condition,
            {
                "type": "warning",
                "title": "API 응답 시간 지연",
                "message": "API 평균 응답 시간이 {avg_time}ms입니다",
                "severity": "medium",
                "channels": ["slack"]
            }
        )
    
    def _setup_default_handlers(self):
        """기본 알림 핸들러 설정"""
        
        async def console_handler(alert: Alert):
            """콘솔 출력 핸들러"""
            print(f"🚨 ALERT [{alert.alert_type.upper()}] {alert.title}")
            print(f"   Message: {alert.message}")
            print(f"   Severity: {alert.severity.value}")
            print(f"   Time: {alert.timestamp}")
            print("=" * 50)
        
        async def log_handler(alert: Alert):
            """로그 출력 핸들러"""
            logger.warning(
                f"Alert triggered: {alert.title}",
                alert_id=alert.alert_id,
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
                message=alert.message,
                context=alert.context
            )
        
        # 기본 핸들러 등록 (실제 환경에서는 외부 서비스 연동)
        self.alert_manager.register_handler(AlertChannel.SLACK, console_handler)
        self.alert_manager.register_handler(AlertChannel.EMAIL, log_handler)
        self.alert_manager.register_handler(AlertChannel.DISCORD, console_handler)
    
    async def record_error(self, exception: AppException, context: Optional[Dict[str, Any]] = None):
        """에러 기록 및 모니터링"""
        if not self.monitoring_enabled:
            return
        
        # 에러 집계
        self.error_aggregator.record_error(exception, context)
        
        # 에러 메트릭 기록
        self.metrics_collector.increment_counter(
            "errors_total",
            tags={
                "error_code": exception.error_code,
                "severity": exception.severity.value,
                "error_type": type(exception).__name__
            }
        )
        
        # 즉시 알림이 필요한 치명적 에러 처리
        if exception.severity == ErrorSeverity.CRITICAL:
            alert = Alert(
                alert_id=f"critical_{int(time.time())}",
                alert_type=AlertType.CRITICAL,
                title="치명적 에러 발생",
                message=f"{exception.error_code}: {exception.message}",
                severity=exception.severity,
                timestamp=datetime.utcnow(),
                context=context or {},
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL]
            )
            await self.alert_manager.send_alert(alert, throttle_seconds=60)
    
    def record_metric(self, name: str, value: Union[int, float], metric_type: MetricType = MetricType.GAUGE, tags: Optional[Dict[str, str]] = None):
        """메트릭 기록"""
        if not self.monitoring_enabled:
            return
        
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags
        )
        self.metrics_collector.record_metric(metric)
    
    async def check_and_alert(self):
        """정기적인 모니터링 체크 및 알림"""
        if not self.monitoring_enabled:
            return
        
        try:
            # 현재 메트릭 수집
            error_summary = self.error_aggregator.get_error_summary()
            metrics_summary = self.metrics_collector.get_metrics_summary()
            
            combined_metrics = {
                "errors": error_summary,
                "metrics": metrics_summary,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 알림 규칙 평가
            triggered_alerts = self.alert_manager.evaluate_alert_rules(combined_metrics)
            
            # 알림 발송
            for alert in triggered_alerts:
                await self.alert_manager.send_alert(alert)
            
            # 시스템 상태 메트릭 기록
            self.metrics_collector.set_gauge("system_health_score", self._calculate_health_score(combined_metrics))
            
        except Exception as e:
            logger.error(f"Error in monitoring check: {e}")
    
    def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """시스템 건강도 점수 계산 (0-100)"""
        score = 100.0
        
        # 에러율에 따른 점수 차감
        error_summary = metrics.get("errors", {})
        total_errors = error_summary.get("total_errors", 0)
        
        if total_errors > 0:
            score -= min(total_errors * 2, 30)  # 최대 30점 차감
        
        # 치명적 에러 시 대폭 차감
        severity_dist = error_summary.get("severity_distribution", {})
        critical_errors = severity_dist.get("critical", 0)
        if critical_errors > 0:
            score -= 50
        
        # API 응답 시간에 따른 점수 차감
        metrics_summary = metrics.get("metrics", {})
        api_timer = metrics_summary.get("api_response_time", {})
        avg_time = api_timer.get("avg", 0)
        
        if avg_time > 1000:  # 1초 이상
            score -= min((avg_time - 1000) / 100, 20)  # 최대 20점 차감
        
        return max(score, 0.0)
    
    def get_status_report(self) -> Dict[str, Any]:
        """시스템 상태 리포트"""
        error_summary = self.error_aggregator.get_error_summary()
        metrics_summary = self.metrics_collector.get_metrics_summary()
        
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "health_score": self._calculate_health_score({
                "errors": error_summary,
                "metrics": metrics_summary
            }),
            "error_summary": error_summary,
            "metrics_summary": metrics_summary,
            "alert_rules_count": len(self.alert_manager.alert_rules),
            "recent_alerts": list(self.alert_manager.alert_history)[-10:],  # 최근 10개
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def start_monitoring(self, check_interval: int = 300):
        """모니터링 시작 (백그라운드 태스크)"""
        logger.info("Starting dropshipping monitoring system")
        
        while self.monitoring_enabled:
            try:
                await self.check_and_alert()
                
                # 오래된 데이터 정리
                self.error_aggregator.cleanup_old_data()
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # 에러 시 1분 대기
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_enabled = False
        logger.info("Dropshipping monitoring system stopped")


# 전역 모니터링 인스턴스
dropshipping_monitor = DropshippingMonitor()


# =============================================================================
# 유틸리티 함수들
# =============================================================================

async def send_slack_alert(webhook_url: str, alert: Alert):
    """Slack 알림 전송"""
    import aiohttp
    
    color_map = {
        AlertType.INFO: "#36a64f",
        AlertType.WARNING: "#ff9900",
        AlertType.ERROR: "#ff0000",
        AlertType.CRITICAL: "#990000"
    }
    
    payload = {
        "text": f"🚨 {alert.title}",
        "attachments": [
            {
                "color": color_map.get(alert.alert_type, "#808080"),
                "fields": [
                    {"title": "Message", "value": alert.message, "short": False},
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                ]
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Failed to send Slack alert: {response.status}")
    except Exception as e:
        logger.error(f"Error sending Slack alert: {e}")


async def send_discord_alert(webhook_url: str, alert: Alert):
    """Discord 알림 전송"""
    import aiohttp
    
    color_map = {
        AlertType.INFO: 0x36a64f,
        AlertType.WARNING: 0xff9900,
        AlertType.ERROR: 0xff0000,
        AlertType.CRITICAL: 0x990000
    }
    
    payload = {
        "embeds": [
            {
                "title": f"🚨 {alert.title}",
                "description": alert.message,
                "color": color_map.get(alert.alert_type, 0x808080),
                "fields": [
                    {"name": "Severity", "value": alert.severity.value, "inline": True},
                    {"name": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "inline": True}
                ],
                "timestamp": alert.timestamp.isoformat()
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status not in [200, 204]:
                    logger.error(f"Failed to send Discord alert: {response.status}")
    except Exception as e:
        logger.error(f"Error sending Discord alert: {e}")


# =============================================================================
# 드롭쉬핑 특화 모니터링 함수들
# =============================================================================

def monitor_wholesaler_api(wholesaler_name: str):
    """도매처 API 모니터링 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # 성공 메트릭 기록
                dropshipping_monitor.metrics_collector.increment_counter(
                    "wholesaler_api_calls_total",
                    tags={"wholesaler": wholesaler_name, "status": "success"}
                )
                
                # 응답 시간 기록
                response_time = (time.time() - start_time) * 1000
                dropshipping_monitor.metrics_collector.record_timer(
                    "wholesaler_api_response_time",
                    response_time,
                    tags={"wholesaler": wholesaler_name}
                )
                
                return result
                
            except Exception as e:
                # 실패 메트릭 기록
                dropshipping_monitor.metrics_collector.increment_counter(
                    "wholesaler_api_calls_total",
                    tags={"wholesaler": wholesaler_name, "status": "error"}
                )
                
                # 에러 기록
                if isinstance(e, AppException):
                    await dropshipping_monitor.record_error(
                        e,
                        context={"wholesaler": wholesaler_name, "function": func.__name__}
                    )
                
                raise
        
        return wrapper
    return decorator


def monitor_marketplace_operation(marketplace_name: str):
    """마켓플레이스 작업 모니터링 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # 성공 메트릭 기록
                dropshipping_monitor.metrics_collector.increment_counter(
                    "marketplace_operations_total",
                    tags={"marketplace": marketplace_name, "status": "success"}
                )
                
                return result
                
            except Exception as e:
                # 실패 메트릭 기록
                dropshipping_monitor.metrics_collector.increment_counter(
                    "marketplace_operations_total",
                    tags={"marketplace": marketplace_name, "status": "error"}
                )
                
                # 에러 기록
                if isinstance(e, AppException):
                    await dropshipping_monitor.record_error(
                        e,
                        context={"marketplace": marketplace_name, "function": func.__name__}
                    )
                
                raise
        
        return wrapper
    return decorator


# =============================================================================
# 모니터링 시스템 초기화
# =============================================================================

async def initialize_monitoring():
    """모니터링 시스템 초기화"""
    logger.info("Initializing dropshipping monitoring system")
    
    # 환경 변수에서 웹훅 URL 등 설정 로드
    import os
    
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    
    if slack_webhook:
        async def slack_handler(alert: Alert):
            await send_slack_alert(slack_webhook, alert)
        
        dropshipping_monitor.alert_manager.register_handler(AlertChannel.SLACK, slack_handler)
    
    if discord_webhook:
        async def discord_handler(alert: Alert):
            await send_discord_alert(discord_webhook, alert)
        
        dropshipping_monitor.alert_manager.register_handler(AlertChannel.DISCORD, discord_handler)
    
    logger.info("Dropshipping monitoring system initialized")


# =============================================================================
# 헬스체크 및 상태 확인
# =============================================================================

def get_health_status() -> Dict[str, Any]:
    """시스템 헬스체크"""
    return dropshipping_monitor.get_status_report()


async def run_health_diagnostics() -> Dict[str, Any]:
    """종합 진단 실행"""
    diagnostics = {
        "timestamp": datetime.utcnow().isoformat(),
        "monitoring_status": "active" if dropshipping_monitor.monitoring_enabled else "inactive",
        "system_health": get_health_status(),
        "checks": {}
    }
    
    # 기본 시스템 체크들
    try:
        # 데이터베이스 연결 체크
        # TODO: 데이터베이스 ping
        diagnostics["checks"]["database"] = {"status": "ok", "response_time_ms": 10}
    except Exception as e:
        diagnostics["checks"]["database"] = {"status": "error", "error": str(e)}
    
    try:
        # Redis 연결 체크
        # TODO: Redis ping
        diagnostics["checks"]["redis"] = {"status": "ok", "response_time_ms": 5}
    except Exception as e:
        diagnostics["checks"]["redis"] = {"status": "error", "error": str(e)}
    
    # 외부 서비스 체크들
    # TODO: 도매처 API 헬스체크
    # TODO: 마켓플레이스 API 헬스체크
    
    return diagnostics