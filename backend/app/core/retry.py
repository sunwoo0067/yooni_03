"""
드롭쉬핑 프로젝트용 자동 복구 메커니즘

재시도, 폴백, 회로 차단기 패턴을 통한
자동 에러 복구 시스템을 제공합니다.

기존 호환성 유지 + 새로운 고급 기능 추가
"""

import asyncio
import functools
import logging
import time
import random
from typing import Callable, Any, Optional, Type, Tuple, Dict, List, Union, TypeVar, Generic
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.exceptions import (
    AppException, ErrorRecoveryAction, ErrorSeverity,
    ExternalServiceError, WholesalerAPIError, MarketplaceAPIError,
    AIServiceError, DatabaseError, ServiceUnavailableError
)

T = TypeVar('T')
logger = logging.getLogger(__name__)


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    지수 백오프 계산
    
    Args:
        attempt: 시도 횟수 (0부터 시작)
        base_delay: 기본 지연 시간 (초)
        max_delay: 최대 지연 시간 (초)
        jitter: 랜덤 지터 추가 여부
        
    Returns:
        계산된 지연 시간 (초)
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    if jitter:
        # 0.5 ~ 1.5 사이의 랜덤 factor 적용
        delay *= (0.5 + random.random())
        
    return delay


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    log_errors: bool = True
):
    """
    동기 함수용 재시도 데코레이터
    
    Args:
        max_attempts: 최대 시도 횟수
        delay: 재시도 간 대기 시간 (초)
        backoff: 지수 백오프 사용 여부
        exceptions: 재시도할 예외 타입들
        on_retry: 재시도 시 호출할 콜백 함수
        log_errors: 에러 로깅 여부
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if log_errors:
                        logger.warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_attempts}): {e}"
                        )
                        
                    if on_retry:
                        on_retry(func, e, attempt)
                        
                    if attempt < max_attempts - 1:
                        wait_time = exponential_backoff(attempt, delay) if backoff else delay
                        
                        if log_errors:
                            logger.info(f"{wait_time:.1f}초 후 재시도...")
                            
                        import time
                        time.sleep(wait_time)
                        
            # 모든 시도 실패
            if log_errors:
                logger.error(f"{func.__name__} 최종 실패: {last_exception}")
                
            raise last_exception
            
        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    log_errors: bool = True
):
    """
    비동기 함수용 재시도 데코레이터
    
    Args:
        max_attempts: 최대 시도 횟수
        delay: 재시도 간 대기 시간 (초)
        backoff: 지수 백오프 사용 여부
        exceptions: 재시도할 예외 타입들
        on_retry: 재시도 시 호출할 콜백 함수
        log_errors: 에러 로깅 여부
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if log_errors:
                        logger.warning(
                            f"{func.__name__} 실패 (시도 {attempt + 1}/{max_attempts}): {e}"
                        )
                        
                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(func, e, attempt)
                        else:
                            on_retry(func, e, attempt)
                            
                    if attempt < max_attempts - 1:
                        wait_time = exponential_backoff(attempt, delay) if backoff else delay
                        
                        if log_errors:
                            logger.info(f"{wait_time:.1f}초 후 재시도...")
                            
                        await asyncio.sleep(wait_time)
                        
            # 모든 시도 실패
            if log_errors:
                logger.error(f"{func.__name__} 최종 실패: {last_exception}")
                
            raise last_exception
            
        return wrapper
    return decorator


class RetryableError(Exception):
    """재시도 가능한 에러"""
    pass


class NonRetryableError(Exception):
    """재시도 불가능한 에러"""
    pass


# 일반적인 재시도 가능한 예외들
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    RetryableError,
    OSError,  # 네트워크 관련 OS 에러
)


# HTTP 상태 코드별 재시도 가능 여부
RETRYABLE_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}


def is_retryable_http_error(status_code: int) -> bool:
    """HTTP 상태 코드가 재시도 가능한지 확인"""
    return status_code in RETRYABLE_STATUS_CODES


