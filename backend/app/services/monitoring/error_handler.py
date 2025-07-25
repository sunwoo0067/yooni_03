"""
Enhanced error handling and monitoring system for dropshipping
Provides comprehensive error tracking, retry logic, and alerting
"""
import asyncio
import logging
import traceback
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Type
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps
import inspect

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category types"""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "auth_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"
    BUSINESS_LOGIC_ERROR = "business_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    CONFIGURATION_ERROR = "config_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Error context information"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    details: Dict[str, Any]
    traceback: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    function_name: Optional[str] = None
    module_name: Optional[str] = None
    platform: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    is_recoverable: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        return data


class ErrorAggregator:
    """Aggregates and analyzes error patterns"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self._error_cache = {}
        self._pattern_cache = {}
    
    async def record_error(self, error_context: ErrorContext):
        """Record error for aggregation"""
        error_key = f"error:{error_context.category.value}:{error_context.platform or 'general'}"
        
        # Store in Redis if available
        if self.redis_client:
            await self.redis_client.hincrby(
                f"error_stats:{datetime.utcnow().strftime('%Y%m%d%H')}",
                error_key,
                1
            )
            await self.redis_client.expire(
                f"error_stats:{datetime.utcnow().strftime('%Y%m%d%H')}",
                86400  # 24 hours
            )
        
        # Update local cache
        if error_key not in self._error_cache:
            self._error_cache[error_key] = []
        
        self._error_cache[error_key].append(error_context)
        
        # Keep only last 100 errors per key
        if len(self._error_cache[error_key]) > 100:
            self._error_cache[error_key] = self._error_cache[error_key][-100:]
    
    async def get_error_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze error patterns"""
        patterns = {
            "top_errors": [],
            "error_trends": {},
            "platform_breakdown": {},
            "severity_distribution": {},
            "recovery_rates": {}
        }
        
        if not self.redis_client:
            return patterns
        
        # Get error stats for the specified time range
        current_hour = datetime.utcnow().hour
        hours_to_check = min(hours, 24)
        
        for i in range(hours_to_check):
            hour_key = (datetime.utcnow() - timedelta(hours=i)).strftime('%Y%m%d%H')
            stats = await self.redis_client.hgetall(f"error_stats:{hour_key}")
            
            for error_key, count in stats.items():
                if error_key not in patterns["error_trends"]:
                    patterns["error_trends"][error_key] = []
                patterns["error_trends"][error_key].append({
                    "hour": hour_key,
                    "count": int(count)
                })
        
        # Calculate top errors
        total_counts = {}
        for error_key, trend in patterns["error_trends"].items():
            total_counts[error_key] = sum(item["count"] for item in trend)
        
        patterns["top_errors"] = [
            {"error": k, "count": v} 
            for k, v in sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return patterns


class RetryPolicy:
    """Configurable retry policy"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
    
    def should_retry(self, error_context: ErrorContext) -> bool:
        """Determine if error should be retried"""
        if error_context.retry_count >= self.max_retries:
            return False
        
        if not error_context.is_recoverable:
            return False
        
        # Don't retry certain error types
        non_retryable_categories = {
            ErrorCategory.AUTHENTICATION_ERROR,
            ErrorCategory.VALIDATION_ERROR,
            ErrorCategory.CONFIGURATION_ERROR
        }
        
        if error_context.category in non_retryable_categories:
            return False
        
        return True
    
    def get_delay(self, retry_count: int) -> float:
        """Calculate delay for retry"""
        delay = self.base_delay * (self.backoff_multiplier ** retry_count)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add jitter
        
        return delay


class ErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        redis_client=None,
        notification_service=None
    ):
        self.db_session = db_session
        self.redis_client = redis_client
        self.notification_service = notification_service
        self.error_aggregator = ErrorAggregator(redis_client)
        self.retry_policies = {}
        self._setup_default_retry_policies()
        self._error_handlers = {}
        self._circuit_breakers = {}
    
    def _setup_default_retry_policies(self):
        """Setup default retry policies for different error categories"""
        self.retry_policies = {
            ErrorCategory.API_ERROR: RetryPolicy(max_retries=3, base_delay=1.0),
            ErrorCategory.NETWORK_ERROR: RetryPolicy(max_retries=5, base_delay=2.0),
            ErrorCategory.RATE_LIMIT_ERROR: RetryPolicy(max_retries=3, base_delay=60.0),
            ErrorCategory.EXTERNAL_SERVICE_ERROR: RetryPolicy(max_retries=3, base_delay=5.0),
            ErrorCategory.DATABASE_ERROR: RetryPolicy(max_retries=2, base_delay=1.0),
            ErrorCategory.UNKNOWN_ERROR: RetryPolicy(max_retries=1, base_delay=1.0)
        }
    
    def register_error_handler(
        self,
        error_type: Type[Exception],
        handler: Callable[[Exception, ErrorContext], Any]
    ):
        """Register custom error handler for specific exception type"""
        self._error_handlers[error_type] = handler
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        platform: Optional[str] = None
    ) -> ErrorContext:
        """Handle error with comprehensive logging and recovery"""
        
        # Create error context
        error_context = self._create_error_context(
            error, context, user_id, platform
        )
        
        # Log error
        await self._log_error(error_context)
        
        # Record for aggregation
        await self.error_aggregator.record_error(error_context)
        
        # Check if we should send alerts
        await self._check_alert_conditions(error_context)
        
        # Try custom error handler
        if type(error) in self._error_handlers:
            try:
                await self._error_handlers[type(error)](error, error_context)
            except Exception as handler_error:
                logger.error(f"Error handler failed: {handler_error}")
        
        return error_context
    
    def _create_error_context(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]],
        user_id: Optional[str],
        platform: Optional[str]
    ) -> ErrorContext:
        """Create comprehensive error context"""
        
        # Determine error category and severity
        category = self._categorize_error(error)
        severity = self._assess_severity(error, category)
        
        # Extract function and module information
        frame = inspect.currentframe()
        function_name = None
        module_name = None
        
        try:
            # Go back through the stack to find the calling function
            while frame:
                frame = frame.f_back
                if frame and frame.f_code.co_filename != __file__:
                    function_name = frame.f_code.co_name
                    module_name = frame.f_globals.get('__name__')
                    break
        except Exception:
            pass
        finally:
            del frame
        
        # Generate unique error ID
        import uuid
        error_id = str(uuid.uuid4())
        
        # Prepare error details
        details = {
            "error_type": type(error).__name__,
            "error_args": str(error.args) if error.args else None,
            "context": context or {},
            "stack_trace": traceback.format_exc()
        }
        
        return ErrorContext(
            error_id=error_id,
            timestamp=datetime.utcnow(),
            severity=severity,
            category=category,
            message=str(error),
            details=details,
            traceback=traceback.format_exc(),
            user_id=user_id,
            platform=platform,
            function_name=function_name,
            module_name=module_name,
            is_recoverable=self._is_recoverable_error(error, category)
        )
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and content"""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # Network-related errors
        if any(keyword in error_type for keyword in ['connection', 'timeout', 'network']):
            return ErrorCategory.NETWORK_ERROR
        
        # Authentication errors
        if any(keyword in error_message for keyword in ['unauthorized', 'forbidden', 'invalid token', 'authentication']):
            return ErrorCategory.AUTHENTICATION_ERROR
        
        # Rate limiting
        if any(keyword in error_message for keyword in ['rate limit', 'too many requests', 'quota exceeded']):
            return ErrorCategory.RATE_LIMIT_ERROR
        
        # Validation errors
        if any(keyword in error_type for keyword in ['validation', 'value']):
            return ErrorCategory.VALIDATION_ERROR
        
        # Database errors
        if any(keyword in error_type for keyword in ['database', 'sql', 'integrity']):
            return ErrorCategory.DATABASE_ERROR
        
        # API errors
        if any(keyword in error_message for keyword in ['api', 'http', 'status']):
            return ErrorCategory.API_ERROR
        
        return ErrorCategory.UNKNOWN_ERROR
    
    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity"""
        
        # Critical severity conditions
        critical_patterns = [
            'database.*connection.*failed',
            'redis.*connection.*failed',
            'authentication.*completely.*failed',
            'critical.*system.*error'
        ]
        
        error_str = str(error).lower()
        for pattern in critical_patterns:
            import re
            if re.search(pattern, error_str):
                return ErrorSeverity.CRITICAL
        
        # High severity for certain categories
        high_severity_categories = {
            ErrorCategory.DATABASE_ERROR,
            ErrorCategory.AUTHENTICATION_ERROR,
            ErrorCategory.CONFIGURATION_ERROR
        }
        
        if category in high_severity_categories:
            return ErrorSeverity.HIGH
        
        # Medium severity for business logic and API errors
        medium_severity_categories = {
            ErrorCategory.API_ERROR,
            ErrorCategory.BUSINESS_LOGIC_ERROR,
            ErrorCategory.EXTERNAL_SERVICE_ERROR
        }
        
        if category in medium_severity_categories:
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW
    
    def _is_recoverable_error(self, error: Exception, category: ErrorCategory) -> bool:
        """Determine if error is recoverable"""
        
        # Non-recoverable categories
        non_recoverable = {
            ErrorCategory.VALIDATION_ERROR,
            ErrorCategory.CONFIGURATION_ERROR,
            ErrorCategory.AUTHENTICATION_ERROR
        }
        
        if category in non_recoverable:
            return False
        
        # Check for specific non-recoverable error messages
        non_recoverable_patterns = [
            'invalid.*credentials',
            'permission.*denied',
            'not.*found',
            'malformed.*request'
        ]
        
        error_str = str(error).lower()
        for pattern in non_recoverable_patterns:
            import re
            if re.search(pattern, error_str):
                return False
        
        return True
    
    async def _log_error(self, error_context: ErrorContext):
        """Log error with appropriate level"""
        log_data = {
            "error_id": error_context.error_id,
            "category": error_context.category.value,
            "severity": error_context.severity.value,
            "message": error_context.message,
            "user_id": error_context.user_id,
            "platform": error_context.platform,
            "function": error_context.function_name,
            "module": error_context.module_name
        }
        
        if error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", extra=log_data)
        elif error_context.severity == ErrorSeverity.HIGH:
            logger.error("High severity error", extra=log_data)
        elif error_context.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error", extra=log_data)
        else:
            logger.info("Low severity error", extra=log_data)
        
        # Store in database if available
        if self.db_session:
            try:
                # Here you would insert into an error_logs table
                # For now, we'll just log that we would store it
                logger.debug(f"Would store error {error_context.error_id} in database")
            except Exception as db_error:
                logger.error(f"Failed to store error in database: {db_error}")
    
    async def _check_alert_conditions(self, error_context: ErrorContext):
        """Check if alerts should be sent"""
        
        # Alert on critical errors immediately
        if error_context.severity == ErrorSeverity.CRITICAL:
            await self._send_alert(error_context, "Critical error occurred")
            return
        
        # Check for error rate thresholds
        error_key = f"error:{error_context.category.value}:{error_context.platform or 'general'}"
        
        if self.redis_client:
            # Check error rate in last hour
            current_hour = datetime.utcnow().strftime('%Y%m%d%H')
            error_count = await self.redis_client.hget(f"error_stats:{current_hour}", error_key)
            
            if error_count and int(error_count) > 10:  # More than 10 errors per hour
                await self._send_alert(
                    error_context,
                    f"High error rate detected: {error_count} errors in last hour"
                )
    
    async def _send_alert(self, error_context: ErrorContext, alert_message: str):
        """Send error alert"""
        if not self.notification_service:
            logger.warning(f"Alert would be sent: {alert_message}")
            return
        
        try:
            await self.notification_service.send_alert({
                "type": "error_alert",
                "severity": error_context.severity.value,
                "message": alert_message,
                "error_context": error_context.to_dict()
            })
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def retry_with_policy(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        error_category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Retry function execution with appropriate policy"""
        
        kwargs = kwargs or {}
        retry_policy = self.retry_policies.get(error_category, self.retry_policies[ErrorCategory.UNKNOWN_ERROR])
        
        last_error = None
        error_context = None
        
        for attempt in range(retry_policy.max_retries + 1):
            try:
                if inspect.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as error:
                last_error = error
                error_context = await self.handle_error(error, context)
                error_context.retry_count = attempt
                
                if not retry_policy.should_retry(error_context):
                    break
                
                if attempt < retry_policy.max_retries:
                    delay = retry_policy.get_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{retry_policy.max_retries})")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        if error_context:
            error_context.retry_count = retry_policy.max_retries
            await self.error_aggregator.record_error(error_context)
        
        raise last_error
    
    def with_error_handling(
        self,
        error_category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None
    ):
        """Decorator for automatic error handling"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as error:
                    await self.handle_error(error, context)
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    # For sync functions, we'll handle error synchronously
                    error_context = self._create_error_context(error, context, None, None)
                    logger.error(f"Error in {func.__name__}: {error}", extra=error_context.to_dict())
                    raise
            
            return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        patterns = await self.error_aggregator.get_error_patterns(hours)
        
        stats = {
            "time_period_hours": hours,
            "error_patterns": patterns,
            "circuit_breaker_status": {},
            "retry_policy_effectiveness": {},
            "system_health_score": self._calculate_health_score(patterns)
        }
        
        return stats
    
    def _calculate_health_score(self, patterns: Dict[str, Any]) -> float:
        """Calculate system health score based on error patterns"""
        if not patterns.get("top_errors"):
            return 100.0
        
        total_errors = sum(error["count"] for error in patterns["top_errors"])
        
        # Simple health score calculation
        # In production, this would be more sophisticated
        if total_errors == 0:
            return 100.0
        elif total_errors < 10:
            return 95.0
        elif total_errors < 50:
            return 80.0
        elif total_errors < 100:
            return 60.0
        else:
            return 30.0


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def with_error_handling(
    error_category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
    context: Optional[Dict[str, Any]] = None
):
    """Convenience decorator for error handling"""
    return get_error_handler().with_error_handling(error_category, context)