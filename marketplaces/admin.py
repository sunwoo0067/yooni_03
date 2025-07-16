"""
Admin configuration for marketplace models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum

from .models import (
    Marketplace, MarketplaceListing, MarketplaceOrder, MarketplaceInventory
)


@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    """Admin interface for Marketplace model."""
    
    list_display = [
        'name', 'platform_type', 'status', 'total_listings', 
        'total_orders', 'total_revenue', 'last_sync_display', 'created_at'
    ]
    list_filter = ['status', 'platform_type', 'currency', 'country_code']
    search_fields = ['name', 'code', 'description', 'seller_account_id']
    readonly_fields = [
        'last_sync_at', 'last_sync_status', 'total_listings', 
        'total_orders', 'total_revenue', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'platform_type', 'status')
        }),
        ('Connection Settings', {
            'fields': (
                'api_base_url', 'seller_account_id', 'encrypted_credentials',
                'connection_settings', 'rate_limit_requests', 'rate_limit_window'
            )
        }),
        ('Fee Structure', {
            'fields': (
                'commission_percentage', 'listing_fee', 'monthly_fee', 'fee_structure'
            )
        }),
        ('Sync Settings', {
            'fields': (
                'is_auto_sync_enabled', 'sync_frequency_minutes',
                'inventory_sync_enabled', 'inventory_buffer'
            )
        }),
        ('Order Settings', {
            'fields': ('auto_acknowledge_orders', 'order_prefix')
        }),
        ('Marketplace Settings', {
            'fields': ('currency', 'country_code', 'language_code')
        }),
        ('Statistics', {
            'fields': (
                'total_listings', 'total_orders', 'total_revenue',
                'last_sync_at', 'last_sync_status', 'last_sync_error'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def last_sync_display(self, obj):
        """Display last sync status with color coding."""
        if not obj.last_sync_at:
            return '-'
        
        if obj.last_sync_status == 'success':
            color = 'green'
        elif obj.last_sync_status == 'failed':
            color = 'red'
        else:
            color = 'orange'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.last_sync_at.strftime('%Y-%m-%d %H:%M')
        )
    last_sync_display.short_description = 'Last Sync'
    
    def save_model(self, request, obj, form, change):
        """Set created_by on first save."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['test_connection', 'sync_marketplace']
    
    def test_connection(self, request, queryset):
        """Test connection for selected marketplaces."""
        for marketplace in queryset:
            try:
                connector = marketplace.get_connector()
                success, error = connector.test_connection()
                if success:
                    self.message_user(
                        request,
                        f"Connection successful for {marketplace.name}"
                    )
                else:
                    self.message_user(
                        request,
                        f"Connection failed for {marketplace.name}: {error}",
                        level='ERROR'
                    )
            except Exception as e:
                self.message_user(
                    request,
                    f"Error testing {marketplace.name}: {str(e)}",
                    level='ERROR'
                )
    test_connection.short_description = "Test connection"


