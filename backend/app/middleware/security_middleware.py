"""
보안 미들웨어
OWASP 권장사항에 따른 보안 헤더 및 보호 기능
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import hashlib
import secrets
from typing import Dict, Any


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더 미들웨어"""
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
    async def dispatch(self, request: Request, call_next):
        # Content Security Policy 생성
        nonce = secrets.token_urlsafe(16)
        
        # 요청 처리
        response = await call_next(request)
        
        # 보안 헤더 추가
        security_headers = {
            # XSS 보호
            "X-XSS-Protection": "1; mode=block",
            
            # Content Type Sniffing 방지
            "X-Content-Type-Options": "nosniff",
            
            # Clickjacking 방지
            "X-Frame-Options": "DENY",
            
            # HTTPS 강제 (프로덕션 환경)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            
            # Referrer 정책
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # 권한 정책
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # Content Security Policy
            "Content-Security-Policy": (
                f"default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                f"style-src 'self' 'unsafe-inline'; "
                f"img-src 'self' data: https:; "
                f"connect-src 'self'; "
                f"font-src 'self'; "
                f"object-src 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self'"
            ),
            
            # 서버 정보 숨기기
            "Server": "Dropshipping-API/2.0"
        }
        
        # 헤더 적용
        for header, value in security_headers.items():
            response.headers[header] = value
            
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """요청 크기 제한 미들웨어"""
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size
        
    async def dispatch(self, request: Request, call_next):
        # Content-Length 확인
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > self.max_request_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request too large",
                            "max_size": self.max_request_size,
                            "received_size": content_length
                        }
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid Content-Length header"}
                )
                
        return await call_next(request)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP 화이트리스트 미들웨어"""
    
    def __init__(self, app, allowed_ips: list = None, enabled: bool = False):
        super().__init__(app)
        self.allowed_ips = set(allowed_ips or [])
        self.enabled = enabled
        
        # 기본 허용 IP (로컬 개발)
        self.allowed_ips.update([
            "127.0.0.1",
            "::1",
            "localhost"
        ])
        
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
            
        # 클라이언트 IP 추출
        client_ip = self._get_client_ip(request)
        
        if client_ip not in self.allowed_ips:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Access denied",
                    "message": "IP not in whitelist"
                }
            )
            
        return await call_next(request)
        
    def _get_client_ip(self, request: Request) -> str:
        """실제 클라이언트 IP 추출"""
        # Proxy 환경 고려
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
            
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
            
        return request.client.host if request.client else "unknown"


class SQLInjectionProtectionMiddleware(BaseHTTPMiddleware):
    """SQL 인젝션 보호 미들웨어"""
    
    def __init__(self, app):
        super().__init__(app)
        # SQL 인젝션 패턴 (간단한 버전)
        self.sql_patterns = [
            r"(?i)(\bunion\b.*\bselect\b)",
            r"(?i)(\bselect\b.*\bfrom\b)",
            r"(?i)(\bdrop\b.*\btable\b)",
            r"(?i)(\bdelete\b.*\bfrom\b)",
            r"(?i)(\binsert\b.*\binto\b)",
            r"(?i)(\bupdate\b.*\bset\b)",
            r"(?i)(\balter\b.*\btable\b)",
            r"(?i)(--|\b\/\*|\*\/)",
            r"(\bor\b.*=.*\bor\b)",
            r"(\band\b.*=.*\band\b)",
            r"(\'.*\bor\b.*\')",
            r"(\".*\bor\b.*\")"
        ]
        
    async def dispatch(self, request: Request, call_next):
        # Query 파라미터 검사
        if request.url.query:
            if self._contains_sql_injection(request.url.query):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Potential SQL injection detected in query parameters"}
                )
                
        # Body 검사 (POST, PUT, PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body and self._contains_sql_injection(body.decode('utf-8', errors='ignore')):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Potential SQL injection detected in request body"}
                    )
            except:
                pass  # Body 읽기 실패 시 무시
                
        return await call_next(request)
        
    def _contains_sql_injection(self, text: str) -> bool:
        """SQL 인젝션 패턴 검사"""
        import re
        text_lower = text.lower()
        
        for pattern in self.sql_patterns:
            if re.search(pattern, text_lower):
                return True
                
        return False


class APIKeyValidationMiddleware(BaseHTTPMiddleware):
    """API 키 검증 미들웨어"""
    
    def __init__(self, app, api_keys: Dict[str, str] = None, enabled: bool = False):
        super().__init__(app)
        self.api_keys = api_keys or {}
        self.enabled = enabled
        
        # 보호하지 않을 경로
        self.excluded_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/",
            "/favicon.ico"
        }
        
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
            
        # 제외 경로 확인
        if request.url.path in self.excluded_paths:
            return await call_next(request)
            
        # API 키 검증
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "API key required"}
            )
            
        # 키 해시 검증 (보안 강화)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if api_key_hash not in self.api_keys.values():
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid API key"}
            )
            
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청 로깅 미들웨어 (보안 이벤트)"""
    
    def __init__(self, app):
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 민감한 정보 제외하고 로깅
        log_data = {
            "method": request.method,
            "url": str(request.url.path),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": time.time()
        }
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        log_data.update({
            "status_code": response.status_code,
            "process_time": process_time
        })
        
        # 보안 이벤트 로깅
        if response.status_code >= 400:
            self._log_security_event(log_data)
            
        return response
        
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
            
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
            
        return request.client.host if request.client else "unknown"
        
    def _log_security_event(self, log_data: Dict[str, Any]):
        """보안 이벤트 로깅"""
        from app.core.logging import logger
        
        if log_data["status_code"] in [401, 403, 429]:
            logger.warning(f"Security event: {log_data}")
        elif log_data["status_code"] >= 500:
            logger.error(f"Server error: {log_data}")