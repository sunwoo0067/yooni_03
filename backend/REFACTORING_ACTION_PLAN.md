# Prioritized Refactoring Action Plan

## Week 1: Critical Security & Stability Fixes

### Day 1-2: Security Vulnerabilities

#### 1. Fix Pickle Deserialization (CRITICAL)

**File**: `backend/app/core/cache_utils.py`
```python
# BEFORE (Vulnerable):
import pickle

def serialize_value(value):
    return pickle.dumps(value)

def deserialize_value(data):
    return pickle.loads(data)  # RCE vulnerability!

# AFTER (Secure):
import json
from typing import Any
from datetime import datetime, date
from decimal import Decimal

class SecureJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

def serialize_value(value: Any) -> bytes:
    """Safely serialize value to JSON bytes."""
    return json.dumps(value, cls=SecureJSONEncoder).encode('utf-8')

def deserialize_value(data: bytes) -> Any:
    """Safely deserialize JSON bytes to value."""
    return json.loads(data.decode('utf-8'))
```

#### 2. Remove Unsafe Eval

**File**: `backend/app/services/automation/product_status_automation.py`
```python
# BEFORE (Unsafe):
def evaluate_rule(rule_expression: str, context: dict):
    def safe_eval(node):  # Not actually safe!
        # Custom eval implementation
    return eval(compile(rule_expression, '<string>', 'eval'))

# AFTER (Safe):
from simpleeval import simple_eval

SAFE_FUNCTIONS = {
    'min': min,
    'max': max,
    'abs': abs,
    'round': round,
}

SAFE_NAMES = {
    'true': True,
    'false': False,
    'null': None,
}

def evaluate_rule(rule_expression: str, context: dict):
    """Safely evaluate rule expressions."""
    try:
        return simple_eval(
            rule_expression,
            names={**context, **SAFE_NAMES},
            functions=SAFE_FUNCTIONS
        )
    except Exception as e:
        logger.error(f"Rule evaluation failed: {e}")
        return False
```

### Day 3-4: Database Connection Consolidation

#### 3. Single Database Manager

**Create**: `backend/app/core/database_manager.py`
```python
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """Unified database connection manager."""
    
    def __init__(self):
        self._engine = None
        self._async_engine = None
        self._sessionmaker = None
        self._async_sessionmaker = None
    
    def initialize(self):
        """Initialize database engines and session makers."""
        # Sync engine
        pool_class = NullPool if settings.DATABASE_URL.startswith("sqlite") else QueuePool
        self._engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            poolclass=pool_class,
            pool_size=settings.DATABASE_POOL_SIZE if pool_class == QueuePool else None,
            max_overflow=settings.DATABASE_MAX_OVERFLOW if pool_class == QueuePool else None,
        )
        
        # Async engine (if supported)
        if settings.DATABASE_URL.startswith("postgresql"):
            async_url = settings.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            self._async_engine = create_async_engine(
                async_url,
                echo=settings.DATABASE_ECHO,
                pool_pre_ping=True,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
            )
            self._async_sessionmaker = async_sessionmaker(
                self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        
        self._sessionmaker = sessionmaker(
            self._engine,
            class_=Session,
            expire_on_commit=False,
        )
        
        logger.info("Database manager initialized")
    
    @property
    def engine(self):
        """Get sync engine."""
        if not self._engine:
            self.initialize()
        return self._engine
    
    @property
    def async_engine(self):
        """Get async engine."""
        if not self._async_engine:
            self.initialize()
        return self._async_engine
    
    def get_session(self) -> Session:
        """Get sync database session."""
        if not self._sessionmaker:
            self.initialize()
        return self._sessionmaker()
    
    async def get_async_session(self) -> AsyncSession:
        """Get async database session."""
        if not self._async_sessionmaker:
            self.initialize()
        return self._async_sessionmaker()
    
    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async session context manager."""
        async with self._async_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close all connections."""
        if self._engine:
            self._engine.dispose()
        if self._async_engine:
            await self._async_engine.dispose()

# Global instance
db_manager = DatabaseManager()

# FastAPI dependencies
def get_db() -> Generator[Session, None, None]:
    """Dependency for sync database session."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for async database session."""
    async with db_manager.async_session() as session:
        yield session
```

### Day 5: Remove Duplicate Endpoints

#### 4. Consolidate Order Endpoints

