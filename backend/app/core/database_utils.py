"""
Safe database transaction utilities.
안전한 데이터베이스 트랜잭션 유틸리티.
"""
import logging
from contextlib import contextmanager
from typing import Optional, Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


@contextmanager
def safe_transaction(db: Session, operation_name: str = "database operation"):
    """
    안전한 트랜잭션 컨텍스트 매니저.
    
    Usage:
        with safe_transaction(db, "order creation") as session:
            # 데이터베이스 작업 수행
            order = Order(...)
            session.add(order)
            # 컨텍스트를 벗어나면 자동 커밋 또는 롤백
    """
    try:
        yield db
        db.commit()
        logger.info(f"Transaction committed successfully: {operation_name}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during {operation_name}: {str(e)}")
        raise DatabaseError(
            message=f"Database operation failed: {operation_name}",
            code="TRANSACTION_ERROR",
            details={"operation": operation_name, "error": str(e)}
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during {operation_name}: {str(e)}")
        raise


def execute_in_transaction(
    db: Session,
    operation: Callable,
    operation_name: str = "database operation",
    *args,
    **kwargs
) -> Any:
    """
    트랜잭션 내에서 작업을 실행하는 헬퍼 함수.
    
    Args:
        db: Database session
        operation: 실행할 함수
        operation_name: 작업 이름 (로깅용)
        *args, **kwargs: operation 함수에 전달할 인자
    
    Returns:
        operation 함수의 반환값
    
    Example:
        def create_order(session, order_data):
            order = Order(**order_data)
            session.add(order)
            return order
        
        order = execute_in_transaction(
            db, 
            create_order, 
            "order creation",
            order_data
        )
    """
    with safe_transaction(db, operation_name):
        return operation(db, *args, **kwargs)


def safe_bulk_insert(
    db: Session,
    model_class: type,
    data_list: list,
    batch_size: int = 100
) -> int:
    """
    대량 데이터를 안전하게 삽입.
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class
        data_list: 삽입할 데이터 리스트
        batch_size: 배치 크기
    
    Returns:
        int: 삽입된 레코드 수
    """
    total_inserted = 0
    
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i + batch_size]
        
        try:
            with safe_transaction(db, f"bulk insert batch {i//batch_size + 1}"):
                objects = [model_class(**data) for data in batch]
                db.bulk_save_objects(objects)
                total_inserted += len(objects)
                
        except Exception as e:
            logger.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
            # 배치 실패 시 계속 진행할지 중단할지 결정
            # 여기서는 로그만 남기고 계속 진행
            continue
    
    logger.info(f"Bulk insert completed: {total_inserted}/{len(data_list)} records")
    return total_inserted


def safe_update(
    db: Session,
    model_instance: Any,
    updates: dict,
    allowed_fields: Optional[list] = None
) -> Any:
    """
    모델 인스턴스를 안전하게 업데이트.
    
    Args:
        db: Database session
        model_instance: 업데이트할 모델 인스턴스
        updates: 업데이트할 필드와 값
        allowed_fields: 업데이트 가능한 필드 목록 (None이면 모든 필드 허용)
    
    Returns:
        업데이트된 모델 인스턴스
    """
    if allowed_fields:
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    try:
        with safe_transaction(db, f"update {model_instance.__class__.__name__}"):
            for key, value in updates.items():
                if hasattr(model_instance, key):
                    setattr(model_instance, key, value)
                else:
                    logger.warning(f"Field {key} not found in model")
            
            db.add(model_instance)
            return model_instance
            
    except Exception as e:
        logger.error(f"Failed to update model: {e}")
        raise


def retry_on_deadlock(max_retries: int = 3, delay: float = 0.1):
    """
    데드락 발생 시 재시도하는 데코레이터.
    
    Usage:
        @retry_on_deadlock(max_retries=3)
        def process_order(db, order_id):
            # 주문 처리 로직
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except SQLAlchemyError as e:
                    if "deadlock" in str(e).lower() and attempt < max_retries - 1:
                        logger.warning(f"Deadlock detected, retrying... (attempt {attempt + 1})")
                        time.sleep(delay * (attempt + 1))  # 점진적 백오프
                        continue
                    raise
            
        return wrapper
    return decorator