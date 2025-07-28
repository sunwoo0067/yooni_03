"""
CRUD operations for products
"""
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy.dialects.postgresql import insert

from app.crud.base import CRUDBase
from app.models.product import (
    Product, ProductVariant, PlatformListing, ProductPriceHistory,
    ProductCategory, ProductStatus, ProductType, PricingStrategy
)
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductFilter, ProductSort,
    ProductVariantCreate, ProductVariantUpdate,
    PlatformListingCreate, PlatformListingUpdate,
    CategoryCreate, CategoryUpdate
)


class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    """CRUD operations for Product"""
    
    def create_with_details(
        self,
        db: Session,
        *,
        obj_in: ProductCreate,
        variants: Optional[List[ProductVariantCreate]] = None,
        platform_listings: Optional[List[PlatformListingCreate]] = None
    ) -> Product:
        """Create product with variants and platform listings"""
        # Create base product
        db_obj = Product(**obj_in.dict(exclude={'variants', 'platform_listings'}))
        db.add(db_obj)
        db.flush()  # Get the ID without committing
        
        # Create variants if provided
        if variants:
            for variant_data in variants:
                variant = ProductVariant(
                    product_id=db_obj.id,
                    **variant_data.dict()
                )
                db.add(variant)
        
        # Create platform listings if provided
        if platform_listings:
            for listing_data in platform_listings:
                listing = PlatformListing(
                    product_id=db_obj.id,
                    **listing_data.dict()
                )
                db.add(listing)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_with_details(self, db: Session, id: UUID) -> Optional[Product]:
        """Get product with all related data"""
        return db.query(Product).options(
            selectinload(Product.variants),
            selectinload(Product.platform_listings),
            selectinload(Product.price_history)
        ).filter(Product.id == id).first()
    
    def get_by_sku(self, db: Session, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        return db.query(Product).filter(Product.sku == sku).first()
    
    def get_by_barcode(self, db: Session, barcode: str) -> Optional[Product]:
        """Get product by barcode"""
        return db.query(Product).filter(Product.barcode == barcode).first()
    
    def get_multi_filtered(
        self,
        db: Session,
        *,
        filter_params: ProductFilter,
        sort: ProductSort = ProductSort.CREATED_DESC,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Product], int]:
        """Get products with filtering and sorting"""
        query = db.query(Product).options(
            selectinload(Product.variants),
            selectinload(Product.platform_listings),
            selectinload(Product.price_history)
        )
        
        # Apply filters
        conditions = []
        
        if filter_params.search:
            search_term = f"%{filter_params.search}%"
            conditions.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.sku.ilike(search_term),
                    Product.brand.ilike(search_term)
                )
            )
        
        if filter_params.sku:
            conditions.append(Product.sku.ilike(f"%{filter_params.sku}%"))
        
        if filter_params.status:
            conditions.append(Product.status.in_(filter_params.status))
        
        if filter_params.product_type:
            conditions.append(Product.product_type.in_(filter_params.product_type))
        
        if filter_params.brand:
            conditions.append(Product.brand.in_(filter_params.brand))
        
        if filter_params.category_path:
            conditions.append(Product.category_path.ilike(f"%{filter_params.category_path}%"))
        
        if filter_params.tags:
            conditions.append(Product.tags.op('&&')(filter_params.tags))
        
        if filter_params.platform_account_id:
            conditions.append(Product.platform_account_id == filter_params.platform_account_id)
        
        if filter_params.min_price is not None:
            conditions.append(Product.sale_price >= filter_params.min_price)
        
        if filter_params.max_price is not None:
            conditions.append(Product.sale_price <= filter_params.max_price)
        
        if filter_params.low_stock is True:
            conditions.append(Product.stock_quantity <= Product.min_stock_level)
        
        if filter_params.out_of_stock is True:
            conditions.append(Product.stock_quantity == 0)
        
        if filter_params.is_featured is not None:
            conditions.append(Product.is_featured == filter_params.is_featured)
        
        if filter_params.created_after:
            conditions.append(Product.created_at >= filter_params.created_after)
        
        if filter_params.created_before:
            conditions.append(Product.created_at <= filter_params.created_before)
        
        if filter_params.updated_after:
            conditions.append(Product.updated_at >= filter_params.updated_after)
        
        if filter_params.updated_before:
            conditions.append(Product.updated_at <= filter_params.updated_before)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if sort == ProductSort.NAME_ASC:
            query = query.order_by(asc(Product.name))
        elif sort == ProductSort.NAME_DESC:
            query = query.order_by(desc(Product.name))
        elif sort == ProductSort.PRICE_ASC:
            query = query.order_by(asc(Product.sale_price))
        elif sort == ProductSort.PRICE_DESC:
            query = query.order_by(desc(Product.sale_price))
        elif sort == ProductSort.STOCK_ASC:
            query = query.order_by(asc(Product.stock_quantity))
        elif sort == ProductSort.STOCK_DESC:
            query = query.order_by(desc(Product.stock_quantity))
        elif sort == ProductSort.CREATED_ASC:
            query = query.order_by(asc(Product.created_at))
        elif sort == ProductSort.CREATED_DESC:
            query = query.order_by(desc(Product.created_at))
        elif sort == ProductSort.UPDATED_ASC:
            query = query.order_by(asc(Product.updated_at))
        elif sort == ProductSort.UPDATED_DESC:
            query = query.order_by(desc(Product.updated_at))
        elif sort == ProductSort.PERFORMANCE_ASC:
            query = query.order_by(asc(Product.performance_score))
        elif sort == ProductSort.PERFORMANCE_DESC:
            query = query.order_by(desc(Product.performance_score))
        
        # Apply pagination
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    def get_by_platform_account(
        self,
        db: Session,
        platform_account_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Get products by platform account"""
        return db.query(Product).filter(
            Product.platform_account_id == platform_account_id
        ).offset(skip).limit(limit).all()
    
    def get_low_stock_products(
        self,
        db: Session,
        platform_account_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[Product]:
        """Get products with low stock"""
        query = db.query(Product).filter(
            Product.stock_quantity <= Product.min_stock_level
        )
        
        if platform_account_id:
            query = query.filter(Product.platform_account_id == platform_account_id)
        
        return query.limit(limit).all()
    
    def bulk_create(
        self,
        db: Session,
        *,
        products: List[ProductCreate]
    ) -> tuple[List[Product], List[Dict[str, Any]]]:
        """Bulk create products"""
        created_products = []
        errors = []
        
        for i, product_data in enumerate(products):
            try:
                # Check if SKU already exists
                if self.get_by_sku(db, product_data.sku):
                    errors.append({
                        "index": i,
                        "sku": product_data.sku,
                        "error": "SKU already exists"
                    })
                    continue
                
                db_obj = Product(**product_data.dict())
                db.add(db_obj)
                db.flush()
                created_products.append(db_obj)
                
            except Exception as e:
                errors.append({
                    "index": i,
                    "sku": product_data.sku,
                    "error": str(e)
                })
                db.rollback()
        
        if created_products:
            db.commit()
            # Refresh all created objects
            for product in created_products:
                db.refresh(product)
        
        return created_products, errors
    
    def bulk_update(
        self,
        db: Session,
        *,
        product_ids: List[UUID],
        update_data: ProductUpdate
    ) -> tuple[List[Product], List[Dict[str, Any]]]:
        """Bulk update products"""
        updated_products = []
        errors = []
        
        # Get all products to update
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        
        for product in products:
            try:
                update_dict = update_data.dict(exclude_unset=True)
                for field, value in update_dict.items():
                    setattr(product, field, value)
                
                updated_products.append(product)
                
            except Exception as e:
                errors.append({
                    "id": str(product.id),
                    "sku": product.sku,
                    "error": str(e)
                })
        
        if updated_products:
            db.commit()
            # Refresh all updated objects
            for product in updated_products:
                db.refresh(product)
        
        return updated_products, errors
    
    def update_stock(
        self,
        db: Session,
        *,
        product_id: UUID,
        quantity_change: int,
        operation: str = "set"  # "set", "add", "subtract"
    ) -> Optional[Product]:
        """Update product stock"""
        product = self.get(db, product_id)
        if not product:
            return None
        
        if operation == "set":
            product.stock_quantity = max(0, quantity_change)
        elif operation == "add":
            product.stock_quantity = max(0, product.stock_quantity + quantity_change)
        elif operation == "subtract":
            product.stock_quantity = max(0, product.stock_quantity - quantity_change)
        
        # Update timestamp
        product.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(product)
        return product
    
    def reserve_stock(
        self,
        db: Session,
        *,
        product_id: UUID,
        quantity: int
    ) -> bool:
        """Reserve stock for an order"""
        product = self.get(db, product_id)
        if not product:
            return False
        
        if product.available_quantity < quantity:
            return False
        
        product.reserved_quantity += quantity
        product.updated_at = datetime.utcnow()
        
        db.commit()
        return True
    
    def release_reserved_stock(
        self,
        db: Session,
        *,
        product_id: UUID,
        quantity: int
    ) -> bool:
        """Release reserved stock"""
        product = self.get(db, product_id)
        if not product:
            return False
        
        product.reserved_quantity = max(0, product.reserved_quantity - quantity)
        product.updated_at = datetime.utcnow()
        
        db.commit()
        return True
    
    def update_price_with_history(
        self,
        db: Session,
        *,
        product_id: UUID,
        new_prices: Dict[str, Decimal],
        changed_by: str = "system",
        change_reason: Optional[str] = None
    ) -> Optional[Product]:
        """Update product price and record history"""
        product = self.get(db, product_id)
        if not product:
            return None
        
        # Store previous prices
        previous_prices = {
            "cost_price": product.cost_price,
            "wholesale_price": product.wholesale_price,
            "retail_price": product.retail_price,
            "sale_price": product.sale_price
        }
        
        # Update prices
        for price_type, new_price in new_prices.items():
            if hasattr(product, price_type):
                setattr(product, price_type, new_price)
        
        # Create price history record
        price_history = ProductPriceHistory(
            product_id=product_id,
            cost_price=new_prices.get("cost_price", product.cost_price),
            wholesale_price=new_prices.get("wholesale_price", product.wholesale_price),
            retail_price=new_prices.get("retail_price", product.retail_price),
            sale_price=new_prices.get("sale_price", product.sale_price),
            changed_by=changed_by,
            change_reason=change_reason,
            previous_prices=previous_prices
        )
        
        db.add(price_history)
        product.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(product)
        return product
    
    def get_products_by_category(
        self,
        db: Session,
        category_path: str,
        include_subcategories: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Get products by category"""
        if include_subcategories:
            # Get products from this category and all subcategories
            query = db.query(Product).filter(
                Product.category_path.like(f"{category_path}%")
            )
        else:
            # Get products from exact category only
            query = db.query(Product).filter(
                Product.category_path == category_path
            )
        
        return query.offset(skip).limit(limit).all()
    
    def search_products(
        self,
        db: Session,
        search_term: str,
        limit: int = 100
    ) -> List[Product]:
        """Full-text search for products"""
        search_term = f"%{search_term}%"
        
        return db.query(Product).filter(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
                Product.sku.ilike(search_term),
                Product.brand.ilike(search_term),
                Product.keywords.op('&&')([search_term.strip('%')])
            )
        ).limit(limit).all()