**Remove**: `orders_v2.py`, `orders_real.py`
**Update**: `backend/app/api/v1/endpoints/orders.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database_manager import get_async_db
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderListResponse
from app.services.core.order_service import OrderService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """Create a new order."""
    try:
        order = await order_service.create_order(
            db=db,
            order_data=order_data,
            user_id=current_user.id
        )
        return OrderResponse.from_orm(order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=OrderListResponse)
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """List orders with pagination and filtering."""
    orders, total = await order_service.list_orders(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status
    )
    return OrderListResponse(
        orders=[OrderResponse.from_orm(order) for order in orders],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """Get order by ID."""
    order = await order_service.get_order(
        db=db,
        order_id=order_id,
        user_id=current_user.id
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return OrderResponse.from_orm(order)

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """Update order."""
    order = await order_service.update_order(
        db=db,
        order_id=order_id,
        order_update=order_update,
        user_id=current_user.id
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return OrderResponse.from_orm(order)

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """Cancel an order."""
    success = await order_service.cancel_order(
        db=db,
        order_id=order_id,
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to cancel order"
        )
    return {"message": "Order cancelled successfully"}
```

## Week 2: Service Layer Refactoring

### Day 1-2: Create Service Structure

#### 5. Implement Domain-Driven Service Structure

**Create directory structure**:
```bash
mkdir -p backend/app/services/core/{product,order,inventory,user}
mkdir -p backend/app/services/integration/{wholesaler,marketplace,payment}
mkdir -p backend/app/services/infrastructure/{cache,messaging,monitoring}
mkdir -p backend/app/services/application/{sourcing,pricing,fulfillment}
```

#### 6. Base Service Pattern

**Create**: `backend/app/services/core/base_service.py`
```python
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.base import Base
from app.core.logging import get_logger

ModelType = TypeVar("ModelType", bound=Base)

class BaseService(Generic[ModelType]):
    """Base service with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.logger = get_logger(f"{__name__}.{model.__name__}")
    
    async def create(
        self,
        db: AsyncSession,
        **kwargs
    ) -> ModelType:
        """Create a new record."""
        try:
            instance = self.model(**kwargs)
            db.add(instance)
            await db.commit()
            await db.refresh(instance)
            return instance
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error creating {self.model.__name__}: {e}")
            raise
    
    async def get(
        self,
        db: AsyncSession,
        id: Any,
        load_relationships: List[str] = None
    ) -> Optional[ModelType]:
        """Get record by ID."""
        query = select(self.model).where(self.model.id == id)
        
        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Dict[str, Any] = None,
        load_relationships: List[str] = None
    ) -> tuple[List[ModelType], int]:
        """List records with pagination."""
        query = select(self.model)
        
        if filters:
            for key, value in filters.items():
                query = query.where(getattr(self.model, key) == value)
        
        if load_relationships:
            for rel in load_relationships:
                query = query.options(selectinload(getattr(self.model, rel)))
        
        # Get total count
        count_query = select(func.count()).select_from(self.model)
        if filters:
            for key, value in filters.items():
                count_query = count_query.where(getattr(self.model, key) == value)
        
        total = await db.scalar(count_query)
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()
        
        return items, total
    
    async def update(
        self,
        db: AsyncSession,
        id: Any,
        **kwargs
    ) -> Optional[ModelType]:
        """Update a record."""
        try:
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(**kwargs)
                .returning(self.model)
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.scalar_one_or_none()
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error updating {self.model.__name__}: {e}")
            raise
    
    async def delete(
        self,
        db: AsyncSession,
        id: Any
    ) -> bool:
        """Delete a record."""
        try:
            stmt = delete(self.model).where(self.model.id == id)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise
```

### Day 3-4: Consolidate Product Services

#### 7. Unified Product Service

