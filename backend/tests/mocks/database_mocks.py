"""
Mock implementations for database operations
"""
import asyncio
from typing import List, Dict, Any, Optional, Type, TypeVar
from unittest.mock import AsyncMock, Mock
from decimal import Decimal
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')


class MockDatabaseSession:
    """Mock database session for testing"""
    
    def __init__(self):
        self.data_store = {}
        self.committed = False
        self.rolled_back = False
        self._transaction_active = True
        
    def add(self, instance):
        """Mock add operation"""
        if not hasattr(instance, 'id') or instance.id is None:
            instance.id = str(uuid.uuid4())
        
        table_name = instance.__class__.__name__.lower()
        if table_name not in self.data_store:
            self.data_store[table_name] = {}
        
        self.data_store[table_name][instance.id] = instance
        
    def delete(self, instance):
        """Mock delete operation"""
        table_name = instance.__class__.__name__.lower()
        if table_name in self.data_store and instance.id in self.data_store[table_name]:
            del self.data_store[table_name][instance.id]
    
    def commit(self):
        """Mock commit operation"""
        self.committed = True
        self._transaction_active = False
        
    def rollback(self):
        """Mock rollback operation"""
        self.rolled_back = True
        self._transaction_active = False
        self.data_store.clear()
        
    def refresh(self, instance):
        """Mock refresh operation"""
        # Update instance with latest data
        table_name = instance.__class__.__name__.lower()
        if table_name in self.data_store and instance.id in self.data_store[table_name]:
            stored_instance = self.data_store[table_name][instance.id]
            for key, value in stored_instance.__dict__.items():
                if not key.startswith('_'):
                    setattr(instance, key, value)
    
    def close(self):
        """Mock close operation"""
        self._transaction_active = False
        
    def query(self, model_class):
        """Mock query operation"""
        return MockQuery(model_class, self.data_store)
    
    def get(self, model_class, primary_key):
        """Mock get operation"""
        table_name = model_class.__name__.lower()
        if table_name in self.data_store and primary_key in self.data_store[table_name]:
            return self.data_store[table_name][primary_key]
        return None


class MockQuery:
    """Mock SQLAlchemy query object"""
    
    def __init__(self, model_class, data_store):
        self.model_class = model_class
        self.data_store = data_store
        self.table_name = model_class.__name__.lower()
        self._filters = []
        self._order_by_fields = []
        self._limit_value = None
        self._offset_value = None
        
    def filter(self, *criteria):
        """Mock filter operation"""
        self._filters.extend(criteria)
        return self
    
    def filter_by(self, **kwargs):
        """Mock filter_by operation"""
        self._filters.append(kwargs)
        return self
    
    def order_by(self, *fields):
        """Mock order_by operation"""
        self._order_by_fields.extend(fields)
        return self
    
    def limit(self, limit):
        """Mock limit operation"""
        self._limit_value = limit
        return self
    
    def offset(self, offset):
        """Mock offset operation"""
        self._offset_value = offset
        return self
    
    def all(self):
        """Mock all() operation"""
        if self.table_name not in self.data_store:
            return []
        
        items = list(self.data_store[self.table_name].values())
        
        # Apply filters (simplified)
        for filter_criteria in self._filters:
            if isinstance(filter_criteria, dict):
                items = [item for item in items 
                        if all(getattr(item, k, None) == v for k, v in filter_criteria.items())]
        
        # Apply ordering (simplified)
        if self._order_by_fields:
            # Simple sorting by first field
            field_name = str(self._order_by_fields[0]).split('.')[-1]
            items.sort(key=lambda x: getattr(x, field_name, 0))
        
        # Apply offset and limit
        if self._offset_value:
            items = items[self._offset_value:]
        if self._limit_value:
            items = items[:self._limit_value]
        
        return items
    
    def first(self):
        """Mock first() operation"""
        results = self.all()
        return results[0] if results else None
    
    def count(self):
        """Mock count() operation"""
        return len(self.all())
    
    def delete(self):
        """Mock delete() operation"""
        items_to_delete = self.all()
        for item in items_to_delete:
            if self.table_name in self.data_store and item.id in self.data_store[self.table_name]:
                del self.data_store[self.table_name][item.id]
        return len(items_to_delete)


class MockAsyncSession:
    """Mock async database session"""
    
    def __init__(self):
        self.sync_session = MockDatabaseSession()
        
    async def add(self, instance):
        """Mock async add"""
        self.sync_session.add(instance)
        
    async def delete(self, instance):
        """Mock async delete"""
        self.sync_session.delete(instance)
        
    async def commit(self):
        """Mock async commit"""
        self.sync_session.commit()
        
    async def rollback(self):
        """Mock async rollback"""
        self.sync_session.rollback()
        
    async def refresh(self, instance):
        """Mock async refresh"""
        self.sync_session.refresh(instance)
        
    async def close(self):
        """Mock async close"""
        self.sync_session.close()
        
    async def get(self, model_class, primary_key):
        """Mock async get"""
        return self.sync_session.get(model_class, primary_key)
    
    def query(self, model_class):
        """Mock query (returns sync query)"""
        return self.sync_session.query(model_class)
    
    async def execute(self, statement):
        """Mock async execute"""
        # Return mock result
        return MockResult([])
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.close()


