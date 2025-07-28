"""
Safe patterns for external API calls.
외부 API 호출을 위한 안전한 패턴.
"""
import asyncio
import time
from typing import Optional, Dict, Any, Callable, Union
from functools import wraps
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_retry,
    after_retry
)

from app.core.logging_utils import get_logger
from app.core.exceptions import ExternalServiceError
from app.core.constants import Limits

logger = get_logger(__name__)


class APIClient:
    """안전한 외부 API 클라이언트 베이스 클래스"""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = headers or {}
        self.logger = get_logger(self.__class__.__name__)
        
        # HTTP 클라이언트 설정
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers=self.headers
        )
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
        
    def _log_retry(self, retry_state):
        """재시도 로깅"""
        self.logger.warning(
            f"Retrying API call",
            attempt=retry_state.attempt_number,
            wait_time=retry_state.next_action.sleep if retry_state.next_action else 0,
            exception=str(retry_state.outcome.exception()) if retry_state.outcome else None
        )
        
    def _log_success(self, retry_state):
        """성공 로깅"""
        if retry_state.attempt_number > 1:
            self.logger.info(
                f"API call succeeded after retry",
                attempts=retry_state.attempt_number
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before=lambda rs: rs.retry_object.fn.__self__._log_retry(rs) if rs.attempt_number > 1 else None,
        after=lambda rs: rs.retry_object.fn.__self__._log_success(rs)
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """HTTP 요청 실행 (재시도 포함)"""
        url = f"{endpoint}" if endpoint.startswith('http') else endpoint
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"HTTP error",
                status_code=e.response.status_code,
                url=str(e.request.url),
                response_text=e.response.text[:500]  # 응답 일부만 로깅
            )
            raise ExternalServiceError(
                service_name=self.__class__.__name__,
                detail=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
            
        except httpx.TimeoutException as e:
            self.logger.error(f"Request timeout", url=str(e.request.url))
            raise
            
        except Exception as e:
            self.logger.error(f"Unexpected error", error=e)
            raise ExternalServiceError(
                service_name=self.__class__.__name__,
                detail=str(e)
            )
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET 요청"""
        response = await self._make_request("GET", endpoint, **kwargs)
        return response.json()
        
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST 요청"""
        response = await self._make_request("POST", endpoint, **kwargs)
        return response.json()
        
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PUT 요청"""
        response = await self._make_request("PUT", endpoint, **kwargs)
        return response.json()
        
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE 요청"""
        response = await self._make_request("DELETE", endpoint, **kwargs)
        return response.json()


class RateLimitedAPIClient(APIClient):
    """
    Rate limiting이 적용된 API 클라이언트.
    """
    
    def __init__(
        self,
        base_url: str,
        rate_limit: int = 10,  # 초당 요청 수
        burst: int = 20,       # 버스트 허용량
        **kwargs
    ):
        super().__init__(base_url, **kwargs)
        self.rate_limit = rate_limit
        self.burst = burst
        self._tokens = burst
        self._last_update = time.time()
        self._lock = asyncio.Lock()
        
    async def _get_token(self):
        """토큰 획득 (rate limiting)"""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_update
            self._last_update = now
            
            # 토큰 충전
            self._tokens = min(
                self.burst,
                self._tokens + elapsed * self.rate_limit
            )
            
            if self._tokens < 1:
                # 토큰이 없으면 대기
                wait_time = (1 - self._tokens) / self.rate_limit
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self._tokens = 1
                
            self._tokens -= 1
            
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Rate limiting이 적용된 요청"""
        await self._get_token()
        return await super()._make_request(method, endpoint, **kwargs)


class CircuitBreakerAPIClient(APIClient):
    """
    Circuit breaker 패턴이 적용된 API 클라이언트.
    """
    
    def __init__(
        self,
        base_url: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        **kwargs
    ):
        super().__init__(base_url, **kwargs)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time = None
        self._circuit_open = False
        
    async def _check_circuit(self):
        """회로 차단기 상태 확인"""
        if not self._circuit_open:
            return
            
        # 복구 시간이 지났는지 확인
        if self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self.logger.info("Circuit breaker: attempting reset")
                self._circuit_open = False
                self._failure_count = 0
            else:
                remaining = self.recovery_timeout - elapsed
                raise ExternalServiceError(
                    service_name=self.__class__.__name__,
                    detail=f"Circuit breaker is open. Retry after {remaining:.0f}s"
                )
                
    def _record_success(self):
        """성공 기록"""
        self._failure_count = 0
        if self._circuit_open:
            self.logger.info("Circuit breaker: reset successful")
            self._circuit_open = False
            
    def _record_failure(self):
        """실패 기록"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self.logger.error(
                f"Circuit breaker: opening circuit",
                failures=self._failure_count
            )
            self._circuit_open = True
            
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Circuit breaker가 적용된 요청"""
        await self._check_circuit()
        
        try:
            response = await super()._make_request(method, endpoint, **kwargs)
            self._record_success()
            return response
        except Exception as e:
            self._record_failure()
            raise


def with_timeout(timeout: int):
    """
    타임아웃 데코레이터.
    
    Usage:
        @with_timeout(5)
        async def fetch_data():
            # 5초 타임아웃
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {timeout}s")
                raise ExternalServiceError(
                    service_name=func.__name__,
                    detail=f"Operation timed out after {timeout} seconds"
                )
        return wrapper
    return decorator


def batch_api_calls(
    batch_size: int = 10,
    delay: float = 0.1
):
    """
    API 호출을 배치로 처리하는 데코레이터.
    
    Usage:
        @batch_api_calls(batch_size=5, delay=0.5)
        async def process_items(items: List[str]):
            results = []
            for item in items:
                result = await api_call(item)
                results.append(result)
            return results
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(items: list, *args, **kwargs):
            results = []
            
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                # 배치 처리
                batch_results = await func(batch, *args, **kwargs)
                results.extend(batch_results)
                
                # 마지막 배치가 아니면 지연
                if i + batch_size < len(items):
                    await asyncio.sleep(delay)
                    
            return results
        return wrapper
    return decorator


# 실제 사용 예제
class ExampleMarketplaceAPI(RateLimitedAPIClient):
    """마켓플레이스 API 클라이언트 예제"""
    
    def __init__(self, api_key: str):
        super().__init__(
            base_url="https://api.marketplace.com",
            rate_limit=10,  # 초당 10개 요청
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """상품 정보 조회"""
        return await self.get(f"/products/{product_id}")
        
    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """주문 생성"""
        return await self.post("/orders", json=order_data)
        
    @with_timeout(10)
    async def search_products(self, keyword: str, page: int = 1) -> Dict[str, Any]:
        """상품 검색 (10초 타임아웃)"""
        return await self.get(
            "/products/search",
            params={"keyword": keyword, "page": page}
        )