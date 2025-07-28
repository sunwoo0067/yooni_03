"""
Alert Manager Service
Manages system alerts and notifications
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import uuid
import asyncio
import json
from collections import defaultdict
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger
from app.services.realtime.dashboard_websocket_manager import dashboard_ws_manager

class AlertSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class AlertStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class AlertType(Enum):
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SECURITY_ISSUE = "security_issue"
    BUSINESS_METRIC = "business_metric"
    RESOURCE_LIMIT = "resource_limit"
    API_FAILURE = "api_failure"
    DATABASE_ISSUE = "database_issue"
    INVENTORY_ALERT = "inventory_alert"

class AlertManager:
    def __init__(self):
        self.alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.redis_client = None
        self.alert_rules = self._initialize_alert_rules()
        self.notification_channels = []
        
    async def _get_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
        
    def _initialize_alert_rules(self) -> List[Dict[str, Any]]:
        """Initialize alert rules"""
        return [
            {
                "name": "High Error Rate",
                "condition": lambda metrics: metrics.get("error_rate", 0) > 5.0,
                "severity": AlertSeverity.CRITICAL,
                "type": AlertType.SYSTEM_ERROR,
                "message": "Error rate exceeded 5%"
            },
            {
                "name": "Slow Response Time",
                "condition": lambda metrics: metrics.get("avg_response_time", 0) > 1000,
                "severity": AlertSeverity.WARNING,
                "type": AlertType.PERFORMANCE_DEGRADATION,
                "message": "Average response time exceeded 1 second"
            },
            {
                "name": "Low Stock Alert",
                "condition": lambda metrics: metrics.get("low_stock_products", 0) > 10,
                "severity": AlertSeverity.WARNING,
                "type": AlertType.INVENTORY_ALERT,
                "message": "More than 10 products are low on stock"
            },
            {
                "name": "Database Connection Limit",
                "condition": lambda metrics: metrics.get("db_connections", 0) > metrics.get("db_max_connections", 100) * 0.9,
                "severity": AlertSeverity.WARNING,
                "type": AlertType.DATABASE_ISSUE,
                "message": "Database connections approaching limit"
            },
            {
                "name": "High Memory Usage",
                "condition": lambda metrics: metrics.get("memory_percent", 0) > 85,
                "severity": AlertSeverity.WARNING,
                "type": AlertType.RESOURCE_LIMIT,
                "message": "Memory usage exceeded 85%"
            },
            {
                "name": "API Failure",
                "condition": lambda metrics: metrics.get("api_failures", {}).get("count", 0) > 5,
                "severity": AlertSeverity.CRITICAL,
                "type": AlertType.API_FAILURE,
                "message": "Multiple API failures detected"
            }
        ]
        
    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new alert"""
        alert_id = str(uuid.uuid4())
        
        alert = {
            "id": alert_id,
            "type": alert_type.value,
            "severity": severity.value,
            "message": message,
            "source": source,
            "status": AlertStatus.ACTIVE.value,
            "created_at": datetime.utcnow(),
            "acknowledged_at": None,
            "resolved_at": None,
            "metadata": metadata or {}
        }
        
        # Store in memory
        self.alerts[alert_id] = alert
        
        # Store in Redis
        redis_client = await self._get_redis()
        await redis_client.hset(
            "alerts:active",
            alert_id,
            json.dumps(alert, default=str)
        )
        
        # Add to sorted set for time-based queries
        await redis_client.zadd(
            "alerts:timeline",
            {alert_id: datetime.utcnow().timestamp()}
        )
        
        # Send real-time notification
        await self._send_alert_notification(alert)
        
        logger.info(f"Alert created: {alert_id} - {message}")
        
        return alert_id
        
    async def acknowledge_alert(self, alert_id: str, user_id: int) -> bool:
        """Acknowledge an alert"""
        if alert_id not in self.alerts:
            return False
            
        alert = self.alerts[alert_id]
        if alert["status"] != AlertStatus.ACTIVE.value:
            return False
            
        alert["status"] = AlertStatus.ACKNOWLEDGED.value
        alert["acknowledged_at"] = datetime.utcnow()
        alert["acknowledged_by"] = user_id
        
        # Update in Redis
        redis_client = await self._get_redis()
        await redis_client.hset(
            "alerts:active",
            alert_id,
            json.dumps(alert, default=str)
        )
        
        # Notify subscribers
        await self._send_alert_update(alert)
        
        logger.info(f"Alert acknowledged: {alert_id} by user {user_id}")
        
        return True
        
    async def resolve_alert(self, alert_id: str, resolution: Optional[str] = None) -> bool:
        """Resolve an alert"""
        if alert_id not in self.alerts:
            return False
            
        alert = self.alerts[alert_id]
        alert["status"] = AlertStatus.RESOLVED.value
        alert["resolved_at"] = datetime.utcnow()
        if resolution:
            alert["resolution"] = resolution
            
        # Move to history
        self.alert_history.append(alert)
        del self.alerts[alert_id]
        
        # Update in Redis
        redis_client = await self._get_redis()
        await redis_client.hdel("alerts:active", alert_id)
        await redis_client.hset(
            "alerts:resolved",
            alert_id,
            json.dumps(alert, default=str)
        )
        
        # Notify subscribers
        await self._send_alert_update(alert)
        
        logger.info(f"Alert resolved: {alert_id}")
        
        return True
        
    async def get_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get alerts with filters"""
        redis_client = await self._get_redis()
        
        # Get alert IDs from timeline
        alert_ids = await redis_client.zrevrange(
            "alerts:timeline",
            offset,
            offset + limit - 1
        )
        
        alerts = []
        for alert_id in alert_ids:
            # Try active alerts first
            alert_data = await redis_client.hget("alerts:active", alert_id)
            if not alert_data:
                # Check resolved alerts
                alert_data = await redis_client.hget("alerts:resolved", alert_id)
                
            if alert_data:
                alert = json.loads(alert_data)
                
                # Apply filters
                if status and alert["status"] != status:
                    continue
                if severity and alert["severity"] != severity:
                    continue
                    
                alerts.append(alert)
                
        return alerts
        
    async def get_active_alerts_count(self) -> int:
        """Get count of active alerts"""
        return len([a for a in self.alerts.values() if a["status"] == AlertStatus.ACTIVE.value])
        
    async def check_alert_rules(self, metrics: Dict[str, Any]) -> None:
        """Check alert rules against current metrics"""
        for rule in self.alert_rules:
            try:
                if rule["condition"](metrics):
                    # Check if similar alert already exists
                    existing = self._find_similar_alert(rule["type"], rule["message"])
                    if not existing:
                        await self.create_alert(
                            rule["type"],
                            rule["severity"],
                            rule["message"],
                            "alert_rules",
                            {"rule_name": rule["name"], "metrics": metrics}
                        )
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {str(e)}")
                
    def _find_similar_alert(self, alert_type: AlertType, message: str) -> Optional[Dict[str, Any]]:
        """Find similar active alert"""
        for alert in self.alerts.values():
            if (alert["type"] == alert_type.value and
                alert["status"] == AlertStatus.ACTIVE.value and
                alert["message"] == message):
                # Check if alert is recent (within last hour)
                if datetime.utcnow() - alert["created_at"] < timedelta(hours=1):
                    return alert
        return None
        
    async def _send_alert_notification(self, alert: Dict[str, Any]) -> None:
        """Send alert notification to subscribers"""
        try:
            # Send via WebSocket to all dashboard users
            await dashboard_ws_manager.broadcast_system_status({
                "type": "new_alert",
                "alert": alert
            })
            
            # Send to specific notification channels
            for channel in self.notification_channels:
                await channel.send(alert)
                
        except Exception as e:
            logger.error(f"Failed to send alert notification: {str(e)}")
            
    async def _send_alert_update(self, alert: Dict[str, Any]) -> None:
        """Send alert update to subscribers"""
        try:
            await dashboard_ws_manager.broadcast_system_status({
                "type": "alert_update",
                "alert": alert
            })
        except Exception as e:
            logger.error(f"Failed to send alert update: {str(e)}")
            
    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """Clean up old resolved alerts"""
        redis_client = await self._get_redis()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get old alert IDs
        old_alerts = await redis_client.zrangebyscore(
            "alerts:timeline",
            0,
            cutoff_date.timestamp()
        )
        
        cleaned = 0
        for alert_id in old_alerts:
            # Remove from resolved alerts
            await redis_client.hdel("alerts:resolved", alert_id)
            # Remove from timeline
            await redis_client.zrem("alerts:timeline", alert_id)
            cleaned += 1
            
        logger.info(f"Cleaned up {cleaned} old alerts")
        return cleaned
        
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics"""
        redis_client = await self._get_redis()
        
        # Count by status
        active_count = await redis_client.hlen("alerts:active")
        
        # Count by severity (from active alerts)
        severity_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for alert in self.alerts.values():
            if alert["status"] == AlertStatus.ACTIVE.value:
                severity_counts[alert["severity"]] += 1
                type_counts[alert["type"]] += 1
                
        return {
            "total_active": active_count,
            "by_severity": dict(severity_counts),
            "by_type": dict(type_counts),
            "recent_alerts": await self.get_alerts(limit=5)
        }
        
    async def monitor_alerts(self) -> None:
        """Background task to monitor and auto-resolve alerts"""
        while True:
            try:
                # Check for auto-resolvable alerts
                for alert_id, alert in list(self.alerts.items()):
                    # Auto-resolve info alerts after 1 hour
                    if (alert["severity"] == AlertSeverity.INFO.value and
                        datetime.utcnow() - alert["created_at"] > timedelta(hours=1)):
                        await self.resolve_alert(alert_id, "Auto-resolved after 1 hour")
                        
                # Clean up old alerts
                await self.cleanup_old_alerts()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Alert monitoring error: {str(e)}")
                await asyncio.sleep(300)

# Global instance
alert_manager = AlertManager()