class MockResult:
    """Mock SQLAlchemy result object"""
    
    def __init__(self, data):
        self.data = data
        
    def fetchall(self):
        """Mock fetchall"""
        return self.data
    
    def fetchone(self):
        """Mock fetchone"""
        return self.data[0] if self.data else None
    
    def scalars(self):
        """Mock scalars"""
        return MockScalarResult(self.data)


class MockScalarResult:
    """Mock scalar result"""
    
    def __init__(self, data):
        self.data = data
        
    def all(self):
        """Mock all"""
        return self.data
    
    def first(self):
        """Mock first"""
        return self.data[0] if self.data else None


class MockCRUDOperations:
    """Mock CRUD operations for testing"""
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
        self.data_store = {}
        
    async def create(self, db: AsyncSession, obj_in: Dict[str, Any]) -> T:
        """Mock create operation"""
        instance = self.model_class(**obj_in)
        if not hasattr(instance, 'id') or instance.id is None:
            instance.id = str(uuid.uuid4())
        
        instance.created_at = datetime.utcnow()
        instance.updated_at = datetime.utcnow()
        
        self.data_store[instance.id] = instance
        return instance
    
    async def get(self, db: AsyncSession, id: str) -> Optional[T]:
        """Mock get operation"""
        return self.data_store.get(id)
    
    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[T]:
        """Mock get_multi operation"""
        items = list(self.data_store.values())
        return items[skip:skip + limit]
    
    async def update(self, db: AsyncSession, *, db_obj: T, obj_in: Dict[str, Any]) -> T:
        """Mock update operation"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.utcnow()
        self.data_store[db_obj.id] = db_obj
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: str) -> T:
        """Mock delete operation"""
        obj = self.data_store.get(id)
        if obj:
            del self.data_store[id]
        return obj
    
    async def get_by_field(self, db: AsyncSession, field: str, value: Any) -> Optional[T]:
        """Mock get by field operation"""
        for item in self.data_store.values():
            if getattr(item, field, None) == value:
                return item
        return None
    
    async def search(self, db: AsyncSession, **filters) -> List[T]:
        """Mock search operation"""
        results = []
        for item in self.data_store.values():
            match = True
            for field, value in filters.items():
                if getattr(item, field, None) != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results
    
    async def count(self, db: AsyncSession, **filters) -> int:
        """Mock count operation"""
        results = await self.search(db, **filters)
        return len(results)
    
    async def exists(self, db: AsyncSession, **filters) -> bool:
        """Mock exists operation"""
        count = await self.count(db, **filters)
        return count > 0


# Mock Model Classes for Testing
class MockProduct:
    """Mock Product model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name', 'Test Product')
        self.description = kwargs.get('description', 'Test Description')
        self.price = kwargs.get('price', Decimal('10000'))
        self.cost = kwargs.get('cost', Decimal('5000'))
        self.sku = kwargs.get('sku', 'TEST-SKU')
        self.category = kwargs.get('category', 'Test Category')
        self.stock_quantity = kwargs.get('stock_quantity', 100)
        self.status = kwargs.get('status', 'active')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())


class MockUser:
    """Mock User model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('username', 'testuser')
        self.email = kwargs.get('email', 'test@example.com')
        self.hashed_password = kwargs.get('hashed_password', 'hashed_password')
        self.full_name = kwargs.get('full_name', 'Test User')
        self.is_active = kwargs.get('is_active', True)
        self.is_superuser = kwargs.get('is_superuser', False)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())


class MockOrder:
    """Mock Order model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.order_number = kwargs.get('order_number', 'TEST-ORDER-001')
        self.user_id = kwargs.get('user_id')
        self.platform = kwargs.get('platform', 'coupang')
        self.total_amount = kwargs.get('total_amount', Decimal('25000'))
        self.status = kwargs.get('status', 'pending')
        self.payment_status = kwargs.get('payment_status', 'paid')
        self.customer_name = kwargs.get('customer_name', 'Test Customer')
        self.customer_email = kwargs.get('customer_email', 'customer@example.com')
        self.order_date = kwargs.get('order_date', datetime.utcnow())
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())


# Factory Functions for Mock Data
def create_mock_product_crud():
    """Create mock product CRUD operations"""
    return MockCRUDOperations(MockProduct)


def create_mock_user_crud():
    """Create mock user CRUD operations"""
    return MockCRUDOperations(MockUser)


def create_mock_order_crud():
    """Create mock order CRUD operations"""
    return MockCRUDOperations(MockOrder)