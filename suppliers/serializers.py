"""
Serializers for Supplier API endpoints.
"""
from rest_framework import serializers

from .models import Supplier, SupplierProduct


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for Supplier model."""
    
    total_products = serializers.IntegerField(read_only=True)
    is_sync_due = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'description', 'connector_type',
            'api_base_url', 'status', 'is_auto_sync_enabled',
            'sync_frequency_hours', 'last_sync_at', 'last_sync_status',
            'total_products', 'is_sync_due', 'contact_name', 
            'contact_email', 'website_url', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'last_sync_at', 'last_sync_status', 'total_products',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Create supplier with current user as creator."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class SupplierProductSerializer(serializers.ModelSerializer):
    """Serializer for SupplierProduct model."""
    
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    primary_image_url = serializers.CharField(read_only=True)
    
    class Meta:
        model = SupplierProduct
        fields = [
            'id', 'supplier', 'supplier_name', 'supplier_sku',
            'supplier_name', 'description', 'category', 'subcategory',
            'brand', 'cost_price', 'msrp', 'currency',
            'quantity_available', 'min_order_quantity', 'lead_time_days',
            'weight', 'dimensions', 'status', 'is_in_stock',
            'primary_image_url', 'image_urls', 'attributes',
            'last_updated_from_supplier', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'last_updated_from_supplier', 'created_at', 'updated_at'
        ]


class SupplierCredentialsSerializer(serializers.Serializer):
    """Serializer for setting supplier credentials."""
    
    credentials = serializers.DictField(
        help_text="Dictionary of API credentials (will be encrypted)"
    )
    
    def validate_credentials(self, value):
        """Validate credentials format."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Credentials must be a dictionary")
        
        # Add specific validation based on supplier type if needed
        return value


class SupplierSyncSerializer(serializers.Serializer):
    """Serializer for supplier sync operations."""
    
    sync_products = serializers.BooleanField(default=True)
    sync_inventory = serializers.BooleanField(default=True)
    sync_pricing = serializers.BooleanField(default=True)
    force = serializers.BooleanField(
        default=False,
        help_text="Force sync even if not due"
    )