**Create**: `backend/app/services/core/product/product_service.py`
```python
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.services.core.base_service import BaseService
from app.models.product import Product, ProductStatus
from app.schemas.product import ProductCreate, ProductUpdate
from app.core.exceptions import BusinessError
from app.core.cache import cache_service

class ProductService(BaseService[Product]):
    """Unified product service handling all product operations."""
    
    def __init__(self):
        super().__init__(Product)
        self.cache_key_prefix = "product"
    
    async def create_product(
        self,
        db: AsyncSession,
        product_data: ProductCreate,
        user_id: int
    ) -> Product:
        """Create a new product with validation."""
        # Validate SKU uniqueness
        existing = await self.get_by_sku(db, product_data.sku)
        if existing:
            raise BusinessError(
                message="Product with this SKU already exists",
                code="PRODUCT_SKU_EXISTS"
            )
        
        # Validate pricing
        if product_data.cost >= product_data.price:
            raise BusinessError(
                message="Product price must be greater than cost",
                code="INVALID_PRICING"
            )
        
        # Create product
        product = await self.create(
            db=db,
            **product_data.dict(),
            user_id=user_id,
            status=ProductStatus.DRAFT
        )
        
        # Invalidate cache
        await self._invalidate_cache()
        
        return product
    
    async def get_by_sku(
        self,
        db: AsyncSession,
        sku: str
    ) -> Optional[Product]:
        """Get product by SKU."""
        cache_key = f"{self.cache_key_prefix}:sku:{sku}"
        
        # Try cache first
        cached = await cache_service.get(cache_key)
        if cached:
            return Product(**cached)
        
        # Query database
        query = select(Product).where(Product.sku == sku)
        result = await db.execute(query)
        product = result.scalar_one_or_none()
        
        # Cache result
        if product:
            await cache_service.set(
                cache_key,
                product.dict(),
                ttl=300  # 5 minutes
            )
        
        return product
    
    async def search_products(
        self,
        db: AsyncSession,
        query: str,
        filters: Dict[str, Any] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Product], int]:
        """Search products with filters."""
        stmt = select(Product)
        
        # Text search
        if query:
            stmt = stmt.where(
                or_(
                    Product.name.ilike(f"%{query}%"),
                    Product.sku.ilike(f"%{query}%"),
                    Product.description.ilike(f"%{query}%")
                )
            )
        
        # Apply filters
        if filters:
            if filters.get("status"):
                stmt = stmt.where(Product.status == filters["status"])
            if filters.get("min_price"):
                stmt = stmt.where(Product.price >= filters["min_price"])
            if filters.get("max_price"):
                stmt = stmt.where(Product.price <= filters["max_price"])
            if filters.get("category_id"):
                stmt = stmt.where(Product.category_id == filters["category_id"])
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await db.scalar(count_stmt)
        
        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(Product.created_at.desc())
        result = await db.execute(stmt)
        products = result.scalars().all()
        
        return products, total
    
    async def calculate_pricing(
        self,
        product: Product,
        margin: Decimal = Decimal("0.3")
    ) -> Dict[str, Decimal]:
        """Calculate product pricing with margin."""
        base_price = product.cost * (1 + margin)
        
        # Apply pricing rules
        if product.category and product.category.min_margin:
            min_price = product.cost * (1 + product.category.min_margin)
            base_price = max(base_price, min_price)
        
        # Competition-based pricing
        if product.competitor_price:
            competitive_price = product.competitor_price * Decimal("0.95")
            base_price = min(base_price, competitive_price)
        
        return {
            "base_price": base_price,
            "sale_price": base_price * Decimal("0.9"),  # 10% discount
            "min_price": product.cost * Decimal("1.1"),  # Min 10% margin
            "recommended_price": base_price
        }
    
    async def _invalidate_cache(self):
        """Invalidate product caches."""
        await cache_service.delete_pattern(f"{self.cache_key_prefix}:*")
```

### Day 5: Consolidate Wholesaler APIs

#### 8. Merge Fixed Versions

