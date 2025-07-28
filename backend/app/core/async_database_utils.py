"""
Async database utilities for safe asynchronous operations.
안전한 비동기 데이터베이스 작업을 위한 유틸리티.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional, Callable, Any, TypeVar, Type, List, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.exceptions import DatabaseError, NotFoundError
from app.core.logging_utils import get_logger

T = TypeVar('T')
logger = get_logger(__name__)


@asynccontextmanager
async def async_safe_transaction(
    db: AsyncSession, 
    operation_name: str = "async database operation"
):
    """
    안전한 비동기 트랜잭션 컨텍스트 매니저.
    
    Usage:
        async with async_safe_transaction(db, "create order") as session:
            order = Order(...)
            session.add(order)
            # 자동 커밋 또는 롤백
    """
    try:
        yield db
        await db.commit()
        logger.info(f"Async transaction committed: {operation_name}")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error in {operation_name}: {str(e)}")
        raise DatabaseError(
            message=f"Async database operation failed: {operation_name}",
            code="ASYNC_TRANSACTION_ERROR",
            details={"operation": operation_name, "error": str(e)}
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in {operation_name}: {str(e)}")
        raise


async def async_get_by_id(
    db: AsyncSession,
    model_class: Type[T],
    id: Any,
    load_relationships: Optional[List[str]] = None
) -> Optional[T]:
    """
    ID로 엔티티를 비동기로 조회.
    
    Args:
        db: Async database session
        model_class: SQLAlchemy model class
        id: Entity ID
        load_relationships: 즉시 로드할 관계 필드 목록
    
    Returns:
        찾은 엔티티 또는 None
    
    Example:
        user = await async_get_by_id(
            db, User, user_id, 
            load_relationships=["orders", "profile"]
        )
    """
    try:
        query = select(model_class).where(model_class.id == id)
        
        # 관계 즉시 로딩
        if load_relationships:
            for relationship in load_relationships:
                query = query.options(selectinload(getattr(model_class, relationship)))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching {model_class.__name__} by id {id}: {e}")
        raise DatabaseError(
            message=f"Failed to fetch {model_class.__name__}",
            code="FETCH_ERROR",
            details={"model": model_class.__name__, "id": str(id)}
        )


async def async_get_or_404(
    db: AsyncSession,
    model_class: Type[T],
    id: Any,
    load_relationships: Optional[List[str]] = None
) -> T:
    """
    ID로 엔티티 조회, 없으면 NotFoundError 발생.
    
    Example:
        order = await async_get_or_404(db, Order, order_id)
    """
    entity = await async_get_by_id(db, model_class, id, load_relationships)
    if not entity:
        raise NotFoundError(
            message=f"{model_class.__name__} not found",
            code="NOT_FOUND",
            details={"model": model_class.__name__, "id": str(id)}
        )
    return entity


async def async_paginate(
    db: AsyncSession,
    query,
    page: int = 1,
    per_page: int = 20
) -> dict:
    """
    비동기 페이지네이션.
    
    Returns:
        {
            "items": List[T],
            "total": int,
            "page": int,
            "per_page": int,
            "pages": int
        }
    """
    # 전체 개수 조회
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 페이지네이션 적용
    offset = (page - 1) * per_page
    items_query = query.offset(offset).limit(per_page)
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page  # 올림
    }


async def async_bulk_create(
    db: AsyncSession,
    model_class: Type[T],
    data_list: List[dict],
    batch_size: int = 100
) -> List[T]:
    """
    대량 데이터를 비동기로 생성.
    
    Args:
        db: Async database session
        model_class: SQLAlchemy model class
        data_list: 생성할 데이터 리스트
        batch_size: 배치 크기
    
    Returns:
        생성된 엔티티 리스트
    """
    created_entities = []
    
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i + batch_size]
        
        async with async_safe_transaction(db, f"bulk create batch {i//batch_size + 1}"):
            entities = [model_class(**data) for data in batch]
            db.add_all(entities)
            await db.flush()
            created_entities.extend(entities)
            
    logger.info(f"Bulk created {len(created_entities)} {model_class.__name__} entities")
    return created_entities


async def async_bulk_update(
    db: AsyncSession,
    model_class: Type[T],
    updates: List[dict],
    batch_size: int = 100
) -> int:
    """
    대량 업데이트를 비동기로 수행.
    
    Args:
        updates: [{"id": 1, "field": "value"}, ...]
    
    Returns:
        업데이트된 레코드 수
    """
    updated_count = 0
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        
        async with async_safe_transaction(db, f"bulk update batch {i//batch_size + 1}"):
            for update_data in batch:
                id = update_data.pop("id")
                stmt = (
                    update(model_class)
                    .where(model_class.id == id)
                    .values(**update_data)
                )
                result = await db.execute(stmt)
                updated_count += result.rowcount
                
    logger.info(f"Bulk updated {updated_count} {model_class.__name__} records")
    return updated_count


class AsyncRepository(Generic[T]):
    """
    비동기 리포지토리 베이스 클래스.
    
    Usage:
        class UserRepository(AsyncRepository[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(db, User)
                
            async def find_by_email(self, email: str) -> Optional[User]:
                query = select(self.model_class).where(
                    self.model_class.email == email
                )
                result = await self.db.execute(query)
                return result.scalar_one_or_none()
    """
    
    def __init__(self, db: AsyncSession, model_class: Type[T]):
        self.db = db
        self.model_class = model_class
        self.logger = get_logger(f"{model_class.__name__}Repository")
        
    async def get_by_id(
        self, 
        id: Any, 
        load_relationships: Optional[List[str]] = None
    ) -> Optional[T]:
        """ID로 조회"""
        return await async_get_by_id(
            self.db, self.model_class, id, load_relationships
        )
        
    async def get_or_404(
        self, 
        id: Any, 
        load_relationships: Optional[List[str]] = None
    ) -> T:
        """ID로 조회, 없으면 404"""
        return await async_get_or_404(
            self.db, self.model_class, id, load_relationships
        )
        
    async def create(self, **kwargs) -> T:
        """새 엔티티 생성"""
        async with async_safe_transaction(self.db, f"create {self.model_class.__name__}"):
            entity = self.model_class(**kwargs)
            self.db.add(entity)
            await self.db.flush()
            return entity
            
    async def update(self, entity: T, **kwargs) -> T:
        """엔티티 업데이트"""
        async with async_safe_transaction(self.db, f"update {self.model_class.__name__}"):
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            await self.db.flush()
            return entity
            
    async def delete(self, entity: T) -> bool:
        """엔티티 삭제"""
        async with async_safe_transaction(self.db, f"delete {self.model_class.__name__}"):
            await self.db.delete(entity)
            return True
            
    async def find_all(
        self, 
        filters: Optional[dict] = None,
        order_by: Optional[Any] = None,
        limit: Optional[int] = None
    ) -> List[T]:
        """조건에 맞는 모든 엔티티 조회"""
        query = select(self.model_class)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
                    
        if order_by is not None:
            query = query.order_by(order_by)
            
        if limit:
            query = query.limit(limit)
            
        result = await self.db.execute(query)
        return result.scalars().all()


# 유용한 헬퍼 함수들
async def async_exists(
    db: AsyncSession,
    model_class: Type[T],
    **filters
) -> bool:
    """
    조건에 맞는 레코드가 존재하는지 확인.
    
    Example:
        exists = await async_exists(db, User, email="test@example.com")
    """
    query = select(model_class.id)
    for key, value in filters.items():
        query = query.where(getattr(model_class, key) == value)
    query = query.limit(1)
    
    result = await db.execute(query)
    return result.first() is not None


from sqlalchemy import func  # 상단에 추가

async def async_count(
    db: AsyncSession,
    model_class: Type[T],
    **filters
) -> int:
    """
    조건에 맞는 레코드 수 조회.
    
    Example:
        count = await async_count(db, Order, status="pending")
    """
    query = select(func.count(model_class.id))
    for key, value in filters.items():
        query = query.where(getattr(model_class, key) == value)
        
    result = await db.execute(query)
    return result.scalar()