class RetryContext:
    """재시도 컨텍스트 관리"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: bool = True,
        timeout: Optional[float] = None
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.timeout = timeout
        self.attempt = 0
        self.start_time = None
        
    def should_retry(self, exception: Exception) -> bool:
        """재시도 여부 결정"""
        # 재시도 불가능한 에러
        if isinstance(exception, NonRetryableError):
            return False
            
        # 최대 시도 횟수 초과
        if self.attempt >= self.max_attempts:
            return False
            
        # 타임아웃 확인
        if self.timeout and self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > self.timeout:
                return False
                
        # 재시도 가능한 예외인지 확인
        return isinstance(exception, RETRYABLE_EXCEPTIONS)
        
    def get_delay(self) -> float:
        """다음 재시도까지의 대기 시간"""
        if self.backoff:
            return exponential_backoff(self.attempt, self.delay)
        return self.delay
        
    def increment(self):
        """시도 횟수 증가"""
        if self.attempt == 0:
            self.start_time = datetime.now()
        self.attempt += 1


# =============================================================================
# 새로운 고급 복구 메커니즘 (드롭쉬핑 특화)
# =============================================================================


class RetryStrategy(str, Enum):
    """재시도 전략"""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    JITTERED_BACKOFF = "jittered_backoff"


class CircuitState(str, Enum):
    """회로 차단기 상태"""
    CLOSED = "closed"      # 정상 동작
    OPEN = "open"          # 차단 상태
    HALF_OPEN = "half_open"  # 반개방 상태


@dataclass
class RetryConfig:
    """재시도 설정"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_factor: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[type] = None
    
    def __post_init__(self):
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [
                ExternalServiceError,
                WholesalerAPIError,
                MarketplaceAPIError,
                AIServiceError,
                DatabaseError,
                ConnectionError,
                TimeoutError
            ]


@dataclass
class CircuitBreakerConfig:
    """회로 차단기 설정"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: float = 60.0
    expected_exception: type = Exception


class CircuitBreakerState:
    """회로 차단기 상태 관리"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.next_attempt_time: Optional[datetime] = None
    
    def can_attempt(self) -> bool:
        """시도 가능 여부 확인"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self.next_attempt_time and datetime.utcnow() >= self.next_attempt_time:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """성공 기록"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """실패 기록"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.next_attempt_time = datetime.utcnow() + timedelta(seconds=self.config.timeout)
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.next_attempt_time = datetime.utcnow() + timedelta(seconds=self.config.timeout)


