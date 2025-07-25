"""
상품 관련 Pydantic 스키마
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class ProductStatusEnum(str, Enum):
    """상품 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"
    PENDING = "pending"


class ProductBase(BaseModel):
    """상품 기본 스키마"""
    product_code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    price: float = Field(..., gt=0)
    cost: Optional[float] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(0, ge=0)
    is_active: bool = True
    product_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProductCreate(ProductBase):
    """상품 생성 스키마"""
    wholesaler_id: Optional[int] = None
    platform_ids: Optional[List[int]] = []


class ProductUpdate(BaseModel):
    """상품 업데이트 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    price: Optional[float] = Field(None, gt=0)
    cost: Optional[float] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    product_attributes: Optional[Dict[str, Any]] = None


class ProductResponse(ProductBase):
    """상품 응답 스키마"""
    id: int
    uuid: UUID
    status: ProductStatusEnum
    wholesaler_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductSearchRequest(BaseModel):
    """상품 검색 요청"""
    query: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    is_active: Optional[bool] = None
    wholesaler_id: Optional[int] = None
    platform_id: Optional[int] = None
    sort_by: Optional[str] = Field("created_at", pattern="^(name|price|created_at|updated_at)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)


class ProductBulkUpdateRequest(BaseModel):
    """상품 대량 업데이트 요청"""
    product_ids: List[int] = Field(..., min_items=1)
    update_data: ProductUpdate


class ProductImportRequest(BaseModel):
    """상품 가져오기 요청"""
    wholesaler_id: int
    category: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)


# Alias for backward compatibility
ProductFilter = ProductSearchRequest
Product = ProductResponse


class ProductSort(str, Enum):
    """상품 정렬 옵션"""
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    STOCK_ASC = "stock_asc"
    STOCK_DESC = "stock_desc"
    CREATED_ASC = "created_asc"
    CREATED_DESC = "created_desc"
    UPDATED_ASC = "updated_asc"
    UPDATED_DESC = "updated_desc"
    PERFORMANCE_ASC = "performance_asc"
    PERFORMANCE_DESC = "performance_desc"


class ProductListResponse(BaseModel):
    """상품 목록 응답"""
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductBulkCreate(BaseModel):
    """상품 대량 생성"""
    products: List[ProductCreate]
    validate_only: bool = False


class ProductBulkUpdate(BaseModel):
    """상품 대량 업데이트"""
    product_ids: List[int]
    update_data: ProductUpdate


class ProductBulkResult(BaseModel):
    """상품 대량 작업 결과"""
    successful: int
    failed: int
    errors: List[str]
    created_ids: List[int] = []
    updated_ids: List[int] = []


class ProductVariant(BaseModel):
    """상품 변형"""
    id: int
    product_id: int
    sku: str
    name: str
    price: float
    stock_quantity: int
    attributes: Dict[str, Any] = {}
    

class ProductVariantCreate(BaseModel):
    """상품 변형 생성"""
    sku: str
    name: str
    price: float
    stock_quantity: int = 0
    attributes: Dict[str, Any] = {}


class ProductVariantUpdate(BaseModel):
    """상품 변형 업데이트"""
    name: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    attributes: Optional[Dict[str, Any]] = None


class PlatformListing(BaseModel):
    """플랫폼 리스팅"""
    id: int
    product_id: int
    platform_id: int
    platform_product_id: str
    title: str
    price: float
    status: str


class PlatformListingCreate(BaseModel):
    """플랫폼 리스팅 생성"""
    platform_id: int
    title: str
    price: float
    description: Optional[str] = None


class PlatformListingUpdate(BaseModel):
    """플랫폼 리스팅 업데이트"""
    title: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None


class PlatformSyncRequest(BaseModel):
    """플랫폼 동기화 요청"""
    platform_ids: List[int]
    force_update: bool = False


class PlatformSyncResult(BaseModel):
    """플랫폼 동기화 결과"""
    platform_id: int
    success: bool
    message: str


class ProductImportRow(BaseModel):
    """상품 가져오기 행 데이터"""
    name: str
    price: float
    description: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    stock_quantity: int = 0


class ProductImportResult(BaseModel):
    """상품 가져오기 결과"""
    successful: int
    failed: int
    errors: List[str]


class ProductOptimizationRequest(BaseModel):
    """상품 최적화 요청"""
    product_ids: List[int]
    optimization_type: str = "all"


class ProductOptimizationResult(BaseModel):
    """상품 최적화 결과"""
    product_id: int
    success: bool
    message: str
    optimizations: Dict[str, Any] = {}


class Category(BaseModel):
    """카테고리"""
    id: int
    name: str
    path: str
    parent_id: Optional[int] = None


class CategoryCreate(BaseModel):
    """카테고리 생성"""
    name: str
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    """카테고리 업데이트"""
    name: Optional[str] = None
    parent_id: Optional[int] = None