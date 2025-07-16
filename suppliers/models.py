"""
Supplier models for managing supplier integrations and product data.
"""
import json
from typing import Any, Dict, Optional

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .utils.encryption import credential_encryption


class Supplier(models.Model):
    """
    Represents a supplier/vendor that provides products.
    Stores connection settings and encrypted API credentials.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('testing', 'Testing'),
    ]
    
    # Connector type choices (can be extended)
    CONNECTOR_CHOICES = [
        ('api', 'REST API'),
        ('ftp', 'FTP/SFTP'),
        ('email', 'Email'),
        ('webhook', 'Webhook'),
        ('custom', 'Custom Integration'),
    ]
    
    # Basic Information
    name = models.CharField(
        max_length=255, 
        unique=True,
        help_text="Supplier company name"
    )
    code = models.SlugField(
        max_length=50, 
        unique=True,
        help_text="Unique identifier code for the supplier"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the supplier and their products"
    )
    
    # Connection Settings
    connector_type = models.CharField(
        max_length=20,
        choices=CONNECTOR_CHOICES,
        default='api',
        help_text="Type of integration connector"
    )
    api_base_url = models.URLField(
        blank=True,
        help_text="Base URL for API connections"
    )
    
    # Encrypted Credentials Storage
    encrypted_credentials = models.TextField(
        blank=True,
        help_text="Encrypted API credentials (API keys, tokens, etc.)"
    )
    
    # Connection Configuration
    connection_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional connection settings (headers, timeout, etc.)"
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
    
    # Status and Metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='inactive'
    )
    is_auto_sync_enabled = models.BooleanField(
        default=False,
        help_text="Enable automatic product synchronization"
    )
    sync_frequency_hours = models.IntegerField(
        default=24,
        help_text="Hours between automatic syncs"
    )
    
    # Contact Information
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website_url = models.URLField(blank=True)
    
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
    total_products = models.IntegerField(
        default=0,
        help_text="Total number of products from this supplier"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='suppliers_created'
    )
    
    class Meta:
        db_table = 'suppliers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
            models.Index(fields=['last_sync_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
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
        Get the appropriate connector instance for this supplier.
        
        Returns:
            Connector instance
        """
        from .connectors.factory import create_connector
        return create_connector(self)
    
    @property
    def is_sync_due(self) -> bool:
        """Check if automatic sync is due based on sync frequency."""
        if not self.is_auto_sync_enabled or not self.last_sync_at:
            return False
        
        hours_since_sync = (timezone.now() - self.last_sync_at).total_seconds() / 3600
        return hours_since_sync >= self.sync_frequency_hours


class SupplierProduct(models.Model):
    """
    Represents a product from a specific supplier.
    Stores supplier-specific product data and mappings.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('discontinued', 'Discontinued'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    # Relationships
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='products'
    )
    
    # Supplier-specific identifiers
    supplier_sku = models.CharField(
        max_length=255,
        help_text="SKU/ID used by the supplier"
    )
    supplier_name = models.CharField(
        max_length=500,
        help_text="Product name from supplier"
    )
    
    # Product Information
    description = models.TextField(blank=True)
    category = models.CharField(max_length=255, blank=True)
    subcategory = models.CharField(max_length=255, blank=True)
    brand = models.CharField(max_length=255, blank=True)
    
    # Pricing
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost price from supplier"
    )
    msrp = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Manufacturer's suggested retail price"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Currency code (e.g., USD, EUR)"
    )
    
    # Inventory
    quantity_available = models.IntegerField(
        default=0,
        help_text="Current available quantity"
    )
    min_order_quantity = models.IntegerField(
        default=1,
        help_text="Minimum order quantity"
    )
    lead_time_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Lead time in days for orders"
    )
    
    # Physical Attributes
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Weight in kg"
    )
    dimensions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dimensions (length, width, height) in cm"
    )
    
    # Additional Data
    supplier_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw data from supplier API"
    )
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional product attributes"
    )
    
    # Media
    image_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of product image URLs"
    )
    
    # Status and Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    last_updated_from_supplier = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time data was updated from supplier"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'supplier_products'
        unique_together = [['supplier', 'supplier_sku']]
        ordering = ['supplier', 'supplier_name']
        indexes = [
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['supplier_sku']),
            models.Index(fields=['last_updated_from_supplier']),
        ]
    
    def __str__(self):
        return f"{self.supplier_name} ({self.supplier_sku}) - {self.supplier.name}"
    
    def update_from_supplier_data(self, data: Dict[str, Any]) -> None:
        """
        Update product fields from supplier API data.
        
        Args:
            data: Dictionary of product data from supplier
        """
        # Update basic fields if present in data
        field_mapping = {
            'name': 'supplier_name',
            'description': 'description',
            'category': 'category',
            'subcategory': 'subcategory',
            'brand': 'brand',
            'price': 'cost_price',
            'msrp': 'msrp',
            'quantity': 'quantity_available',
            'min_order_qty': 'min_order_quantity',
            'weight': 'weight',
            'lead_time': 'lead_time_days',
        }
        
        for api_field, model_field in field_mapping.items():
            if api_field in data:
                setattr(self, model_field, data[api_field])
        
        # Store the complete data
        self.supplier_data = data
        self.last_updated_from_supplier = timezone.now()
    
    @property
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.quantity_available > 0 and self.status == 'active'
    
    @property
    def primary_image_url(self) -> Optional[str]:
        """Get the primary product image URL."""
        if self.image_urls and isinstance(self.image_urls, list) and len(self.image_urls) > 0:
            return self.image_urls[0]
        return None