class RetryManager:
    """재시도 관리자"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.fallback_registry: Dict[str, List[Callable]] = {}
    
    def register_fallback(self, service_name: str, fallback_func: Callable):
        """폴백 함수 등록"""
        if service_name not in self.fallback_registry:
            self.fallback_registry[service_name] = []
        self.fallback_registry[service_name].append(fallback_func)
    
    def get_circuit_breaker(self, service_name: str, config: CircuitBreakerConfig) -> CircuitBreakerState:
        """회로 차단기 인스턴스 가져오기"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreakerState(config)
        return self.circuit_breakers[service_name]
    
    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """재시도 지연 시간 계산"""
        if config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_factor ** (attempt - 1))
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt
        elif config.strategy == RetryStrategy.JITTERED_BACKOFF:
            base_delay = config.base_delay * (config.backoff_factor ** (attempt - 1))
            jitter = random.uniform(0, base_delay * 0.1)
            delay = base_delay + jitter
        else:
            delay = config.base_delay
        
        # 최대 지연 시간 제한
        delay = min(delay, config.max_delay)
        
        # 지터 추가 (선택적)
        if config.jitter and config.strategy != RetryStrategy.JITTERED_BACKOFF:
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
        
        return delay
    
    def is_retryable_exception(self, exception: Exception, config: RetryConfig) -> bool:
        """재시도 가능한 예외인지 확인"""
        # AppException인 경우 복구 액션 확인
        if isinstance(exception, AppException):
            return exception.recovery_action == ErrorRecoveryAction.RETRY
        
        # 설정된 예외 타입 확인
        return any(isinstance(exception, exc_type) for exc_type in config.retryable_exceptions)
    
    async def execute_with_retry(
        self,
        func: Callable[..., T],
        config: RetryConfig,
        *args,
        **kwargs
    ) -> T:
        """재시도 로직이 포함된 함수 실행"""
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                logger.debug(
                    f"Executing function attempt {attempt}/{config.max_attempts}",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt,
                        "max_attempts": config.max_attempts
                    }
                )
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 성공 시 로깅
                if attempt > 1:
                    logger.info(
                        f"Function succeeded on attempt {attempt}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "total_attempts": attempt
                        }
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 재시도 가능 여부 확인
                if not self.is_retryable_exception(e, config):
                    logger.warning(
                        f"Non-retryable exception occurred",
                        extra={
                            "function": func.__name__,
                            "exception_type": type(e).__name__,
                            "exception_message": str(e),
                            "attempt": attempt
                        }
                    )
                    raise e
                
                # 마지막 시도인 경우
                if attempt == config.max_attempts:
                    logger.error(
                        f"Function failed after {config.max_attempts} attempts",
                        extra={
                            "function": func.__name__,
                            "total_attempts": config.max_attempts,
                            "final_exception_type": type(e).__name__,
                            "final_exception_message": str(e)
                        }
                    )
                    raise e
                
                # 재시도 지연
                delay = self.calculate_delay(attempt, config)
                logger.warning(
                    f"Function failed on attempt {attempt}, retrying in {delay}s",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "retry_delay": delay
                    }
                )
                
                await asyncio.sleep(delay)
        
        # 이 코드에 도달하면 안 되지만, 안전을 위해
        raise last_exception
    
    async def execute_with_circuit_breaker(
        self,
        func: Callable[..., T],
        service_name: str,
        config: CircuitBreakerConfig,
        *args,
        **kwargs
    ) -> T:
        """회로 차단기가 포함된 함수 실행"""
        circuit_breaker = self.get_circuit_breaker(service_name, config)
        
        # 회로 차단기 상태 확인
        if not circuit_breaker.can_attempt():
            raise ServiceUnavailableError(
                f"Circuit breaker is OPEN for service {service_name}",
                context={"service_name": service_name, "circuit_state": circuit_breaker.state.value}
            )
        
        try:
            logger.debug(
                f"Executing function with circuit breaker",
                extra={
                    "service_name": service_name,
                    "circuit_state": circuit_breaker.state.value,
                    "function": func.__name__
                }
            )
            
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 성공 기록
            circuit_breaker.record_success()
            
            if circuit_breaker.state == CircuitState.HALF_OPEN:
                logger.info(
                    f"Circuit breaker transitioning to CLOSED",
                    extra={
                        "service_name": service_name,
                        "function": func.__name__
                    }
                )
            
            return result
            
        except Exception as e:
            # 예상된 예외인 경우만 실패로 기록
            if isinstance(e, config.expected_exception):
                circuit_breaker.record_failure()
                
                if circuit_breaker.state == CircuitState.OPEN:
                    logger.warning(
                        f"Circuit breaker opened due to failures",
                        extra={
                            "service_name": service_name,
                            "function": func.__name__,
                            "failure_count": circuit_breaker.failure_count,
                            "next_attempt_time": circuit_breaker.next_attempt_time.isoformat() if circuit_breaker.next_attempt_time else None
                        }
                    )
            
            raise e
    
    async def execute_with_fallback(
        self,
        func: Callable[..., T],
        service_name: str,
        *args,
        **kwargs
    ) -> T:
        """폴백이 포함된 함수 실행"""
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            return result
            
        except Exception as e:
            logger.warning(
                f"Primary function failed, trying fallbacks",
                extra={
                    "service_name": service_name,
                    "function": func.__name__,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                }
            )
            
            # 폴백 함수들 시도
            fallback_functions = self.fallback_registry.get(service_name, [])
            
            for i, fallback_func in enumerate(fallback_functions):
                try:
                    logger.info(
                        f"Trying fallback function {i+1}/{len(fallback_functions)}",
                        extra={
                            "service_name": service_name,
                            "fallback_function": fallback_func.__name__
                        }
                    )
                    
                    if asyncio.iscoroutinefunction(fallback_func):
                        result = await fallback_func(*args, **kwargs)
                    else:
                        result = fallback_func(*args, **kwargs)
                    
                    logger.info(
                        f"Fallback function succeeded",
                        extra={
                            "service_name": service_name,
                            "fallback_function": fallback_func.__name__,
                            "fallback_index": i+1
                        }
                    )
                    
                    return result
                    
                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback function {i+1} failed",
                        extra={
                            "service_name": service_name,
                            "fallback_function": fallback_func.__name__,
                            "fallback_exception_type": type(fallback_error).__name__,
                            "fallback_exception_message": str(fallback_error)
                        }
                    )
                    continue
            
            # 모든 폴백 실패 시 원래 예외 발생
            logger.error(
                f"All fallback functions failed",
                extra={
                    "service_name": service_name,
                    "fallback_count": len(fallback_functions)
                }
            )
            raise e