**Update**: `backend/app/services/integration/wholesaler/ownerclan.py`
```python
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from decimal import Decimal

from app.services.integration.wholesaler.base import BaseWholesaler
from app.core.config import settings
from app.core.logging import get_logger
from app.models.wholesaler import WholesalerType

logger = get_logger(__name__)

class OwnerClanAPI(BaseWholesaler):
    """OwnerClan wholesaler integration with all fixes applied."""
    
    def __init__(self):
        super().__init__(WholesalerType.OWNERCLAN)
        self.base_url = "https://ownerclan.com/api/v1"
        self.graphql_url = f"{self.base_url}/graphql"
        self.token = None
        self.token_expires = None
    
    async def authenticate(self) -> bool:
        """Authenticate with OwnerClan API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/token",
                    json={
                        "username": settings.OWNERCLAN_USERNAME,
                        "password": settings.OWNERCLAN_PASSWORD.get_secret_value()
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Handle both JSON and plain text responses
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        data = response.json()
                        self.token = data.get("access_token")
                    else:
                        # Plain text token (fixed version)
                        self.token = response.text.strip()
                    
                    self.token_expires = datetime.now().timestamp() + 3600
                    logger.info("OwnerClan authentication successful")
                    return True
                else:
                    logger.error(f"OwnerClan auth failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"OwnerClan auth error: {e}")
            return False
    
    async def fetch_products(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch products from OwnerClan."""
        if not await self._ensure_authenticated():
            return []
        
        query = """
        query GetProducts($first: Int!, $category: String) {
            products(first: $first, category: $category) {
                edges {
                    node {
                        id
                        name
                        sku
                        price
                        cost
                        stock
                        description
                        category
                        images
                        attributes
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        
        variables = {
            "first": limit,
            "category": category
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.graphql_url,
                    json={"query": query, "variables": variables},
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and "products" in data["data"]:
                        products = []
                        for edge in data["data"]["products"]["edges"]:
                            product = self._transform_product(edge["node"])
                            products.append(product)
                        return products
                    else:
                        logger.error(f"Invalid response structure: {data}")
                        return []
                else:
                    logger.error(f"Failed to fetch products: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching OwnerClan products: {e}")
            return []
    
    def _transform_product(self, raw_product: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OwnerClan product to standard format."""
        return {
            "source": self.wholesaler_type.value,
            "source_id": raw_product.get("id"),
            "sku": raw_product.get("sku"),
            "name": raw_product.get("name"),
            "description": raw_product.get("description", ""),
            "cost": Decimal(str(raw_product.get("cost", 0))),
            "price": Decimal(str(raw_product.get("price", 0))),
            "stock": raw_product.get("stock", 0),
            "category": raw_product.get("category"),
            "images": raw_product.get("images", []),
            "attributes": raw_product.get("attributes", {}),
            "is_active": raw_product.get("stock", 0) > 0,
            "collected_at": datetime.now()
        }
    
    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid token."""
        if not self.token or datetime.now().timestamp() >= self.token_expires:
            return await self.authenticate()
        return True
```

## Week 3: Performance & Testing

### Day 1-2: Database Optimization

#### 9. Add Indexes and Query Optimization

**Create migration**: `backend/alembic/versions/xxx_add_performance_indexes.py`
```python
"""Add performance indexes

Revision ID: xxx
Revises: yyy
Create Date: 2024-xx-xx

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Product indexes
    op.create_index('idx_product_sku', 'products', ['sku'])
    op.create_index('idx_product_status', 'products', ['status'])
    op.create_index('idx_product_created', 'products', ['created_at'])
    op.create_index('idx_product_search', 'products', ['name', 'sku'])
    
    # Order indexes
    op.create_index('idx_order_user_status', 'orders', ['user_id', 'status'])
    op.create_index('idx_order_created', 'orders', ['created_at'])
    op.create_index('idx_order_number', 'orders', ['order_number'], unique=True)
    
    # Platform listing indexes
    op.create_index('idx_listing_platform_sku', 'platform_listings', ['platform_type', 'platform_sku'])
    op.create_index('idx_listing_product', 'platform_listings', ['product_id'])
    
    # Inventory indexes
    op.create_index('idx_inventory_product_warehouse', 'inventory_items', ['product_id', 'warehouse_id'])
    op.create_index('idx_inventory_available', 'inventory_items', ['available_quantity'])

def downgrade():
    # Remove all indexes
    op.drop_index('idx_product_sku', 'products')
    op.drop_index('idx_product_status', 'products')
    op.drop_index('idx_product_created', 'products')
    op.drop_index('idx_product_search', 'products')
    op.drop_index('idx_order_user_status', 'orders')
    op.drop_index('idx_order_created', 'orders')
    op.drop_index('idx_order_number', 'orders')
    op.drop_index('idx_listing_platform_sku', 'platform_listings')
    op.drop_index('idx_listing_product', 'platform_listings')
    op.drop_index('idx_inventory_product_warehouse', 'inventory_items')
    op.drop_index('idx_inventory_available', 'inventory_items')
```

### Day 3-4: Implement Proper Caching

#### 10. Centralized Cache Service

