"""
Enhanced Platform API Factory with improved error handling and monitoring
Supports dynamic platform registration, health monitoring, and failover
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Type, Protocol
from abc import ABC, abstractmethod
from enum import Enum
import importlib
import inspect

from app.models.platform_account import PlatformType, PlatformAccount
from app.services.monitoring.error_handler import ErrorHandler, ErrorCategory, with_error_handling
from app.utils.encryption import decrypt_sensitive_data

logger = logging.getLogger(__name__)


class APIHealthStatus(Enum):
    """API health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PlatformAPIProtocol(Protocol):
    """Protocol for platform API implementations"""
    
    async def __aenter__(self):
        """Async context manager entry"""
        ...
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        ...
    
    async def test_connection(self) -> bool:
        """Test API connection"""
        ...
    
    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create product on platform"""
        ...
    
    async def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product on platform"""
        ...
    
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get product from platform"""
        ...
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete product from platform"""
        ...
    
    async def update_inventory(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """Update product inventory"""
        ...
    
    async def get_orders(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get orders from platform"""
        ...


class BasePlatformAPI(ABC):
    """Enhanced base class for platform APIs"""
    
    def __init__(self, credentials: Dict[str, str], config: Optional[Dict[str, Any]] = None):
        """Initialize platform API
        
        Args:
            credentials: Platform credentials
            config: Optional configuration
        """
        self.credentials = credentials
        self.config = config or {}
        self.error_handler = ErrorHandler()
        self._health_status = APIHealthStatus.UNKNOWN
        self._last_health_check = None
        self._rate_limit_info = {}
        self._client = None
        
        # API capabilities
        self.capabilities = {
            "create_product": True,
            "update_product": True,
            "delete_product": True,
            "bulk_operations": False,
            "image_upload": False,
            "real_time_inventory": True,
            "order_management": True
        }
    
    @property
    def platform_type(self) -> PlatformType:
        """Get platform type"""
        raise NotImplementedError
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_client()
    
    async def _initialize_client(self):
        """Initialize HTTP client with platform-specific settings"""
        import httpx
        
        timeout_config = httpx.Timeout(
            connect=self.config.get('connect_timeout', 10.0),
            read=self.config.get('read_timeout', 30.0),
            write=self.config.get('write_timeout', 10.0),
            pool=self.config.get('pool_timeout', 10.0)
        )
        
        self._client = httpx.AsyncClient(
            timeout=timeout_config,
            limits=httpx.Limits(
                max_connections=self.config.get('max_connections', 20),
                max_keepalive_connections=self.config.get('max_keepalive', 5)
            ),
            headers=self._get_default_headers()
        )
    
    async def _cleanup_client(self):
        """Cleanup HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers"""
        return {
            "User-Agent": f"DropshippingSystem/1.0 ({self.platform_type.value})",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    @with_error_handling(ErrorCategory.API_ERROR)
    async def test_connection(self) -> bool:
        """Test API connection with health check"""
        try:
            result = await self._perform_health_check()
            self._health_status = APIHealthStatus.HEALTHY if result else APIHealthStatus.UNHEALTHY
            self._last_health_check = datetime.utcnow()
            return result
        except Exception as e:
            self._health_status = APIHealthStatus.UNHEALTHY
            self._last_health_check = datetime.utcnow()
            logger.error(f"Health check failed for {self.platform_type.value}: {e}")
            return False
    
    @abstractmethod
    async def _perform_health_check(self) -> bool:
        """Platform-specific health check implementation"""
        pass
    
    @with_error_handling(ErrorCategory.API_ERROR)
    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create product with enhanced error handling"""
        if not self.capabilities.get("create_product"):
            raise NotImplementedError(f"Product creation not supported by {self.platform_type.value}")
        
        # Validate product data
        validation_result = await self._validate_product_data(product_data)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid product data: {validation_result['errors']}")
        
        # Check rate limits
        await self._check_rate_limits("create_product")
        
        # Transform data for platform
        transformed_data = await self._transform_product_data(product_data)
        
        # Perform creation
        result = await self._create_product_impl(transformed_data)
        
        # Update rate limit info
        await self._update_rate_limit_info("create_product")
        
        return result
    
    @abstractmethod
    async def _create_product_impl(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Platform-specific product creation implementation"""
        pass
    
    async def _validate_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate product data for platform requirements"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Basic validation
        required_fields = ["name", "price"]
        for field in required_fields:
            if field not in product_data or not product_data[field]:
                validation["valid"] = False
                validation["errors"].append(f"Missing required field: {field}")
        
        # Platform-specific validation
        platform_validation = await self._validate_platform_specific(product_data)
        validation["errors"].extend(platform_validation.get("errors", []))
        validation["warnings"].extend(platform_validation.get("warnings", []))
        
        if platform_validation.get("errors"):
            validation["valid"] = False
        
        return validation
    
    async def _validate_platform_specific(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Platform-specific validation - override in subclasses"""
        return {"errors": [], "warnings": []}
    
    async def _transform_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform product data for platform format - override in subclasses"""
        return product_data
    
    async def _check_rate_limits(self, operation: str):
        """Check and enforce rate limits"""
        if operation not in self._rate_limit_info:
            return  # No rate limit info available
        
        rate_info = self._rate_limit_info[operation]
        current_time = datetime.utcnow()
        
        # Check if we're within rate limits
        if rate_info.get("reset_time") and current_time < rate_info["reset_time"]:
            remaining = rate_info.get("remaining", 0)
            if remaining <= 0:
                reset_in = (rate_info["reset_time"] - current_time).total_seconds()
                raise Exception(f"Rate limit exceeded. Resets in {reset_in:.0f} seconds")
    
    async def _update_rate_limit_info(self, operation: str, response_headers: Optional[Dict[str, str]] = None):
        """Update rate limit information from response headers"""
        if not response_headers:
            return
        
        # Common rate limit header patterns
        limit_headers = {
            "x-ratelimit-limit": "limit",
            "x-ratelimit-remaining": "remaining", 
            "x-ratelimit-reset": "reset_time",
            "x-rate-limit-limit": "limit",
            "x-rate-limit-remaining": "remaining",
            "x-rate-limit-reset": "reset_time"
        }
        
        rate_info = {}
        for header, key in limit_headers.items():
            if header in response_headers:
                value = response_headers[header]
                if key == "reset_time":
                    # Convert timestamp to datetime
                    try:
                        rate_info[key] = datetime.fromtimestamp(int(value))
                    except (ValueError, TypeError):
                        pass
                else:
                    try:
                        rate_info[key] = int(value)
                    except (ValueError, TypeError):
                        pass
        
        if rate_info:
            self._rate_limit_info[operation] = rate_info
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "status": self._health_status.value,
            "last_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "capabilities": self.capabilities,
            "rate_limits": self._rate_limit_info
        }
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        status = {}
        current_time = datetime.utcnow()
        
        for operation, info in self._rate_limit_info.items():
            reset_time = info.get("reset_time")
            status[operation] = {
                "limit": info.get("limit"),
                "remaining": info.get("remaining"),
                "reset_in_seconds": (reset_time - current_time).total_seconds() if reset_time else None,
                "is_limited": info.get("remaining", 1) <= 0
            }
        
        return status


class EnhancedPlatformFactory:
    """Enhanced platform factory with monitoring and failover capabilities"""
    
    def __init__(self):
        """Initialize platform factory"""
        self._registered_platforms = {}
        self._platform_instances = {}
        self._health_monitor = {}
        self._failover_config = {}
        self._error_handler = ErrorHandler()
        
        # Register default platforms
        self._register_default_platforms()
    
    def _register_default_platforms(self):
        """Register default platform implementations"""
        default_platforms = {
            PlatformType.COUPANG: {
                "class_path": "app.services.platforms.coupang_api.CoupangAPI",
                "health_check_interval": 300,  # 5 minutes
                "max_failures": 3,
                "circuit_breaker_timeout": 600  # 10 minutes
            },
            PlatformType.NAVER: {
                "class_path": "app.services.platforms.naver_api.NaverAPI",
                "health_check_interval": 300,
                "max_failures": 3,
                "circuit_breaker_timeout": 600
            },
            PlatformType.ELEVEN_ST: {
                "class_path": "app.services.platforms.eleventh_street_api.EleventhStreetAPI",
                "health_check_interval": 300,
                "max_failures": 3,
                "circuit_breaker_timeout": 600
            }
        }
        
        for platform_type, config in default_platforms.items():
            self.register_platform(platform_type, config)
    
    def register_platform(self, platform_type: PlatformType, config: Dict[str, Any]):
        """Register a platform implementation
        
        Args:
            platform_type: Platform type
            config: Platform configuration including class_path
        """
        self._registered_platforms[platform_type] = config
        self._health_monitor[platform_type] = {
            "status": APIHealthStatus.UNKNOWN,
            "last_check": None,
            "failure_count": 0,
            "circuit_open": False,
            "circuit_open_until": None
        }
        
        logger.info(f"Registered platform: {platform_type.value}")
    
    async def get_platform_api(
        self,
        platform_type: PlatformType,
        account: PlatformAccount,
        force_new: bool = False
    ) -> PlatformAPIProtocol:
        """Get platform API instance with enhanced error handling
        
        Args:
            platform_type: Platform type
            account: Platform account
            force_new: Force creation of new instance
            
        Returns:
            Platform API instance
        """
        cache_key = f"{platform_type.value}_{account.id}"
        
        # Check circuit breaker
        if await self._is_circuit_open(platform_type):
            raise Exception(f"Circuit breaker open for {platform_type.value}")
        
        # Return cached instance if available and not forcing new
        if not force_new and cache_key in self._platform_instances:
            return self._platform_instances[cache_key]
        
        # Create new instance
        try:
            api_instance = await self._create_platform_instance(platform_type, account)
            
            # Test connection
            connection_ok = await api_instance.test_connection()
            if not connection_ok:
                await self._record_platform_failure(platform_type)
                raise Exception(f"Failed to connect to {platform_type.value}")
            
            # Cache instance
            self._platform_instances[cache_key] = api_instance
            
            # Record success
            await self._record_platform_success(platform_type)
            
            return api_instance
            
        except Exception as e:
            await self._record_platform_failure(platform_type)
            await self._error_handler.handle_error(
                e,
                context={"platform": platform_type.value, "account_id": str(account.id)}
            )
            raise
    
    async def _create_platform_instance(
        self,
        platform_type: PlatformType,
        account: PlatformAccount
    ) -> PlatformAPIProtocol:
        """Create platform API instance"""
        
        if platform_type not in self._registered_platforms:
            raise ValueError(f"Platform {platform_type.value} not registered")
        
        config = self._registered_platforms[platform_type]
        class_path = config["class_path"]
        
        # Import the class dynamically
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        api_class = getattr(module, class_name)
        
        # Decrypt credentials
        credentials = self._decrypt_account_credentials(account)
        
        # Create instance
        return api_class(credentials, config.get("api_config", {}))
    
    def _decrypt_account_credentials(self, account: PlatformAccount) -> Dict[str, str]:
        """Decrypt account credentials"""
        credentials = {}
        
        if account.api_key:
            credentials["api_key"] = decrypt_sensitive_data(account.api_key)
        if account.api_secret:
            credentials["api_secret"] = decrypt_sensitive_data(account.api_secret)
        if account.access_token:
            credentials["access_token"] = decrypt_sensitive_data(account.access_token)
        if account.refresh_token:
            credentials["refresh_token"] = decrypt_sensitive_data(account.refresh_token)
        
        # Add non-sensitive fields
        if account.seller_id:
            credentials["seller_id"] = account.seller_id
        if account.account_id:
            credentials["account_id"] = account.account_id
        
        # Platform-specific mappings
        if account.platform_type == PlatformType.COUPANG:
            credentials["access_key"] = credentials.get("api_key", "")
            credentials["secret_key"] = credentials.get("api_secret", "")
            credentials["vendor_id"] = account.seller_id or ""
        elif account.platform_type == PlatformType.NAVER:
            credentials["client_id"] = credentials.get("api_key", "")
            credentials["client_secret"] = credentials.get("api_secret", "")
            credentials["store_id"] = account.seller_id or ""
        
        return credentials
    
    async def _is_circuit_open(self, platform_type: PlatformType) -> bool:
        """Check if circuit breaker is open for platform"""
        health_info = self._health_monitor.get(platform_type, {})
        
        if not health_info.get("circuit_open"):
            return False
        
        open_until = health_info.get("circuit_open_until")
        if open_until and datetime.utcnow() > open_until:
            # Circuit breaker timeout expired, close circuit
            health_info["circuit_open"] = False
            health_info["circuit_open_until"] = None
            health_info["failure_count"] = 0
            return False
        
        return True
    
    async def _record_platform_failure(self, platform_type: PlatformType):
        """Record platform failure and update circuit breaker"""
        health_info = self._health_monitor.get(platform_type, {})
        health_info["failure_count"] = health_info.get("failure_count", 0) + 1
        health_info["status"] = APIHealthStatus.UNHEALTHY
        health_info["last_check"] = datetime.utcnow()
        
        # Check if we should open circuit breaker
        config = self._registered_platforms.get(platform_type, {})
        max_failures = config.get("max_failures", 3)
        
        if health_info["failure_count"] >= max_failures:
            health_info["circuit_open"] = True
            circuit_timeout = config.get("circuit_breaker_timeout", 600)
            health_info["circuit_open_until"] = datetime.utcnow() + timedelta(seconds=circuit_timeout)
            
            logger.warning(f"Circuit breaker opened for {platform_type.value}")
    
    async def _record_platform_success(self, platform_type: PlatformType):
        """Record platform success"""
        health_info = self._health_monitor.get(platform_type, {})
        health_info["failure_count"] = 0
        health_info["status"] = APIHealthStatus.HEALTHY
        health_info["last_check"] = datetime.utcnow()
        health_info["circuit_open"] = False
        health_info["circuit_open_until"] = None
    
    async def health_check_all_platforms(self) -> Dict[str, Any]:
        """Perform health check on all registered platforms"""
        results = {}
        
        for platform_type in self._registered_platforms.keys():
            try:
                # This would require test credentials or mock testing
                # For now, we'll return the cached status
                health_info = self._health_monitor.get(platform_type, {})
                results[platform_type.value] = {
                    "status": health_info.get("status", APIHealthStatus.UNKNOWN).value,
                    "last_check": health_info.get("last_check"),
                    "failure_count": health_info.get("failure_count", 0),
                    "circuit_open": health_info.get("circuit_open", False)
                }
            except Exception as e:
                results[platform_type.value] = {
                    "status": APIHealthStatus.UNHEALTHY.value,
                    "error": str(e)
                }
        
        return results
    
    async def get_platform_capabilities(self, platform_type: PlatformType) -> Dict[str, Any]:
        """Get platform capabilities"""
        if platform_type not in self._registered_platforms:
            return {}
        
        # This would typically be loaded from the platform class
        # For now, return default capabilities
        return {
            "create_product": True,
            "update_product": True,
            "delete_product": True,
            "bulk_operations": platform_type in [PlatformType.COUPANG, PlatformType.NAVER],
            "image_upload": True,
            "real_time_inventory": True,
            "order_management": True,
            "supported_formats": ["json"],
            "max_images_per_product": 10,
            "max_products_per_batch": 100 if platform_type == PlatformType.COUPANG else 50
        }
    
    async def cleanup_instances(self):
        """Cleanup all cached instances"""
        for instance in self._platform_instances.values():
            try:
                if hasattr(instance, '__aexit__'):
                    await instance.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up platform instance: {e}")
        
        self._platform_instances.clear()
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """Get factory statistics"""
        return {
            "registered_platforms": list(self._registered_platforms.keys()),
            "active_instances": len(self._platform_instances),
            "health_monitor": {
                platform.value: {
                    "status": info.get("status", APIHealthStatus.UNKNOWN).value,
                    "failure_count": info.get("failure_count", 0),
                    "circuit_open": info.get("circuit_open", False)
                }
                for platform, info in self._health_monitor.items()
            }
        }


# Global factory instance
_platform_factory: Optional[EnhancedPlatformFactory] = None


def get_platform_factory() -> EnhancedPlatformFactory:
    """Get global platform factory instance"""
    global _platform_factory
    if _platform_factory is None:
        _platform_factory = EnhancedPlatformFactory()
    return _platform_factory