# 전역 재시도 관리자 인스턴스
retry_manager = RetryManager()


# =============================================================================
# 새로운 데코레이터들
# =============================================================================

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[type]] = None
):
    """재시도 데코레이터"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        backoff_factor=backoff_factor,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await retry_manager.execute_with_retry(func, config, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # 동기 함수를 비동기로 실행
            return asyncio.run(retry_manager.execute_with_retry(func, config, *args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def with_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 60.0,
    expected_exception: type = Exception
):
    """회로 차단기 데코레이터"""
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout,
        expected_exception=expected_exception
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await retry_manager.execute_with_circuit_breaker(
                func, service_name, config, *args, **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return asyncio.run(
                retry_manager.execute_with_circuit_breaker(
                    func, service_name, config, *args, **kwargs
                )
            )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def with_fallback(service_name: str):
    """폴백 데코레이터"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            return await retry_manager.execute_with_fallback(func, service_name, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return asyncio.run(retry_manager.execute_with_fallback(func, service_name, *args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def with_resilience(
    service_name: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    enable_fallback: bool = True
):
    """통합 복원력 데코레이터 (재시도 + 회로 차단기 + 폴백)"""
    retry_conf = retry_config or RetryConfig()
    circuit_conf = circuit_breaker_config or CircuitBreakerConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # 회로 차단기 + 재시도 + 폴백 조합
            try:
                return await retry_manager.execute_with_circuit_breaker(
                    lambda *a, **kw: retry_manager.execute_with_retry(func, retry_conf, *a, **kw),
                    service_name,
                    circuit_conf,
                    *args,
                    **kwargs
                )
            except Exception as e:
                if enable_fallback:
                    return await retry_manager.execute_with_fallback(
                        func, service_name, *args, **kwargs
                    )
                raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# =============================================================================
# 폴백 함수 등록 헬퍼
# =============================================================================

def register_fallback(service_name: str, fallback_func: Callable):
    """폴백 함수 등록 헬퍼"""
    retry_manager.register_fallback(service_name, fallback_func)


# =============================================================================
# 드롭쉬핑 특화 복구 전략
# =============================================================================

class DropshippingRecoveryStrategy:
    """드롭쉬핑 특화 복구 전략"""
    
    @staticmethod
    def setup_wholesaler_fallbacks():
        """도매처 폴백 설정"""
        
        async def ownerclan_fallback(*args, **kwargs):
            """OwnerClan 폴백 - Zentrade로 대체"""
            logger.info("Using Zentrade as fallback for OwnerClan")
            # TODO: Zentrade API 호출 로직
            return {"status": "fallback", "source": "zentrade"}
        
        async def zentrade_fallback(*args, **kwargs):
            """Zentrade 폴백 - OwnerClan으로 대체"""
            logger.info("Using OwnerClan as fallback for Zentrade")
            # TODO: OwnerClan API 호출 로직
            return {"status": "fallback", "source": "ownerclan"}
        
        async def domeggook_fallback(*args, **kwargs):
            """Domeggook 폴백 - 샘플 데이터 사용"""
            logger.info("Using sample data as fallback for Domeggook")
            return {"status": "fallback", "source": "sample_data"}
        
        # 폴백 함수 등록
        register_fallback("ownerclan", zentrade_fallback)
        register_fallback("zentrade", ownerclan_fallback)
        register_fallback("domeggook", domeggook_fallback)
    
    @staticmethod
    def setup_ai_service_fallbacks():
        """AI 서비스 폴백 설정"""
        
        async def gemini_fallback(*args, **kwargs):
            """Gemini 폴백 - Ollama 사용"""
            logger.info("Using Ollama as fallback for Gemini")
            # TODO: Ollama API 호출 로직
            return {"status": "fallback", "source": "ollama"}
        
        async def ollama_fallback(*args, **kwargs):
            """Ollama 폴백 - Gemini 사용"""
            logger.info("Using Gemini as fallback for Ollama")
            # TODO: Gemini API 호출 로직
            return {"status": "fallback", "source": "gemini"}
        
        # 폴백 함수 등록
        register_fallback("gemini", ollama_fallback)
        register_fallback("ollama", gemini_fallback)
    
    @staticmethod
    def setup_marketplace_fallbacks():
        """마켓플레이스 폴백 설정"""
        
        async def marketplace_fallback(*args, **kwargs):
            """마켓플레이스 폴백 - 큐에 저장 후 나중에 처리"""
            logger.info("Saving marketplace operation to queue for later processing")
            # TODO: 큐에 작업 저장 로직
            return {"status": "queued", "message": "작업이 큐에 저장되었습니다"}
        
        # 모든 마켓플레이스에 동일한 폴백 적용
        register_fallback("coupang", marketplace_fallback)
        register_fallback("naver", marketplace_fallback)
        register_fallback("11st", marketplace_fallback)


