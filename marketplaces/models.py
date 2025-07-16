"""
Marketplace models for managing marketplace integrations, listings, orders, and inventory.
"""
import json
from decimal import Decimal
from typing import Any, Dict, Optional, List

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .utils.encryption import credential_encryption


class Marketplace(models.Model):
    """
    Represents a marketplace platform (e.g., Amazon, eBay, Shopify).
    Stores connection settings, encrypted API credentials, and fee structures.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('testing', 'Testing'),
        ('pending', 'Pending Approval'),
    ]
    
    # Platform type choices
    PLATFORM_CHOICES = [
        ('amazon', 'Amazon'),
        ('ebay', 'eBay'),
        ('shopify', 'Shopify'),
        ('walmart', 'Walmart'),
        ('etsy', 'Etsy'),
        ('mercadolibre', 'MercadoLibre'),
        ('custom', 'Custom Platform'),
    ]
    
    # Basic Information
    name = models.CharField(
        max_length=255, 
        unique=True,
        help_text="Marketplace name"
    )
    code = models.SlugField(
        max_length=50, 
        unique=True,
        help_text="Unique identifier code for the marketplace"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the marketplace and selling strategy"
    )
    platform_type = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        help_text="Type of marketplace platform"
    )
    
    # Connection Settings
    api_base_url = models.URLField(
        blank=True,
        help_text="Base URL for API connections"
    )
    seller_account_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Seller/Merchant account ID on the marketplace"
    )
    
    # Encrypted Credentials Storage
    encrypted_credentials = models.TextField(
        blank=True,
        help_text="Encrypted API credentials (API keys, tokens, secrets)"
    )
    
    # Connection Configuration
    connection_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Marketplace-specific configuration (region, currency, endpoints)"
    )
    
    # Fee Structure
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Default commission percentage charged by marketplace"
    )
    listing_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fee charged per listing (if applicable)"
    )
    monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Monthly subscription/store fee"
    )
    fee_structure = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed fee structure (category-specific fees, etc.)"
    )
    
    # Rate Limiting
    rate_limit_requests = models.IntegerField(
        default=100,
        help_text="Maximum requests per rate limit window"
    )
    rate_limit_window = models.IntegerField(
        default=3600,
        help_text="Rate limit window in seconds"
    )
    
    # Inventory Settings
    inventory_sync_enabled = models.BooleanField(
        default=True,
        help_text="Enable automatic inventory synchronization"
    )
    inventory_buffer = models.IntegerField(
        default=0,
        help_text="Buffer quantity to reserve from actual inventory"
    )
    
    # Order Settings
    auto_acknowledge_orders = models.BooleanField(
        default=False,
        help_text="Automatically acknowledge new orders"
    )
    order_prefix = models.CharField(
        max_length=10,
        blank=True,
        help_text="Prefix to add to internal order numbers"
    )
    
    # Status and Metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive'
    )
    is_auto_sync_enabled = models.BooleanField(
        default=False,
        help_text="Enable automatic synchronization"
    )
    sync_frequency_minutes = models.IntegerField(
        default=60,
        help_text="Minutes between automatic syncs"
    )
    
    # Marketplace Settings
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Default currency for this marketplace"
    )
    country_code = models.CharField(
        max_length=2,
        blank=True,
        help_text="Two-letter country code (e.g., US, UK)"
    )
    language_code = models.CharField(
        max_length=10,
        default='en',
        help_text="Language code for marketplace (e.g., en, es, fr)"
    )
    
    # Tracking
    last_sync_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last successful synchronization"
    )
    last_sync_status = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Status of the last sync attempt"
    )
    last_sync_error = models.TextField(
        blank=True,
        help_text="Error message from last failed sync"
    )
    
    # Statistics
    total_listings = models.IntegerField(
        default=0,
        help_text="Total number of active listings"
    )
    total_orders = models.IntegerField(
        default=0,
        help_text="Total number of orders received"
    )
    total_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total revenue from this marketplace"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='marketplaces_created'
    )
    
    class Meta:
        db_table = 'marketplaces'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
            models.Index(fields=['platform_type']),
            models.Index(fields=['last_sync_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.platform_type})"
    
    def save(self, *args, **kwargs):
        """Override save to ensure code is lowercase."""
        self.code = self.code.lower()
        super().save(*args, **kwargs)
    
    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Set and encrypt API credentials.
        
        Args:
            credentials: Dictionary of credentials to encrypt and store
        """
        if not isinstance(credentials, dict):
            raise ValidationError("Credentials must be a dictionary")
        
        self.encrypted_credentials = credential_encryption.encrypt_credentials(credentials)
    
    def get_decrypted_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Get decrypted API credentials.
        
        Returns:
            Dictionary of decrypted credentials or None
        """
        if not self.encrypted_credentials:
            return None
        
        return credential_encryption.decrypt_credentials(self.encrypted_credentials)
    
    def update_sync_status(self, success: bool, error_message: str = "") -> None:
        """
        Update synchronization status after a sync attempt.
        
        Args:
            success: Whether the sync was successful
            error_message: Error message if sync failed
        """
        self.last_sync_at = timezone.now()
        self.last_sync_status = "success" if success else "failed"
        self.last_sync_error = error_message if not success else ""
        self.save(update_fields=['last_sync_at', 'last_sync_status', 'last_sync_error'])
    
    def get_connector(self):
        """
        Get the appropriate connector instance for this marketplace.
        
        Returns:
            Connector instance
        """
        from .connectors.factory import create_connector
        return create_connector(self)
    
    @property
    def is_sync_due(self) -> bool:
        """Check if automatic sync is due based on sync frequency."""
        if not self.is_auto_sync_enabled or not self.last_sync_at:
            return True
        
        minutes_since_sync = (timezone.now() - self.last_sync_at).total_seconds() / 60
        return minutes_since_sync >= self.sync_frequency_minutes
    
    def calculate_marketplace_fees(self, amount: Decimal) -> Dict[str, Decimal]:
        """
        Calculate marketplace fees for a given amount.
        
        Args:
            amount: Sale amount
            
        Returns:
            Dictionary with fee breakdown
        """
        commission = amount * (self.commission_percentage / 100)
        return {
            'commission': commission,
            'listing_fee': self.listing_fee,
            'total_fees': commission + self.listing_fee
        }


class MarketplaceListing(models.Model):
    """
    Represents a product listing on a specific marketplace.
    Links internal products to marketplace listings.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
        ('error', 'Error'),
        ('out_of_stock', 'Out of Stock'),
        ('ended', 'Ended'),
    ]
    
    # Listing type choices
    LISTING_TYPE_CHOICES = [
        ('fixed', 'Fixed Price'),
        ('auction', 'Auction'),
        ('variation', 'Variation/Multi-SKU'),
    ]
    
    # Relationships
    marketplace = models.ForeignKey(
        Marketplace,
        on_delete=models.CASCADE,
        related_name='listings'
    )
    
    # Marketplace identifiers
    marketplace_listing_id = models.CharField(
        max_length=255,
        help_text="Listing ID on the marketplace"
    )
    marketplace_sku = models.CharField(
        max_length=255,
        help_text="SKU used on the marketplace"
    )
    
    # Listing Information
    title = models.CharField(
        max_length=500,
        help_text="Listing title on marketplace"
    )
    description = models.TextField(
        blank=True,
        help_text="Listing description"
    )
    listing_type = models.CharField(
        max_length=20,
        choices=LISTING_TYPE_CHOICES,
        default='fixed'
    )
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Listing price on marketplace"
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sale/promotional price"
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost of goods sold"
    )
    
    # Inventory
    quantity_listed = models.IntegerField(
        default=0,
        help_text="Quantity available on marketplace"
    )
    quantity_sold = models.IntegerField(
        default=0,
        help_text="Total quantity sold"
    )
    
    # Category and Attributes
    marketplace_category_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Category ID on marketplace"
    )
    marketplace_category_name = models.CharField(
        max_length=500,
        blank=True,
        help_text="Category name on marketplace"
    )
    listing_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Marketplace-specific attributes"
    )
    
    # Media
    image_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of image URLs for the listing"
    )
    
    # Performance Metrics
    views = models.IntegerField(
        default=0,
        help_text="Number of listing views"
    )
    watchers = models.IntegerField(
        default=0,
        help_text="Number of watchers (if applicable)"
    )
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Conversion rate percentage"
    )
    
    # Status and Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    listing_url = models.URLField(
        blank=True,
        help_text="URL to view listing on marketplace"
    )
    
    # Dates
    listed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the listing went live"
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the listing ends (for auctions)"
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last sync with marketplace"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Last error message if any"
    )
    error_count = models.IntegerField(
        default=0,
        help_text="Number of consecutive errors"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_listings'
        unique_together = [['marketplace', 'marketplace_listing_id']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['marketplace', 'status']),
            models.Index(fields=['marketplace_sku']),
            models.Index(fields=['last_synced_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.marketplace.name}"
    
    @property
    def is_active(self) -> bool:
        """Check if listing is active and available."""
        return self.status == 'active' and self.quantity_listed > 0
    
    @property
    def profit_margin(self) -> Optional[Decimal]:
        """Calculate profit margin percentage."""
        if self.cost and self.price > 0:
            profit = self.price - self.cost
            fees = self.marketplace.calculate_marketplace_fees(self.price)['total_fees']
            net_profit = profit - fees
            return (net_profit / self.price) * 100
        return None
    
    def update_from_marketplace(self, data: Dict[str, Any]) -> None:
        """
        Update listing data from marketplace response.
        
        Args:
            data: Dictionary of listing data from marketplace
        """
        # Update fields based on marketplace data
        field_mapping = {
            'title': 'title',
            'description': 'description',
            'price': 'price',
            'quantity': 'quantity_listed',
            'status': 'status',
            'views': 'views',
            'category_id': 'marketplace_category_id',
            'category_name': 'marketplace_category_name',
        }
        
        for api_field, model_field in field_mapping.items():
            if api_field in data:
                setattr(self, model_field, data[api_field])
        
        self.last_synced_at = timezone.now()
        self.error_message = ""
        self.error_count = 0


class MarketplaceOrder(models.Model):
    """
    Represents an order from a marketplace.
    Tracks order lifecycle from marketplace to fulfillment.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('error', 'Error'),
    ]
    
    # Relationships
    marketplace = models.ForeignKey(
        Marketplace,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    # Order identifiers
    marketplace_order_id = models.CharField(
        max_length=255,
        help_text="Order ID from marketplace"
    )
    internal_order_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Internal order reference number"
    )
    
    # Customer Information
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=50, blank=True)
    
    # Shipping Address
    shipping_address = models.JSONField(
        default=dict,
        help_text="Complete shipping address"
    )
    billing_address = models.JSONField(
        default=dict,
        blank=True,
        help_text="Billing address if different from shipping"
    )
    
    # Order Details
    order_items = models.JSONField(
        default=list,
        help_text="List of order items with details"
    )
    
    # Financial
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Order subtotal before tax/shipping"
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total order amount"
    )
    marketplace_fees = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total fees charged by marketplace"
    )
    
    # Shipping Information
    shipping_method = models.CharField(
        max_length=255,
        blank=True,
        help_text="Selected shipping method"
    )
    tracking_number = models.CharField(
        max_length=255,
        blank=True,
        help_text="Shipment tracking number"
    )
    carrier = models.CharField(
        max_length=100,
        blank=True,
        help_text="Shipping carrier"
    )
    
    # Status and Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    marketplace_status = models.CharField(
        max_length=100,
        blank=True,
        help_text="Status on the marketplace"
    )
    
    # Important Dates
    ordered_at = models.DateTimeField(help_text="When order was placed")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Additional Data
    marketplace_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw order data from marketplace"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about the order"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last sync with marketplace"
    )
    
    class Meta:
        db_table = 'marketplace_orders'
        unique_together = [['marketplace', 'marketplace_order_id']]
        ordering = ['-ordered_at']
        indexes = [
            models.Index(fields=['marketplace', 'status']),
            models.Index(fields=['internal_order_number']),
            models.Index(fields=['ordered_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Order {self.internal_order_number} - {self.marketplace.name}"
    
    def save(self, *args, **kwargs):
        """Generate internal order number if not set."""
        if not self.internal_order_number:
            prefix = self.marketplace.order_prefix or self.marketplace.code.upper()
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.internal_order_number = f"{prefix}-{timestamp}"
        super().save(*args, **kwargs)
    
    @property
    def net_revenue(self) -> Decimal:
        """Calculate net revenue after marketplace fees."""
        return self.total_amount - self.marketplace_fees
    
    @property
    def is_fulfilled(self) -> bool:
        """Check if order has been fulfilled."""
        return self.status in ['shipped', 'delivered']
    
    def acknowledge_order(self) -> None:
        """Mark order as acknowledged."""
        self.status = 'acknowledged'
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['status', 'acknowledged_at', 'updated_at'])
    
    def mark_as_shipped(self, tracking_number: str, carrier: str) -> None:
        """
        Mark order as shipped with tracking information.
        
        Args:
            tracking_number: Shipment tracking number
            carrier: Shipping carrier name
        """
        self.status = 'shipped'
        self.tracking_number = tracking_number
        self.carrier = carrier
        self.shipped_at = timezone.now()
        self.save(update_fields=['status', 'tracking_number', 'carrier', 'shipped_at', 'updated_at'])


class MarketplaceInventory(models.Model):
    """
    Tracks inventory synchronization between internal stock and marketplace listings.
    Manages inventory allocation and updates across marketplaces.
    """
    
    # Sync status choices
    SYNC_STATUS_CHOICES = [
        ('synced', 'Synced'),
        ('pending', 'Pending Sync'),
        ('error', 'Sync Error'),
        ('manual', 'Manual Override'),
    ]
    
    # Relationships
    marketplace = models.ForeignKey(
        Marketplace,
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    listing = models.ForeignKey(
        MarketplaceListing,
        on_delete=models.CASCADE,
        related_name='inventory_records'
    )
    
    # SKU Mapping
    internal_sku = models.CharField(
        max_length=255,
        help_text="Internal product SKU"
    )
    marketplace_sku = models.CharField(
        max_length=255,
        help_text="SKU on marketplace"
    )
    
    # Inventory Levels
    available_quantity = models.IntegerField(
        default=0,
        help_text="Quantity available for sale"
    )
    reserved_quantity = models.IntegerField(
        default=0,
        help_text="Quantity reserved for pending orders"
    )
    marketplace_quantity = models.IntegerField(
        default=0,
        help_text="Quantity shown on marketplace"
    )
    buffer_quantity = models.IntegerField(
        default=0,
        help_text="Buffer to maintain between actual and listed"
    )
    
    # Sync Information
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='pending'
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful sync"
    )
    last_sync_error = models.TextField(
        blank=True,
        help_text="Error from last sync attempt"
    )
    sync_attempts = models.IntegerField(
        default=0,
        help_text="Number of sync attempts since last success"
    )
    
    # Override Settings
    manual_override = models.BooleanField(
        default=False,
        help_text="Manually override automatic sync"
    )
    override_quantity = models.IntegerField(
        null=True,
        blank=True,
        help_text="Manual override quantity"
    )
    override_reason = models.TextField(
        blank=True,
        help_text="Reason for manual override"
    )
    
    # Tracking
    quantity_changes = models.JSONField(
        default=list,
        blank=True,
        help_text="History of quantity changes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_inventory'
        unique_together = [['marketplace', 'marketplace_sku']]
        ordering = ['marketplace', 'internal_sku']
        indexes = [
            models.Index(fields=['sync_status']),
            models.Index(fields=['last_sync_at']),
            models.Index(fields=['internal_sku']),
        ]
    
    def __str__(self):
        return f"{self.internal_sku} on {self.marketplace.name}"
    
    @property
    def effective_quantity(self) -> int:
        """Get the effective quantity to list on marketplace."""
        if self.manual_override and self.override_quantity is not None:
            return self.override_quantity
        
        # Apply marketplace buffer setting
        buffer = self.buffer_quantity or self.marketplace.inventory_buffer
        return max(0, self.available_quantity - self.reserved_quantity - buffer)
    
    def log_quantity_change(self, old_qty: int, new_qty: int, reason: str) -> None:
        """
        Log inventory quantity changes.
        
        Args:
            old_qty: Previous quantity
            new_qty: New quantity
            reason: Reason for change
        """
        change_entry = {
            'timestamp': timezone.now().isoformat(),
            'old_quantity': old_qty,
            'new_quantity': new_qty,
            'reason': reason
        }
        
        if not isinstance(self.quantity_changes, list):
            self.quantity_changes = []
        
        self.quantity_changes.append(change_entry)
        # Keep only last 100 changes
        self.quantity_changes = self.quantity_changes[-100:]
    
    def sync_to_marketplace(self) -> bool:
        """
        Sync inventory quantity to marketplace.
        
        Returns:
            True if sync successful, False otherwise
        """
        try:
            connector = self.marketplace.get_connector()
            quantity = self.effective_quantity
            
            # Call marketplace API to update inventory
            success = connector.update_inventory(
                self.marketplace_sku,
                quantity
            )
            
            if success:
                self.marketplace_quantity = quantity
                self.sync_status = 'synced'
                self.last_sync_at = timezone.now()
                self.last_sync_error = ''
                self.sync_attempts = 0
            else:
                self.sync_status = 'error'
                self.sync_attempts += 1
                
            self.save()
            return success
            
        except Exception as e:
            self.sync_status = 'error'
            self.last_sync_error = str(e)
            self.sync_attempts += 1
            self.save()
            return False
