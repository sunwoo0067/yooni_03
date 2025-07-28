"""
Base service class to reduce code duplication.
코드 중복을 줄이기 위한 베이스 서비스 클래스.
기존 서비스들이 점진적으로 이 클래스를 상속받을 수 있도록 설계.
"""
import logging
from typing import Optional, TypeVar, Generic, Type
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppException,
    NotFoundError,
    DatabaseError,
    ValidationError
)

# Generic type for models
T = TypeVar('T')


class BaseService(Generic[T]):
    """
    Base service class with common functionality.
    기존 코드와 호환되도록 설계된 베이스 서비스 클래스.
    """
    
    def __init__(self, db: Session, model_class: Type[T] = None):
        """
        Initialize base service.
        
        Args:
            db: Database session (sync or async)
            model_class: SQLAlchemy model class
        """
        self.db = db
        self.model_class = model_class
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def log_info(self, message: str, **kwargs):
        """통일된 정보 로깅"""
        self.logger.info(message, extra=kwargs)
        
    def log_error(self, message: str, error: Exception = None, **kwargs):
        """통일된 에러 로깅"""
        error_details = {
            "error_type": type(error).__name__ if error else "Unknown",
            "error_message": str(error) if error else "No error details",
            **kwargs
        }
        self.logger.error(message, extra=error_details)
        
    def log_warning(self, message: str, **kwargs):
        """통일된 경고 로깅"""
        self.logger.warning(message, extra=kwargs)
        
    def handle_not_found(self, resource: str, identifier: any) -> NotFoundError:
        """리소스를 찾을 수 없을 때의 표준 처리"""
        message = f"{resource} not found: {identifier}"
        self.log_warning(message, resource=resource, identifier=str(identifier))
        return NotFoundError(
            message=message,
            code="NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)}
        )
        
    def handle_database_error(self, operation: str, error: Exception) -> DatabaseError:
        """데이터베이스 에러의 표준 처리"""
        message = f"Database error during {operation}"
        self.log_error(message, error=error, operation=operation)
        return DatabaseError(
            message=message,
            code="DATABASE_ERROR",
            details={"operation": operation, "error": str(error)}
        )
        
    def handle_validation_error(self, field: str, value: any, reason: str) -> ValidationError:
        """검증 에러의 표준 처리"""
        message = f"Validation failed for {field}: {reason}"
        self.log_warning(message, field=field, value=str(value), reason=reason)
        return ValidationError(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, "value": str(value), "reason": reason}
        )


class AsyncBaseService(BaseService[T]):
    """
    Async version of base service for async operations.
    비동기 작업을 위한 베이스 서비스 클래스.
    """
    
    def __init__(self, db: AsyncSession, model_class: Type[T] = None):
        super().__init__(db, model_class)
        
    async def get_by_id(self, id: any) -> Optional[T]:
        """ID로 엔티티 조회 (비동기)"""
        try:
            # 실제 비동기 쿼리는 각 서비스에서 구현
            # 여기서는 인터페이스만 제공
            raise NotImplementedError("Subclass must implement get_by_id")
        except Exception as e:
            raise self.handle_database_error("get_by_id", e)


# 기존 서비스와의 호환성을 위한 헬퍼 함수들
def create_logger(service_name: str) -> logging.Logger:
    """서비스용 로거 생성"""
    return logging.getLogger(service_name)


def safe_commit(db: Session, operation: str = "commit") -> bool:
    """
    안전한 커밋 처리
    
    Returns:
        bool: 성공 여부
    """
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger = logging.getLogger("safe_commit")
        logger.error(f"Commit failed during {operation}: {e}")
        return False


def safe_rollback(db: Session, reason: str = "unknown") -> None:
    """안전한 롤백 처리"""
    try:
        db.rollback()
        logger = logging.getLogger("safe_rollback")
        logger.info(f"Rollback completed: {reason}")
    except Exception as e:
        logger = logging.getLogger("safe_rollback")
        logger.error(f"Rollback failed: {e}")