# 시스템 시작 시 폴백 설정 초기화
def initialize_recovery_strategies():
    """복구 전략 초기화"""
    strategy = DropshippingRecoveryStrategy()
    strategy.setup_wholesaler_fallbacks()
    strategy.setup_ai_service_fallbacks()
    strategy.setup_marketplace_fallbacks()
    
    logger.info("Dropshipping recovery strategies initialized")


# =============================================================================
# 드롭쉬핑 특화 데코레이터들
# =============================================================================

def dropshipping_resilient(
    service_type: str,  # "wholesaler", "marketplace", "ai"
    service_name: str,
    max_attempts: int = 3
):
    """드롭쉬핑 특화 복원력 데코레이터"""
    
    # 서비스 타입별 설정
    if service_type == "wholesaler":
        retry_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retryable_exceptions=[WholesalerAPIError, ConnectionError, TimeoutError]
        )
        circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=30.0,
            expected_exception=WholesalerAPIError
        )
    elif service_type == "marketplace":
        retry_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=1.0,
            strategy=RetryStrategy.JITTERED_BACKOFF,
            retryable_exceptions=[MarketplaceAPIError, ConnectionError]
        )
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            timeout=60.0,
            expected_exception=MarketplaceAPIError
        )
    elif service_type == "ai":
        retry_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=1.5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retryable_exceptions=[AIServiceError, ConnectionError, TimeoutError]
        )
        circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=45.0,
            expected_exception=AIServiceError
        )
    else:
        # 기본 설정
        retry_config = RetryConfig(max_attempts=max_attempts)
        circuit_config = CircuitBreakerConfig()
    
    return with_resilience(
        service_name=f"{service_type}_{service_name}",
        retry_config=retry_config,
        circuit_breaker_config=circuit_config,
        enable_fallback=True
    )


# =============================================================================
# 기존 호환성 유지
# =============================================================================

# 사용 예시
"""
# 기존 방식 (호환성 유지)
@retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError, TimeoutError))
def fetch_data(url):
    # API 호출
    pass

@async_retry(max_attempts=5, delay=2.0, backoff=True)
async def async_api_call(endpoint):
    # 비동기 API 호출
    pass

# 새로운 방식 (고급 기능)
@dropshipping_resilient("wholesaler", "ownerclan", max_attempts=3)
async def get_products_from_ownerclan():
    # OwnerClan API 호출
    pass

@with_resilience("marketplace_coupang", enable_fallback=True)
async def register_product_to_coupang(product_data):
    # 쿠팡 상품 등록
    pass

# 폴백 함수 등록
@register_fallback("custom_service")
async def fallback_function(*args, **kwargs):
    # 폴백 로직
    pass

# 수동 재시도 관리 (기존)
async def manual_retry_example():
    ctx = RetryContext(max_attempts=3, timeout=30.0)
    
    while True:
        try:
            result = await some_operation()
            return result
        except Exception as e:
            ctx.increment()
            
            if not ctx.should_retry(e):
                raise
                
            delay = ctx.get_delay()
            await asyncio.sleep(delay)
"""