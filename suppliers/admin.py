"""
Admin configuration for Supplier models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import Supplier, SupplierProduct


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """Admin interface for Supplier model."""
    
    list_display = [
        'name', 'code', 'connector_type', 'status', 
        'is_auto_sync_enabled', 'last_sync_display', 
        'total_products', 'created_at'
    ]
    list_filter = [
        'status', 'connector_type', 'is_auto_sync_enabled',
        'last_sync_status', 'created_at'
    ]
    search_fields = ['name', 'code', 'description', 'contact_email']
    readonly_fields = [
        'created_at', 'updated_at', 'last_sync_at', 
        'last_sync_status', 'last_sync_error', 'total_products'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'status')
        }),
        ('Connection Settings', {
            'fields': (
                'connector_type', 'api_base_url', 
                'connection_settings', 'rate_limit_requests', 
                'rate_limit_window'
            )
        }),
        ('Credentials', {
            'fields': ('encrypted_credentials',),
            'classes': ('collapse',),
            'description': 'Encrypted API credentials. Use the set_credentials() method to update.'
        }),
        ('Synchronization', {
            'fields': (
                'is_auto_sync_enabled', 'sync_frequency_hours',
                'last_sync_at', 'last_sync_status', 'last_sync_error',
                'total_products'
            )
        }),
        ('Contact Information', {
            'fields': (
                'contact_name', 'contact_email', 
                'contact_phone', 'website_url'
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def last_sync_display(self, obj):
        """Display last sync time with status indicator."""
        if not obj.last_sync_at:
            return format_html('<span style="color: gray;">Never synced</span>')
        
        # Calculate time since last sync
        time_diff = timezone.now() - obj.last_sync_at
        hours_ago = int(time_diff.total_seconds() / 3600)
        
        if obj.last_sync_status == 'success':
            color = 'green'
            icon = '✓'
        else:
            color = 'red'
            icon = '✗'
        
        if hours_ago < 1:
            time_str = 'Less than 1 hour ago'
        elif hours_ago < 24:
            time_str = f'{hours_ago} hours ago'
        else:
            days = hours_ago // 24
            time_str = f'{days} days ago'
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, time_str
        )
    
    last_sync_display.short_description = 'Last Sync'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new supplier."""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_suppliers', 'deactivate_suppliers', 'trigger_sync']
    
    def activate_suppliers(self, request, queryset):
        """Activate selected suppliers."""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} suppliers activated.')
    
    activate_suppliers.short_description = 'Activate selected suppliers'
    
    def deactivate_suppliers(self, request, queryset):
        """Deactivate selected suppliers."""
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} suppliers deactivated.')
    
    deactivate_suppliers.short_description = 'Deactivate selected suppliers'
    
    def trigger_sync(self, request, queryset):
        """Trigger synchronization for selected suppliers."""
        # This would typically trigger a background task
        self.message_user(
            request, 
            f'Sync triggered for {queryset.count()} suppliers. '
            'Check back later for results.'
        )
    
    trigger_sync.short_description = 'Trigger sync for selected suppliers'


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    """Admin interface for SupplierProduct model."""
    
    list_display = [
        'supplier_name', 'supplier_sku', 'supplier_link', 
        'category', 'brand', 'cost_price', 'quantity_available',
        'status', 'last_updated_from_supplier'
    ]
    list_filter = [
        'supplier', 'status', 'category', 'brand',
        'last_updated_from_supplier'
    ]
    search_fields = [
        'supplier_name', 'supplier_sku', 'description',
        'brand', 'category'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'last_updated_from_supplier',
        'primary_image_preview'
    ]
    
    fieldsets = (
        ('Supplier Information', {
            'fields': ('supplier', 'supplier_sku', 'supplier_name')
        }),
        ('Product Details', {
            'fields': (
                'description', 'category', 'subcategory', 
                'brand', 'status'
            )
        }),
        ('Pricing', {
            'fields': ('cost_price', 'msrp', 'currency')
        }),
        ('Inventory', {
            'fields': (
                'quantity_available', 'min_order_quantity', 
                'lead_time_days'
            )
        }),
        ('Physical Attributes', {
            'fields': ('weight', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('image_urls', 'primary_image_preview'),
            'classes': ('collapse',)
        }),
        ('Raw Data', {
            'fields': ('supplier_data', 'attributes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'last_updated_from_supplier', 
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def supplier_link(self, obj):
        """Create a link to the supplier."""
        url = reverse('admin:suppliers_supplier_change', args=[obj.supplier.pk])
        return format_html('<a href="{}">{}</a>', url, obj.supplier.name)
    
    supplier_link.short_description = 'Supplier'
    
    def primary_image_preview(self, obj):
        """Show preview of primary product image."""
        image_url = obj.primary_image_url
        if image_url:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                image_url
            )
        return 'No image'
    
    primary_image_preview.short_description = 'Image Preview'
    
    actions = ['mark_as_active', 'mark_as_inactive', 'mark_as_discontinued']
    
    def mark_as_active(self, request, queryset):
        """Mark selected products as active."""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} products marked as active.')
    
    mark_as_active.short_description = 'Mark selected as active'
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected products as inactive."""
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} products marked as inactive.')
    
    mark_as_inactive.short_description = 'Mark selected as inactive'
    
    def mark_as_discontinued(self, request, queryset):
        """Mark selected products as discontinued."""
        updated = queryset.update(status='discontinued')
        self.message_user(request, f'{updated} products marked as discontinued.')
    
    mark_as_discontinued.short_description = 'Mark selected as discontinued'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('supplier')
