"""
Monitoring middleware for automatic metrics collection.
자동 메트릭 수집을 위한 모니터링 미들웨어.
"""
import time
import traceback
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging_utils import get_logger
from app.services.monitoring.monitoring_service_v2 import ApplicationMonitor, MetricsCollector


class MonitoringMiddleware(BaseHTTPMiddleware):
    """모니터링 미들웨어"""
    
    def __init__(self, app: ASGIApp, metrics_collector: MetricsCollector):
        super().__init__(app)
        self.app_monitor = ApplicationMonitor(metrics_collector)
        self.logger = get_logger(self.__class__.__name__)
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 및 메트릭 수집"""
        # 시작 시간
        start_time = time.time()
        
        # 경로 정보
        path = request.url.path
        method = request.method
        
        # 제외할 경로 (헬스체크 등)
        if path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 응답 시간 계산
            duration = (time.time() - start_time) * 1000  # 밀리초
            
            # 메트릭 기록
            self.app_monitor.record_request(
                endpoint=self._normalize_path(path),
                method=method,
                status_code=response.status_code,
                response_time=duration
            )
            
            # 응답 헤더에 메트릭 추가
            response.headers["X-Response-Time"] = f"{duration:.2f}ms"
            
            return response
            
        except Exception as e:
            # 에러 처리
            duration = (time.time() - start_time) * 1000
            
            # 에러 메트릭 기록
            self.app_monitor.record_request(
                endpoint=self._normalize_path(path),
                method=method,
                status_code=500,
                response_time=duration
            )
            
            # 에러 로깅
            self.logger.error(
                f"Request failed",
                extra={
                    "path": path,
                    "method": method,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            )
            
            raise
            
    def _normalize_path(self, path: str) -> str:
        """경로 정규화 (파라미터 제거)"""
        # /api/v1/orders/123 -> /api/v1/orders/{id}
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            if part and (part.isdigit() or self._is_uuid(part)):
                normalized.append("{id}")
            else:
                normalized.append(part)
                
        return "/".join(normalized)
        
    def _is_uuid(self, value: str) -> bool:
        """UUID 형식 확인"""
        import re
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        return bool(re.match(uuid_pattern, value.lower()))


class DatabaseMonitoringMiddleware:
    """데이터베이스 모니터링 미들웨어"""
    
    def __init__(self, app_monitor: ApplicationMonitor):
        self.app_monitor = app_monitor
        self.logger = get_logger(self.__class__.__name__)
        
    def __call__(self, execute):
        """SQLAlchemy 실행 래퍼"""
        def wrapper(conn, clause, params, context):
            start_time = time.time()
            
            try:
                # 쿼리 실행
                result = execute(conn, clause, params, context)
                
                # 성공 메트릭
                duration = (time.time() - start_time) * 1000
                self._record_query_metric(clause, duration, True)
                
                return result
                
            except Exception as e:
                # 실패 메트릭
                duration = (time.time() - start_time) * 1000
                self._record_query_metric(clause, duration, False)
                raise
                
        return wrapper
        
    def _record_query_metric(self, clause, duration: float, success: bool):
        """쿼리 메트릭 기록"""
        # 쿼리 타입 추출
        query_str = str(clause).strip().upper()
        
        if query_str.startswith("SELECT"):
            operation = "select"
        elif query_str.startswith("INSERT"):
            operation = "insert"
        elif query_str.startswith("UPDATE"):
            operation = "update"
        elif query_str.startswith("DELETE"):
            operation = "delete"
        else:
            operation = "other"
            
        # 테이블 이름 추출 (간단한 파싱)
        table = self._extract_table_name(query_str)
        
        # 메트릭 기록
        self.app_monitor.record_database_query(
            operation=operation,
            table=table,
            duration=duration,
            success=success
        )
        
    def _extract_table_name(self, query: str) -> str:
        """쿼리에서 테이블 이름 추출"""
        # 간단한 파싱 (실제로는 더 정교한 파싱 필요)
        keywords = ["FROM", "INTO", "UPDATE", "DELETE FROM"]
        
        for keyword in keywords:
            if keyword in query:
                parts = query.split(keyword)
                if len(parts) > 1:
                    table_part = parts[1].strip().split()[0]
                    return table_part.lower().strip('"').strip('`')
                    
        return "unknown"


class CacheMonitoringWrapper:
    """캐시 모니터링 래퍼"""
    
    def __init__(self, cache_manager, app_monitor: ApplicationMonitor):
        self.cache_manager = cache_manager
        self.app_monitor = app_monitor
        self.logger = get_logger(self.__class__.__name__)
        
    def get(self, key: str):
        """캐시 조회 모니터링"""
        start_time = time.time()
        
        try:
            value = self.cache_manager.get(key)
            duration = (time.time() - start_time) * 1000
            
            self.app_monitor.record_cache_operation(
                operation="get",
                hit=value is not None,
                duration=duration
            )
            
            return value
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            self.app_monitor.record_cache_operation(
                operation="get",
                hit=False,
                duration=duration
            )
            
            self.logger.error(f"Cache get error: {e}")
            return None
            
    def set(self, key: str, value, ttl: int = None):
        """캐시 저장 모니터링"""
        start_time = time.time()
        
        try:
            result = self.cache_manager.set(key, value, ttl)
            duration = (time.time() - start_time) * 1000
            
            self.app_monitor.record_cache_operation(
                operation="set",
                hit=result,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            self.app_monitor.record_cache_operation(
                operation="set",
                hit=False,
                duration=duration
            )
            
            self.logger.error(f"Cache set error: {e}")
            return False
            
    def delete(self, key: str):
        """캐시 삭제 모니터링"""
        start_time = time.time()
        
        try:
            result = self.cache_manager.delete(key)
            duration = (time.time() - start_time) * 1000
            
            self.app_monitor.record_cache_operation(
                operation="delete",
                hit=result,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            self.app_monitor.record_cache_operation(
                operation="delete",
                hit=False,
                duration=duration
            )
            
            self.logger.error(f"Cache delete error: {e}")
            return False