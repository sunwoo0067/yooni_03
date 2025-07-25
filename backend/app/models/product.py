"""
Product models for multi-platform product management
"""
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import enum

from .base import BaseModel


class ProductStatus(enum.Enum):
    """Product status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    REJECTED = "rejected"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class ProductType(enum.Enum):
    """Product type enumeration"""
    SIMPLE = "simple"  # Simple product
    VARIABLE = "variable"  # Product with variants
    BUNDLE = "bundle"  # Bundle of products
    DIGITAL = "digital"  # Digital product


class PricingStrategy(enum.Enum):
    """Pricing strategy enumeration"""
    FIXED = "fixed"
    COST_PLUS = "cost_plus"
    COMPETITIVE = "competitive"
    DYNAMIC = "dynamic"


class Product(BaseModel):
    """Master product information"""
    __tablename__ = "products"
    
    # Basic Information
    platform_account_id = Column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=True, index=True)
    wholesale_account_id = Column(UUID(as_uuid=True), ForeignKey("wholesale_accounts.id"), nullable=True, index=True)
    
    # Product Identity
    sku = Column(String(100), unique=True, nullable=False, index=True)  # Internal SKU
    barcode = Column(String(50), nullable=True, index=True)  # EAN, UPC, etc.
    model_number = Column(String(100), nullable=True, index=True)
    
    # Basic Details
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True, index=True)
    manufacturer = Column(String(100), nullable=True)
    
    # Classification
    product_type = Column(SQLEnum(ProductType), default=ProductType.SIMPLE, nullable=False, index=True)
    category_path = Column(String(500), nullable=True, index=True)  # Category hierarchy
    tags = Column(ARRAY(String), nullable=True)
    
    # Pricing
    cost_price = Column(Numeric(12, 2), nullable=True)  # Purchase cost
    wholesale_price = Column(Numeric(12, 2), nullable=True)  # Wholesale price
    retail_price = Column(Numeric(12, 2), nullable=True)  # Suggested retail price
    sale_price = Column(Numeric(12, 2), nullable=True)  # Current sale price
    
    # Pricing Configuration
    pricing_strategy = Column(SQLEnum(PricingStrategy), default=PricingStrategy.FIXED, nullable=False)
    margin_percentage = Column(Numeric(5, 2), nullable=True)  # Target margin
    min_price = Column(Numeric(12, 2), nullable=True)  # Minimum allowed price
    max_price = Column(Numeric(12, 2), nullable=True)  # Maximum allowed price
    
    # Physical Properties
    weight = Column(Numeric(8, 3), nullable=True)  # Weight in kg
    dimensions = Column(JSONB, nullable=True)  # length, width, height
    
    # Status and Visibility
    status = Column(SQLEnum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False, index=True)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_digital = Column(Boolean, default=False, nullable=False)
    
    # SEO and Marketing
    seo_title = Column(String(200), nullable=True)
    seo_description = Column(Text, nullable=True)
    keywords = Column(ARRAY(String), nullable=True)
    
    # Images and Media
    main_image_url = Column(String(1000), nullable=True)
    image_urls = Column(JSONB, nullable=True)  # Array of image URLs
    video_urls = Column(JSONB, nullable=True)  # Array of video URLs
    
    # Inventory Information
    stock_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)  # Reserved for orders
    min_stock_level = Column(Integer, default=0, nullable=False)
    max_stock_level = Column(Integer, nullable=True)
    
    # Shipping
    requires_shipping = Column(Boolean, default=True, nullable=False)
    shipping_weight = Column(Numeric(8, 3), nullable=True)
    shipping_dimensions = Column(JSONB, nullable=True)
    
    # AI and Analytics
    ai_optimized = Column(Boolean, default=False, nullable=False)
    performance_score = Column(Numeric(5, 2), nullable=True)  # 0.0 to 10.0
    search_rank = Column(Integer, nullable=True)
    
    # 드롭쉬핑 관련 필드
    is_dropshipping = Column(Boolean, default=False, nullable=False, index=True)
    wholesaler_id = Column(Integer, ForeignKey("wholesalers.id"), nullable=True, index=True)
    wholesaler_product_id = Column(String(100), nullable=True, index=True)
    selling_price = Column(Numeric(12, 2), nullable=True)  # 실제 판매가
    deactivated_at = Column(DateTime, nullable=True)
    reactivated_at = Column(DateTime, nullable=True)
    price_updated_at = Column(DateTime, nullable=True)
    
    # Additional Data
    attributes = Column(JSONB, nullable=True)  # Flexible product attributes
    
    # Relationships
    platform_account = relationship("PlatformAccount", back_populates="products")
    wholesale_account = relationship("WholesaleAccount", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    platform_listings = relationship("PlatformListing", back_populates="product", cascade="all, delete-orphan")
    inventory_items = relationship("InventoryItem", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    price_history = relationship("ProductPriceHistory", back_populates="product", cascade="all, delete-orphan")
    
    # 드롭쉬핑 관련 관계
    outofstock_history = relationship("OutOfStockHistory", back_populates="product")
    restock_history = relationship("RestockHistory", back_populates="product")
    stock_check_logs = relationship("StockCheckLog", back_populates="product")
    dropshipping_price_history = relationship("PriceHistory", back_populates="product")
    profit_protection_logs = relationship("ProfitProtectionLog", back_populates="product")
    stockout_predictions = relationship("StockoutPredictionHistory", back_populates="product")
    demand_analyses = relationship("DemandAnalysisHistory", back_populates="product")
    automation_executions = relationship("AutomationExecution", back_populates="product")
    
    # 상품가공 관련 관계
    image_processing_history = relationship("ImageProcessingHistory", back_populates="product")
    name_generations = relationship("ProductNameGeneration", back_populates="product")
    purpose_analyses = relationship("ProductPurposeAnalysis", back_populates="product")
    competitor_analyses = relationship("CompetitorAnalysis", back_populates="product")
    
    def __repr__(self):
        return f"<Product(sku={self.sku}, name={self.name[:50]})>"
    
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (stock - reserved)"""
        return max(0, self.stock_quantity - self.reserved_quantity)
    
    @property
    def is_low_stock(self) -> bool:
        """Check if product is low on stock"""
        return self.stock_quantity <= self.min_stock_level
    
    @property
    def gross_margin(self) -> Optional[float]:
        """Calculate gross margin percentage"""
        if not self.cost_price or not self.sale_price or self.cost_price <= 0:
            return None
        return ((self.sale_price - self.cost_price) / self.sale_price) * 100


