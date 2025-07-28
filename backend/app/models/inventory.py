"""
Inventory management models
"""
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from .base import BaseModel, get_json_type


class MovementType(enum.Enum):
    """Inventory movement type enumeration"""
    PURCHASE = "purchase"  # Stock increase from purchase
    SALE = "sale"  # Stock decrease from sale
    ADJUSTMENT = "adjustment"  # Manual adjustment
    TRANSFER = "transfer"  # Transfer between warehouses
    RETURN = "return"  # Return from customer
    DAMAGE = "damage"  # Damaged goods
    LOSS = "loss"  # Lost goods
    FOUND = "found"  # Found goods
    RESERVATION = "reservation"  # Reserved for order
    RELEASE = "release"  # Released from reservation


class InventoryStatus(enum.Enum):
    """Inventory status enumeration"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    DAMAGED = "damaged"
    QUARANTINE = "quarantine"
    EXPIRED = "expired"


class Warehouse(BaseModel):
    """Warehouse/storage location information"""
    __tablename__ = "warehouses"
    
    # Basic Information
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Location
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(2), default="KR", nullable=False)
    
    # Contact Information
    manager_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Capacity
    total_capacity = Column(Numeric(12, 3), nullable=True)  # Total capacity in cubic meters
    used_capacity = Column(Numeric(12, 3), default=0, nullable=False)
    
    # Settings
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    auto_reorder = Column(Boolean, default=True, nullable=False)
    
    # Operational hours
    operating_hours = Column(get_json_type(), nullable=True)  # JSON with daily hours
    
    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="warehouse", cascade="all, delete-orphan")
    movements = relationship("InventoryMovement", back_populates="warehouse", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Warehouse(name={self.name}, code={self.code})>"
    
    @property
    def capacity_utilization(self) -> float:
        """Calculate capacity utilization percentage"""
        if not self.total_capacity or self.total_capacity <= 0:
            return 0.0
        return (self.used_capacity / self.total_capacity) * 100


class InventoryItem(BaseModel):
    """Inventory item tracking"""
    __tablename__ = "inventory_items"
    
    # References
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=True, index=True)
    
    # Stock Information
    quantity_available = Column(Integer, default=0, nullable=False)
    quantity_reserved = Column(Integer, default=0, nullable=False)
    quantity_damaged = Column(Integer, default=0, nullable=False)
    quantity_quarantine = Column(Integer, default=0, nullable=False)
    
    # Stock Levels
    min_stock_level = Column(Integer, default=0, nullable=False)
    max_stock_level = Column(Integer, nullable=True)
    reorder_point = Column(Integer, default=0, nullable=False)
    reorder_quantity = Column(Integer, nullable=True)
    
    # Location within warehouse
    location_code = Column(String(50), nullable=True, index=True)  # Shelf, bin, etc.
    zone = Column(String(50), nullable=True)
    aisle = Column(String(20), nullable=True)
    shelf = Column(String(20), nullable=True)
    bin = Column(String(20), nullable=True)
    
    # Cost Information
    average_cost = Column(Numeric(12, 4), nullable=True)  # Weighted average cost
    last_cost = Column(Numeric(12, 4), nullable=True)  # Last purchase cost
    
    # Tracking
    last_counted_at = Column(DateTime, nullable=True, index=True)
    last_movement_at = Column(DateTime, nullable=True, index=True)
    
    # Status
    status = Column(SQLEnum(InventoryStatus), default=InventoryStatus.AVAILABLE, nullable=False, index=True)
    
    # Additional Information
    batch_number = Column(String(100), nullable=True, index=True)
    serial_numbers = Column(get_json_type(), nullable=True)  # Array of serial numbers
    expiry_date = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    warehouse = relationship("Warehouse", back_populates="inventory_items")
    variant = relationship("ProductVariant")
    movements = relationship("InventoryMovement", back_populates="inventory_item", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<InventoryItem(product_id={self.product_id}, warehouse_id={self.warehouse_id}, available={self.quantity_available})>"
    
    @property
    def total_quantity(self) -> int:
        """Calculate total quantity across all statuses"""
        return (self.quantity_available + self.quantity_reserved + 
                self.quantity_damaged + self.quantity_quarantine)
    
    @property
    def is_low_stock(self) -> bool:
        """Check if item is below reorder point"""
        return self.quantity_available <= self.reorder_point
    
    @property
    def is_overstocked(self) -> bool:
        """Check if item is above max stock level"""
        if not self.max_stock_level:
            return False
        return self.quantity_available > self.max_stock_level
    
    def reserve_quantity(self, quantity: int) -> bool:
        """Reserve quantity for order"""
        if self.quantity_available >= quantity:
            self.quantity_available -= quantity
            self.quantity_reserved += quantity
            return True
        return False
    
    def release_reservation(self, quantity: int) -> bool:
        """Release reserved quantity"""
        if self.quantity_reserved >= quantity:
            self.quantity_reserved -= quantity
            self.quantity_available += quantity
            return True
        return False


class InventoryMovement(BaseModel):
    """Inventory movement/transaction history"""
    __tablename__ = "inventory_movements"
    
    # References
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True)
    
    # Movement Details
    movement_type = Column(SQLEnum(MovementType), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)  # Positive for increase, negative for decrease
    
    # Before/After quantities for audit
    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    
    # Cost Information
    unit_cost = Column(Numeric(12, 4), nullable=True)
    total_cost = Column(Numeric(15, 4), nullable=True)
    
    # Reference Documents
    reference_type = Column(String(50), nullable=True)  # order, purchase, adjustment, etc.
    reference_id = Column(String(100), nullable=True, index=True)
    document_number = Column(String(100), nullable=True)
    
    # Additional Information
    reason = Column(Text, nullable=True)
    performed_by = Column(String(100), nullable=True)  # User who performed the movement
    
    # Location (if moved within warehouse)
    from_location = Column(String(100), nullable=True)
    to_location = Column(String(100), nullable=True)
    
    # Batch/Serial tracking
    batch_number = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    
    # Additional data
    movement_data = Column(get_json_type(), nullable=True)
    
    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="movements")
    warehouse = relationship("Warehouse", back_populates="movements")
    
    def __repr__(self):
        return f"<InventoryMovement(type={self.movement_type.value}, quantity={self.quantity})>"


class StockAdjustment(BaseModel):
    """Stock adjustment records"""
    __tablename__ = "stock_adjustments"
    
    # Basic Information
    adjustment_number = Column(String(50), unique=True, nullable=False, index=True)
    adjustment_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Reason
    reason = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, approved, rejected
    
    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Created by
    created_by = Column(String(100), nullable=False)
    
    # Relationships
    adjustment_items = relationship("StockAdjustmentItem", back_populates="adjustment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<StockAdjustment(number={self.adjustment_number}, status={self.status})>"


class StockAdjustmentItem(BaseModel):
    """Individual items in stock adjustment"""
    __tablename__ = "stock_adjustment_items"
    
    # References
    adjustment_id = Column(UUID(as_uuid=True), ForeignKey("stock_adjustments.id"), nullable=False, index=True)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True)
    
    # Quantities
    quantity_expected = Column(Integer, nullable=False)  # Expected quantity
    quantity_actual = Column(Integer, nullable=False)    # Actual quantity found
    quantity_difference = Column(Integer, nullable=False)  # Difference (actual - expected)
    
    # Cost impact
    unit_cost = Column(Numeric(12, 4), nullable=True)
    cost_impact = Column(Numeric(15, 4), nullable=True)  # Total cost impact
    
    # Reason for specific item
    item_reason = Column(Text, nullable=True)
    
    # Relationships
    adjustment = relationship("StockAdjustment", back_populates="adjustment_items")
    inventory_item = relationship("InventoryItem")
    
    def __repr__(self):
        return f"<StockAdjustmentItem(difference={self.quantity_difference})>"


class StockCount(BaseModel):
    """Stock counting/cycle counting records"""
    __tablename__ = "stock_counts"
    
    # Basic Information
    count_number = Column(String(50), unique=True, nullable=False, index=True)
    count_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    count_type = Column(String(20), nullable=False)  # full, cycle, spot
    
    # Scope
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True, index=True)
    location_filter = Column(String(200), nullable=True)  # Specific locations to count
    
    # Status
    status = Column(String(20), default="planned", nullable=False, index=True)  # planned, in_progress, completed
    
    # Personnel
    assigned_to = Column(String(100), nullable=True)
    counted_by = Column(String(100), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Instructions
    instructions = Column(Text, nullable=True)
    
    # Relationships
    warehouse = relationship("Warehouse")
    count_items = relationship("StockCountItem", back_populates="stock_count", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<StockCount(number={self.count_number}, type={self.count_type})>"


class StockCountItem(BaseModel):
    """Individual items in stock count"""
    __tablename__ = "stock_count_items"
    
    # References
    count_id = Column(UUID(as_uuid=True), ForeignKey("stock_counts.id"), nullable=False, index=True)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True)
    
    # Expected vs Actual
    quantity_expected = Column(Integer, nullable=False)
    quantity_counted = Column(Integer, nullable=True)  # Null until counted
    variance = Column(Integer, nullable=True)  # counted - expected
    
    # Count details
    counted_at = Column(DateTime, nullable=True)
    counted_by = Column(String(100), nullable=True)
    
    # Location verification
    expected_location = Column(String(100), nullable=True)
    actual_location = Column(String(100), nullable=True)
    
    # Notes
    count_notes = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default="pending", nullable=False)  # pending, counted, verified
    
    # Relationships
    stock_count = relationship("StockCount", back_populates="count_items")
    inventory_item = relationship("InventoryItem")
    
    def __repr__(self):
        return f"<StockCountItem(expected={self.quantity_expected}, counted={self.quantity_counted})>"