**Update**: `backend/app/services/infrastructure/cache/cache_service.py`
```python
from typing import Any, Optional, Callable, TypeVar, Union
from datetime import timedelta
import json
import hashlib
from functools import wraps

from app.core.redis_client import get_redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

class CacheService:
    """Centralized caching service with proper invalidation."""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.default_ttl = 300  # 5 minutes
    
    async def get(
        self,
        key: str,
        deserializer: Callable[[str], T] = json.loads
    ) -> Optional[T]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value:
                return deserializer(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serializer: Callable[[Any], str] = json.dumps
    ) -> bool:
        """Set value in cache."""
        try:
            ttl = ttl or self.default_ttl
            serialized = serializer(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl: Optional[int] = None
    ) -> T:
        """Get from cache or compute and cache."""
        # Try to get from cache
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Compute value
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        
        # Cache it
        await self.set(key, value, ttl)
        
        return value
    
    def cached(
        self,
        key_prefix: str,
        ttl: Optional[int] = None,
        key_builder: Optional[Callable] = None
    ):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default key builder
                    key_parts = [key_prefix, func.__name__]
                    if args:
                        key_parts.extend(str(arg) for arg in args)
                    if kwargs:
                        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = ":".join(key_parts)
                
                # Get or compute
                return await self.get_or_set(
                    cache_key,
                    lambda: func(*args, **kwargs),
                    ttl
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we need to run in event loop
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(async_wrapper(*args, **kwargs))
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator

# Global cache service instance
cache_service = CacheService()

# Example usage in service
class ProductService:
    @cache_service.cached(key_prefix="product", ttl=300)
    async def get_product(self, product_id: int):
        # This will be cached for 5 minutes
        return await self.db.query(Product).filter(Product.id == product_id).first()
```

### Day 5: Add Comprehensive Tests

#### 11. Test Structure Setup

**Create**: `backend/tests/conftest.py`
```python
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.models.base import Base
from app.core.config import settings
from app.core.database_manager import db_manager
from app.models.user import User
from app.core.security import create_access_token

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[db_manager.get_async_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers."""
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}

# Test data factories
@pytest.fixture
def product_data():
    """Sample product data."""
    return {
        "name": "Test Product",
        "sku": "TEST-001",
        "description": "Test product description",
        "cost": "10.00",
        "price": "15.00",
        "stock": 100,
        "category_id": 1
    }

@pytest.fixture
def order_data():
    """Sample order data."""
    return {
        "items": [
            {
                "product_id": 1,
                "quantity": 2,
                "price": "15.00"
            }
        ],
        "shipping_address": {
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
            "country": "US"
        },
        "payment_method": "credit_card"
    }
```

#### 12. Service Tests

**Create**: `backend/tests/unit/services/test_product_service.py`
```python
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core.product.product_service import ProductService
from app.schemas.product import ProductCreate
from app.core.exceptions import BusinessError

class TestProductService:
    """Test product service functionality."""
    
    @pytest.fixture
    def product_service(self):
        return ProductService()
    
    @pytest.mark.asyncio
    async def test_create_product_success(
        self,
        db_session: AsyncSession,
        product_service: ProductService,
        product_data: dict
    ):
        """Test successful product creation."""
        # Create product
        product = await product_service.create_product(
            db=db_session,
            product_data=ProductCreate(**product_data),
            user_id=1
        )
        
        # Assertions
        assert product.id is not None
        assert product.name == product_data["name"]
        assert product.sku == product_data["sku"]
        assert product.status == "draft"
    
    @pytest.mark.asyncio
    async def test_create_product_duplicate_sku(
        self,
        db_session: AsyncSession,
        product_service: ProductService,
        product_data: dict
    ):
        """Test product creation with duplicate SKU."""
        # Create first product
        await product_service.create_product(
            db=db_session,
            product_data=ProductCreate(**product_data),
            user_id=1
        )
        
        # Try to create duplicate
        with pytest.raises(BusinessError) as exc:
            await product_service.create_product(
                db=db_session,
                product_data=ProductCreate(**product_data),
                user_id=1
            )
        
        assert exc.value.code == "PRODUCT_SKU_EXISTS"
    
    @pytest.mark.asyncio
    async def test_calculate_pricing(
        self,
        product_service: ProductService
    ):
        """Test pricing calculation."""
        from app.models.product import Product
        
        # Create mock product
        product = Product(
            name="Test Product",
            cost=Decimal("10.00"),
            competitor_price=Decimal("20.00")
        )
        
        # Calculate pricing
        pricing = await product_service.calculate_pricing(
            product=product,
            margin=Decimal("0.3")
        )
        
        # Assertions
        assert pricing["base_price"] == Decimal("13.00")
        assert pricing["min_price"] == Decimal("11.00")
        assert pricing["sale_price"] == Decimal("11.70")
    
    @pytest.mark.asyncio
    async def test_search_products(
        self,
        db_session: AsyncSession,
        product_service: ProductService
    ):
        """Test product search functionality."""
        # Create test products
        products_data = [
            {"name": "Red Shirt", "sku": "SHIRT-001", "cost": "10", "price": "20"},
            {"name": "Blue Pants", "sku": "PANTS-001", "cost": "15", "price": "30"},
            {"name": "Red Hat", "sku": "HAT-001", "cost": "5", "price": "10"},
        ]
        
        for data in products_data:
            await product_service.create_product(
                db=db_session,
                product_data=ProductCreate(**data),
                user_id=1
            )
        
        # Search for "Red" products
        results, total = await product_service.search_products(
            db=db_session,
            query="Red",
            skip=0,
            limit=10
        )
        
        assert total == 2
        assert len(results) == 2
        assert all("Red" in r.name for r in results)
```

