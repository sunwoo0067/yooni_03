"""
Product API endpoints
"""
from typing import List, Optional, Any
from uuid import UUID
import io
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.dependencies.database import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.product import (
    Product, ProductCreate, ProductUpdate, ProductListResponse,
    ProductFilter, ProductSort, ProductBulkCreate, ProductBulkUpdate, ProductBulkResult,
    ProductVariant, ProductVariantCreate, ProductVariantUpdate,
    PlatformListing, PlatformListingCreate, PlatformListingUpdate,
    PlatformSyncRequest, PlatformSyncResult,
    ProductImportRequest, ProductImportResult,
    ProductOptimizationRequest, ProductOptimizationResult,
    Category, CategoryCreate, CategoryUpdate
)
from app.services.product_service import product_service
from app.crud.product import product as product_crud, product_category as category_crud
from app.utils.product_utils import generate_product_export_csv
from app.core.cache import cache_result, invalidate_cache

router = APIRouter()


# Product CRUD endpoints
@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
@invalidate_cache("products_list:*")  # 상품 생성 시 목록 캐시 무효화
async def create_product(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_in: ProductCreate,
    auto_optimize: bool = Query(True, description="Auto-optimize product data"),
    create_platform_listings: bool = Query(False, description="Create platform listings")
):
    """Create a new product"""
    try:
        product = await product_service.create_product(
            db,
            product_data=product_in,
            auto_optimize=auto_optimize,
            create_platform_listings=create_platform_listings
        )
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/", response_model=ProductListResponse)
@cache_result(prefix="products_list", ttl=300)  # 5분 캐싱
async def get_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # Search and filter parameters
    search: Optional[str] = Query(None, description="Search in name, description, SKU"),
    sku: Optional[str] = Query(None, description="Filter by SKU"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    product_type: Optional[List[str]] = Query(None, description="Filter by product type"),
    brand: Optional[List[str]] = Query(None, description="Filter by brand"),
    category_path: Optional[str] = Query(None, description="Filter by category path"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    platform_account_id: Optional[UUID] = Query(None, description="Filter by platform account"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    low_stock: Optional[bool] = Query(None, description="Filter low stock products"),
    out_of_stock: Optional[bool] = Query(None, description="Filter out of stock products"),
    is_featured: Optional[bool] = Query(None, description="Filter featured products"),
    # Sorting and pagination
    sort: ProductSort = Query(ProductSort.CREATED_DESC, description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """Get products with filtering and pagination"""
    # Build filter object
    filter_params = ProductFilter(
        search=search,
        sku=sku,
        status=status,
        product_type=product_type,
        brand=brand,
        category_path=category_path,
        tags=tags,
        platform_account_id=platform_account_id,
        min_price=min_price,
        max_price=max_price,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        is_featured=is_featured
    )
    
    # Get filtered products
    products, total, pages = product_service.get_products_filtered(
        db,
        filter_params=filter_params,
        sort=sort,
        page=page,
        size=size
    )
    
    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{product_id}", response_model=Product)
@cache_result(prefix="product_detail", ttl=600)  # 10분 캐싱
async def get_product(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID
):
    """Get a single product by ID"""
    product = product_crud.get_with_details(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=Product)
@invalidate_cache("products_list:*")  # 목록 캐시 무효화
@invalidate_cache("product_detail:*")  # 상세 캐시 무효화
async def update_product(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    product_in: ProductUpdate,
    update_platform_listings: bool = Query(True, description="Update platform listings")
):
    """Update a product"""
    try:
        updated_product = await product_service.update_product(
            db,
            product_id=product_id,
            product_data=product_in,
            update_platform_listings=update_platform_listings
        )
        if not updated_product:
            raise HTTPException(status_code=404, detail="Product not found")
        return updated_product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID
):
    """Delete a product"""
    product = product_crud.get(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_crud.remove(db, id=product_id)


# Bulk operations
@router.post("/bulk", response_model=ProductBulkResult)
async def bulk_create_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bulk_data: ProductBulkCreate
):
    """Bulk create products"""
    try:
        result = await product_service.bulk_create_products(db, bulk_data=bulk_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk create failed: {str(e)}")


@router.put("/bulk", response_model=ProductBulkResult)
async def bulk_update_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bulk_data: ProductBulkUpdate
):
    """Bulk update products"""
    try:
        result = await product_service.bulk_update_products(db, bulk_data=bulk_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")


# Platform operations
@router.post("/{product_id}/platforms", response_model=List[PlatformSyncResult])
async def sync_product_to_platforms(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    sync_request: PlatformSyncRequest
):
    """Sync product to multiple platforms"""
    try:
        results = await product_service.sync_product_to_platforms(
            db,
            product_id=product_id,
            sync_request=sync_request
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Platform sync failed: {str(e)}")


@router.get("/{product_id}/platforms", response_model=List[PlatformListing])
def get_product_platform_listings(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID
):
    """Get platform listings for a product"""
    from app.crud.product import platform_listing
    listings = platform_listing.get_by_product(db, product_id)
    return listings


# Stock management
@router.put("/{product_id}/stock")
def update_product_stock(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    quantity_change: int,
    operation: str = Query("set", pattern="^(set|add|subtract)$"),
    reason: Optional[str] = Query(None, description="Reason for stock change")
):
    """Update product stock"""
    try:
        updated_product = product_service.update_product_stock(
            db,
            product_id=product_id,
            quantity_change=quantity_change,
            operation=operation,
            reason=reason
        )
        if not updated_product:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"message": "Stock updated successfully", "new_stock": updated_product.stock_quantity}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stock update failed: {str(e)}")


# Pricing
@router.post("/{product_id}/pricing/calculate")
def calculate_dynamic_pricing(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    market_data: Optional[dict] = None
):
    """Calculate dynamic pricing for a product"""
    try:
        pricing_result = product_service.calculate_dynamic_pricing(
            db,
            product_id=product_id,
            market_data=market_data
        )
        return pricing_result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pricing calculation failed: {str(e)}")


# Product variants
@router.get("/{product_id}/variants", response_model=List[ProductVariant])
def get_product_variants(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID
):
    """Get variants for a product"""
    from app.crud.product import product_variant
    variants = product_variant.get_by_product(db, product_id)
    return variants


@router.post("/{product_id}/variants", response_model=ProductVariant, status_code=status.HTTP_201_CREATED)
def create_product_variant(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    variant_in: ProductVariantCreate
):
    """Create a variant for a product"""
    from app.crud.product import product_variant
    
    # Check if parent product exists
    product = product_crud.get(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        variant = product_variant.create_for_product(
            db,
            product_id=product_id,
            obj_in=variant_in
        )
        return variant
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant creation failed: {str(e)}")


@router.put("/{product_id}/variants/{variant_id}", response_model=ProductVariant)
def update_product_variant(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    variant_id: UUID,
    variant_in: ProductVariantUpdate
):
    """Update a product variant"""
    from app.crud.product import product_variant
    
    variant = product_variant.get(db, variant_id)
    if not variant or variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    try:
        updated_variant = product_variant.update(db, db_obj=variant, obj_in=variant_in)
        return updated_variant
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant update failed: {str(e)}")


@router.delete("/{product_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_variant(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    variant_id: UUID
):
    """Delete a product variant"""
    from app.crud.product import product_variant
    
    variant = product_variant.get(db, variant_id)
    if not variant or variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    product_variant.remove(db, id=variant_id)


# Image management
@router.post("/{product_id}/images")
async def upload_product_images(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: UUID,
    images: List[UploadFile] = File(...),
    is_main: bool = Form(False, description="Set first image as main image")
):
    """Upload images for a product"""
    product = product_crud.get(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # This is a placeholder - in production, you'd upload to cloud storage
    image_urls = []
    for i, image in enumerate(images):
        # Validate file type
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {image.filename} is not an image")
        
        # In production, upload to cloud storage and get URL
        # For now, we'll create placeholder URLs
        image_url = f"/uploads/products/{product_id}/image_{i}_{image.filename}"
        image_urls.append(image_url)
    
    # Update product with new images
    update_data = {}
    if is_main and image_urls:
        update_data["main_image_url"] = image_urls[0]
    
    if product.image_urls:
        product.image_urls.extend(image_urls)
        update_data["image_urls"] = product.image_urls
    else:
        update_data["image_urls"] = image_urls
    
    if update_data:
        product_crud.update(db, db_obj=product, obj_in=ProductUpdate(**update_data))
    
    return {"message": f"Uploaded {len(image_urls)} images", "image_urls": image_urls}


# Import/Export
@router.post("/import", response_model=ProductImportResult)
async def import_products_from_csv(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    platform_account_id: Optional[UUID] = Form(None),
    update_existing: bool = Form(False),
    validate_only: bool = Form(False)
):
    """Import products from CSV file"""
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read CSV content
        csv_content = await file.read()
        csv_string = csv_content.decode('utf-8')
        
        # Create import request
        import_request = ProductImportRequest(
            data=[],  # Will be populated from CSV
            platform_account_id=platform_account_id,
            update_existing=update_existing,
            validate_only=validate_only
        )
        
        # Import products
        result = await product_service.import_products_from_csv(
            db,
            csv_content=csv_string,
            import_request=import_request
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/export/csv")
def export_products_to_csv(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_account_id: Optional[UUID] = Query(None),
    category_path: Optional[str] = Query(None),
    status: Optional[List[str]] = Query(None)
):
    """Export products to CSV"""
    try:
        # Build filter
        filter_params = ProductFilter(
            platform_account_id=platform_account_id,
            category_path=category_path,
            status=status
        )
        
        # Get products
        products, _, _ = product_service.get_products_filtered(
            db,
            filter_params=filter_params,
            page=1,
            size=10000  # Large limit for export
        )
        
        # Generate CSV
        csv_content = generate_product_export_csv(products)
        
        # Return as streaming response
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=products_export.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# AI Optimization
@router.post("/optimize", response_model=List[ProductOptimizationResult])
async def optimize_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    optimization_request: ProductOptimizationRequest
):
    """Optimize products using AI"""
    try:
        results = await product_service.optimize_products_with_ai(
            db,
            optimization_request=optimization_request
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


# Categories
@router.get("/categories", response_model=List[Category])
def get_categories(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    parent_id: Optional[UUID] = Query(None, description="Get categories under parent"),
    tree: bool = Query(False, description="Get complete category tree")
):
    """Get product categories"""
    if tree:
        categories = category_crud.get_category_tree(db)
    elif parent_id:
        categories = category_crud.get_children(db, parent_id)
    else:
        categories = category_crud.get_root_categories(db)
    
    return categories


@router.post("/categories", response_model=Category, status_code=status.HTTP_201_CREATED)
def create_category(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category_in: CategoryCreate
):
    """Create a new category"""
    try:
        category = category_crud.create(db, obj_in=category_in)
        return category
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Category creation failed: {str(e)}")


@router.put("/categories/{category_id}", response_model=Category)
def update_category(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category_id: UUID,
    category_in: CategoryUpdate
):
    """Update a category"""
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        updated_category = category_crud.update(db, db_obj=category, obj_in=category_in)
        return updated_category
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Category update failed: {str(e)}")


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category_id: UUID
):
    """Delete a category"""
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category has children
    children = category_crud.get_children(db, category_id)
    if children:
        raise HTTPException(status_code=400, detail="Cannot delete category with subcategories")
    
    category_crud.remove(db, id=category_id)


# Analytics and reporting
@router.get("/analytics/low-stock")
def get_low_stock_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_account_id: Optional[UUID] = Query(None),
    limit: int = Query(100, le=1000)
):
    """Get products with low stock"""
    products = product_crud.get_low_stock_products(
        db,
        platform_account_id=platform_account_id,
        limit=limit
    )
    return products


@router.get("/analytics/performance")
def get_product_performance(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    product_id: Optional[UUID] = Query(None),
    platform_account_id: Optional[UUID] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    """Get product performance analytics"""
    # This would integrate with analytics service
    # For now, return placeholder data
    return {
        "message": "Performance analytics endpoint - to be implemented with analytics service",
        "product_id": product_id,
        "platform_account_id": platform_account_id,
        "days": days
    }