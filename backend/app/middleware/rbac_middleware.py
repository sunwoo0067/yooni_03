"""
RBAC Middleware for automatic permission enforcement
Provides centralized permission checking and audit logging
"""
import json
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional, List, Set
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import re

from app.core.database import SessionLocal
from app.models.user import User
from app.models.rbac import UserPermissionAudit
from app.services.rbac import get_permission_service, PermissionContext
from app.core.security import SecurityManager
from app.services.cache_service import cache_service


class RBACMiddleware(BaseHTTPMiddleware):
    """
    RBAC Middleware for automatic permission enforcement
    """
    
    def __init__(
        self,
        app,
        excluded_paths: Optional[Set[str]] = None,
        permission_mappings: Optional[Dict[str, Dict[str, str]]] = None,
        enable_audit_logging: bool = True,
        enable_caching: bool = True,
        cache_ttl: int = 300
    ):
        super().__init__(app)
        
        # Default excluded paths (authentication, health checks, etc.)
        self.excluded_paths = excluded_paths or {
            "/auth/login",
            "/auth/logout", 
            "/auth/refresh",
            "/auth/register",
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        }
        
        # Default permission mappings for HTTP methods and endpoints
        self.permission_mappings = permission_mappings or self._get_default_permission_mappings()
        
        self.enable_audit_logging = enable_audit_logging
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        
        # Compile regex patterns for performance
        self._compiled_patterns = {}
        for pattern in self.permission_mappings.keys():
            if '*' in pattern or '{' in pattern:
                # Convert path patterns to regex
                regex_pattern = pattern.replace('*', '.*')
                regex_pattern = re.sub(r'\{[^}]+\}', r'[^/]+', regex_pattern)
                self._compiled_patterns[pattern] = re.compile(f"^{regex_pattern}$")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch method"""
        
        # Skip excluded paths
        if self._should_skip_path(request.url.path):
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            # Extract user from request
            user = await self._extract_user_from_request(request)
            if not user:
                # Allow anonymous access for specific endpoints
                if self._allows_anonymous_access(request):
                    return await call_next(request)
                
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "인증이 필요합니다"}
                )
            
            # Check permissions
            permission_check_result = await self._check_permissions(request, user)
            if not permission_check_result["granted"]:
                await self._log_access_denied(request, user, permission_check_result["reason"])
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "권한이 부족합니다",
                        "reason": permission_check_result["reason"],
                        "required_permission": permission_check_result.get("required_permission")
                    }
                )
            
            # Add user and permission info to request state
            request.state.user = user
            request.state.permission_check = permission_check_result
            
            # Process the request
            response = await call_next(request)
            
            # Log successful access if enabled
            if self.enable_audit_logging and permission_check_result.get("should_log", False):
                processing_time = time.time() - start_time
                await self._log_successful_access(
                    request, user, response, 
                    permission_check_result.get("required_permission"),
                    processing_time
                )
            
            return response
            
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            # Log unexpected errors
            if self.enable_audit_logging:
                await self._log_error(request, str(e))
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "서버 내부 오류가 발생했습니다"}
            )

    def _should_skip_path(self, path: str) -> bool:
        """Check if path should be skipped"""
        # Exact match
        if path in self.excluded_paths:
            return True
        
        # Pattern match
        for excluded_path in self.excluded_paths:
            if '*' in excluded_path:
                pattern = excluded_path.replace('*', '.*')
                if re.match(f"^{pattern}$", path):
                    return True
        
        return False

    def _allows_anonymous_access(self, request: Request) -> bool:
        """Check if endpoint allows anonymous access"""
        anonymous_endpoints = {
            "/health",
            "/docs", 
            "/openapi.json",
            "/auth/register",  # If registration is public
        }
        
        return request.url.path in anonymous_endpoints

    async def _extract_user_from_request(self, request: Request) -> Optional[User]:
        """Extract user from JWT token in request"""
        try:
            # Check for Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            
            # Decode and validate token
            payload = SecurityManager.decode_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                return None
            
            # Get user from database
            with SessionLocal() as db:
                user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
                if user:
                    # Detach from session to avoid issues
                    db.expunge(user)
                return user
                
        except Exception:
            return None

    async def _check_permissions(self, request: Request, user: User) -> Dict[str, Any]:
        """Check if user has required permissions for the request"""
        
        # Get required permission for this endpoint
        required_permission = self._get_required_permission(request)
        
        if not required_permission:
            # No specific permission required, allow access
            return {"granted": True, "reason": "No permission required"}
        
        # Create permission context
        context = PermissionContext(
            user=user,
            resource_type=self._extract_resource_type(request),
            resource_id=self._extract_resource_id(request),
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            additional_context={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params)
            }
        )
        
        # Check permission using service
        with SessionLocal() as db:
            permission_service = get_permission_service(db)
            
            # Check cache first if enabled
            if self.enable_caching:
                cache_key = f"rbac_check:{user.id}:{required_permission}:{hash(str(context.__dict__))}"
                cached_result = await self._get_cached_result(cache_key)
                if cached_result:
                    return cached_result
            
            # Evaluate permission
            result = await permission_service.evaluate_permission(user, required_permission, context)
            
            permission_result = {
                "granted": result.granted,
                "reason": result.reason,
                "required_permission": required_permission,
                "delegated": result.delegated,
                "expires_at": result.expires_at,
                "should_log": True  # Log this access attempt
            }
            
            # Cache result if enabled
            if self.enable_caching and result.granted:
                await self._cache_result(cache_key, permission_result, self.cache_ttl)
            
            return permission_result

    def _get_required_permission(self, request: Request) -> Optional[str]:
        """Get required permission for the request"""
        method = request.method.upper()
        path = request.url.path
        
        # Try exact path match first
        endpoint_key = f"{method} {path}"
        if endpoint_key in self.permission_mappings:
            return self.permission_mappings[endpoint_key]
        
        # Try pattern matching
        for pattern, permission in self.permission_mappings.items():
            if pattern.startswith(method + " "):
                path_pattern = pattern[len(method + " "):]
                if path_pattern in self._compiled_patterns:
                    if self._compiled_patterns[path_pattern].match(path):
                        return permission
                elif path_pattern == path:
                    return permission
        
        # Default permission mapping based on method
        default_mappings = {
            "GET": self._get_read_permission(path),
            "POST": self._get_create_permission(path),
            "PUT": self._get_update_permission(path),
            "PATCH": self._get_update_permission(path),
            "DELETE": self._get_delete_permission(path)
        }
        
        return default_mappings.get(method)

    def _get_read_permission(self, path: str) -> Optional[str]:
        """Get read permission based on path"""
        if "/products" in path:
            return "products.read.own" if "/{" in path else "products.read.all"
        elif "/orders" in path:
            return "orders.read.own" if "/{" in path else "orders.read.all"
        elif "/users" in path:
            return "users.read"
        elif "/analytics" in path:
            return "analytics.read"
        elif "/reports" in path:
            return "reports.read"
        return None

    def _get_create_permission(self, path: str) -> Optional[str]:
        """Get create permission based on path"""
        if "/products" in path:
            return "products.create.own"
        elif "/orders" in path:
            return "orders.create"
        elif "/users" in path:
            return "users.create"
        elif "/reports" in path:
            return "reports.create"
        return None

    def _get_update_permission(self, path: str) -> Optional[str]:
        """Get update permission based on path"""
        if "/products" in path:
            return "products.update.own"
        elif "/orders" in path:
            return "orders.process"
        elif "/users" in path:
            return "users.update"
        elif "/settings" in path:
            return "settings.update"
        return None

    def _get_delete_permission(self, path: str) -> Optional[str]:
        """Get delete permission based on path"""
        if "/products" in path:
            return "products.delete.own"
        elif "/orders" in path:
            return "orders.cancel"
        elif "/users" in path:
            return "users.delete"
        return None

    def _extract_resource_type(self, request: Request) -> Optional[str]:
        """Extract resource type from request path"""
        path_parts = request.url.path.strip('/').split('/')
        if len(path_parts) >= 2:
            # Look for common resource patterns
            if 'products' in path_parts:
                return 'product'
            elif 'orders' in path_parts:
                return 'order'
            elif 'users' in path_parts:
                return 'user'
        return None

    def _extract_resource_id(self, request: Request) -> Optional[str]:
        """Extract resource ID from request path"""
        path_parts = request.url.path.strip('/').split('/')
        # Look for UUID patterns or numeric IDs
        for part in path_parts:
            if len(part) == 36 and '-' in part:  # UUID
                return part
            elif part.isdigit():  # Numeric ID
                return part
        return None

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request"""
        # Check forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, "host"):
            return request.client.host
        
        return None

    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached permission check result"""
        if not cache_service:
            return None
        
        try:
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass
        
        return None

    async def _cache_result(self, cache_key: str, result: Dict[str, Any], ttl: int):
        """Cache permission check result"""
        if not cache_service:
            return
        
        try:
            # Remove non-serializable items
            cacheable_result = result.copy()
            if 'expires_at' in cacheable_result and cacheable_result['expires_at']:
                cacheable_result['expires_at'] = cacheable_result['expires_at'].isoformat()
            
            await cache_service.set(cache_key, json.dumps(cacheable_result), ttl)
        except Exception:
            pass

    async def _log_successful_access(
        self,
        request: Request,
        user: User,
        response: Response,
        permission: Optional[str],
        processing_time: float
    ):
        """Log successful access attempt"""
        try:
            with SessionLocal() as db:
                audit_log = UserPermissionAudit(
                    user_id=user.id,
                    action="ACCESS_GRANTED",
                    reason=f"Successful access to {request.method} {request.url.path}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    new_value={
                        "method": request.method,
                        "path": request.url.path,
                        "permission": permission,
                        "status_code": response.status_code,
                        "processing_time_ms": round(processing_time * 1000, 2)
                    }
                )
                db.add(audit_log)
                db.commit()
        except Exception:
            # Don't fail the request if logging fails
            pass

    async def _log_access_denied(
        self,
        request: Request,
        user: User,
        reason: str
    ):
        """Log access denied attempt"""
        try:
            with SessionLocal() as db:
                audit_log = UserPermissionAudit(
                    user_id=user.id,
                    action="ACCESS_DENIED",
                    reason=f"Access denied: {reason}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    old_value={
                        "method": request.method,
                        "path": request.url.path,
                        "reason": reason
                    }
                )
                db.add(audit_log)
                db.commit()
        except Exception:
            pass

    async def _log_error(self, request: Request, error: str):
        """Log middleware errors"""
        try:
            with SessionLocal() as db:
                audit_log = UserPermissionAudit(
                    action="MIDDLEWARE_ERROR",
                    reason=f"RBAC middleware error: {error}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    old_value={
                        "method": request.method,
                        "path": request.url.path,
                        "error": error
                    }
                )
                db.add(audit_log)
                db.commit()
        except Exception:
            pass

    def _get_default_permission_mappings(self) -> Dict[str, str]:
        """Get default permission mappings for endpoints"""
        return {
            # Product endpoints
            "GET /api/v1/products": "products.read.all",
            "GET /api/v1/products/{product_id}": "products.read.own",
            "POST /api/v1/products": "products.create.own",
            "PUT /api/v1/products/{product_id}": "products.update.own",
            "DELETE /api/v1/products/{product_id}": "products.delete.own",
            "POST /api/v1/products/bulk-update": "products.bulk_update",
            "POST /api/v1/products/sync": "products.sync",
            
            # Order endpoints
            "GET /api/v1/orders": "orders.read.all",
            "GET /api/v1/orders/{order_id}": "orders.read.own",
            "POST /api/v1/orders": "orders.create",
            "PUT /api/v1/orders/{order_id}": "orders.process",
            "POST /api/v1/orders/{order_id}/approve": "orders.approve",
            "DELETE /api/v1/orders/{order_id}": "orders.cancel",
            
            # Inventory endpoints
            "GET /api/v1/inventory": "inventory.read",
            "PUT /api/v1/inventory": "inventory.update",
            "POST /api/v1/inventory/sync": "inventory.sync",
            
            # Sourcing endpoints
            "GET /api/v1/sourcing": "sourcing.read",
            "POST /api/v1/sourcing": "sourcing.create",
            "PUT /api/v1/sourcing": "sourcing.manage",
            
            # Marketplace endpoints
            "GET /api/v1/marketplaces": "marketplaces.read",
            "POST /api/v1/marketplaces/configure": "marketplaces.configure",
            "POST /api/v1/marketplaces/sync": "marketplaces.sync",
            
            # Wholesaler endpoints
            "GET /api/v1/wholesalers": "wholesalers.read",
            "POST /api/v1/wholesalers/configure": "wholesalers.configure",
            "POST /api/v1/wholesalers/sync": "wholesalers.sync",
            
            # Pricing endpoints
            "GET /api/v1/pricing": "pricing.read",
            "PUT /api/v1/pricing": "pricing.update",
            "POST /api/v1/pricing/manage": "pricing.manage",
            
            # Financial endpoints
            "GET /api/v1/profits": "profits.read",
            "GET /api/v1/payments": "payments.read",
            "POST /api/v1/payments/process": "payments.process",
            
            # Analytics endpoints
            "GET /api/v1/analytics": "analytics.read",
            "GET /api/v1/analytics/*": "analytics.read",
            
            # Reports endpoints
            "GET /api/v1/reports": "reports.read",
            "POST /api/v1/reports": "reports.create",
            "GET /api/v1/reports/export": "reports.export",
            
            # User management endpoints
            "GET /api/v1/users": "users.read",
            "POST /api/v1/users": "users.create",
            "PUT /api/v1/users/{user_id}": "users.update",
            "DELETE /api/v1/users/{user_id}": "users.delete",
            
            # Role management endpoints
            "GET /api/v1/rbac/roles": "roles.read",
            "POST /api/v1/rbac/roles": "roles.create",
            "PUT /api/v1/rbac/roles/{role_id}": "roles.update",
            "DELETE /api/v1/rbac/roles/{role_id}": "roles.delete",
            
            # Settings endpoints
            "GET /api/v1/settings": "settings.read",
            "PUT /api/v1/settings": "settings.update",
            
            # AI services endpoints
            "GET /api/v1/ai": "ai_services.read",
            "POST /api/v1/ai/*": "ai_services.use",
            "PUT /api/v1/ai/configure": "ai_services.configure",
            
            # Automation endpoints
            "GET /api/v1/automation": "automation.read",
            "POST /api/v1/automation/configure": "automation.configure",
            "PUT /api/v1/automation/manage": "automation.manage",
        }


# Middleware configuration utilities
class RBACMiddlewareConfig:
    """Configuration helper for RBAC middleware"""
    
    @staticmethod
    def create_development_config() -> Dict[str, Any]:
        """Create configuration for development environment"""
        return {
            "excluded_paths": {
                "/auth/login", "/auth/logout", "/auth/refresh", "/auth/register",
                "/health", "/docs", "/openapi.json", "/favicon.ico",
                "/debug/*"  # Allow debug endpoints in development
            },
            "enable_audit_logging": True,
            "enable_caching": True,
            "cache_ttl": 60  # Shorter cache for development
        }
    
    @staticmethod
    def create_production_config() -> Dict[str, Any]:
        """Create configuration for production environment"""
        return {
            "excluded_paths": {
                "/auth/login", "/auth/logout", "/auth/refresh",
                "/health", "/docs", "/openapi.json"
            },
            "enable_audit_logging": True,
            "enable_caching": True,
            "cache_ttl": 300  # 5 minutes cache
        }
    
    @staticmethod
    def create_high_security_config() -> Dict[str, Any]:
        """Create configuration for high security environments"""
        return {
            "excluded_paths": {
                "/auth/login", "/auth/logout", "/health"
            },
            "enable_audit_logging": True,
            "enable_caching": False,  # Disable caching for maximum security
            "cache_ttl": 0
        }


# Factory function for middleware creation
def create_rbac_middleware(config_type: str = "development") -> RBACMiddleware:
    """Factory function to create RBAC middleware with predefined configurations"""
    
    configs = {
        "development": RBACMiddlewareConfig.create_development_config(),
        "production": RBACMiddlewareConfig.create_production_config(),
        "high_security": RBACMiddlewareConfig.create_high_security_config()
    }
    
    config = configs.get(config_type, configs["development"])
    
    return lambda app: RBACMiddleware(app, **config)