## Week 4: Documentation & Monitoring

### Day 1-2: API Documentation

#### 13. Enhanced API Documentation

**Update**: `backend/app/api/v1/endpoints/products.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

router = APIRouter(prefix="/products", tags=["products"])

@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="""
    Create a new product with the following validations:
    - SKU must be unique
    - Price must be greater than cost
    - Stock quantity must be non-negative
    
    The product will be created in DRAFT status and must be activated separately.
    """,
    responses={
        201: {"description": "Product created successfully"},
        400: {"description": "Invalid product data"},
        409: {"description": "Product with this SKU already exists"},
    }
)
async def create_product(
    product_data: ProductCreate = Body(
        ...,
        example={
            "name": "Wireless Mouse",
            "sku": "MOUSE-001",
            "description": "Ergonomic wireless mouse with 3-year battery life",
            "cost": "15.00",
            "price": "29.99",
            "stock": 100,
            "category_id": 1,
            "images": ["https://example.com/mouse1.jpg"],
            "attributes": {
                "color": "Black",
                "connectivity": "Bluetooth 5.0",
                "battery": "AA x 2"
            }
        }
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    product_service: ProductService = Depends(),
):
    """Create a new product."""
    # Implementation...
```

### Day 3-4: Monitoring Setup

#### 14. Metrics Collection

**Create**: `backend/app/services/infrastructure/monitoring/metrics_service.py`
```python
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Callable

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_users = Gauge(
    'active_users',
    'Number of active users'
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

order_processing_duration = Histogram(
    'order_processing_duration_seconds',
    'Order processing duration in seconds',
    ['order_type']
)

products_collected = Counter(
    'products_collected_total',
    'Total products collected',
    ['source']
)

api_errors = Counter(
    'api_errors_total',
    'Total API errors',
    ['endpoint', 'error_type']
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_key_prefix']
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_key_prefix']
)

# Decorator for timing functions
def track_time(metric: Histogram, labels: dict = None):
    """Track execution time of a function."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Usage example
class OrderService:
    @track_time(order_processing_duration, {"order_type": "standard"})
    async def process_order(self, order_data: dict):
        # Order processing logic
        pass
```

### Day 5: Final Integration

#### 15. Update Main Application

**Update**: `backend/main.py` (key sections)
```python
from prometheus_client import make_asgi_app
from app.services.infrastructure.monitoring.metrics_service import (
    http_requests_total,
    http_request_duration_seconds,
    db_connections_active
)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Update middleware to track metrics
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    """Track HTTP metrics."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Track metrics
    duration = time.time() - start_time
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# Health check with detailed status
@app.get("/health", response_model=HealthCheckResponse)
async def health_check(
    db: AsyncSession = Depends(get_async_db),
    redis: Redis = Depends(get_redis_client)
):
    """Comprehensive health check."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "checks": {}
    }
    
    # Database check
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": 5
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    try:
        await redis.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "response_time_ms": 2
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return health_status
```

## Conclusion

This action plan provides concrete steps to refactor the dropshipping project from its current state to a well-architected, maintainable system. Each week focuses on specific areas with clear deliverables and code examples.

The key improvements include:
1. **Security**: Eliminating critical vulnerabilities
2. **Architecture**: Clear service boundaries and responsibilities
3. **Performance**: Optimized queries and proper caching
4. **Quality**: Comprehensive testing and monitoring
5. **Maintainability**: Clean code and documentation

Following this plan will result in a production-ready codebase that can scale with business needs while remaining maintainable and secure.