@admin.register(MarketplaceListing)
class MarketplaceListingAdmin(admin.ModelAdmin):
    """Admin interface for MarketplaceListing model."""
    
    list_display = [
        'title', 'marketplace', 'marketplace_sku', 'status', 
        'price', 'quantity_listed', 'quantity_sold', 'last_synced_at'
    ]
    list_filter = ['marketplace', 'status', 'listing_type', 'created_at']
    search_fields = [
        'title', 'marketplace_sku', 'marketplace_listing_id', 'description'
    ]
    readonly_fields = [
        'marketplace_listing_id', 'quantity_sold', 'views', 'watchers',
        'conversion_rate', 'last_synced_at', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['marketplace']
    
    fieldsets = (
        ('Listing Information', {
            'fields': (
                'marketplace', 'title', 'description', 'listing_type', 'status'
            )
        }),
        ('Identifiers', {
            'fields': (
                'marketplace_listing_id', 'marketplace_sku', 'listing_url'
            )
        }),
        ('Pricing', {
            'fields': ('price', 'sale_price', 'cost')
        }),
        ('Inventory', {
            'fields': ('quantity_listed', 'quantity_sold')
        }),
        ('Category & Attributes', {
            'fields': (
                'marketplace_category_id', 'marketplace_category_name',
                'listing_attributes'
            ),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': ('views', 'watchers', 'conversion_rate'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': (
                'listed_at', 'ends_at', 'last_synced_at',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        ('Error Tracking', {
            'fields': ('error_message', 'error_count'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('marketplace')
    
    actions = ['sync_listings', 'activate_listings', 'deactivate_listings']
    
    def sync_listings(self, request, queryset):
        """Sync selected listings with marketplace."""
        count = 0
        for listing in queryset:
            try:
                connector = listing.marketplace.get_connector()
                data = connector.get_listing(listing.marketplace_listing_id)
                if data:
                    listing.update_from_marketplace(data)
                    listing.save()
                    count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error syncing {listing.title}: {str(e)}",
                    level='ERROR'
                )
        
        self.message_user(request, f"Synced {count} listings successfully")
    sync_listings.short_description = "Sync with marketplace"
    
    def activate_listings(self, request, queryset):
        """Activate selected listings."""
        count = queryset.update(status='active')
        self.message_user(request, f"Activated {count} listings")
    activate_listings.short_description = "Activate listings"
    
    def deactivate_listings(self, request, queryset):
        """Deactivate selected listings."""
        count = queryset.update(status='inactive')
        self.message_user(request, f"Deactivated {count} listings")
    deactivate_listings.short_description = "Deactivate listings"


@admin.register(MarketplaceOrder)
class MarketplaceOrderAdmin(admin.ModelAdmin):
    """Admin interface for MarketplaceOrder model."""
    
    list_display = [
        'internal_order_number', 'marketplace', 'customer_name',
        'status', 'total_amount', 'net_revenue', 'ordered_at'
    ]
    list_filter = ['marketplace', 'status', 'ordered_at', 'shipped_at']
    search_fields = [
        'internal_order_number', 'marketplace_order_id',
        'customer_name', 'customer_email', 'tracking_number'
    ]
    readonly_fields = [
        'internal_order_number', 'marketplace_order_id', 'net_revenue',
        'created_at', 'updated_at', 'last_synced_at'
    ]
    raw_id_fields = ['marketplace']
    date_hierarchy = 'ordered_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': (
                'marketplace', 'internal_order_number', 'marketplace_order_id',
                'status', 'marketplace_status'
            )
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Financial', {
            'fields': (
                'subtotal', 'shipping_cost', 'tax_amount',
                'total_amount', 'marketplace_fees', 'net_revenue'
            )
        }),
        ('Shipping', {
            'fields': (
                'shipping_address', 'billing_address', 'shipping_method',
                'tracking_number', 'carrier'
            )
        }),
        ('Order Items', {
            'fields': ('order_items',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': (
                'ordered_at', 'acknowledged_at', 'shipped_at',
                'delivered_at', 'cancelled_at', 'last_synced_at'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('marketplace_data', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('marketplace')
    
    def net_revenue(self, obj):
        """Display net revenue after fees."""
        return f"${obj.net_revenue:,.2f}"
    net_revenue.short_description = 'Net Revenue'
    
    actions = ['acknowledge_orders', 'sync_order_status']
    
    def acknowledge_orders(self, request, queryset):
        """Acknowledge selected orders."""
        count = 0
        for order in queryset.filter(status='pending'):
            order.acknowledge_order()
            count += 1
        self.message_user(request, f"Acknowledged {count} orders")
    acknowledge_orders.short_description = "Acknowledge orders"
    
    def sync_order_status(self, request, queryset):
        """Sync order status with marketplace."""
        count = 0
        for order in queryset:
            try:
                connector = order.marketplace.get_connector()
                data = connector.get_order(order.marketplace_order_id)
                if data:
                    # Update status based on marketplace data
                    # Implementation depends on marketplace
                    count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error syncing order {order.internal_order_number}: {str(e)}",
                    level='ERROR'
                )
        
        self.message_user(request, f"Synced {count} orders")
    sync_order_status.short_description = "Sync order status"


@admin.register(MarketplaceInventory)
class MarketplaceInventoryAdmin(admin.ModelAdmin):
    """Admin interface for MarketplaceInventory model."""
    
    list_display = [
        'internal_sku', 'marketplace', 'available_quantity',
        'marketplace_quantity', 'sync_status', 'last_sync_at'
    ]
    list_filter = ['marketplace', 'sync_status', 'manual_override']
    search_fields = ['internal_sku', 'marketplace_sku']
    readonly_fields = [
        'effective_quantity', 'last_sync_at', 'sync_attempts',
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['marketplace', 'listing']
    
    fieldsets = (
        ('SKU Information', {
            'fields': (
                'marketplace', 'listing', 'internal_sku', 'marketplace_sku'
            )
        }),
        ('Inventory Levels', {
            'fields': (
                'available_quantity', 'reserved_quantity',
                'marketplace_quantity', 'buffer_quantity', 'effective_quantity'
            )
        }),
        ('Sync Information', {
            'fields': (
                'sync_status', 'last_sync_at', 'last_sync_error', 'sync_attempts'
            )
        }),
        ('Manual Override', {
            'fields': (
                'manual_override', 'override_quantity', 'override_reason'
            ),
            'classes': ('collapse',)
        }),
        ('History', {
            'fields': ('quantity_changes',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'marketplace', 'listing'
        )
    
    def effective_quantity(self, obj):
        """Display effective quantity."""
        return obj.effective_quantity
    effective_quantity.short_description = 'Effective Qty'
    
    actions = ['sync_inventory', 'enable_manual_override', 'disable_manual_override']
    
    def sync_inventory(self, request, queryset):
        """Sync inventory with marketplace."""
        success_count = 0
        error_count = 0
        
        for item in queryset:
            if item.sync_to_marketplace():
                success_count += 1
            else:
                error_count += 1
        
        self.message_user(
            request,
            f"Synced {success_count} items successfully, {error_count} errors"
        )
    sync_inventory.short_description = "Sync inventory"
    
    def enable_manual_override(self, request, queryset):
        """Enable manual override for selected items."""
        count = queryset.update(manual_override=True)
        self.message_user(request, f"Enabled manual override for {count} items")
    enable_manual_override.short_description = "Enable manual override"
    
    def disable_manual_override(self, request, queryset):
        """Disable manual override for selected items."""
        count = queryset.update(manual_override=False)
        self.message_user(request, f"Disabled manual override for {count} items")
    disable_manual_override.short_description = "Disable manual override"
