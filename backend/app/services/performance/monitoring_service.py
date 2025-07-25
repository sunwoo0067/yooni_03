"""
시스템 모니터링 및 알림 서비스
실시간 성능 모니터링, 로깅, 알림 시스템
"""

import asyncio
import logging
import json
import smtplib
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import text
import psutil
import requests

from ...core.config import get_settings
from .cache_manager import CacheManager


@dataclass
class Alert:
    """알림 데이터 클래스"""
    id: str
    type: str
    severity: str  # low, medium, high, critical
    title: str
    message: str
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class HealthCheck:
    """헬스체크 결과 데이터 클래스"""
    service: str
    status: str  # healthy, unhealthy, degraded
    response_time_ms: float
    timestamp: datetime
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class MonitoringService:
    """시스템 모니터링 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.cache_manager = CacheManager()
        
        # 알림 저장소
        self.alerts: List[Alert] = []
        self.health_checks: List[HealthCheck] = []
        
        # 모니터링 설정
        self.monitoring_interval = 30  # 30초마다 체크
        self.alert_thresholds = {
            "cpu_percent": {"warning": 70, "critical": 85},
            "memory_percent": {"warning": 80, "critical": 90},
            "disk_percent": {"warning": 85, "critical": 95},
            "response_time_ms": {"warning": 1000, "critical": 3000},
            "error_rate_percent": {"warning": 5, "critical": 10},
            "db_connections": {"warning": 80, "critical": 95}
        }
        
        # 알림 채널 설정
        self.notification_channels = {
            "email": self._send_email_alert,
            "slack": self._send_slack_alert,
            "discord": self._send_discord_alert
        }
        
        # 로거 설정
        self.logger = self._setup_structured_logger()
    
    def _setup_structured_logger(self) -> logging.Logger:
        """구조화된 로거 설정"""
        logger = logging.getLogger("yooni_monitoring")
        logger.setLevel(logging.INFO)
        
        # 핸들러가 이미 있으면 제거
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 파일 핸들러
        file_handler = logging.FileHandler("logs/monitoring.log")
        file_handler.setLevel(logging.INFO)
        
        # JSON 포맷터
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # 추가 필드가 있으면 포함
                if hasattr(record, 'extra_fields'):
                    log_entry.update(record.extra_fields)
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
        return logger
    
    async def start_monitoring(self):
        """모니터링 시작"""
        self.logger.info("Monitoring service started")
        
        while True:
            try:
                # 시스템 메트릭 수집
                await self._collect_system_metrics()
                
                # 헬스체크 실행
                await self._run_health_checks()
                
                # 알림 처리
                await self._process_alerts()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error("Monitoring error", extra={
                    'extra_fields': {'error': str(e)}
                })
                await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_system_metrics(self):
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # 네트워크 I/O
            network = psutil.net_io_counters()
            
            # 데이터베이스 연결 수
            db_connections = await self._get_db_connection_count()
            
            # 메트릭 로깅
            self.logger.info("System metrics collected", extra={
                'extra_fields': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'db_connections': db_connections,
                    'network_bytes_sent': network.bytes_sent,
                    'network_bytes_recv': network.bytes_recv
                }
            })
            
            # 임계값 체크 및 알림 생성
            await self._check_thresholds({
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'db_connections': db_connections
            })
            
            # 캐시에 메트릭 저장
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'db_connections': db_connections
            }
            
            self.cache_manager.set(
                f"metrics:{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                metrics_data, 
                ttl=3600,  # 1시간 보관
                namespace="monitoring"
            )
            
        except Exception as e:
            self.logger.error("Failed to collect system metrics", extra={
                'extra_fields': {'error': str(e)}
            })
    
    async def _get_db_connection_count(self) -> int:
        """데이터베이스 연결 수 조회"""
        try:
            result = self.db.execute(text(
                "SELECT count(*) as conn_count FROM pg_stat_activity WHERE state = 'active'"
            )).fetchone()
            return result.conn_count if result else 0
        except Exception:
            return 0
    
    async def _check_thresholds(self, metrics: Dict[str, float]):
        """임계값 체크 및 알림 생성"""
        for metric_name, value in metrics.items():
            if metric_name in self.alert_thresholds:
                thresholds = self.alert_thresholds[metric_name]
                
                severity = None
                if value >= thresholds["critical"]:
                    severity = "critical"
                elif value >= thresholds["warning"]:
                    severity = "warning"
                
                if severity:
                    await self._create_alert(
                        alert_type=f"{metric_name}_high",
                        severity=severity,
                        title=f"{metric_name.replace('_', ' ').title()} High",
                        message=f"{metric_name} is {value:.1f}% (threshold: {thresholds[severity]}%)",
                        source="system_monitor",
                        metadata={"metric": metric_name, "value": value, "threshold": thresholds[severity]}
                    )
    
    async def _run_health_checks(self):
        """헬스체크 실행"""
        health_checks = []
        
        # 데이터베이스 헬스체크
        db_health = await self._check_database_health()
        health_checks.append(db_health)
        
        # Redis 헬스체크
        redis_health = await self._check_redis_health()
        health_checks.append(redis_health)
        
        # API 엔드포인트 헬스체크
        api_health = await self._check_api_health()
        health_checks.append(api_health)
        
        # 결과 저장
        self.health_checks.extend(health_checks)
        
        # 오래된 헬스체크 결과 정리 (최근 100개만 유지)
        if len(self.health_checks) > 100:
            self.health_checks = self.health_checks[-100:]
        
        # 불건전한 서비스에 대한 알림
        for health in health_checks:
            if health.status == "unhealthy":
                await self._create_alert(
                    alert_type="service_unhealthy",
                    severity="critical",
                    title=f"Service {health.service} Unhealthy",
                    message=f"Service {health.service} failed health check: {health.error_message}",
                    source="health_check",
                    metadata=asdict(health)
                )
    
    async def _check_database_health(self) -> HealthCheck:
        """데이터베이스 헬스체크"""
        start_time = datetime.now()
        
        try:
            # 간단한 쿼리 실행
            self.db.execute(text("SELECT 1"))
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                service="database",
                status="healthy",
                response_time_ms=response_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                service="database",
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    async def _check_redis_health(self) -> HealthCheck:
        """Redis 헬스체크"""
        start_time = datetime.now()
        
        try:
            # Redis ping
            self.cache_manager.redis_client.ping()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                service="redis",
                status="healthy",
                response_time_ms=response_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                service="redis",
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    async def _check_api_health(self) -> HealthCheck:
        """API 헬스체크"""
        start_time = datetime.now()
        
        try:
            # 내부 헬스체크 엔드포인트 호출
            response = requests.get("http://localhost:8000/health", timeout=5)
            response.raise_for_status()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                service="api",
                status="healthy",
                response_time_ms=response_time,
                timestamp=datetime.now(),
                details={"status_code": response.status_code}
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheck(
                service="api",
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    async def _create_alert(self, alert_type: str, severity: str, title: str, 
                          message: str, source: str, metadata: Dict[str, Any]):
        """알림 생성"""
        alert = Alert(
            id=f"{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata
        )
        
        # 중복 알림 체크 (같은 타입의 알림이 최근 10분 내에 있으면 무시)
        recent_alerts = [
            a for a in self.alerts 
            if a.type == alert_type and 
            (datetime.now() - a.timestamp).total_seconds() < 600
        ]
        
        if not recent_alerts:
            self.alerts.append(alert)
            
            # 로깅
            self.logger.warning(f"Alert created: {title}", extra={
                'extra_fields': {
                    'alert_id': alert.id,
                    'alert_type': alert_type,
                    'severity': severity,
                    'source': source
                }
            })
            
            # 심각도가 높으면 즉시 알림 발송
            if severity in ["critical", "high"]:
                await self._send_notifications(alert)
    
    async def _process_alerts(self):
        """알림 처리"""
        # 해결되지 않은 알림들 처리
        unresolved_alerts = [a for a in self.alerts if not a.resolved]
        
        for alert in unresolved_alerts:
            # 오래된 알림 자동 해결 (24시간 후)
            if (datetime.now() - alert.timestamp).total_seconds() > 86400:
                alert.resolved = True
                self.logger.info(f"Alert auto-resolved: {alert.id}")
    
    async def _send_notifications(self, alert: Alert):
        """알림 발송"""
        for channel_name, send_func in self.notification_channels.items():
            try:
                await send_func(alert)
            except Exception as e:
                self.logger.error(f"Failed to send {channel_name} notification", extra={
                    'extra_fields': {
                        'error': str(e),
                        'alert_id': alert.id,
                        'channel': channel_name
                    }
                })
    
    async def _send_email_alert(self, alert: Alert):
        """이메일 알림 발송"""
        if not hasattr(self.settings, 'EMAIL_HOST'):
            return
        
        msg = MIMEMultipart()
        msg['From'] = self.settings.EMAIL_FROM
        msg['To'] = self.settings.ADMIN_EMAIL
        msg['Subject'] = f"[Yooni Alert] {alert.title}"
        
        body = f"""
        알림 유형: {alert.type}
        심각도: {alert.severity}
        발생 시간: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        소스: {alert.source}
        
        메시지: {alert.message}
        
        상세 정보:
        {json.dumps(alert.metadata, indent=2, ensure_ascii=False)}
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(self.settings.EMAIL_HOST, self.settings.EMAIL_PORT)
        server.starttls()
        server.login(self.settings.EMAIL_USER, self.settings.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(self.settings.EMAIL_FROM, self.settings.ADMIN_EMAIL, text)
        server.quit()
    
    async def _send_slack_alert(self, alert: Alert):
        """Slack 알림 발송"""
        if not hasattr(self.settings, 'SLACK_WEBHOOK_URL'):
            return
        
        color_map = {
            "low": "#36a64f",
            "medium": "#ff9500", 
            "high": "#ff0000",
            "critical": "#8b0000"
        }
        
        payload = {
            "attachments": [{
                "color": color_map.get(alert.severity, "#ff0000"),
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "심각도", "value": alert.severity.upper(), "short": True},
                    {"title": "소스", "value": alert.source, "short": True},
                    {"title": "발생 시간", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "short": True}
                ],
                "timestamp": alert.timestamp.timestamp()
            }]
        }
        
        requests.post(self.settings.SLACK_WEBHOOK_URL, json=payload)
    
    async def _send_discord_alert(self, alert: Alert):
        """Discord 알림 발송"""
        if not hasattr(self.settings, 'DISCORD_WEBHOOK_URL'):
            return
        
        color_map = {
            "low": 0x36a64f,
            "medium": 0xff9500,
            "high": 0xff0000,
            "critical": 0x8b0000
        }
        
        payload = {
            "embeds": [{
                "title": alert.title,
                "description": alert.message,
                "color": color_map.get(alert.severity, 0xff0000),
                "fields": [
                    {"name": "심각도", "value": alert.severity.upper(), "inline": True},
                    {"name": "소스", "value": alert.source, "inline": True},
                    {"name": "발생 시간", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "inline": True}
                ],
                "timestamp": alert.timestamp.isoformat()
            }]
        }
        
        requests.post(self.settings.DISCORD_WEBHOOK_URL, json=payload)
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """모니터링 대시보드 데이터"""
        current_time = datetime.now()
        
        # 최근 알림들
        recent_alerts = [
            a for a in self.alerts 
            if (current_time - a.timestamp).total_seconds() < 3600  # 최근 1시간
        ]
        
        # 심각도별 알림 수
        alert_counts = {
            "critical": len([a for a in recent_alerts if a.severity == "critical"]),
            "high": len([a for a in recent_alerts if a.severity == "high"]),
            "medium": len([a for a in recent_alerts if a.severity == "medium"]),
            "low": len([a for a in recent_alerts if a.severity == "low"])
        }
        
        # 최근 헬스체크 결과
        recent_health_checks = self.health_checks[-10:] if self.health_checks else []
        
        # 시스템 현재 상태
        current_metrics = {}
        try:
            current_metrics = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": (lambda d: (d.used / d.total) * 100)(psutil.disk_usage('/')),
                "db_connections": asyncio.run(self._get_db_connection_count()) if hasattr(self, 'db') else 0
            }
        except Exception:
            pass
        
        return {
            "timestamp": current_time.isoformat(),
            "system_status": "healthy" if alert_counts["critical"] == 0 else "unhealthy",
            "current_metrics": current_metrics,
            "alert_summary": {
                "total_alerts": len(recent_alerts),
                "by_severity": alert_counts,
                "unresolved_count": len([a for a in recent_alerts if not a.resolved])
            },
            "health_checks": [asdict(hc) for hc in recent_health_checks],
            "recent_alerts": [asdict(a) for a in recent_alerts[-10:]]
        }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """알림 확인 처리"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self.logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """알림 해결 처리"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                self.logger.info(f"Alert resolved: {alert_id}")
                return True
        return False


# 글로벌 모니터링 서비스 인스턴스 (필요시 사용)
_monitoring_service = None

def get_monitoring_service(db: Session) -> MonitoringService:
    """모니터링 서비스 인스턴스 반환"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService(db)
    return _monitoring_service