class CRUDProductVariant(CRUDBase[ProductVariant, ProductVariantCreate, ProductVariantUpdate]):
    """CRUD operations for ProductVariant"""
    
    def get_by_product(
        self,
        db: Session,
        product_id: UUID
    ) -> List[ProductVariant]:
        """Get all variants for a product"""
        return db.query(ProductVariant).filter(
            ProductVariant.product_id == product_id
        ).all()
    
    def get_by_sku(self, db: Session, variant_sku: str) -> Optional[ProductVariant]:
        """Get variant by SKU"""
        return db.query(ProductVariant).filter(
            ProductVariant.variant_sku == variant_sku
        ).first()
    
    def create_for_product(
        self,
        db: Session,
        *,
        product_id: UUID,
        obj_in: ProductVariantCreate
    ) -> ProductVariant:
        """Create variant for a specific product"""
        db_obj = ProductVariant(
            product_id=product_id,
            **obj_in.dict()
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDPlatformListing(CRUDBase[PlatformListing, PlatformListingCreate, PlatformListingUpdate]):
    """CRUD operations for PlatformListing"""
    
    def get_by_product(
        self,
        db: Session,
        product_id: UUID
    ) -> List[PlatformListing]:
        """Get all platform listings for a product"""
        return db.query(PlatformListing).filter(
            PlatformListing.product_id == product_id
        ).all()
    
    def get_by_platform_account(
        self,
        db: Session,
        platform_account_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[PlatformListing]:
        """Get listings by platform account"""
        return db.query(PlatformListing).filter(
            PlatformListing.platform_account_id == platform_account_id
        ).offset(skip).limit(limit).all()
    
    def get_by_platform_product_id(
        self,
        db: Session,
        platform_product_id: str,
        platform_account_id: UUID
    ) -> Optional[PlatformListing]:
        """Get listing by platform product ID"""
        return db.query(PlatformListing).filter(
            and_(
                PlatformListing.platform_product_id == platform_product_id,
                PlatformListing.platform_account_id == platform_account_id
            )
        ).first()
    
    def update_sync_status(
        self,
        db: Session,
        *,
        listing_id: UUID,
        sync_status: str,
        sync_error: Optional[str] = None,
        platform_product_id: Optional[str] = None,
        listing_url: Optional[str] = None
    ) -> Optional[PlatformListing]:
        """Update listing sync status"""
        listing = self.get(db, listing_id)
        if not listing:
            return None
        
        listing.sync_status = sync_status
        listing.sync_error = sync_error
        listing.last_synced_at = datetime.utcnow()
        
        if platform_product_id:
            listing.platform_product_id = platform_product_id
        
        if listing_url:
            listing.listing_url = listing_url
        
        db.commit()
        db.refresh(listing)
        return listing


class CRUDProductCategory(CRUDBase[ProductCategory, CategoryCreate, CategoryUpdate]):
    """CRUD operations for ProductCategory"""
    
    def get_by_slug(self, db: Session, slug: str) -> Optional[ProductCategory]:
        """Get category by slug"""
        return db.query(ProductCategory).filter(
            ProductCategory.slug == slug
        ).first()
    
    def get_root_categories(self, db: Session) -> List[ProductCategory]:
        """Get root categories (no parent)"""
        return db.query(ProductCategory).filter(
            ProductCategory.parent_id.is_(None)
        ).order_by(ProductCategory.sort_order).all()
    
    def get_children(
        self,
        db: Session,
        parent_id: UUID
    ) -> List[ProductCategory]:
        """Get child categories"""
        return db.query(ProductCategory).filter(
            ProductCategory.parent_id == parent_id
        ).order_by(ProductCategory.sort_order).all()
    
    def get_category_tree(self, db: Session) -> List[ProductCategory]:
        """Get complete category tree"""
        # This is a simplified version - in production, you might want to use
        # recursive CTEs or other optimized approaches for large category trees
        categories = db.query(ProductCategory).order_by(
            ProductCategory.level,
            ProductCategory.sort_order
        ).all()
        
        # Build tree structure
        category_dict = {cat.id: cat for cat in categories}
        root_categories = []
        
        for category in categories:
            if category.parent_id is None:
                root_categories.append(category)
            else:
                parent = category_dict.get(category.parent_id)
                if parent:
                    if not hasattr(parent, 'children') or parent.children is None:
                        parent.children = []
                    parent.children.append(category)
        
        return root_categories
    
    def get_category_path(self, db: Session, category_id: UUID) -> str:
        """Get full category path"""
        category = self.get(db, category_id)
        if not category:
            return ""
        
        path_parts = [category.name]
        current = category
        
        while current.parent_id:
            parent = self.get(db, current.parent_id)
            if not parent:
                break
            path_parts.insert(0, parent.name)
            current = parent
        
        return " > ".join(path_parts)


# Create instances
product = CRUDProduct(Product)
product_crud = product  # Alias for backward compatibility
product_variant = CRUDProductVariant(ProductVariant)
platform_listing = CRUDPlatformListing(PlatformListing)
product_category = CRUDProductCategory(ProductCategory)