class ProductVariant(BaseModel):
    """Product variants for variable products"""
    __tablename__ = "product_variants"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # Variant Identity
    variant_sku = Column(String(100), unique=True, nullable=False, index=True)
    barcode = Column(String(50), nullable=True, index=True)
    
    # Variant Attributes
    name = Column(String(200), nullable=False)
    attributes = Column(JSONB, nullable=False)  # color, size, etc.
    
    # Pricing
    cost_price = Column(Numeric(12, 2), nullable=True)
    sale_price = Column(Numeric(12, 2), nullable=True)
    
    # Inventory
    stock_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    
    # Physical Properties
    weight = Column(Numeric(8, 3), nullable=True)
    dimensions = Column(JSONB, nullable=True)
    
    # Images
    image_urls = Column(JSONB, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="variants")
    
    def __repr__(self):
        return f"<ProductVariant(sku={self.variant_sku}, name={self.name})>"


class PlatformListing(BaseModel):
    """Platform-specific product listings"""
    __tablename__ = "platform_listings"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    platform_account_id = Column(UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False, index=True)
    
    # Platform-specific identifiers
    platform_product_id = Column(String(100), nullable=True, index=True)
    platform_sku = Column(String(100), nullable=True, index=True)
    listing_url = Column(String(1000), nullable=True)
    
    # Platform-specific details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    platform_category_id = Column(String(100), nullable=True)
    platform_category_name = Column(String(200), nullable=True)
    
    # Pricing
    listed_price = Column(Numeric(12, 2), nullable=False)
    sale_price = Column(Numeric(12, 2), nullable=True)
    
    # Status
    is_published = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    listing_status = Column(String(50), nullable=True)  # Platform-specific status
    
    # Performance metrics
    views = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    orders = Column(Integer, default=0, nullable=False)
    conversion_rate = Column(Numeric(5, 4), nullable=True)
    
    # Platform-specific settings
    platform_settings = Column(JSONB, nullable=True)
    
    # Sync information
    last_synced_at = Column(DateTime, nullable=True, index=True)
    sync_status = Column(String(20), default="pending", nullable=False)  # pending, synced, error
    sync_error = Column(Text, nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="platform_listings")
    platform_account = relationship("PlatformAccount")
    
    def __repr__(self):
        return f"<PlatformListing(product_id={self.product_id}, platform={self.platform_account.platform_type.value if self.platform_account else 'unknown'})>"


class ProductPriceHistory(BaseModel):
    """Product price change history"""
    __tablename__ = "product_price_history"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    
    # Price information
    cost_price = Column(Numeric(12, 2), nullable=True)
    wholesale_price = Column(Numeric(12, 2), nullable=True)
    retail_price = Column(Numeric(12, 2), nullable=True)
    sale_price = Column(Numeric(12, 2), nullable=True)
    
    # Change information
    changed_by = Column(String(50), nullable=True)  # user, system, ai
    change_reason = Column(String(200), nullable=True)
    previous_prices = Column(JSONB, nullable=True)
    
    # Market data
    competitor_prices = Column(JSONB, nullable=True)
    market_average = Column(Numeric(12, 2), nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="price_history")
    
    def __repr__(self):
        return f"<ProductPriceHistory(product_id={self.product_id}, sale_price={self.sale_price})>"


class ProductCategory(BaseModel):
    """Product category hierarchy"""
    __tablename__ = "product_categories"
    
    name = Column(String(200), nullable=False, index=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Hierarchy
    parent_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id"), nullable=True, index=True)
    level = Column(Integer, default=0, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # SEO
    seo_title = Column(String(200), nullable=True)
    seo_description = Column(Text, nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=True)  # Platform commission rate
    
    # Relationships
    parent = relationship("ProductCategory", remote_side="ProductCategory.id", backref="children")
    
    def __repr__(self):
        return f"<ProductCategory(name={self.name}, level={self.level})>"