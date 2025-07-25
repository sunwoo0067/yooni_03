"""
Product service layer for business logic
"""
import csv
import io
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import asyncio
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.crud.product import product, product_variant, platform_listing, product_category
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductFilter, ProductSort,
    ProductBulkCreate, ProductBulkUpdate, ProductBulkResult,
    ProductVariantCreate, ProductVariantUpdate,
    PlatformListingCreate, PlatformListingUpdate,
    PlatformSyncRequest, PlatformSyncResult,
    ProductImportRequest, ProductImportResult, ProductImportRow,
    ProductOptimizationRequest, ProductOptimizationResult,
    CategoryCreate, CategoryUpdate
)
from app.models.product import Product, ProductStatus, PricingStrategy
from app.utils.product_utils import (
    calculate_optimal_price, validate_product_data,
    generate_seo_keywords, optimize_product_title,
    calculate_shipping_cost
)
from app.utils.category_mapping import map_internal_to_platform_category

logger = logging.getLogger(__name__)


class ProductService:
    """Product service for business logic operations"""
    
    def __init__(self):
        self.logger = logger
    
    async def create_product(
        self,
        db: Session,
        *,
        product_data: ProductCreate,
        auto_optimize: bool = True,
        create_platform_listings: bool = False
    ) -> Product:
        """Create a new product with business logic"""
        try:
            # Validate product data
            validation_errors = validate_product_data(product_data.dict())
            if validation_errors:
                raise ValueError(f"Validation errors: {validation_errors}")
            
            # Auto-optimize if requested
            if auto_optimize:
                product_data = await self._optimize_product_data(product_data)
            
            # Create the product
            db_product = product.create(db, obj_in=product_data)
            
            # Create platform listings if requested
            if create_platform_listings and product_data.platform_account_id:
                await self._create_default_platform_listings(db, db_product)
            
            self.logger.info(f"Created product: {db_product.sku}")
            return db_product
            
        except Exception as e:
            self.logger.error(f"Error creating product: {str(e)}")
            raise
    
    async def update_product(
        self,
        db: Session,
        *,
        product_id: UUID,
        product_data: ProductUpdate,
        update_platform_listings: bool = True
    ) -> Optional[Product]:
        """Update product with business logic"""
        try:
            # Get existing product
            existing_product = product.get(db, product_id)
            if not existing_product:
                return None
            
            # Update the product
            updated_product = product.update(db, db_obj=existing_product, obj_in=product_data)
            
            # Update platform listings if requested
            if update_platform_listings:
                await self._sync_platform_listings(db, updated_product)
            
            self.logger.info(f"Updated product: {updated_product.sku}")
            return updated_product
            
        except Exception as e:
            self.logger.error(f"Error updating product {product_id}: {str(e)}")
            raise
    
    def get_products_filtered(
        self,
        db: Session,
        *,
        filter_params: ProductFilter,
        sort: ProductSort = ProductSort.CREATED_DESC,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[Product], int, int]:
        """Get filtered products with pagination"""
        skip = (page - 1) * size
        
        products_list, total = product.get_multi_filtered(
            db,
            filter_params=filter_params,
            sort=sort,
            skip=skip,
            limit=size
        )
        
        pages = (total + size - 1) // size
        
        return products_list, total, pages
    
    async def bulk_create_products(
        self,
        db: Session,
        *,
        bulk_data: ProductBulkCreate
    ) -> ProductBulkResult:
        """Bulk create products with validation and error handling"""
        try:
            success_ids = []
            errors = []
            
            # Apply default attributes
            products_to_create = []
            for product_data in bulk_data.products:
                # Merge default attributes
                if bulk_data.default_attributes:
                    if not product_data.attributes:
                        product_data.attributes = {}
                    product_data.attributes.update(bulk_data.default_attributes)
                
                # Set default platform account if not provided
                if not product_data.platform_account_id and bulk_data.default_platform_account_id:
                    product_data.platform_account_id = bulk_data.default_platform_account_id
                
                products_to_create.append(product_data)
            
            # Bulk create
            created_products, creation_errors = product.bulk_create(
                db, products=products_to_create
            )
            
            success_ids = [p.id for p in created_products]
            errors = creation_errors
            
            # Log results
            self.logger.info(
                f"Bulk created {len(created_products)} products, "
                f"{len(errors)} errors"
            )
            
            return ProductBulkResult(
                success_count=len(created_products),
                error_count=len(errors),
                success_ids=success_ids,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"Error in bulk create: {str(e)}")
            raise
    
    async def bulk_update_products(
        self,
        db: Session,
        *,
        bulk_data: ProductBulkUpdate
    ) -> ProductBulkResult:
        """Bulk update products"""
        try:
            updated_products, errors = product.bulk_update(
                db,
                product_ids=bulk_data.product_ids,
                update_data=bulk_data.update_data
            )
            
            success_ids = [p.id for p in updated_products]
            
            self.logger.info(
                f"Bulk updated {len(updated_products)} products, "
                f"{len(errors)} errors"
            )
            
            return ProductBulkResult(
                success_count=len(updated_products),
                error_count=len(errors),
                success_ids=success_ids,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"Error in bulk update: {str(e)}")
            raise
    
    async def sync_product_to_platforms(
        self,
        db: Session,
        *,
        product_id: UUID,
        sync_request: PlatformSyncRequest
    ) -> List[PlatformSyncResult]:
        """Sync product to multiple platforms"""
        try:
            product_obj = product.get_with_details(db, product_id)
            if not product_obj:
                raise ValueError(f"Product {product_id} not found")
            
            results = []
            
            for platform_account_id in sync_request.platform_account_ids:
                result = await self._sync_to_single_platform(
                    db,
                    product_obj,
                    platform_account_id,
                    sync_request.force_update,
                    sync_request.custom_settings.get(platform_account_id) if sync_request.custom_settings else None
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error syncing product {product_id}: {str(e)}")
            raise
    
    async def import_products_from_csv(
        self,
        db: Session,
        *,
        csv_content: str,
        import_request: ProductImportRequest
    ) -> ProductImportResult:
        """Import products from CSV data"""
        try:
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            validation_errors = []
            import_errors = []
            imported_products = []
            skipped_count = 0
            
            for i, row in enumerate(rows):
                try:
                    # Convert row to ProductImportRow
                    import_row = self._convert_csv_row_to_import_row(row)
                    
                    # Validate row
                    if not import_row.sku or not import_row.name:
                        validation_errors.append({
                            "row": i + 1,
                            "error": "SKU and name are required"
                        })
                        continue
                    
                    # Check if product exists
                    existing_product = product.get_by_sku(db, import_row.sku)
                    
                    if existing_product and not import_request.update_existing:
                        skipped_count += 1
                        continue
                    
                    # If validation only, skip actual import
                    if import_request.validate_only:
                        continue
                    
                    # Create or update product
                    if existing_product and import_request.update_existing:
                        # Update existing product
                        update_data = self._convert_import_row_to_update(import_row)
                        updated_product = product.update(
                            db, db_obj=existing_product, obj_in=update_data
                        )
                        imported_products.append(updated_product.id)
                    else:
                        # Create new product
                        create_data = self._convert_import_row_to_create(
                            import_row, import_request.platform_account_id
                        )
                        new_product = product.create(db, obj_in=create_data)
                        imported_products.append(new_product.id)
                
                except Exception as e:
                    import_errors.append({
                        "row": i + 1,
                        "sku": row.get("sku", ""),
                        "error": str(e)
                    })
            
            return ProductImportResult(
                total_rows=len(rows),
                success_count=len(imported_products),
                error_count=len(import_errors),
                skipped_count=skipped_count,
                validation_errors=validation_errors,
                import_errors=import_errors,
                imported_products=imported_products
            )
            
        except Exception as e:
            self.logger.error(f"Error importing products: {str(e)}")
            raise
    
    async def optimize_products_with_ai(
        self,
        db: Session,
        *,
        optimization_request: ProductOptimizationRequest
    ) -> List[ProductOptimizationResult]:
        """Optimize products using AI"""
        try:
            results = []
            
            for product_id in optimization_request.product_ids:
                result = await self._optimize_single_product(
                    db,
                    product_id,
                    optimization_request.optimization_type,
                    optimization_request.target_platforms,
                    optimization_request.custom_instructions
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error optimizing products: {str(e)}")
            raise
    
    def update_product_stock(
        self,
        db: Session,
        *,
        product_id: UUID,
        quantity_change: int,
        operation: str = "set",
        reason: Optional[str] = None
    ) -> Optional[Product]:
        """Update product stock with logging"""
        try:
            updated_product = product.update_stock(
                db,
                product_id=product_id,
                quantity_change=quantity_change,
                operation=operation
            )
            
            if updated_product:
                self.logger.info(
                    f"Stock updated for product {product_id}: "
                    f"{operation} {quantity_change}, new stock: {updated_product.stock_quantity}"
                )
            
            return updated_product
            
        except Exception as e:
            self.logger.error(f"Error updating stock for product {product_id}: {str(e)}")
            raise
    
    def calculate_dynamic_pricing(
        self,
        db: Session,
        *,
        product_id: UUID,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Decimal]:
        """Calculate dynamic pricing for a product"""
        try:
            product_obj = product.get(db, product_id)
            if not product_obj:
                raise ValueError(f"Product {product_id} not found")
            
            if product_obj.pricing_strategy != PricingStrategy.DYNAMIC:
                return {
                    "sale_price": product_obj.sale_price or Decimal("0"),
                    "reason": "Product not set for dynamic pricing"
                }
            
            # Calculate optimal price based on various factors
            optimal_price = calculate_optimal_price(
                cost_price=product_obj.cost_price,
                current_price=product_obj.sale_price,
                margin_percentage=product_obj.margin_percentage,
                min_price=product_obj.min_price,
                max_price=product_obj.max_price,
                market_data=market_data,
                stock_level=product_obj.stock_quantity,
                performance_score=product_obj.performance_score
            )
            
            return {
                "sale_price": optimal_price,
                "reason": "Dynamic pricing calculation"
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating dynamic pricing for product {product_id}: {str(e)}")
            raise
    
    # Private helper methods
    
    async def _optimize_product_data(self, product_data: ProductCreate) -> ProductCreate:
        """Optimize product data using AI/algorithms"""
        optimized_data = product_data.copy()
        
        # Optimize title
        if product_data.name:
            optimized_title = optimize_product_title(
                product_data.name,
                product_data.brand,
                product_data.category_path
            )
            optimized_data.name = optimized_title
        
        # Generate SEO keywords
        if not product_data.keywords:
            keywords = generate_seo_keywords(
                product_data.name,
                product_data.description,
                product_data.brand,
                product_data.category_path
            )
            optimized_data.keywords = keywords
        
        # Set AI optimized flag
        optimized_data.ai_optimized = True
        
        return optimized_data
    
    async def _create_default_platform_listings(self, db: Session, product_obj: Product):
        """Create default platform listings for a product"""
        # This would integrate with platform APIs
        # For now, we'll create basic listings
        pass
    
    async def _sync_platform_listings(self, db: Session, product_obj: Product):
        """Sync product changes to platform listings"""
        # Get all platform listings for this product
        listings = platform_listing.get_by_product(db, product_obj.id)
        
        for listing in listings:
            # Update listing with new product data
            try:
                await self._update_platform_listing(db, listing, product_obj)
            except Exception as e:
                self.logger.error(f"Error syncing listing {listing.id}: {str(e)}")
    
    async def _sync_to_single_platform(
        self,
        db: Session,
        product_obj: Product,
        platform_account_id: UUID,
        force_update: bool,
        custom_settings: Optional[Dict[str, Any]]
    ) -> PlatformSyncResult:
        """Sync product to a single platform"""
        try:
            # Check if listing already exists
            existing_listing = db.query(platform_listing.model).filter(
                platform_listing.model.product_id == product_obj.id,
                platform_listing.model.platform_account_id == platform_account_id
            ).first()
            
            if existing_listing and not force_update:
                return PlatformSyncResult(
                    platform_account_id=platform_account_id,
                    success=True,
                    platform_product_id=existing_listing.platform_product_id,
                    listing_url=existing_listing.listing_url
                )
            
            # Create or update platform listing
            # This would integrate with actual platform APIs
            # For now, we'll create a basic listing record
            
            if existing_listing:
                # Update existing listing
                updated_listing = platform_listing.update(
                    db,
                    db_obj=existing_listing,
                    obj_in=PlatformListingUpdate(
                        title=product_obj.name,
                        description=product_obj.description,
                        listed_price=product_obj.sale_price or Decimal("0"),
                        is_published=True
                    )
                )
                listing_obj = updated_listing
            else:
                # Create new listing
                new_listing = platform_listing.create(
                    db,
                    obj_in=PlatformListingCreate(
                        platform_account_id=platform_account_id,
                        title=product_obj.name,
                        description=product_obj.description,
                        listed_price=product_obj.sale_price or Decimal("0"),
                        is_published=True
                    )
                )
                listing_obj = new_listing
            
            return PlatformSyncResult(
                platform_account_id=platform_account_id,
                success=True,
                platform_product_id=listing_obj.platform_product_id,
                listing_url=listing_obj.listing_url
            )
            
        except Exception as e:
            return PlatformSyncResult(
                platform_account_id=platform_account_id,
                success=False,
                error_message=str(e)
            )
    
    async def _update_platform_listing(self, db: Session, listing, product_obj: Product):
        """Update a platform listing with product changes"""
        # Update listing with new product data
        update_data = PlatformListingUpdate(
            title=product_obj.name,
            description=product_obj.description,
            listed_price=product_obj.sale_price or Decimal("0")
        )
        
        platform_listing.update(db, db_obj=listing, obj_in=update_data)
    
    def _convert_csv_row_to_import_row(self, row: Dict[str, str]) -> ProductImportRow:
        """Convert CSV row to ProductImportRow"""
        return ProductImportRow(
            sku=row.get("sku", ""),
            name=row.get("name", ""),
            description=row.get("description"),
            brand=row.get("brand"),
            category_path=row.get("category_path"),
            cost_price=Decimal(row["cost_price"]) if row.get("cost_price") else None,
            sale_price=Decimal(row["sale_price"]) if row.get("sale_price") else None,
            stock_quantity=int(row.get("stock_quantity", "0")),
            weight=float(row["weight"]) if row.get("weight") else None,
            tags=row.get("tags"),
            main_image_url=row.get("main_image_url")
        )
    
    def _convert_import_row_to_create(
        self,
        import_row: ProductImportRow,
        platform_account_id: Optional[UUID]
    ) -> ProductCreate:
        """Convert ProductImportRow to ProductCreate"""
        tags_list = []
        if import_row.tags:
            tags_list = [tag.strip() for tag in import_row.tags.split(",")]
        
        return ProductCreate(
            platform_account_id=platform_account_id,
            sku=import_row.sku,
            name=import_row.name,
            description=import_row.description,
            brand=import_row.brand,
            category_path=import_row.category_path,
            cost_price=import_row.cost_price,
            sale_price=import_row.sale_price,
            stock_quantity=import_row.stock_quantity,
            weight=import_row.weight,
            tags=tags_list if tags_list else None,
            main_image_url=import_row.main_image_url,
            attributes=import_row.additional_data
        )
    
    def _convert_import_row_to_update(self, import_row: ProductImportRow) -> ProductUpdate:
        """Convert ProductImportRow to ProductUpdate"""
        tags_list = []
        if import_row.tags:
            tags_list = [tag.strip() for tag in import_row.tags.split(",")]
        
        return ProductUpdate(
            name=import_row.name,
            description=import_row.description,
            brand=import_row.brand,
            category_path=import_row.category_path,
            cost_price=import_row.cost_price,
            sale_price=import_row.sale_price,
            stock_quantity=import_row.stock_quantity,
            weight=import_row.weight,
            tags=tags_list if tags_list else None,
            main_image_url=import_row.main_image_url,
            attributes=import_row.additional_data
        )
    
    async def _optimize_single_product(
        self,
        db: Session,
        product_id: UUID,
        optimization_type: str,
        target_platforms: Optional[List[str]],
        custom_instructions: Optional[str]
    ) -> ProductOptimizationResult:
        """Optimize a single product"""
        try:
            product_obj = product.get(db, product_id)
            if not product_obj:
                return ProductOptimizationResult(
                    product_id=product_id,
                    success=False,
                    optimized_fields={},
                    original_fields={},
                    error_message="Product not found"
                )
            
            original_fields = {
                "name": product_obj.name,
                "description": product_obj.description,
                "keywords": product_obj.keywords
            }
            
            optimized_fields = {}
            
            # Optimize based on type
            if optimization_type == "title" or optimization_type == "all":
                optimized_title = optimize_product_title(
                    product_obj.name,
                    product_obj.brand,
                    product_obj.category_path
                )
                optimized_fields["name"] = optimized_title
            
            if optimization_type == "keywords" or optimization_type == "all":
                optimized_keywords = generate_seo_keywords(
                    product_obj.name,
                    product_obj.description,
                    product_obj.brand,
                    product_obj.category_path
                )
                optimized_fields["keywords"] = optimized_keywords
            
            # Update product if changes were made
            if optimized_fields:
                update_data = ProductUpdate(**optimized_fields, ai_optimized=True)
                product.update(db, db_obj=product_obj, obj_in=update_data)
            
            return ProductOptimizationResult(
                product_id=product_id,
                success=True,
                optimized_fields=optimized_fields,
                original_fields=original_fields
            )
            
        except Exception as e:
            return ProductOptimizationResult(
                product_id=product_id,
                success=False,
                optimized_fields={},
                original_fields={},
                error_message=str(e)
            )


# Create service instance
product_service = ProductService()