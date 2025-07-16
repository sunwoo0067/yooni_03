"""
Serializers for marketplace models.
"""
from rest_framework import serializers
from .models import (
    Marketplace, MarketplaceListing, MarketplaceOrder, MarketplaceInventory
)


class MarketplaceSerializer(serializers.ModelSerializer):
    """Serializer for Marketplace model."""
    
    fee_total = serializers.SerializerMethodField()
    is_sync_due = serializers.ReadOnlyField()
    
    class Meta:
        model = Marketplace
        fields = [
            'id', 'name', 'code', 'description', 'platform_type',
            'api_base_url', 'seller_account_id', 'connection_settings',
            'commission_percentage', 'listing_fee', 'monthly_fee',
            'fee_structure', 'fee_total', 'rate_limit_requests',
            'rate_limit_window', 'inventory_sync_enabled', 'inventory_buffer',
            'auto_acknowledge_orders', 'order_prefix', 'status',
            'is_auto_sync_enabled', 'sync_frequency_minutes', 'currency',
            'country_code', 'language_code', 'last_sync_at', 'last_sync_status',
            'last_sync_error', 'total_listings', 'total_orders', 'total_revenue',
            'is_sync_due', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'last_sync_at', 'last_sync_status', 'last_sync_error',
            'total_listings', 'total_orders', 'total_revenue',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'code': {'validators': []},  # Handle lowercase conversion in model
        }
    
    def get_fee_total(self, obj):
        """Calculate total monthly fees."""
        return float(obj.monthly_fee + obj.listing_fee)
    
    def create(self, validated_data):
        """Handle credential setting on create."""
        credentials = self.initial_data.get('credentials')
        instance = super().create(validated_data)
        
        if credentials:
            instance.set_credentials(credentials)
            instance.save()
        
        return instance
    
    def update(self, instance, validated_data):
        """Handle credential setting on update."""
        credentials = self.initial_data.get('credentials')
        instance = super().update(instance, validated_data)
        
        if credentials:
            instance.set_credentials(credentials)
            instance.save()
        
        return instance


class MarketplaceListingSerializer(serializers.ModelSerializer):
    """Serializer for MarketplaceListing model."""
    
    marketplace_name = serializers.CharField(source='marketplace.name', read_only=True)
    is_active = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()
    
    class Meta:
        model = MarketplaceListing
        fields = [
            'id', 'marketplace', 'marketplace_name', 'marketplace_listing_id',
            'marketplace_sku', 'title', 'description', 'listing_type',
            'price', 'sale_price', 'cost', 'quantity_listed', 'quantity_sold',
            'marketplace_category_id', 'marketplace_category_name',
            'listing_attributes', 'image_urls', 'views', 'watchers',
            'conversion_rate', 'status', 'listing_url', 'listed_at',
            'ends_at', 'last_synced_at', 'error_message', 'error_count',
            'is_active', 'profit_margin', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'marketplace_listing_id', 'quantity_sold', 'views', 'watchers',
            'conversion_rate', 'last_synced_at', 'error_count',
            'created_at', 'updated_at'
        ]


class OrderItemSerializer(serializers.Serializer):
    """Serializer for order items."""
    
    sku = serializers.CharField()
    title = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


class MarketplaceOrderSerializer(serializers.ModelSerializer):
    """Serializer for MarketplaceOrder model."""
    
    marketplace_name = serializers.CharField(source='marketplace.name', read_only=True)
    net_revenue = serializers.ReadOnlyField()
    is_fulfilled = serializers.ReadOnlyField()
    order_items_detail = OrderItemSerializer(source='order_items', many=True, read_only=True)
    
    class Meta:
        model = MarketplaceOrder
        fields = [
            'id', 'marketplace', 'marketplace_name', 'marketplace_order_id',
            'internal_order_number', 'customer_name', 'customer_email',
            'customer_phone', 'shipping_address', 'billing_address',
            'order_items', 'order_items_detail', 'subtotal', 'shipping_cost',
            'tax_amount', 'total_amount', 'marketplace_fees', 'net_revenue',
            'shipping_method', 'tracking_number', 'carrier', 'status',
            'marketplace_status', 'ordered_at', 'acknowledged_at',
            'shipped_at', 'delivered_at', 'cancelled_at', 'marketplace_data',
            'notes', 'is_fulfilled', 'last_synced_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'internal_order_number', 'marketplace_order_id', 'net_revenue',
            'is_fulfilled', 'created_at', 'updated_at', 'last_synced_at'
        ]


class MarketplaceInventorySerializer(serializers.ModelSerializer):
    """Serializer for MarketplaceInventory model."""
    
    marketplace_name = serializers.CharField(source='marketplace.name', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    effective_quantity = serializers.ReadOnlyField()
    
    class Meta:
        model = MarketplaceInventory
        fields = [
            'id', 'marketplace', 'marketplace_name', 'listing', 'listing_title',
            'internal_sku', 'marketplace_sku', 'available_quantity',
            'reserved_quantity', 'marketplace_quantity', 'buffer_quantity',
            'effective_quantity', 'sync_status', 'last_sync_at',
            'last_sync_error', 'sync_attempts', 'manual_override',
            'override_quantity', 'override_reason', 'quantity_changes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'marketplace_quantity', 'effective_quantity', 'last_sync_at',
            'sync_attempts', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Validate inventory data."""
        if data.get('manual_override') and data.get('override_quantity') is None:
            raise serializers.ValidationError(
                "Override quantity is required when manual override is enabled"
            )
        return data