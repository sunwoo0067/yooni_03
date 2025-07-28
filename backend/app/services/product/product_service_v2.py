"""
Refactored Product Service with safe patterns.
안전한 패턴이 적용된 리팩토링된 상품 서비스.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.constants import ProductStatus, Limits, CacheKeys
from app.core.exceptions import NotFoundError, ValidationError, ServiceException
from app.core.async_database_utils import (
    AsyncRepository, 
    async_safe_transaction,
    async_paginate,
    async_exists
)
from app.core.cache_utils import CacheService, cache_key_wrapper
from app.core.logging_utils import get_logger, log_execution_time, LogContext
from app.core.validators import SafeValidator
from app.models.product import Product, ProductVariant
from app.services.base_service import AsyncBaseService


class ProductRepository(AsyncRepository[Product]):
    """상품 리포지토리"""
    
    async def find_by_sku(self, sku: str) -> Optional[Product]:
        """SKU로 상품 조회"""
        query = select(self.model_class).where(
            self.model_class.sku == sku
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
        
    async def find_active_products(
        self, 
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        page: int = 1,
        per_page: int = 20
    ) -> dict:
        """활성 상품 조회 (페이지네이션)"""
        query = select(self.model_class).where(
            self.model_class.status == ProductStatus.ACTIVE.value
        )
        
        if category:
            query = query.where(self.model_class.category == category)
            
        if min_price is not None:
            query = query.where(self.model_class.price >= min_price)
            
        if max_price is not None:
            query = query.where(self.model_class.price <= max_price)
            
        query = query.order_by(self.model_class.created_at.desc())
        
        return await async_paginate(self.db, query, page, per_page)
        
    async def update_stock(
        self, 
        product_id: str, 
        quantity_change: int
    ) -> Optional[Product]:
        """재고 업데이트"""
        async with async_safe_transaction(self.db, "update product stock"):
            product = await self.get_by_id(product_id)
            if not product:
                return None
                
            new_quantity = product.stock_quantity + quantity_change
            if new_quantity < 0:
                raise ValidationError(
                    "Insufficient stock",
                    code="INSUFFICIENT_STOCK",
                    details={
                        "current_stock": product.stock_quantity,
                        "requested_change": quantity_change
                    }
                )
                
            product.stock_quantity = new_quantity
            
            # 재고 상태 자동 업데이트
            if new_quantity == 0:
                product.status = ProductStatus.OUT_OF_STOCK.value
            elif product.status == ProductStatus.OUT_OF_STOCK.value:
                product.status = ProductStatus.ACTIVE.value
                
            await self.db.flush()
            return product


class ProductCacheService(CacheService):
    """상품 캐시 서비스"""
    
    def __init__(self, cache_manager):
        super().__init__(cache_manager, "product", default_ttl=3600)
        
    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """캐시에서 상품 조회"""
        key = self.make_key("detail", product_id)
        return self.get(key)
        
    async def set_product(
        self, 
        product_id: str, 
        product_data: Dict[str, Any]
    ) -> bool:
        """상품 정보 캐싱"""
        key = self.make_key("detail", product_id)
        return self.set(key, product_data)
        
    async def invalidate_product(self, product_id: str) -> bool:
        """상품 캐시 무효화"""
        key = self.make_key("detail", product_id)
        return self.delete(key)
        
    async def get_category_products(
        self, 
        category: str, 
        page: int
    ) -> Optional[Dict[str, Any]]:
        """카테고리별 상품 목록 캐시 조회"""
        key = self.make_key("category", category, f"page_{page}")
        return self.get(key)
        
    async def set_category_products(
        self,
        category: str,
        page: int,
        data: Dict[str, Any]
    ) -> bool:
        """카테고리별 상품 목록 캐싱"""
        key = self.make_key("category", category, f"page_{page}")
        return self.set(key, data, ttl=600)  # 10분 캐싱


class ProductServiceV2(AsyncBaseService[Product]):
    """
    개선된 상품 서비스.
    - 비동기 DB 작업
    - 캐싱 전략
    - 표준화된 에러 처리
    - 구조화된 로깅
    """
    
    def __init__(
        self, 
        db: AsyncSession,
        cache_service: Optional[ProductCacheService] = None
    ):
        super().__init__(db, Product)
        self.repository = ProductRepository(db, Product)
        self.cache_service = cache_service
        self.logger = get_logger(self.__class__.__name__)
        
    @log_execution_time("get_product_detail")
    async def get_product_detail(
        self, 
        product_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """상품 상세 정보 조회"""
        # ID 검증
        validated_id = SafeValidator.validate_id(product_id, "product_id")
        
        # 캐시 조회
        if use_cache and self.cache_service:
            cached = await self.cache_service.get_product(validated_id)
            if cached:
                return cached
                
        # DB 조회
        product = await self.repository.get_or_404(
            validated_id,
            load_relationships=["variants", "images"]
        )
        
        # 응답 데이터 구성
        product_data = {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "price": float(product.price),
            "status": product.status,
            "stock_quantity": product.stock_quantity,
            "variants": [
                {
                    "id": str(v.id),
                    "name": v.name,
                    "price": float(v.price),
                    "stock": v.stock_quantity
                }
                for v in product.variants
            ] if hasattr(product, 'variants') else [],
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }
        
        # 캐싱
        if use_cache and self.cache_service:
            await self.cache_service.set_product(validated_id, product_data)
            
        return product_data
        
    async def search_products(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """상품 검색"""
        with LogContext(
            self.logger,
            operation="search_products",
            keyword=keyword,
            category=category,
            page=page
        ):
            # 페이지네이션 검증
            page, per_page = SafeValidator.validate_pagination(page, per_page)
            
            # 카테고리 캐시 확인
            cache_key = None
            if category and not keyword and not min_price and not max_price:
                if self.cache_service:
                    cached = await self.cache_service.get_category_products(
                        category, page
                    )
                    if cached:
                        return cached
                        
            # DB 검색
            result = await self.repository.find_active_products(
                category=category,
                min_price=min_price,
                max_price=max_price,
                page=page,
                per_page=per_page
            )
            
            # 응답 데이터 구성
            response = {
                "items": [
                    {
                        "id": str(p.id),
                        "sku": p.sku,
                        "name": p.name,
                        "category": p.category,
                        "price": float(p.price),
                        "status": p.status,
                        "stock_quantity": p.stock_quantity
                    }
                    for p in result["items"]
                ],
                "pagination": {
                    "total": result["total"],
                    "page": result["page"],
                    "per_page": result["per_page"],
                    "pages": result["pages"]
                }
            }
            
            # 카테고리 검색 결과 캐싱
            if category and not keyword and not min_price and not max_price:
                if self.cache_service:
                    await self.cache_service.set_category_products(
                        category, page, response
                    )
                    
            return response
            
    async def create_product(
        self,
        product_data: Dict[str, Any]
    ) -> Product:
        """새 상품 생성"""
        # 검증
        validated_data = self._validate_product_data(product_data)
        
        # SKU 중복 확인
        if await async_exists(self.db, Product, sku=validated_data["sku"]):
            raise ValidationError(
                "SKU already exists",
                code="DUPLICATE_SKU",
                details={"sku": validated_data["sku"]}
            )
            
        # 상품 생성
        async with async_safe_transaction(self.db, "create product"):
            product = await self.repository.create(**validated_data)
            
            # 변형 상품 생성
            if "variants" in product_data:
                await self._create_variants(product.id, product_data["variants"])
                
            self.logger.info(
                "Product created",
                product_id=product.id,
                sku=product.sku
            )
            
            # 캐시 무효화 (카테고리)
            if self.cache_service:
                pattern = self.cache_service.make_key("category", product.category, "*")
                self.cache_service.cache_manager.delete_pattern(pattern)
                
            return product
            
    async def update_product(
        self,
        product_id: str,
        updates: Dict[str, Any]
    ) -> Product:
        """상품 정보 업데이트"""
        validated_id = SafeValidator.validate_id(product_id, "product_id")
        
        # 허용된 필드만 업데이트
        allowed_fields = [
            "name", "description", "category", "price", 
            "status", "stock_quantity"
        ]
        
        filtered_updates = {
            k: v for k, v in updates.items() 
            if k in allowed_fields
        }
        
        if not filtered_updates:
            raise ValidationError("No valid fields to update")
            
        # 업데이트 실행
        product = await self.repository.get_or_404(validated_id)
        updated_product = await self.repository.update(product, **filtered_updates)
        
        # 캐시 무효화
        if self.cache_service:
            await self.cache_service.invalidate_product(validated_id)
            
        return updated_product
        
    async def update_stock(
        self,
        product_id: str,
        quantity_change: int,
        reason: str = "manual"
    ) -> Product:
        """재고 업데이트"""
        validated_id = SafeValidator.validate_id(product_id, "product_id")
        
        with LogContext(
            self.logger,
            operation="update_stock",
            product_id=validated_id,
            quantity_change=quantity_change,
            reason=reason
        ):
            product = await self.repository.update_stock(
                validated_id, 
                quantity_change
            )
            
            if not product:
                raise NotFoundError("Product", validated_id)
                
            # 캐시 무효화
            if self.cache_service:
                await self.cache_service.invalidate_product(validated_id)
                
            return product
            
    def _validate_product_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """상품 데이터 검증"""
        required_fields = ["sku", "name", "category", "price"]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"{field} is required")
                
        return {
            "sku": SafeValidator.sanitize_string(data["sku"], max_length=50),
            "name": SafeValidator.sanitize_string(data["name"], max_length=200),
            "description": SafeValidator.sanitize_string(
                data.get("description", ""), 
                max_length=1000
            ),
            "category": SafeValidator.sanitize_string(data["category"], max_length=50),
            "price": SafeValidator.validate_positive_decimal(data["price"], "price"),
            "status": data.get("status", ProductStatus.ACTIVE.value),
            "stock_quantity": int(data.get("stock_quantity", 0))
        }
        
    async def _create_variants(
        self,
        product_id: str,
        variants_data: List[Dict[str, Any]]
    ) -> None:
        """변형 상품 생성"""
        # 구현은 프로젝트 구조에 맞게 조정
        pass